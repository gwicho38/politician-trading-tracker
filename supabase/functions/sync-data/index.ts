import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Initialize Supabase client with service role key
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const url = new URL(req.url)
    const path = url.pathname.split('/').pop()

    switch (path) {
      case 'sync-all':
        return await handleSyncAll(supabaseClient)
      case 'sync-politicians':
        return await handleSyncPoliticians(supabaseClient)
      case 'sync-trades':
        return await handleSyncTrades(supabaseClient)
      case 'update-stats':
        return await handleUpdateStats(supabaseClient)
      case 'sync-full':
        return await handleSyncFull(supabaseClient)
      default:
        return new Response(
          JSON.stringify({ error: 'Invalid endpoint' }),
          {
            status: 404,
            headers: { ...corsHeaders, 'Content-Type': 'application/json' }
          }
        )
    }
  } catch (error) {
    console.error('Edge function error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})

async function handleSyncAll(supabaseClient: any) {
  console.log('Starting sync of all politicians...')

  // Get all politicians from complex schema
  const { data: politicians, error: politiciansError } = await supabaseClient
    .from('politicians')
    .select('*')

  if (politiciansError) {
    throw new Error(`Failed to fetch politicians: ${politiciansError.message}`)
  }

  let syncedCount = 0
  if (politicians) {
    for (const politician of politicians) {
      try {
        // Transform politician data
        const transformed = transformPolitician(politician)

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
          console.error(`Failed to sync politician ${politician.id}:`, upsertError)
        } else {
          syncedCount++
        }
      } catch (error) {
        console.error(`Error processing politician ${politician.id}:`, error)
      }
    }
  }

  return new Response(
    JSON.stringify({
      success: true,
      message: `Synchronized ${syncedCount} politicians`,
      count: syncedCount
    }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function handleSyncPoliticians(supabaseClient: any) {
  // Alias for sync-all
  return await handleSyncAll(supabaseClient)
}

async function handleSyncTrades(supabaseClient: any) {
  console.log('Starting sync of all trades...')

  // Get all disclosures
  const { data: disclosures, error: disclosuresError } = await supabaseClient
    .from('trading_disclosures')
    .select('*')

  if (disclosuresError) {
    throw new Error(`Failed to fetch disclosures: ${disclosuresError.message}`)
  }

  let syncedCount = 0
  if (disclosures) {
    for (const disclosure of disclosures) {
      try {
        // Get politician mapping
        const { data: politicians } = await supabaseClient
          .from('politicians')
          .select('id')
          .eq('name', disclosure.politician_id ? 'Unknown' : 'Unknown') // Simplified mapping
          .single()

        if (politicians) {
          const transformed = transformTrade(disclosure, politicians.id)

          // Insert trade (skip duplicates)
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

          if (!insertError) {
            syncedCount++
          }
        }
      } catch (error) {
        console.error(`Error processing disclosure ${disclosure.id}:`, error)
      }
    }
  }

  // Update politician totals
  await updatePoliticianTotals(supabaseClient)

  return new Response(
    JSON.stringify({
      success: true,
      message: `Synchronized ${syncedCount} trades`,
      count: syncedCount
    }),
    {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function handleUpdateStats(supabaseClient: any) {
  console.log('Updating dashboard statistics...')

  // Calculate statistics
  const stats = await calculateDashboardStats(supabaseClient)

  // Update dashboard_stats table
  const { error: updateError } = await supabaseClient
    .from('dashboard_stats')
    .upsert({
      total_trades: stats.total_trades,
      total_volume: stats.total_volume,
      active_politicians: stats.active_politicians,
      jurisdictions_tracked: stats.jurisdictions_tracked,
      average_trade_size: stats.average_trade_size,
      recent_filings: stats.recent_filings,
      updated_at: new Date().toISOString()
    })

  if (updateError) {
    throw new Error(`Failed to update stats: ${updateError.message}`)
  }

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

async function handleSyncFull(supabaseClient: any) {
  console.log('Starting full synchronization...')

  // Sync politicians
  const politiciansResult = await handleSyncAll(supabaseClient)
  const politiciansData = await politiciansResult.json()

  // Sync trades
  const tradesResult = await handleSyncTrades(supabaseClient)
  const tradesData = await tradesResult.json()

  // Update stats
  const statsResult = await handleUpdateStats(supabaseClient)
  const statsData = await statsResult.json()

  return new Response(
    JSON.stringify({
      success: true,
      message: 'Full synchronization completed',
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

// Helper functions
function transformPolitician(politician: any) {
  // Map role to chamber
  const role = (politician.role || '').toLowerCase()
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
  let party = politician.party || 'Other'
  if (!['D', 'R', 'I', 'Other'].includes(party)) {
    party = 'Other'
  }

  return {
    name: politician.full_name || politician.name || 'Unknown',
    party: party,
    chamber: chamber,
    jurisdiction_id: jurisdiction_id,
    state: politician.state_or_country,
    total_trades: 0,
    total_volume: 0
  }
}

function transformTrade(disclosure: any, politicianId: string) {
  // Map transaction type
  const transactionType = (disclosure.transaction_type || '').toLowerCase()
  let trade_type = 'buy'
  if (transactionType.includes('sell') || transactionType.includes('sale')) {
    trade_type = 'sell'
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

  return {
    politician_id: politicianId,
    ticker: disclosure.asset_ticker || '',
    company: disclosure.asset_name || '',
    trade_type: trade_type,
    amount_range: amount_range,
    estimated_value: Math.round(estimated_value),
    filing_date: disclosure.disclosure_date ? disclosure.disclosure_date.split('T')[0] : '',
    transaction_date: disclosure.transaction_date ? disclosure.transaction_date.split('T')[0] : ''
  }
}

async function updatePoliticianTotals(supabaseClient: any) {
  // Get all politicians
  const { data: politicians } = await supabaseClient
    .from('politicians')
    .select('id')

  if (politicians) {
    for (const politician of politicians) {
      // Calculate totals for this politician
      const { data: trades } = await supabaseClient
        .from('trades')
        .select('estimated_value')
        .eq('politician_id', politician.id)

      let total_trades = 0
      let total_volume = 0

      if (trades) {
        total_trades = trades.length
        total_volume = trades.reduce((sum: number, trade: any) => sum + (trade.estimated_value || 0), 0)
      }

      // Update politician
      await supabaseClient
        .from('politicians')
        .update({
          total_trades: total_trades,
          total_volume: total_volume,
          updated_at: new Date().toISOString()
        })
        .eq('id', politician.id)
    }
  }
}

async function calculateDashboardStats(supabaseClient: any) {
  // Total trades and volume
  const { data: trades, count: totalTrades } = await supabaseClient
    .from('trades')
    .select('estimated_value', { count: 'exact', head: true })

  let totalVolume = 0
  if (trades) {
    totalVolume = trades.reduce((sum: number, trade: any) => sum + (trade.estimated_value || 0), 0)
  }

  // Active politicians
  const { count: activePoliticians } = await supabaseClient
    .from('politicians')
    .select('*', { count: 'exact', head: true })

  // Jurisdictions tracked
  const { count: jurisdictionsTracked } = await supabaseClient
    .from('jurisdictions')
    .select('*', { count: 'exact', head: true })

  // Average trade size
  const averageTradeSize = totalTrades && totalTrades > 0 ? Math.round(totalVolume / totalTrades) : 0

  // Recent filings (last 7 days)
  const sevenDaysAgo = new Date()
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
  const { count: recentFilings } = await supabaseClient
    .from('trades')
    .select('*', { count: 'exact', head: true })
    .gte('filing_date', sevenDaysAgo.toISOString().split('T')[0])

  return {
    total_trades: totalTrades || 0,
    total_volume: totalVolume,
    active_politicians: activePoliticians || 0,
    jurisdictions_tracked: jurisdictionsTracked || 0,
    average_trade_size: averageTradeSize,
    recent_filings: recentFilings || 0
  }
}