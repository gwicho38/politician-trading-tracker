"""
Supabase Edge Functions for politician trading data collection

This module provides the function code that can be deployed as Supabase Edge Functions
for automated data collection via cron jobs.
"""

# Edge Function code for Supabase (TypeScript/Deno)
POLITICIAN_TRADING_EDGE_FUNCTION = """
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

serve(async (req) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    console.log('🏛️ Starting politician trading data collection cron job');

    // Create a new job record
    const jobId = crypto.randomUUID();
    const startTime = new Date().toISOString();
    
    const { error: jobError } = await supabase
      .from('data_pull_jobs')
      .insert({
        id: jobId,
        job_type: 'automated_collection',
        status: 'running',
        started_at: startTime,
        config_snapshot: {
          triggered_by: 'supabase_cron',
          timestamp: startTime
        }
      });

    if (jobError) {
      console.error('Failed to create job record:', jobError);
      throw jobError;
    }

    // Simulate data collection (in production, this would call actual APIs)
    const results = await performDataCollection(supabase);

    // Update job with results
    const { error: updateError } = await supabase
      .from('data_pull_jobs')
      .update({
        status: 'completed',
        completed_at: new Date().toISOString(),
        records_found: results.recordsFound,
        records_processed: results.recordsProcessed,
        records_new: results.recordsNew,
        records_updated: results.recordsUpdated,
        records_failed: results.recordsFailed
      })
      .eq('id', jobId);

    if (updateError) {
      console.error('Failed to update job record:', updateError);
    }

    console.log('✅ Politician trading collection completed:', results);

    return new Response(
      JSON.stringify({
        success: true,
        jobId,
        results,
        timestamp: new Date().toISOString()
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200,
      }
    );

  } catch (error) {
    console.error('❌ Cron job failed:', error);
    
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 500,
      }
    );
  }
});

async function performDataCollection(supabase) {
  // This would implement the actual data collection logic
  // For now, we'll return mock results
  
  const results = {
    recordsFound: 0,
    recordsProcessed: 0,
    recordsNew: 0,
    recordsUpdated: 0,
    recordsFailed: 0
  };

  try {
    // Example: Check for new trading disclosures
    // In production, this would make HTTP requests to government APIs
    
    // Simulate finding some new records
    const mockDisclosures = await simulateDataFetch();
    results.recordsFound = mockDisclosures.length;

    for (const disclosure of mockDisclosures) {
      try {
        // Check if disclosure already exists
        const { data: existing } = await supabase
          .from('trading_disclosures')
          .select('id')
          .eq('politician_id', disclosure.politician_id)
          .eq('transaction_date', disclosure.transaction_date)
          .eq('asset_name', disclosure.asset_name)
          .eq('transaction_type', disclosure.transaction_type)
          .single();

        if (existing) {
          // Update existing record
          const { error } = await supabase
            .from('trading_disclosures')
            .update({
              ...disclosure,
              updated_at: new Date().toISOString()
            })
            .eq('id', existing.id);

          if (error) {
            console.error('Update failed:', error);
            results.recordsFailed++;
          } else {
            results.recordsUpdated++;
          }
        } else {
          // Insert new record
          const { error } = await supabase
            .from('trading_disclosures')
            .insert({
              ...disclosure,
              id: crypto.randomUUID(),
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString()
            });

          if (error) {
            console.error('Insert failed:', error);
            results.recordsFailed++;
          } else {
            results.recordsNew++;
          }
        }

        results.recordsProcessed++;

      } catch (error) {
        console.error('Processing error:', error);
        results.recordsFailed++;
      }
    }

  } catch (error) {
    console.error('Data collection error:', error);
    throw error;
  }

  return results;
}

async function simulateDataFetch() {
  // Simulate fetching data from external APIs
  // In production, this would make real HTTP requests
  
  return [
    {
      politician_id: 'sample-politician-id',
      transaction_date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Yesterday
      disclosure_date: new Date().toISOString(),
      transaction_type: 'purchase',
      asset_name: 'Sample Corp',
      asset_ticker: 'SMPL',
      asset_type: 'stock',
      amount_range_min: 1001,
      amount_range_max: 15000,
      source_url: 'https://example.com/disclosure',
      raw_data: {
        source: 'simulated',
        timestamp: new Date().toISOString()
      },
      status: 'processed'
    }
  ];
}
"""

