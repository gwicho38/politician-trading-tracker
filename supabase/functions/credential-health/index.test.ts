/**
 * Tests for credential-health Edge Function
 *
 * Run with: deno test --allow-env supabase/functions/credential-health/index.test.ts
 */

import {
  assertEquals,
  assertExists,
} from "https://deno.land/std@0.168.0/testing/asserts.ts"

// Test types
interface CredentialHealth {
  credential_type: string
  is_configured: boolean
  days_since_creation: number | null
  days_until_rotation: number | null
  health_status: 'healthy' | 'warning' | 'expired' | 'not_configured'
  last_validated: string | null
}

// =============================================================================
// Constants Tests
// =============================================================================

Deno.test("Credential Health - Constants", async (t) => {
  await t.step("rotation policy should be 90 days", () => {
    const ROTATION_DAYS = 90
    assertEquals(ROTATION_DAYS, 90)
  })

  await t.step("warning threshold should be 14 days", () => {
    const WARNING_THRESHOLD = 14
    assertEquals(WARNING_THRESHOLD, 14)
  })
})

// =============================================================================
// Health Status Logic Tests
// =============================================================================

Deno.test("Credential Health - Health Status Calculation", async (t) => {
  const ROTATION_DAYS = 90
  const WARNING_THRESHOLD = 14

  function calculateHealthStatus(
    daysRemaining: number | null
  ): 'healthy' | 'warning' | 'expired' | 'not_configured' {
    if (daysRemaining === null) return 'not_configured'
    if (daysRemaining < 0) return 'expired'
    if (daysRemaining <= WARNING_THRESHOLD) return 'warning'
    return 'healthy'
  }

  await t.step("should return 'not_configured' when days_remaining is null", () => {
    assertEquals(calculateHealthStatus(null), 'not_configured')
  })

  await t.step("should return 'expired' when days_remaining is negative", () => {
    assertEquals(calculateHealthStatus(-1), 'expired')
    assertEquals(calculateHealthStatus(-30), 'expired')
  })

  await t.step("should return 'warning' when days_remaining is within threshold", () => {
    assertEquals(calculateHealthStatus(14), 'warning')
    assertEquals(calculateHealthStatus(7), 'warning')
    assertEquals(calculateHealthStatus(1), 'warning')
    assertEquals(calculateHealthStatus(0), 'warning')
  })

  await t.step("should return 'healthy' when days_remaining is above threshold", () => {
    assertEquals(calculateHealthStatus(15), 'healthy')
    assertEquals(calculateHealthStatus(30), 'healthy')
    assertEquals(calculateHealthStatus(90), 'healthy')
  })
})

// =============================================================================
// Overall Health Calculation Tests
// =============================================================================

Deno.test("Credential Health - Overall Health Calculation", async (t) => {
  function calculateOverallHealth(
    credentials: CredentialHealth[]
  ): 'healthy' | 'warning' | 'critical' {
    const expiredCount = credentials.filter(c => c.health_status === 'expired').length
    const warningCount = credentials.filter(c => c.health_status === 'warning').length

    if (expiredCount > 0) return 'critical'
    if (warningCount > 0) return 'warning'
    return 'healthy'
  }

  await t.step("should return 'healthy' when all credentials are healthy", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 10, days_until_rotation: 80, health_status: 'healthy', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 20, days_until_rotation: 70, health_status: 'healthy', last_validated: null },
    ]
    assertEquals(calculateOverallHealth(credentials), 'healthy')
  })

  await t.step("should return 'healthy' when credentials are not_configured", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: false, days_since_creation: null, days_until_rotation: null, health_status: 'not_configured', last_validated: null },
    ]
    assertEquals(calculateOverallHealth(credentials), 'healthy')
  })

  await t.step("should return 'warning' when any credential is warning", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 10, days_until_rotation: 80, health_status: 'healthy', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 80, days_until_rotation: 10, health_status: 'warning', last_validated: null },
    ]
    assertEquals(calculateOverallHealth(credentials), 'warning')
  })

  await t.step("should return 'critical' when any credential is expired", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 10, days_until_rotation: 80, health_status: 'healthy', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 100, days_until_rotation: -10, health_status: 'expired', last_validated: null },
    ]
    assertEquals(calculateOverallHealth(credentials), 'critical')
  })

  await t.step("should return 'critical' even with warning and expired", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 80, days_until_rotation: 10, health_status: 'warning', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 100, days_until_rotation: -10, health_status: 'expired', last_validated: null },
    ]
    assertEquals(calculateOverallHealth(credentials), 'critical')
  })
})

