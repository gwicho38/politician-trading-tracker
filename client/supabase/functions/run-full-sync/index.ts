import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders })
  }

  try {
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, serviceRoleKey)

    // Verify admin role from auth header
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    const anonClient = createClient(supabaseUrl, Deno.env.get('SUPABASE_ANON_KEY')!)
    const { data: { user }, error: authError } = await anonClient.auth.getUser(authHeader.replace('Bearer ', ''))
    
    if (authError || !user) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    // Check if user is admin
    const { data: roleData } = await supabase
      .from('user_roles')
      .select('role')
      .eq('user_id', user.id)
      .eq('role', 'admin')
      .single()

    if (!roleData) {
      return new Response(JSON.stringify({ error: 'Admin access required' }), {
        status: 403,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })
    }

    console.log('Starting full sync...')

    // Create sync log entry
    const { data: syncLog, error: logError } = await supabase
      .from('sync_logs')
      .insert({
        sync_type: 'full_sync',
        status: 'running',
        metadata: { triggered_by: user.id, source: 'admin_panel' }
      })
      .select()
      .single()

    if (logError) {
      console.error('Failed to create sync log:', logError)
      throw logError
    }

    const logId = syncLog.id
    let recordsUpdated = 0

    try {
      // 1. Recalculate politician totals
      console.log('Recalculating politician totals...')
      const { data: politicians } = await supabase.from('politicians').select('id')
      
      for (const pol of politicians || []) {
        const { data: trades } = await supabase
          .from('trades')
          .select('estimated_value')
          .eq('politician_id', pol.id)

        const totalTrades = trades?.length || 0
        const totalVolume = trades?.reduce((sum, t) => sum + (t.estimated_value || 0), 0) || 0

        await supabase
          .from('politicians')
          .update({
            total_trades: totalTrades,
            total_volume: totalVolume,
            updated_at: new Date().toISOString()
          })
          .eq('id', pol.id)
        
        recordsUpdated++
      }

      // 2. Recalculate chart data
      console.log('Recalculating chart data...')
      const { data: allTrades } = await supabase
        .from('trades')
        .select('trade_type, estimated_value, filing_date')

      const monthlyData: Record<string, { year: number; month: string; buys: number; sells: number; volume: number }> = {}

      for (const trade of allTrades || []) {
        const date = new Date(trade.filing_date)
        const month = date.toLocaleString('en-US', { month: 'short' })
        const year = date.getFullYear()
        const key = `${year}-${month}`

        if (!monthlyData[key]) {
          monthlyData[key] = { year, month, buys: 0, sells: 0, volume: 0 }
        }

        if (trade.trade_type === 'buy') {
          monthlyData[key].buys++
        } else {
          monthlyData[key].sells++
        }
        monthlyData[key].volume += trade.estimated_value || 0
      }

      for (const data of Object.values(monthlyData)) {
        const { data: existing } = await supabase
          .from('chart_data')
          .select('id')
          .eq('year', data.year)
          .eq('month', data.month)
          .single()

        if (existing) {
          await supabase.from('chart_data').update(data).eq('id', existing.id)
        } else {
          await supabase.from('chart_data').insert(data)
        }
      }

      // 3. Recalculate dashboard stats
      console.log('Recalculating dashboard stats...')
      const { count: politicianCount } = await supabase.from('politicians').select('*', { count: 'exact', head: true })
      const { count: jurisdictionCount } = await supabase.from('jurisdictions').select('*', { count: 'exact', head: true })
      
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      const { count: recentCount } = await supabase
        .from('trades')
        .select('*', { count: 'exact', head: true })
        .gte('filing_date', weekAgo)

      const totalVolume = allTrades?.reduce((sum, t) => sum + (t.estimated_value || 0), 0) || 0
      const totalTradesCount = allTrades?.length || 0
      const avgTradeSize = totalTradesCount > 0 ? Math.floor(totalVolume / totalTradesCount) : 0

      const dashboardStats = {
        total_trades: totalTradesCount,
        total_volume: totalVolume,
        active_politicians: politicianCount || 0,
        jurisdictions_tracked: jurisdictionCount || 0,
        average_trade_size: avgTradeSize,
        recent_filings: recentCount || 0,
        updated_at: new Date().toISOString()
      }

      const { data: existingStats } = await supabase.from('dashboard_stats').select('id').limit(1).single()
      
      if (existingStats) {
        await supabase.from('dashboard_stats').update(dashboardStats).eq('id', existingStats.id)
      } else {
        await supabase.from('dashboard_stats').insert(dashboardStats)
      }

      // Complete sync log
      await supabase
        .from('sync_logs')
        .update({
          status: 'success',
          records_processed: politicians?.length || 0,
          records_updated: recordsUpdated,
          completed_at: new Date().toISOString()
        })
        .eq('id', logId)

      console.log('Full sync completed successfully')

      return new Response(JSON.stringify({
        success: true,
        stats: dashboardStats,
        politicians_updated: recordsUpdated
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      })

    } catch (syncError) {
      const errorMessage = syncError instanceof Error ? syncError.message : 'Unknown error'
      console.error('Sync error:', syncError)
      
      // Update sync log with failure
      await supabase
        .from('sync_logs')
        .update({
          status: 'failed',
          error_message: errorMessage,
          completed_at: new Date().toISOString()
        })
        .eq('id', logId)

      // Create failure notification for all admins
      const { data: admins } = await supabase
        .from('user_roles')
        .select('user_id')
        .eq('role', 'admin')

      for (const admin of admins || []) {
        await supabase.from('notifications').insert({
          user_id: admin.user_id,
          title: 'Sync Failed',
          message: `Full sync failed: ${errorMessage}`,
          type: 'error',
          read: false
        })
      }

      console.log('Created failure notifications for admins')
      throw syncError
    }

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    console.error('Error:', error)
    return new Response(JSON.stringify({ error: errorMessage }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    })
  }
})
