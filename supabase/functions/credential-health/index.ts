/**
 * Credential Health Edge Function
 *
 * Provides credential rotation status and health monitoring.
 * Returns the age and health status of all configured API keys.
 *
 * Security: Requires authenticated user, returns only their own credential status.
 *
 * Endpoints:
 *   GET /credential-health - Get credential health status for authenticated user
 *   GET /credential-health?action=rotation-needed - Get users needing rotation (admin only)
 */

import { createClient } from 'supabase'
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { corsHeaders, corsJsonResponse, corsErrorResponse, handleCorsPreflightRequest } from '../_shared/cors.ts'
import { isServiceRoleRequest } from '../_shared/auth.ts'

interface CredentialHealth {
  credential_type: string
  is_configured: boolean
  days_since_creation: number | null
  days_until_rotation: number | null
  health_status: 'healthy' | 'warning' | 'expired' | 'not_configured'
  last_validated: string | null
}

interface RotationNeededUser {
  user_email: string
  user_name: string | null
  credentials_expiring: string[]
  earliest_expiry_days: number
}

const ROTATION_DAYS = 90
const WARNING_THRESHOLD = 14

serve(async (req) => {
  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    return handleCorsPreflightRequest(req)
  }

  const origin = req.headers.get('origin')

  try {
    // Create Supabase clients
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!

    // Get authorization header
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      return corsErrorResponse('Missing Authorization header', 401, origin)
    }

    // Check for admin-only action
    const url = new URL(req.url)
    const action = url.searchParams.get('action')

    if (action === 'rotation-needed') {
      // Admin-only: Get all users needing rotation reminders
      if (!isServiceRoleRequest(req)) {
        return corsErrorResponse('Admin access required', 403, origin)
      }

      const adminClient = createClient(supabaseUrl, supabaseServiceKey)

      const { data, error } = await adminClient.rpc('get_users_needing_rotation_reminder')

      if (error) {
        console.error('Error fetching rotation needed users:', error)
        return corsErrorResponse(`Database error: ${error.message}`, 500, origin)
      }

      return corsJsonResponse({
        success: true,
        data: data as RotationNeededUser[],
        count: data?.length ?? 0,
        metadata: {
          rotation_policy_days: ROTATION_DAYS,
          warning_threshold_days: WARNING_THRESHOLD,
        }
      }, 200, origin)
    }

    // Regular user: Get their own credential health
    const userClient = createClient(supabaseUrl, supabaseAnonKey, {
      global: { headers: { Authorization: authHeader } }
    })

    // Get the authenticated user
    const { data: { user }, error: authError } = await userClient.auth.getUser()
    if (authError || !user?.email) {
      return corsErrorResponse('Authentication failed', 401, origin)
    }

    // Call the credential health function
    const adminClient = createClient(supabaseUrl, supabaseServiceKey)
    const { data: healthData, error: healthError } = await adminClient
      .rpc('get_credential_health', { p_user_email: user.email })

    if (healthError) {
      console.error('Error fetching credential health:', healthError)
      return corsErrorResponse(`Database error: ${healthError.message}`, 500, origin)
    }

    // Format the response
    const credentials = healthData as CredentialHealth[]

    // Calculate overall health
    const configuredCredentials = credentials.filter(c => c.health_status !== 'not_configured')
    const expiredCount = credentials.filter(c => c.health_status === 'expired').length
    const warningCount = credentials.filter(c => c.health_status === 'warning').length

    let overallHealth: 'healthy' | 'warning' | 'critical' = 'healthy'
    if (expiredCount > 0) {
      overallHealth = 'critical'
    } else if (warningCount > 0) {
      overallHealth = 'warning'
    }

    // Find earliest expiring credential
    const nearestExpiry = credentials
      .filter(c => c.days_until_rotation !== null)
      .sort((a, b) => (a.days_until_rotation ?? Infinity) - (b.days_until_rotation ?? Infinity))[0]

    return corsJsonResponse({
      success: true,
      data: {
        user_email: user.email,
        overall_health: overallHealth,
        credentials,
        summary: {
          configured_count: configuredCredentials.length,
          healthy_count: credentials.filter(c => c.health_status === 'healthy').length,
          warning_count: warningCount,
          expired_count: expiredCount,
        },
        nearest_expiry: nearestExpiry ? {
          credential_type: nearestExpiry.credential_type,
          days_remaining: nearestExpiry.days_until_rotation,
        } : null,
      },
      metadata: {
        rotation_policy_days: ROTATION_DAYS,
        warning_threshold_days: WARNING_THRESHOLD,
        checked_at: new Date().toISOString(),
      }
    }, 200, origin)

  } catch (error) {
    console.error('Unexpected error:', error)
    return corsErrorResponse(`Internal server error: ${error.message}`, 500, origin)
  }
})
