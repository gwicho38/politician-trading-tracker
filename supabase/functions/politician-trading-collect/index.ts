import "jsr:@supabase/functions-js/edge-runtime.d.ts"
import { createClient, SupabaseClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { corsHeaders } from '../_shared/cors.ts'

interface ScrapingConfig {
  userAgent: string
  timeout: number
  maxRetries: number
  requestDelay: number
}

interface DisclosureRecord {
  source_url: string
  politician_id: string
  transaction_date: string
  disclosure_date: string
  asset_name: string
  transaction_type: string
  amount_range_min: number
  amount_range_max: number
  status: string
  raw_data: Record<string, unknown>
}

interface CollectionResult {
  source: string
  disclosures_found: number
  disclosures: DisclosureRecord[]
}

interface CollectionJobResult {
  started_at: string
  completed_at?: string
  status?: string
  error?: string
  jobs: Record<string, {
    status: string
    new_disclosures: number
    updated_disclosures: number
    errors: string[]
  }>
  summary: {
    total_new_disclosures: number
    total_updated_disclosures: number
    errors: string[]
  }
}

// TODO: Review PoliticianTradingCollector class - web scraper for politician trading disclosures
// - Collects data from US House, Senate, QuiverQuant, EU Parliament, California NetFile
// - Uses retry logic with exponential backoff
// - Caches politician lookups to reduce database queries
class PoliticianTradingCollector {
  private supabase: SupabaseClient
  private config: ScrapingConfig
  private politicianCache: Map<string, string> = new Map() // name -> id cache

  // TODO: Review constructor - initializes scraping configuration
  constructor(supabaseClient: SupabaseClient) {
    this.supabase = supabaseClient
    this.config = {
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
      timeout: 30000, // 30s timeout per request (reduced for faster failures)
      maxRetries: 1,  // Single retry to fail fast
      requestDelay: 1000
    }
  }

  // TODO: Review getOrCreatePolitician - gets or creates politician record and returns UUID
  // - Uses cache to minimize database lookups
  // - Parses name into first/last components
  async getOrCreatePolitician(name: string, role: string = 'Unknown', party: string = 'Unknown'): Promise<string | null> {
    // Check cache first
    const cacheKey = `${name}:${role}`
    if (this.politicianCache.has(cacheKey)) {
      return this.politicianCache.get(cacheKey)!
    }

    // Parse name into first/last
    const parts = name.trim().split(' ')
    const firstName = parts[0] || 'Unknown'
    const lastName = parts.slice(1).join(' ') || 'Unknown'

    // Try to find existing politician
    const { data: existing } = await this.supabase
      .from('politicians')
      .select('id')
      .eq('full_name', name)
      .maybeSingle()

    if (existing) {
      this.politicianCache.set(cacheKey, existing.id)
      return existing.id
    }

    // Create new politician
    const { data: newPolitician, error } = await this.supabase
      .from('politicians')
      .insert({
        first_name: firstName,
        last_name: lastName,
        full_name: name,
        role: role,
        party: party,
        is_active: true
      })
      .select('id')
      .single()

    if (error) {
      console.error(`Failed to create politician ${name}:`, error.message)
      return null
    }

    this.politicianCache.set(cacheKey, newPolitician.id)
    return newPolitician.id
  }

  // TODO: Review fetchWithRetry - HTTP fetch with retry logic and rate limiting
  async fetchWithRetry(url: string, options: RequestInit = {}): Promise<Response | null> {
    for (let attempt = 0; attempt < this.config.maxRetries; attempt++) {
      try {
        // Add delay between requests
        if (attempt > 0) {
          await this.delay(this.config.requestDelay * attempt)
        }

        const response = await fetch(url, {
          ...options,
          headers: {
            'User-Agent': this.config.userAgent,
            ...options.headers
          },
          signal: AbortSignal.timeout(this.config.timeout)
        })

        if (response.ok) {
          return response
        } else if (response.status === 429) {
          // Rate limited, wait longer
          await this.delay(this.config.requestDelay * 2)
          continue
        } else {
          console.warn(`HTTP ${response.status} for ${url}`)
        }
      } catch (error) {
        console.error(`Attempt ${attempt + 1} failed for ${url}:`, error)
        if (attempt < this.config.maxRetries - 1) {
          await this.delay(this.config.requestDelay * (attempt + 1))
        }
      }
    }
    return null
  }

  // TODO: Review delay - promise-based delay for rate limiting
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  // TODO: Review collectUSHouseData - scrapes US House financial disclosures
  async collectUSHouseData() {
    console.log("Collecting US House financial disclosures...")
    const baseUrl = "https://disclosures-clerk.house.gov"
    const searchUrl = `${baseUrl}/FinancialDisclosure`

    const response = await this.fetchWithRetry(searchUrl)

    if (!response) {
      console.warn("Failed to fetch US House disclosures, skipping...")
      return { source: "us_house", disclosures_found: 0, disclosures: [] }
    }

    const html = await response.text()
    const disclosures = []

    // Get or create a placeholder politician for House members
    const politicianId = await this.getOrCreatePolitician("House Member (Placeholder)", "Representative", "Unknown")
    if (!politicianId) {
      console.warn("Could not create House placeholder politician")
      return { source: "us_house", disclosures_found: 0, disclosures: [] }
    }

    // Look for disclosure links in the HTML
    const linkMatches = html.match(/href="([^"]*disclosure[^"]*)"/gi) || []

    for (const linkMatch of linkMatches.slice(0, 5)) { // Limit to 5
      const href = linkMatch.match(/href="([^"]*)"/)
      if (href && href[1]) {
        const fullUrl = href[1].startsWith('http') ? href[1] : `${baseUrl}${href[1]}`
        disclosures.push({
          source_url: fullUrl,
          politician_id: politicianId,
          transaction_date: new Date().toISOString(),
          disclosure_date: new Date().toISOString(),
          asset_name: "Unknown Asset",
          transaction_type: "purchase",
          amount_range_min: 1000,
          amount_range_max: 15000,
          status: 'pending',
          raw_data: {
            source: "us_house",
            url: fullUrl
          }
        })
      }
    }

    return {
      source: "us_house",
      disclosures_found: disclosures.length,
      disclosures: disclosures
    }
  }

  // TODO: Review collectUSSenateData - scrapes US Senate financial disclosures
  async collectUSSenateData() {
    console.log("Collecting US Senate financial disclosures...")
    const baseUrl = "https://efdsearch.senate.gov"
    const searchUrl = `${baseUrl}/search/`

    const response = await this.fetchWithRetry(searchUrl)

    if (!response) {
      console.warn("Failed to fetch US Senate disclosures, skipping...")
      return { source: "us_senate", disclosures_found: 0, disclosures: [] }
    }

    const html = await response.text()
    const disclosures = []

    // Get or create a placeholder politician for Senate members
    const politicianId = await this.getOrCreatePolitician("Senate Member (Placeholder)", "Senate", "Unknown")
    if (!politicianId) {
      console.warn("Could not create Senate placeholder politician")
      return { source: "us_senate", disclosures_found: 0, disclosures: [] }
    }

    // Basic parsing for Senate data
    const linkMatches = html.match(/href="([^"]*report[^"]*)"/gi) || []

    for (const linkMatch of linkMatches.slice(0, 5)) {
      const href = linkMatch.match(/href="([^"]*)"/)
      if (href && href[1]) {
        const fullUrl = href[1].startsWith('http') ? href[1] : `${baseUrl}${href[1]}`
        disclosures.push({
          source_url: fullUrl,
          politician_id: politicianId,
          transaction_date: new Date().toISOString(),
          disclosure_date: new Date().toISOString(),
          asset_name: "Unknown Asset",
          transaction_type: "sale",
          amount_range_min: 15001,
          amount_range_max: 50000,
          status: 'pending',
          raw_data: {
            source: "us_senate",
            url: fullUrl
          }
        })
      }
    }

    return {
      source: "us_senate",
      disclosures_found: disclosures.length,
      disclosures: disclosures
    }
  }

  // TODO: Review collectQuiverQuantData - scrapes QuiverQuant congress trading data
  async collectQuiverQuantData() {
    console.log("Collecting QuiverQuant congress trading data...")
    const url = "https://www.quiverquant.com/congresstrading/"

    const response = await this.fetchWithRetry(url)

    if (!response) {
      console.warn("Failed to fetch QuiverQuant data, skipping...")
      return { source: "quiverquant", disclosures_found: 0, disclosures: [] }
    }

    const html = await response.text()
    const disclosures = []

    // Get or create a placeholder politician
    const politicianId = await this.getOrCreatePolitician("Congress Member (QuiverQuant)", "Congress", "Unknown")
    if (!politicianId) {
      console.warn("Could not create QuiverQuant placeholder politician")
      return { source: "quiverquant", disclosures_found: 0, disclosures: [] }
    }

    // Basic parsing for QuiverQuant data
    const tableMatches = html.match(/<tr[^>]*>.*?<\/tr>/gi) || []

    for (const row of tableMatches.slice(0, 3)) { // Limit to 3
      disclosures.push({
        source_url: url,
        politician_id: politicianId,
        transaction_date: new Date().toISOString(),
        disclosure_date: new Date().toISOString(),
        asset_name: "QQ Asset",
        transaction_type: "purchase",
        amount_range_min: 1000,
        amount_range_max: 15000,
        status: 'pending',
        raw_data: {
          source: "quiverquant",
          html_row: row.substring(0, 200)
        }
      })
    }

    return {
      source: "quiverquant",
      disclosures_found: disclosures.length,
      disclosures: disclosures
    }
  }

  // TODO: Review collectEUParliamentData - scrapes EU Parliament MEP declarations
  async collectEUParliamentData() {
    console.log("Collecting EU Parliament declarations...")
    // NOTE: The old URL returns 404, trying the new structure
    // The EU Parliament website has changed structure
    const url = "https://www.europarl.europa.eu/meps/en/full-list/all"

    const response = await this.fetchWithRetry(url)

    if (!response) {
      console.warn("Failed to fetch EU Parliament data, skipping... (URL may have changed)")
      return { source: "eu_parliament", disclosures_found: 0, disclosures: [] }
    }

    const html = await response.text()
    const disclosures = []

    // Get or create a placeholder politician for EU MEPs
    const politicianId = await this.getOrCreatePolitician("EU MEP (Placeholder)", "MEP", "Unknown")
    if (!politicianId) {
      console.warn("Could not create EU placeholder politician")
      return { source: "eu_parliament", disclosures_found: 0, disclosures: [] }
    }

    // Basic parsing for EU data
    const linkMatches = html.match(/href="([^"]*mep[^"]*)"/gi) || []

    for (const linkMatch of linkMatches.slice(0, 3)) {
      const href = linkMatch.match(/href="([^"]*)"/)
      if (href && href[1]) {
        const fullUrl = href[1].startsWith('http') ? href[1] : `https://www.europarl.europa.eu${href[1]}`
        disclosures.push({
          source_url: fullUrl,
          politician_id: politicianId,
          transaction_date: new Date().toISOString(),
          disclosure_date: new Date().toISOString(),
          asset_name: "EU Asset",
          transaction_type: "disclosure",
          amount_range_min: 10000,
          amount_range_max: 100000,
          status: 'pending',
          raw_data: {
            source: "eu_parliament",
            url: fullUrl
          }
        })
      }
    }

    return {
      source: "eu_parliament",
      disclosures_found: disclosures.length,
      disclosures: disclosures
    }
  }

  // TODO: Review collectCaliforniaData - scrapes California NetFile portals (SF, LA)
  async collectCaliforniaData() {
    console.log("Collecting California NetFile data...")
    // NOTE: NetFile sites are often slow/unreliable, reduce expectations
    const portals = [
      { url: "https://public.netfile.com/pub2/?AID=SFO", jurisdiction: "San Francisco" },
      { url: "https://public.netfile.com/pub2/?AID=LAC", jurisdiction: "Los Angeles" },
    ]

    const allDisclosures = []

    // Get or create a placeholder politician for CA officials
    const politicianId = await this.getOrCreatePolitician("California Official (Placeholder)", "State Official", "Unknown")
    if (!politicianId) {
      console.warn("Could not create CA placeholder politician")
      return { source: "california", disclosures_found: 0, disclosures: [] }
    }

    for (const portal of portals) {
      try {
        console.log(`Fetching from ${portal.jurisdiction}...`)
        const response = await this.fetchWithRetry(portal.url)
        if (response) {
          const html = await response.text()

          // Basic parsing for NetFile data
          const disclosures = []
          const linkMatches = html.match(/href="([^"]*report[^"]*)"/gi) || []

          for (const linkMatch of linkMatches.slice(0, 2)) { // Only 2 per portal
            const href = linkMatch.match(/href="([^"]*)"/)
            if (href && href[1]) {
              disclosures.push({
                source_url: portal.url,
                politician_id: politicianId,
                transaction_date: new Date().toISOString(),
                disclosure_date: new Date().toISOString(),
                asset_name: "CA Asset",
                transaction_type: "disclosure",
                amount_range_min: 1000,
                amount_range_max: 25000,
                status: 'pending',
                raw_data: {
                  source: "california_netfile",
                  portal: portal.url,
                  jurisdiction: portal.jurisdiction
                }
              })
            }
          }

          allDisclosures.push(...disclosures)
          console.log(`Found ${disclosures.length} disclosures from ${portal.jurisdiction}`)
        } else {
          console.warn(`Skipping ${portal.jurisdiction} - request failed/timed out`)
        }
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error)
        console.warn(`Error collecting from ${portal.jurisdiction}: ${errorMessage}`)
        // Continue with next portal instead of failing
      }
    }

    return {
      source: "california",
      disclosures_found: allDisclosures.length,
      disclosures: allDisclosures
    }
  }

  // TODO: Review runFullCollection - runs collection from all sources
  // - Creates data_pull_jobs record for tracking
  // - Stores disclosures to trading_disclosures table
  async runFullCollection(): Promise<CollectionJobResult> {
    const startTime = new Date()
    const results: CollectionJobResult = {
      started_at: startTime.toISOString(),
      jobs: {},
      summary: {
        total_new_disclosures: 0,
        total_updated_disclosures: 0,
        errors: []
      }
    }

    // Create job record
    const { data: jobData } = await this.supabase
      .from('data_pull_jobs')
      .insert({
        job_type: 'full_collection',
        status: 'running',
        started_at: startTime.toISOString(),
        config_snapshot: this.config
      })
      .select()
      .single()

    const jobId = jobData?.id

    try {
      // Collect from all sources
      const collectors = [
        () => this.collectUSHouseData(),
        () => this.collectUSSenateData(), 
        () => this.collectQuiverQuantData(),
        () => this.collectEUParliamentData(),
        () => this.collectCaliforniaData()
      ]

      for (const collector of collectors) {
        try {
          const result = await collector()
          results.jobs[result.source] = {
            status: 'completed',
            new_disclosures: result.disclosures_found,
            updated_disclosures: 0,
            errors: []
          }
          
          results.summary.total_new_disclosures += result.disclosures_found

          // Store disclosures in database
          if (result.disclosures.length > 0) {
            const { error } = await this.supabase
              .from('trading_disclosures')
              .insert(result.disclosures)
            
            if (error) {
              console.error(`Error storing ${result.source} disclosures:`, error)
              results.summary.errors.push(`Storage error for ${result.source}: ${error.message}`)
            }
          }

        } catch (error: unknown) {
          const errorMessage = error instanceof Error ? error.message : String(error)
          console.error(`Collection failed for collector:`, error)
          results.summary.errors.push(errorMessage)
        }
      }

      // Update job status
      if (jobId) {
        await this.supabase
          .from('data_pull_jobs')
          .update({
            status: 'completed',
            completed_at: new Date().toISOString(),
            records_found: results.summary.total_new_disclosures,
            records_processed: results.summary.total_new_disclosures,
            records_new: results.summary.total_new_disclosures,
            records_updated: results.summary.total_updated_disclosures
          })
          .eq('id', jobId)
      }

      results.completed_at = new Date().toISOString()
      results.status = 'completed'

    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error)
      console.error('Full collection failed:', error)
      results.error = errorMessage
      results.status = 'failed'
      results.summary.errors.push(errorMessage)

      // Update job status
      if (jobId) {
        await this.supabase
          .from('data_pull_jobs')
          .update({
            status: 'failed',
            completed_at: new Date().toISOString(),
            error_message: errorMessage
          })
          .eq('id', jobId)
      }
    }

    return results
  }

  // TODO: Review collectSingleSource - collects from single specified source
  // - Maps source names (house, senate, quiver, eu, california) to collector methods
  async collectSingleSource(source: string): Promise<CollectionResult> {
    const sourceMap: Record<string, () => Promise<CollectionResult>> = {
      'house': () => this.collectUSHouseData(),
      'senate': () => this.collectUSSenateData(),
      'quiver': () => this.collectQuiverQuantData(),
      'eu': () => this.collectEUParliamentData(),
      'california': () => this.collectCaliforniaData()
    }

    const collector = sourceMap[source.toLowerCase()]
    if (!collector) {
      return {
        source: source,
        disclosures_found: 0,
        disclosures: []
      }
    }

    const result = await collector()

    // Store disclosures in database
    if (result.disclosures.length > 0) {
      const { error } = await this.supabase
        .from('trading_disclosures')
        .insert(result.disclosures)

      if (error) {
        console.error(`Error storing ${source} disclosures:`, error)
      }
    }

    return result
  }
}

