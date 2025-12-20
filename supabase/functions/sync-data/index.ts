import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

// =============================================================================
// LOGGING UTILITY
// =============================================================================

type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'

interface LogMetadata {
  [key: string]: unknown
}

function log(level: LogLevel, fn: string, message: string, metadata?: LogMetadata) {
  const timestamp = new Date().toISOString()
  const prefix = `[${timestamp}] [${level}] [${fn}]`

  if (metadata) {
    console.log(`${prefix} ${message}`, JSON.stringify(metadata))
  } else {
    console.log(`${prefix} ${message}`)
  }
}

const logger = {
  debug: (fn: string, message: string, metadata?: LogMetadata) => log('DEBUG', fn, message, metadata),
  info: (fn: string, message: string, metadata?: LogMetadata) => log('INFO', fn, message, metadata),
  warn: (fn: string, message: string, metadata?: LogMetadata) => log('WARN', fn, message, metadata),
  error: (fn: string, message: string, metadata?: LogMetadata) => log('ERROR', fn, message, metadata),
}

// =============================================================================
// MAIN HANDLER
// =============================================================================

serve(async (req) => {
  const requestId = crypto.randomUUID().slice(0, 8)
  logger.info('serve', `Request received`, { requestId, method: req.method, url: req.url })

  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    logger.debug('serve', 'CORS preflight request')
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Initialize Supabase client with service role key
    logger.debug('serve', 'Initializing Supabase client')
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const url = new URL(req.url)
    const path = url.pathname.split('/').pop()
    logger.info('serve', `Routing to endpoint: ${path}`, { requestId })

    switch (path) {
      case 'sync-all':
        return await handleSyncAll(supabaseClient, requestId)
      case 'sync-politicians':
        return await handleSyncPoliticians(supabaseClient, requestId)
      case 'sync-trades':
        return await handleSyncTrades(supabaseClient, requestId)
      case 'update-stats':
        return await handleUpdateStats(supabaseClient, requestId)
      case 'sync-full':
        return await handleSyncFull(supabaseClient, requestId)
      case 'update-chart-data':
        return await handleUpdateChartData(supabaseClient, requestId)
      case 'update-politician-totals':
        return await handleUpdatePoliticianTotals(supabaseClient, requestId)
      case 'update-politician-parties':
        return await handleUpdatePoliticianParties(supabaseClient, requestId)
      default:
        logger.warn('serve', `Invalid endpoint: ${path}`, { requestId })
        return new Response(
          JSON.stringify({ error: 'Invalid endpoint' }),
          {
            status: 404,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
    }
  } catch (error) {
    logger.error('serve', `Edge function error: ${error.message}`, { requestId, stack: error.stack })
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})

async function handleSyncAll(supabaseClient: any, requestId: string) {
  const fn = 'handleSyncAll'
  logger.info(fn, 'START - Syncing all politicians', { requestId })

  // Get all politicians from complex schema
  logger.debug(fn, 'Fetching politicians from database...')
  const { data: politicians, error: politiciansError } = await supabaseClient
    .from('politicians')
    .select('*')

  if (politiciansError) {
    logger.error(fn, `Failed to fetch politicians: ${politiciansError.message}`, { requestId })
    throw new Error(`Failed to fetch politicians: ${politiciansError.message}`)
  }

  const totalCount = politicians?.length || 0
  logger.info(fn, `Found ${totalCount} politicians to sync`, { requestId, totalCount })

  let syncedCount = 0
  let errorCount = 0

  if (politicians) {
    for (let i = 0; i < politicians.length; i++) {
      const politician = politicians[i]
      try {
        // Transform politician data
        const transformed = transformPolitician(politician)
        logger.debug(fn, `Processing ${i + 1}/${totalCount}: ${politician.id}`, {
          name: transformed.name,
          party: transformed.party,
          chamber: transformed.chamber
        })

        // Upsert to simplified schema
        const { error: upsertError } = await supabaseClient
          .from('politicians')
          .upsert({
            name: transformed.name,
            party: transformed.party,
            chamber: transformed.chamber,
            jurisdiction_id: transformed.jurisdiction_id,
            state: transformed.state,
            total_trades: transformed.total_trades,
            total_volume: transformed.total_volume,
            updated_at: new Date().toISOString()
          }, {
            onConflict: 'name'
          })

        if (upsertError) {
          errorCount++
          logger.error(fn, `Failed to sync politician ${politician.id}: ${upsertError.message}`)
        } else {
          syncedCount++
        }

        // Log progress every 50 records
        if ((i + 1) % 50 === 0) {
          logger.info(fn, `Progress: ${i + 1}/${totalCount} processed`, { synced: syncedCount, errors: errorCount })
        }
      } catch (error) {
        errorCount++
        logger.error(fn, `Error processing politician ${politician.id}: ${error.message}`)
      }
    }
  }

  logger.info(fn, 'END', { requestId, total: totalCount, synced: syncedCount, errors: errorCount })

  return new Response(
    JSON.stringify({
      success: true,
      message: `Synchronized ${syncedCount} politicians`,
      count: syncedCount,
      errors: errorCount
    }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function handleSyncPoliticians(supabaseClient: any, requestId: string) {
  logger.debug('handleSyncPoliticians', 'Alias for handleSyncAll', { requestId })
  return await handleSyncAll(supabaseClient, requestId)
}

async function handleSyncTrades(supabaseClient: any, requestId: string) {
  const fn = 'handleSyncTrades'
  logger.info(fn, 'START - Syncing all trades', { requestId })

  // Get all disclosures with politician info joined
  logger.debug(fn, 'Fetching disclosures with politician join...')
  const { data: disclosures, error: disclosuresError } = await supabaseClient
    .from('trading_disclosures')
    .select('*, politicians!inner(id, full_name, name)')

  if (disclosuresError) {
    logger.error(fn, `Failed to fetch disclosures: ${disclosuresError.message}`, { requestId })
    throw new Error(`Failed to fetch disclosures: ${disclosuresError.message}`)
  }

  const totalCount = disclosures?.length || 0
  logger.info(fn, `Found ${totalCount} disclosures to sync`, { requestId, totalCount })

  let syncedCount = 0
  let skippedCount = 0
  let duplicateCount = 0
  let errorCount = 0

  if (disclosures) {
    for (let i = 0; i < disclosures.length; i++) {
      const disclosure = disclosures[i]
      try {
        // Use the politician_id FK directly from the disclosure
        const politicianId = disclosure.politician_id

        if (!politicianId) {
          logger.warn(fn, `Disclosure ${disclosure.id} has no politician_id, skipping`)
          skippedCount++
          continue
        }

        const transformed = transformTrade(disclosure, politicianId)
        logger.debug(fn, `Processing ${i + 1}/${totalCount}: ${disclosure.id}`, {
          ticker: transformed.ticker,
          trade_type: transformed.trade_type,
          estimated_value: transformed.estimated_value
        })

        // Check for existing trade to avoid duplicates
        const { data: existing } = await supabaseClient
          .from('trades')
          .select('id')
          .eq('politician_id', transformed.politician_id)
          .eq('ticker', transformed.ticker)
          .eq('transaction_date', transformed.transaction_date)
          .maybeSingle()

        if (existing) {
          logger.debug(fn, `Duplicate trade skipped: ${transformed.ticker} on ${transformed.transaction_date}`)
          duplicateCount++
          continue
        }

        // Insert new trade
        const { error: insertError } = await supabaseClient
          .from('trades')
          .insert({
            politician_id: transformed.politician_id,
            ticker: transformed.ticker,
            company: transformed.company,
            trade_type: transformed.trade_type,
            amount_range: transformed.amount_range,
            estimated_value: transformed.estimated_value,
            filing_date: transformed.filing_date,
            transaction_date: transformed.transaction_date
          })

        if (insertError) {
          errorCount++
          logger.error(fn, `Failed to insert trade for disclosure ${disclosure.id}: ${insertError.message}`)
        } else {
          syncedCount++
          logger.debug(fn, `INSERTED: ${transformed.ticker} (${transformed.trade_type}) value=$${transformed.estimated_value}`)
        }

        // Log progress every 100 records
        if ((i + 1) % 100 === 0) {
          logger.info(fn, `Progress: ${i + 1}/${totalCount}`, { synced: syncedCount, duplicates: duplicateCount, errors: errorCount })
        }
      } catch (error) {
        errorCount++
        logger.error(fn, `Error processing disclosure ${disclosure.id}: ${error.message}`)
      }
    }
  }

  // Update politician totals after syncing trades
  logger.info(fn, 'Updating politician totals...')
  await updatePoliticianTotals(supabaseClient, requestId)

  logger.info(fn, 'END', {
    requestId,
    total: totalCount,
    synced: syncedCount,
    duplicates: duplicateCount,
    skipped: skippedCount,
    errors: errorCount
  })

  return new Response(
    JSON.stringify({
      success: true,
      message: `Synchronized ${syncedCount} trades (${duplicateCount} duplicates, ${skippedCount} skipped)`,
      count: syncedCount,
      duplicates: duplicateCount,
      skipped: skippedCount,
      errors: errorCount
    }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function handleUpdateStats(supabaseClient: any, requestId: string) {
  const fn = 'handleUpdateStats'
  logger.info(fn, 'START - Updating dashboard statistics', { requestId })

  // Calculate statistics
  logger.debug(fn, 'Calculating statistics...')
  const stats = await calculateDashboardStats(supabaseClient, requestId)

  logger.info(fn, 'Calculated stats', stats)

  // Update dashboard_stats table - use fixed ID for singleton row
  const DASHBOARD_STATS_ID = '00000000-0000-0000-0000-000000000001'
  logger.debug(fn, 'Upserting to dashboard_stats table...')
  const { error: updateError } = await supabaseClient
    .from('dashboard_stats')
    .upsert({
      id: DASHBOARD_STATS_ID,
      total_trades: stats.total_trades,
      total_volume: stats.total_volume,
      active_politicians: stats.active_politicians,
      jurisdictions_tracked: stats.jurisdictions_tracked,
      average_trade_size: stats.average_trade_size,
      recent_filings: stats.recent_filings,
      updated_at: new Date().toISOString()
    }, { onConflict: 'id' })

  if (updateError) {
    logger.error(fn, `Failed to update stats: ${updateError.message}`, { requestId })
    throw new Error(`Failed to update stats: ${updateError.message}`)
  }

  logger.info(fn, 'END - Dashboard statistics updated', { requestId })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Dashboard statistics updated',
      stats: stats
    }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function handleUpdateChartData(supabaseClient: any, requestId: string) {
  const fn = 'handleUpdateChartData'
  logger.info(fn, 'START - Updating chart data', { requestId })

  try {
    // Aggregate by month/year - fetch all records using pagination
    const chartDataMap = new Map<string, { buys: number, sells: number, volume: number }>()
    const PAGE_SIZE = 1000
    let offset = 0
    let totalFetched = 0

    logger.debug(fn, 'Fetching disclosures for chart aggregation (paginated)...')

    while (true) {
      const { data: disclosures, error: fetchError } = await supabaseClient
        .from('trading_disclosures')
        .select('transaction_date, transaction_type, amount_range_min, amount_range_max')
        .eq('status', 'active')
        .range(offset, offset + PAGE_SIZE - 1)

      if (fetchError) {
        throw new Error(`Failed to fetch disclosures: ${fetchError.message}`)
      }

      const batchSize = disclosures?.length || 0
      if (batchSize === 0) break

      totalFetched += batchSize
      logger.debug(fn, `Fetched batch: ${batchSize} records (total: ${totalFetched})`)

      for (const disclosure of disclosures || []) {
        if (!disclosure.transaction_date) continue

        const date = new Date(disclosure.transaction_date)
        const year = date.getFullYear()
        const month = date.getMonth() + 1 // 1-12
        const key = `${year}-${month}`

        if (!chartDataMap.has(key)) {
          chartDataMap.set(key, { buys: 0, sells: 0, volume: 0 })
        }

        const entry = chartDataMap.get(key)!
        const transactionType = (disclosure.transaction_type || '').toLowerCase()
        const minVal = disclosure.amount_range_min || 0
        const maxVal = disclosure.amount_range_max || minVal
        const volume = (minVal + maxVal) / 2

        if (transactionType.includes('purchase') || transactionType.includes('buy')) {
          entry.buys++
        } else if (transactionType.includes('sale') || transactionType.includes('sell')) {
          entry.sells++
        }
        entry.volume += volume
      }

      // If we got less than PAGE_SIZE, we've reached the end
      if (batchSize < PAGE_SIZE) break
      offset += PAGE_SIZE
    }

    logger.info(fn, `Processed ${totalFetched} total disclosures`)

    // Clear existing chart data and insert new data
    logger.debug(fn, 'Clearing existing chart data...')
    await supabaseClient.from('chart_data').delete().neq('id', '00000000-0000-0000-0000-000000000000')

    // Insert new chart data
    const chartDataRows = Array.from(chartDataMap.entries()).map(([key, data]) => {
      const [year, month] = key.split('-')
      return {
        month: parseInt(month),
        year: parseInt(year),
        buys: data.buys,
        sells: data.sells,
        volume: Math.round(data.volume)
      }
    })

    if (chartDataRows.length > 0) {
      logger.debug(fn, `Inserting ${chartDataRows.length} chart data rows...`)
      const { error: insertError } = await supabaseClient
        .from('chart_data')
        .insert(chartDataRows)

      if (insertError) {
        logger.warn(fn, `Failed to insert chart data: ${insertError.message}`)
      }
    }

    logger.info(fn, 'END - Chart data updated', { requestId, rows: chartDataRows.length })

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Chart data updated',
        rows: chartDataRows.length
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    logger.error(fn, `Error: ${error.message}`, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}

async function handleSyncFull(supabaseClient: any, requestId: string) {
  const fn = 'handleSyncFull'
  const startTime = Date.now()
  logger.info(fn, 'START - Full synchronization', { requestId })

  // Sync politicians
  logger.info(fn, 'Step 1/3: Syncing politicians...')
  const politiciansResult = await handleSyncAll(supabaseClient, requestId)
  const politiciansData = await politiciansResult.json()
  logger.info(fn, 'Step 1/3 complete: Politicians synced', { count: politiciansData.count })

  // Sync trades
  logger.info(fn, 'Step 2/3: Syncing trades...')
  const tradesResult = await handleSyncTrades(supabaseClient, requestId)
  const tradesData = await tradesResult.json()
  logger.info(fn, 'Step 2/3 complete: Trades synced', { count: tradesData.count })

  // Update stats
  logger.info(fn, 'Step 3/3: Updating stats...')
  const statsResult = await handleUpdateStats(supabaseClient, requestId)
  const statsData = await statsResult.json()
  logger.info(fn, 'Step 3/3 complete: Stats updated')

  const duration = Date.now() - startTime
  logger.info(fn, 'END - Full synchronization completed', {
    requestId,
    duration_ms: duration,
    politicians: politiciansData.count,
    trades: tradesData.count
  })

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Full synchronization completed',
      duration_ms: duration,
      results: {
        politicians: politiciansData,
        trades: tradesData,
        stats: statsData
      }
    }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function handleUpdatePoliticianTotals(supabaseClient: any, requestId: string) {
  const fn = 'handleUpdatePoliticianTotals'
  logger.info(fn, 'START - Updating politician totals', { requestId })

  try {
    // Get aggregated trade data per politician from trading_disclosures
    logger.debug(fn, 'Fetching aggregated trade data per politician...')

    // Get all politicians
    const { data: politicians, error: politiciansError } = await supabaseClient
      .from('politicians')
      .select('id')

    if (politiciansError) {
      throw new Error(`Failed to fetch politicians: ${politiciansError.message}`)
    }

    const totalCount = politicians?.length || 0
    let updatedCount = 0

    // Update each politician's totals
    for (const politician of (politicians || [])) {
      // Get disclosure stats for this politician
      const { data: disclosures } = await supabaseClient
        .from('trading_disclosures')
        .select('amount_range_min, amount_range_max')
        .eq('politician_id', politician.id)
        .eq('status', 'active')

      let total_trades = 0
      let total_volume = 0

      if (disclosures && disclosures.length > 0) {
        total_trades = disclosures.length
        total_volume = disclosures.reduce((sum: number, d: any) => {
          const min = d.amount_range_min || 0
          const max = d.amount_range_max || min
          return sum + ((min + max) / 2)
        }, 0)
      }

      // Only update if there are trades
      if (total_trades > 0) {
        const { error: updateError } = await supabaseClient
          .from('politicians')
          .update({
            total_trades,
            total_volume,
            updated_at: new Date().toISOString()
          })
          .eq('id', politician.id)

        if (!updateError) {
          updatedCount++
        }
      }

      // Log progress every 100 records
      if ((updatedCount + 1) % 100 === 0) {
        logger.info(fn, `Progress: ${updatedCount}/${totalCount} updated`)
      }
    }

    logger.info(fn, 'END - Politician totals updated', { requestId, total: totalCount, updated: updatedCount })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Updated ${updatedCount} politicians with trade data`,
        total: totalCount,
        updated: updatedCount
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  } catch (error) {
    logger.error(fn, `Error: ${error.message}`, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function transformPolitician(politician: any) {
  const fn = 'transformPolitician'
  const originalRole = politician.role || ''
  const originalParty = politician.party || 'Other'

  // Map role to chamber
  const role = originalRole.toLowerCase()
  let chamber = 'Other'
  let jurisdiction_id = 'other'

  if (role.includes('house')) {
    chamber = 'House'
    jurisdiction_id = 'us-house'
  } else if (role.includes('senate') || role.includes('senator')) {
    chamber = 'Senate'
    jurisdiction_id = 'us-senate'
  }

  // Standardize party
  let party = originalParty
  if (!['D', 'R', 'I', 'Other'].includes(party)) {
    logger.debug(fn, `Non-standard party '${party}' -> 'Other'`)
    party = 'Other'
  }

  const result = {
    name: politician.full_name || politician.name || 'Unknown',
    party: party,
    chamber: chamber,
    jurisdiction_id: jurisdiction_id,
    state: politician.state_or_country,
    total_trades: 0,
    total_volume: 0
  }

  logger.debug(fn, `Transformed: ${result.name}`, { chamber, jurisdiction_id, party })
  return result
}

function transformTrade(disclosure: any, politicianId: string) {
  const fn = 'transformTrade'
  const originalTransactionType = disclosure.transaction_type || ''

  // Map transaction type
  const transactionType = originalTransactionType.toLowerCase()
  let trade_type = 'buy'
  if (transactionType.includes('sell') || transactionType.includes('sale')) {
    trade_type = 'sell'
  } else if (!transactionType.includes('buy') && !transactionType.includes('purchase')) {
    logger.debug(fn, `Unknown transaction type '${originalTransactionType}' -> 'buy'`)
  }

  // Calculate estimated value
  let estimated_value = 0
  if (disclosure.amount_exact) {
    estimated_value = disclosure.amount_exact
  } else if (disclosure.amount_range_min && disclosure.amount_range_max) {
    estimated_value = (disclosure.amount_range_min + disclosure.amount_range_max) / 2
  } else if (disclosure.amount_range_min) {
    estimated_value = disclosure.amount_range_min
  } else if (disclosure.amount_range_max) {
    estimated_value = disclosure.amount_range_max
  }

  // Format amount range
  let amount_range = 'Unknown'
  if (disclosure.amount_exact) {
    amount_range = `$${disclosure.amount_exact.toLocaleString()}`
  } else if (disclosure.amount_range_min && disclosure.amount_range_max) {
    amount_range = `$${disclosure.amount_range_min.toLocaleString()} - $${disclosure.amount_range_max.toLocaleString()}`
  }

  const ticker = disclosure.asset_ticker || ''
  const result = {
    politician_id: politicianId,
    ticker: ticker,
    company: disclosure.asset_name || '',
    trade_type: trade_type,
    amount_range: amount_range,
    estimated_value: Math.round(estimated_value),
    filing_date: disclosure.disclosure_date ? disclosure.disclosure_date.split('T')[0] : '',
    transaction_date: disclosure.transaction_date ? disclosure.transaction_date.split('T')[0] : ''
  }

  logger.debug(fn, `Transformed: ${ticker} (${trade_type})`, { estimated_value: result.estimated_value })
  return result
}

async function updatePoliticianTotals(supabaseClient: any, requestId: string) {
  const fn = 'updatePoliticianTotals'
  logger.info(fn, 'START - Updating politician totals', { requestId })

  // Get all politicians
  const { data: politicians } = await supabaseClient
    .from('politicians')
    .select('id')

  const totalCount = politicians?.length || 0
  logger.info(fn, `Updating ${totalCount} politicians`)

  if (politicians) {
    for (let i = 0; i < politicians.length; i++) {
      const politician = politicians[i]
      // Calculate totals for this politician from trading_disclosures
      const { data: disclosures } = await supabaseClient
        .from('trading_disclosures')
        .select('amount_range_min, amount_range_max')
        .eq('politician_id', politician.id)
        .eq('status', 'active')

      let total_trades = 0
      let total_volume = 0

      if (disclosures) {
        total_trades = disclosures.length
        // Calculate volume using midpoint of amount ranges
        total_volume = disclosures.reduce((sum: number, d: any) => {
          const min = d.amount_range_min || 0
          const max = d.amount_range_max || min
          return sum + ((min + max) / 2)
        }, 0)
      }

      logger.debug(fn, `Updating ${politician.id}: trades=${total_trades}, volume=$${total_volume}`)

      // Update politician
      await supabaseClient
        .from('politicians')
        .update({
          total_trades: total_trades,
          total_volume: total_volume,
          updated_at: new Date().toISOString()
        })
        .eq('id', politician.id)

      // Log progress every 50 records
      if ((i + 1) % 50 === 0) {
        logger.info(fn, `Progress: ${i + 1}/${totalCount}`)
      }
    }
  }

  logger.info(fn, 'END', { requestId, updated: totalCount })
}

async function calculateDashboardStats(supabaseClient: any, requestId: string) {
  const fn = 'calculateDashboardStats'
  logger.debug(fn, 'START', { requestId })

  // Total disclosures and volume from trading_disclosures table
  logger.debug(fn, 'Fetching trading disclosures count...')
  const { data: disclosures, count: totalTrades } = await supabaseClient
    .from('trading_disclosures')
    .select('amount_range_min, amount_range_max', { count: 'exact' })
    .eq('status', 'active')

  // Calculate total volume from amount ranges (using midpoint)
  let totalVolume = 0
  if (disclosures) {
    totalVolume = disclosures.reduce((sum: number, d: any) => {
      const min = d.amount_range_min || 0
      const max = d.amount_range_max || min
      return sum + ((min + max) / 2)
    }, 0)
  }
  logger.debug(fn, `disclosures=${totalTrades}, volume=$${totalVolume}`)

  // Active politicians
  logger.debug(fn, 'Fetching politicians count...')
  const { count: activePoliticians } = await supabaseClient
    .from('politicians')
    .select('*', { count: 'exact', head: true })
    .eq('is_active', true)
  logger.debug(fn, `active_politicians=${activePoliticians}`)

  // Jurisdictions tracked - count unique roles from politicians
  logger.debug(fn, 'Counting jurisdictions...')
  const { data: rolesData } = await supabaseClient
    .from('politicians')
    .select('role')
    .eq('is_active', true)
  const uniqueRoles = new Set((rolesData || []).map((p: any) => p.role).filter(Boolean))
  const jurisdictionsTracked = uniqueRoles.size || 4 // Default to 4 for US House, Senate, EU, UK
  logger.debug(fn, `jurisdictions=${jurisdictionsTracked}`)

  // Average trade size
  const averageTradeSize = totalTrades && totalTrades > 0 ? Math.round(totalVolume / totalTrades) : 0

  // Recent filings (last 7 days)
  const sevenDaysAgo = new Date()
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
  const weekAgoStr = sevenDaysAgo.toISOString().split('T')[0]
  logger.debug(fn, `Fetching recent filings since ${weekAgoStr}...`)
  const { count: recentFilings } = await supabaseClient
    .from('trading_disclosures')
    .select('*', { count: 'exact', head: true })
    .eq('status', 'active')
    .gte('disclosure_date', weekAgoStr)
  logger.debug(fn, `recent_filings=${recentFilings}`)

  const stats = {
    total_trades: totalTrades || 0,
    total_volume: totalVolume,
    active_politicians: activePoliticians || 0,
    jurisdictions_tracked: jurisdictionsTracked,
    average_trade_size: averageTradeSize,
    recent_filings: recentFilings || 0
  }

  logger.debug(fn, 'END', stats)
  return stats
}

// =============================================================================
// POLITICIAN PARTY LOOKUP VIA OLLAMA
// =============================================================================

const OLLAMA_API_URL = 'https://ollama.lefv.io/api/generate'
const OLLAMA_API_KEY = '2df4dc81117fa1845a8ee21a6a315676a4aa099833b79602697dbe15d48af7fc'
const OLLAMA_MODEL = 'llama3.1:8b'

// Well-known politician party mappings (for speed - avoids API calls)
const KNOWN_PARTIES: Record<string, string> = {
  // Senate Republicans
  'mitch mcconnell': 'R',
  'a. mitchell mcconnell': 'R',
  'john cornyn': 'R',
  'john thune': 'R',
  'rick scott': 'R',
  'marco rubio': 'R',
  'ted cruz': 'R',
  'rand paul': 'R',
  'susan collins': 'R',
  'susan m collins': 'R',
  'lisa murkowski': 'R',
  'mitt romney': 'R',
  'john boozman': 'R',
  'tom cotton': 'R',
  'bill cassidy': 'R',
  'william cassidy': 'R',
  'pat toomey': 'R',
  'patrick j toomey': 'R',
  'kelly loeffler': 'R',
  'david perdue': 'R',
  'jerry moran': 'R',
  'pat roberts': 'R',
  'ron johnson': 'R',
  'mike lee': 'R',
  'lindsey graham': 'R',
  'tim scott': 'R',
  // Senate Democrats
  'chuck schumer': 'D',
  'charles schumer': 'D',
  'dick durbin': 'D',
  'richard durbin': 'D',
  'patty murray': 'D',
  'debbie stabenow': 'D',
  'elizabeth warren': 'D',
  'bernie sanders': 'I',
  'mark warner': 'D',
  'mark r warner': 'D',
  'tim kaine': 'D',
  'timothy m kaine': 'D',
  'michael bennet': 'D',
  'michael f bennet': 'D',
  'chris coons': 'D',
  'christopher a coons': 'D',
  'jeanne shaheen': 'D',
  'maggie hassan': 'D',
  'angus king': 'I',
  'angus s king': 'I',
  'joe manchin': 'D',
  'kyrsten sinema': 'I',
  'jon ossoff': 'D',
  'raphael warnock': 'D',
  // House members & others
  'nancy pelosi': 'D',
  'kevin mccarthy': 'R',
  'mike johnson': 'R',
  'hakeem jeffries': 'D',
  'justin amash': 'I',
  'ron desantis': 'R',
  'greg abbott': 'R',
  'gavin newsom': 'D',
  'dade phelan': 'R',
}

async function lookupPartyFromOllama(politicianName: string, role: string): Promise<string | null> {
  try {
    const prompt = `What is the political party of ${politicianName}${role ? ` (${role})` : ''} in US politics? Reply with ONLY a JSON object: {"party": "R"} for Republican, {"party": "D"} for Democrat, {"party": "I"} for Independent. No other text.`

    const response = await fetch(OLLAMA_API_URL, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OLLAMA_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        prompt: prompt,
        stream: false
      })
    })

    if (!response.ok) {
      console.warn(`Ollama API error for ${politicianName}: ${response.status}`)
      return null
    }

    const data = await response.json()
    const responseText = data.response?.trim() || ''

    // Try to parse JSON from response
    const jsonMatch = responseText.match(/\{[^}]+\}/)
    if (jsonMatch) {
      try {
        const parsed = JSON.parse(jsonMatch[0])
        if (parsed.party && ['R', 'D', 'I'].includes(parsed.party)) {
          return parsed.party
        }
      } catch {
        // JSON parse failed
      }
    }

    // Fallback: look for party indicators in text
    const lowerResponse = responseText.toLowerCase()
    if (lowerResponse.includes('republican') || lowerResponse.includes('"r"')) {
      return 'R'
    } else if (lowerResponse.includes('democrat') || lowerResponse.includes('"d"')) {
      return 'D'
    } else if (lowerResponse.includes('independent') || lowerResponse.includes('"i"')) {
      return 'I'
    }

    return null
  } catch (error) {
    console.warn(`Ollama lookup failed for ${politicianName}:`, error)
    return null
  }
}

async function handleUpdatePoliticianParties(supabaseClient: any, requestId: string) {
  const fn = 'handleUpdatePoliticianParties'
  logger.info(fn, 'START - Updating politician parties via Ollama', { requestId })

  try {
    // Get politicians with missing party info
    const { data: politicians, error: fetchError } = await supabaseClient
      .from('politicians')
      .select('id, full_name, party, role')
      .or('party.is.null,party.eq.')
      .limit(100) // Process in batches to avoid timeout

    if (fetchError) {
      throw new Error(`Failed to fetch politicians: ${fetchError.message}`)
    }

    if (!politicians || politicians.length === 0) {
      logger.info(fn, 'No politicians need party updates', { requestId })
      return new Response(
        JSON.stringify({ success: true, message: 'All politicians have party info', updated: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    logger.info(fn, `Found ${politicians.length} politicians needing party lookup`, { requestId })

    let updatedCount = 0
    let skippedCount = 0
    let ollamaCallCount = 0

    for (const politician of politicians) {
      const name = politician.full_name || ''
      const normalizedName = name.toLowerCase().replace(/[.,]+/g, '').trim()

      let party: string | null = null

      // First check known parties mapping (instant)
      if (KNOWN_PARTIES[normalizedName]) {
        party = KNOWN_PARTIES[normalizedName]
        logger.debug(fn, `Found ${name} in known parties: ${party}`)
      } else {
        // Fall back to Ollama
        ollamaCallCount++
        party = await lookupPartyFromOllama(name, politician.role)
        logger.debug(fn, `Ollama lookup for ${name}: ${party}`)

        // Rate limit: small delay between Ollama calls
        if (ollamaCallCount % 5 === 0) {
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      }

      if (party) {
        const { error: updateError } = await supabaseClient
          .from('politicians')
          .update({
            party: party,
            updated_at: new Date().toISOString()
          })
          .eq('id', politician.id)

        if (updateError) {
          logger.warn(fn, `Failed to update ${name}: ${updateError.message}`)
          skippedCount++
        } else {
          updatedCount++
          logger.info(fn, `Updated ${name} -> ${party}`)
        }
      } else {
        skippedCount++
        logger.warn(fn, `Could not determine party for ${name}`)
      }
    }

    logger.info(fn, 'END', {
      requestId,
      total: politicians.length,
      updated: updatedCount,
      skipped: skippedCount,
      ollamaCalls: ollamaCallCount
    })

    return new Response(
      JSON.stringify({
        success: true,
        message: `Updated ${updatedCount} politician parties`,
        total: politicians.length,
        updated: updatedCount,
        skipped: skippedCount,
        ollamaCalls: ollamaCallCount
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    logger.error(fn, `Error: ${error.message}`, { requestId })
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
}