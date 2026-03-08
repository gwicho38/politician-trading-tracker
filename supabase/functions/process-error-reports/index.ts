import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders } from '../_shared/cors.ts'

interface ErrorReport {
  id: string
  disclosure_id: string
  error_type: string
  description: string
  disclosure_snapshot: Record<string, any>
  status: string
}

interface CorrectionResult {
  field: string
  old_value: any
  new_value: any
  confidence: number
  reasoning: string
}

interface ProcessingResult {
  report_id: string
  status: 'fixed' | 'needs_review' | 'invalid' | 'error'
  corrections: CorrectionResult[]
  admin_notes: string
}

interface OllamaConfig {
  baseUrl: string
  apiKey: string
  model: string
}

const log = {
  info: (message: string, metadata?: any) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      service: 'process-error-reports',
      message,
      ...metadata
    }))
  },
  error: (message: string, error?: any, metadata?: any) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      service: 'process-error-reports',
      message,
      error: error?.message || error,
      ...metadata
    }))
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const ollamaBaseUrl = Deno.env.get('OLLAMA_API_BASE')
    if (!ollamaBaseUrl) {
      throw new Error('OLLAMA_API_BASE not configured')
    }

    const ollama: OllamaConfig = {
      baseUrl: ollamaBaseUrl,
      apiKey: Deno.env.get('OLLAMA_API_KEY') ?? '',
      model: Deno.env.get('OLLAMA_MODEL') ?? 'llama3.1:8b',
    }

    const url = new URL(req.url)
    const path = url.pathname.split('/').pop()

    let response: Response

    switch (path) {
      case 'process-pending':
        response = await handleProcessPending(supabase, ollama)
        break
      case 'process-one':
        const body = await req.json()
        response = await handleProcessOne(supabase, ollama, body.report_id)
        break
      case 'preview':
        const previewBody = await req.json()
        response = await handlePreview(supabase, ollama, previewBody.report_id)
        break
      default:
        response = new Response(
          JSON.stringify({ error: 'Invalid endpoint. Use: process-pending, process-one, preview' }),
          { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
        )
    }

    return response

  } catch (error) {
    log.error('Edge function error', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
})