# Python function that can be called from the edge function
PYTHON_COLLECTION_FUNCTION = '''
"""
Python function for data collection that can be called from the edge function
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from .workflow import run_politician_trading_collection

async def handle_cron_collection() -> Dict[str, Any]:
    """
    Main function called by the Supabase cron job
    """
    try:
        print("🏛️ Starting scheduled politician trading data collection")
        
        # Run the full collection workflow
        result = await run_politician_trading_collection()
        
        # Log results
        print(f"✅ Collection completed: {result.get('summary', {})}")
        
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_msg = f"❌ Scheduled collection failed: {e}"
        print(error_msg)
        
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Export for cron usage
cron_handler = handle_cron_collection
'''

# Supabase SQL for setting up the cron job
CRON_JOB_SQL = """
-- Politician Trading Data Collection Cron Job Setup

-- Enable the pg_cron extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Create the cron job to run every 6 hours
SELECT cron.schedule(
    'politician-trading-collection',  -- job name
    '0 */6 * * *',                   -- cron expression: every 6 hours at minute 0
    $$
    -- Call the Edge Function via HTTP
    SELECT net.http_post(
        url := 'https://uljsqvwkomdrlnofmlad.supabase.co/functions/v1/politician-trading-collect',
        headers := '{"Content-Type": "application/json", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVsanNxdndrb21kcmxub2ZtbGFkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MDIyNDQsImV4cCI6MjA3MjM3ODI0NH0.QCpfcEpxGX_5Wn8ljf_J2KWjJLGdF8zRsV_7OatxmHI"}'::jsonb,
        body := '{}'::jsonb
    ) as request_id;
    $$
);

-- Alternative: Direct database operation (if you prefer not to use Edge Functions)
SELECT cron.schedule(
    'politician-trading-db-check',
    '0 */2 * * *',  -- Every 2 hours
    $$
    -- Insert a status check record
    INSERT INTO data_pull_jobs (
        job_type,
        status,
        started_at,
        config_snapshot
    ) VALUES (
        'cron_status_check',
        'completed',
        NOW(),
        '{"type": "automatic_status_check"}'::jsonb
    );
    $$
);

-- View all scheduled cron jobs
SELECT * FROM cron.job;

-- View cron job run history
SELECT * FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 10;

-- Delete a cron job (if needed)
-- SELECT cron.unschedule('politician-trading-collection');

-- Monitor cron job failures
CREATE OR REPLACE VIEW cron_job_monitoring AS
SELECT 
    jobname,
    status,
    return_message,
    start_time,
    end_time,
    (end_time - start_time) as duration
FROM cron.job_run_details 
WHERE jobname = 'politician-trading-collection'
ORDER BY start_time DESC;

-- Create notification for failed jobs (optional)
CREATE OR REPLACE FUNCTION notify_cron_failure()
RETURNS trigger AS $$
BEGIN
    IF NEW.status = 'failed' AND NEW.jobname = 'politician-trading-collection' THEN
        INSERT INTO data_pull_jobs (
            job_type,
            status,
            error_message,
            started_at
        ) VALUES (
            'cron_failure_alert',
            'failed',
            NEW.return_message,
            NOW()
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for cron failure notifications
DROP TRIGGER IF EXISTS cron_failure_trigger ON cron.job_run_details;
CREATE TRIGGER cron_failure_trigger
    AFTER INSERT ON cron.job_run_details
    FOR EACH ROW
    EXECUTE FUNCTION notify_cron_failure();
"""