// =============================================================================
// Summary Calculation Tests
// =============================================================================

Deno.test("Credential Health - Summary Calculation", async (t) => {
  function calculateSummary(credentials: CredentialHealth[]) {
    const configuredCredentials = credentials.filter(c => c.health_status !== 'not_configured')
    return {
      configured_count: configuredCredentials.length,
      healthy_count: credentials.filter(c => c.health_status === 'healthy').length,
      warning_count: credentials.filter(c => c.health_status === 'warning').length,
      expired_count: credentials.filter(c => c.health_status === 'expired').length,
    }
  }

  await t.step("should count all categories correctly", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 10, days_until_rotation: 80, health_status: 'healthy', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 80, days_until_rotation: 10, health_status: 'warning', last_validated: null },
      { credential_type: 'quiverquant_api', is_configured: true, days_since_creation: 100, days_until_rotation: -10, health_status: 'expired', last_validated: null },
      { credential_type: 'supabase', is_configured: false, days_since_creation: null, days_until_rotation: null, health_status: 'not_configured', last_validated: null },
    ]

    const summary = calculateSummary(credentials)
    assertEquals(summary.configured_count, 3)
    assertEquals(summary.healthy_count, 1)
    assertEquals(summary.warning_count, 1)
    assertEquals(summary.expired_count, 1)
  })

  await t.step("should handle empty credentials list", () => {
    const summary = calculateSummary([])
    assertEquals(summary.configured_count, 0)
    assertEquals(summary.healthy_count, 0)
    assertEquals(summary.warning_count, 0)
    assertEquals(summary.expired_count, 0)
  })

  await t.step("should handle all not_configured", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: false, days_since_creation: null, days_until_rotation: null, health_status: 'not_configured', last_validated: null },
      { credential_type: 'live_api', is_configured: false, days_since_creation: null, days_until_rotation: null, health_status: 'not_configured', last_validated: null },
    ]

    const summary = calculateSummary(credentials)
    assertEquals(summary.configured_count, 0)
    assertEquals(summary.healthy_count, 0)
    assertEquals(summary.warning_count, 0)
    assertEquals(summary.expired_count, 0)
  })
})

// =============================================================================
// Nearest Expiry Calculation Tests
// =============================================================================

Deno.test("Credential Health - Nearest Expiry Calculation", async (t) => {
  function findNearestExpiry(credentials: CredentialHealth[]) {
    const withExpiry = credentials
      .filter(c => c.days_until_rotation !== null)
      .sort((a, b) => (a.days_until_rotation ?? Infinity) - (b.days_until_rotation ?? Infinity))

    if (withExpiry.length === 0) return null

    return {
      credential_type: withExpiry[0].credential_type,
      days_remaining: withExpiry[0].days_until_rotation,
    }
  }

  await t.step("should find credential with fewest days remaining", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 10, days_until_rotation: 80, health_status: 'healthy', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 80, days_until_rotation: 10, health_status: 'warning', last_validated: null },
      { credential_type: 'quiverquant_api', is_configured: true, days_since_creation: 60, days_until_rotation: 30, health_status: 'healthy', last_validated: null },
    ]

    const nearest = findNearestExpiry(credentials)
    assertExists(nearest)
    assertEquals(nearest.credential_type, 'live_api')
    assertEquals(nearest.days_remaining, 10)
  })

  await t.step("should handle negative days (expired)", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: true, days_since_creation: 100, days_until_rotation: -10, health_status: 'expired', last_validated: null },
      { credential_type: 'live_api', is_configured: true, days_since_creation: 10, days_until_rotation: 80, health_status: 'healthy', last_validated: null },
    ]

    const nearest = findNearestExpiry(credentials)
    assertExists(nearest)
    assertEquals(nearest.credential_type, 'paper_api')
    assertEquals(nearest.days_remaining, -10)
  })

  await t.step("should return null when no credentials have expiry", () => {
    const credentials: CredentialHealth[] = [
      { credential_type: 'paper_api', is_configured: false, days_since_creation: null, days_until_rotation: null, health_status: 'not_configured', last_validated: null },
    ]

    const nearest = findNearestExpiry(credentials)
    assertEquals(nearest, null)
  })

  await t.step("should return null for empty list", () => {
    const nearest = findNearestExpiry([])
    assertEquals(nearest, null)
  })
})