async function handleProcessPending(supabase: any, ollama: OllamaConfig): Promise<Response> {
  log.info('Processing all pending error reports')

  const { data: reports, error } = await supabase
    .from('user_error_reports')
    .select('*')
    .eq('status', 'pending')
    .order('created_at', { ascending: true })
    .limit(10)

  if (error) {
    throw new Error(`Failed to fetch reports: ${error.message}`)
  }

  if (!reports || reports.length === 0) {
    return new Response(
      JSON.stringify({ success: true, message: 'No pending reports', processed: 0 }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  log.info('Found pending reports', { count: reports.length })

  const results: ProcessingResult[] = []

  for (const report of reports) {
    try {
      const result = await processReport(supabase, ollama, report)
      results.push(result)
    } catch (e) {
      log.error('Failed to process report', e, { reportId: report.id })
      results.push({
        report_id: report.id,
        status: 'error',
        corrections: [],
        admin_notes: `Processing error: ${e.message}`
      })
    }
  }

  const fixed = results.filter(r => r.status === 'fixed').length
  const needsReview = results.filter(r => r.status === 'needs_review').length

  return new Response(
    JSON.stringify({ success: true, processed: results.length, fixed, needs_review: needsReview, results }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function handleProcessOne(supabase: any, ollama: OllamaConfig, reportId: string): Promise<Response> {
  if (!reportId) {
    return new Response(
      JSON.stringify({ error: 'report_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: report, error } = await supabase
    .from('user_error_reports')
    .select('*')
    .eq('id', reportId)
    .single()

  if (error || !report) {
    return new Response(
      JSON.stringify({ error: 'Report not found' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const result = await processReport(supabase, ollama, report)

  return new Response(
    JSON.stringify({ success: true, result }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function handlePreview(supabase: any, ollama: OllamaConfig, reportId: string): Promise<Response> {
  if (!reportId) {
    return new Response(
      JSON.stringify({ error: 'report_id is required' }),
      { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const { data: report, error } = await supabase
    .from('user_error_reports')
    .select('*')
    .eq('id', reportId)
    .single()

  if (error || !report) {
    return new Response(
      JSON.stringify({ error: 'Report not found' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }

  const corrections = await interpretCorrections(ollama, report)

  return new Response(
    JSON.stringify({
      success: true,
      preview: true,
      report_id: reportId,
      error_type: report.error_type,
      user_description: report.description,
      current_values: report.disclosure_snapshot,
      proposed_corrections: corrections,
      would_auto_fix: corrections.every(c => c.confidence >= 0.8)
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function processReport(supabase: any, ollama: OllamaConfig, report: ErrorReport): Promise<ProcessingResult> {
  log.info('Processing report', { reportId: report.id, errorType: report.error_type })

  const corrections = await interpretCorrections(ollama, report)

  if (corrections.length === 0) {
    await updateReportStatus(supabase, report.id, 'reviewed', 'Could not automatically determine correction from description')
    return {
      report_id: report.id,
      status: 'needs_review',
      corrections: [],
      admin_notes: 'Could not automatically determine correction from description'
    }
  }

  const allHighConfidence = corrections.every(c => c.confidence >= 0.8)

  if (!allHighConfidence) {
    const notes = corrections.map(c =>
      `${c.field}: ${c.old_value} → ${c.new_value} (confidence: ${(c.confidence * 100).toFixed(0)}%)`
    ).join('; ')
    await updateReportStatus(supabase, report.id, 'reviewed', `Low confidence corrections suggested: ${notes}`)
    return {
      report_id: report.id,
      status: 'needs_review',
      corrections,
      admin_notes: `Suggested corrections need human review due to low confidence`
    }
  }

  const updateData: Record<string, any> = {}
  for (const correction of corrections) {
    updateData[correction.field] = correction.new_value
  }
  updateData.updated_at = new Date().toISOString()

  const { error: updateError } = await supabase
    .from('trading_disclosures')
    .update(updateData)
    .eq('id', report.disclosure_id)

  if (updateError) {
    log.error('Failed to apply correction', updateError, { reportId: report.id })
    await updateReportStatus(supabase, report.id, 'reviewed', `Failed to apply correction: ${updateError.message}`)
    return {
      report_id: report.id,
      status: 'error',
      corrections,
      admin_notes: `Database update failed: ${updateError.message}`
    }
  }

  const sourceUrl = report.disclosure_snapshot.source_url
  if (sourceUrl) {
    await applyToRelatedDisclosures(supabase, report.disclosure_id, sourceUrl, updateData, corrections)
  }

  const correctionSummary = corrections.map(c =>
    `${c.field}: ${c.old_value} → ${c.new_value}`
  ).join('; ')

  await updateReportStatus(supabase, report.id, 'fixed', `Auto-corrected: ${correctionSummary}`)

  log.info('Report processed successfully', { reportId: report.id, corrections: corrections.length })

  return {
    report_id: report.id,
    status: 'fixed',
    corrections,
    admin_notes: `Auto-corrected: ${correctionSummary}`
  }
}

// Uses Ollama's OpenAI-compatible /v1/chat/completions endpoint
async function interpretCorrections(ollama: OllamaConfig, report: ErrorReport): Promise<CorrectionResult[]> {
  const prompt = `You are analyzing a user-submitted error report for a financial disclosure database record.

ERROR REPORT:
- Error Type: ${report.error_type}
- User Description: "${report.description}"

CURRENT DISCLOSURE DATA:
${JSON.stringify(report.disclosure_snapshot, null, 2)}

TASK:
Based on the user's description, determine what field(s) need to be corrected and what the new value(s) should be.

FIELD MAPPING:
- wrong_amount → amount_range_min and/or amount_range_max (numeric values in dollars, no commas)
- wrong_date → transaction_date or disclosure_date (ISO 8601 format: YYYY-MM-DD)
- wrong_ticker → asset_ticker (uppercase stock symbol)
- wrong_politician → politician_name or politician_party
- other → any field

RESPONSE FORMAT (JSON only, no markdown):
{
  "corrections": [
    {
      "field": "field_name",
      "old_value": <current value from snapshot>,
      "new_value": <corrected value>,
      "confidence": <0.0 to 1.0>,
      "reasoning": "brief explanation"
    }
  ]
}

RULES:
1. Parse dollar amounts like "$5,000,001 - $25,000,000" into numeric min/max values
2. Confidence should be 0.9+ only if the user clearly states the correct value
3. Confidence should be 0.5-0.8 if you're inferring the correction
4. Return empty corrections array if you cannot determine what to fix
5. For amount ranges, always provide BOTH amount_range_min and amount_range_max

Respond with ONLY the JSON object, no other text.`

  try {
    const response = await fetch(`${ollama.baseUrl}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${ollama.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: ollama.model,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 1024,
        temperature: 0,
      }),
    })

    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.status} ${await response.text()}`)
    }

    const data = await response.json()
    const text = data.choices?.[0]?.message?.content ?? ''

    // Strip markdown code fences if present
    const cleaned = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim()
    const result = JSON.parse(cleaned)
    return result.corrections || []

  } catch (e) {
    log.error('LLM interpretation failed', e)
    return []
  }
}

async function applyToRelatedDisclosures(
  supabase: any,
  excludeId: string,
  sourceUrl: string,
  updateData: Record<string, any>,
  corrections: CorrectionResult[]
): Promise<void> {
  const amountCorrections = corrections.filter(c =>
    c.field === 'amount_range_min' || c.field === 'amount_range_max'
  )

  if (amountCorrections.length === 0) return

  const { data: related, error } = await supabase
    .from('trading_disclosures')
    .select('id')
    .eq('source_url', sourceUrl)
    .neq('id', excludeId)
    .is('amount_range_min', null)

  if (error || !related || related.length === 0) return

  log.info('Applying corrections to related disclosures', { count: related.length, sourceUrl })

  const amountUpdate: Record<string, any> = {}
  for (const c of amountCorrections) {
    amountUpdate[c.field] = c.new_value
  }
  amountUpdate.updated_at = new Date().toISOString()

  for (const record of related) {
    await supabase
      .from('trading_disclosures')
      .update(amountUpdate)
      .eq('id', record.id)
  }
}

async function updateReportStatus(
  supabase: any,
  reportId: string,
  status: 'pending' | 'reviewed' | 'fixed' | 'invalid',
  adminNotes: string
): Promise<void> {
  await supabase
    .from('user_error_reports')
    .update({
      status,
      admin_notes: adminNotes,
      updated_at: new Date().toISOString()
    })
    .eq('id', reportId)
}