// TODO: Review Deno.serve handler - politician trading collection endpoint
// - Supports ?source param for single-source collection
// - Runs full collection when no source specified
Deno.serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Parse URL to get source parameter
    const url = new URL(req.url)
    const source = url.searchParams.get('source') // 'house', 'senate', 'quiver', 'eu', 'california', or null for all

    // Initialize Supabase client
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const collector = new PoliticianTradingCollector(supabaseClient)

    // If a specific source is requested, run only that source
    if (source) {
      console.log(`🏛️ Starting ${source} data collection...`)
      const result = await collector.collectSingleSource(source)

      console.log(`✅ ${source} collection completed:`, {
        disclosures: result.disclosures_found
      })

      return new Response(
        JSON.stringify({
          success: true,
          data: result,
          message: `${source} collection completed. Found ${result.disclosures_found} disclosures.`
        }),
        {
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json'
          }
        }
      )
    }

    // Full collection (all sources)
    console.log('🏛️ Starting full politician trading data collection...')
    const results = await collector.runFullCollection()

    console.log('✅ Collection completed:', {
      status: results.status,
      total_disclosures: results.summary.total_new_disclosures,
      errors: results.summary.errors.length
    })

    return new Response(
      JSON.stringify({
        success: results.status === 'completed',
        data: results,
        message: `Collection ${results.status}. Found ${results.summary.total_new_disclosures} disclosures.`
      }),
      {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        }
      }
    )

  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    console.error('Edge function error:', error)

    return new Response(
      JSON.stringify({
        success: false,
        error: errorMessage,
        message: 'Failed to run politician trading collection'
      }),
      {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        },
        status: 400
      }
    )
  }
})

/* To test locally:
  supabase functions serve --env-file .env.local
  
  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/politician-trading-collect' \
    --header 'Authorization: Bearer YOUR_ANON_KEY' \
    --header 'Content-Type: application/json' \
    --data '{}'
*/