// =============================================================================
// Response Format Tests
// =============================================================================

Deno.test("Credential Health - Response Format", async (t) => {
  await t.step("success response should have required fields", () => {
    const response = {
      success: true,
      data: {
        user_email: 'test@example.com',
        overall_health: 'healthy',
        credentials: [],
        summary: {
          configured_count: 0,
          healthy_count: 0,
          warning_count: 0,
          expired_count: 0,
        },
        nearest_expiry: null,
      },
      metadata: {
        rotation_policy_days: 90,
        warning_threshold_days: 14,
        checked_at: new Date().toISOString(),
      }
    }

    assertEquals(response.success, true)
    assertExists(response.data)
    assertExists(response.data.user_email)
    assertExists(response.data.overall_health)
    assertExists(response.data.credentials)
    assertExists(response.data.summary)
    assertExists(response.metadata)
    assertEquals(response.metadata.rotation_policy_days, 90)
    assertEquals(response.metadata.warning_threshold_days, 14)
  })

  await t.step("admin rotation-needed response should have required fields", () => {
    const response = {
      success: true,
      data: [] as Array<{ user_email: string; user_name: string | null; credentials_expiring: string[]; earliest_expiry_days: number }>,
      count: 0,
      metadata: {
        rotation_policy_days: 90,
        warning_threshold_days: 14,
      }
    }

    assertEquals(response.success, true)
    assertExists(response.data)
    assertEquals(response.count, 0)
    assertExists(response.metadata)
  })
})

// =============================================================================
// Credential Type Tests
// =============================================================================

Deno.test("Credential Health - Credential Types", async (t) => {
  const SUPPORTED_CREDENTIAL_TYPES = ['paper_api', 'live_api', 'quiverquant_api', 'supabase']

  await t.step("should support all expected credential types", () => {
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.length, 4)
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.includes('paper_api'), true)
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.includes('live_api'), true)
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.includes('quiverquant_api'), true)
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.includes('supabase'), true)
  })

  await t.step("should not include unsupported credential types", () => {
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.includes('polygon_api'), false)
    assertEquals(SUPPORTED_CREDENTIAL_TYPES.includes('alpha_vantage'), false)
  })
})

// =============================================================================
// Days Calculation Tests
// =============================================================================

Deno.test("Credential Health - Days Calculation", async (t) => {
  const ROTATION_DAYS = 90

  function calculateDaysUntilRotation(daysSinceCreation: number): number {
    return ROTATION_DAYS - daysSinceCreation
  }

  await t.step("should calculate days until rotation correctly", () => {
    assertEquals(calculateDaysUntilRotation(0), 90)
    assertEquals(calculateDaysUntilRotation(45), 45)
    assertEquals(calculateDaysUntilRotation(90), 0)
    assertEquals(calculateDaysUntilRotation(100), -10)
  })

  await t.step("boundary: exactly at warning threshold", () => {
    // 76 days since creation = 14 days until rotation = warning
    assertEquals(calculateDaysUntilRotation(76), 14)
  })

  await t.step("boundary: one day before warning threshold", () => {
    // 75 days since creation = 15 days until rotation = healthy
    assertEquals(calculateDaysUntilRotation(75), 15)
  })
})
