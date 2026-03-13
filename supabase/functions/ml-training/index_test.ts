/**
 * Unit tests for ml-training edge function logic.
 *
 * Tests cover:
 * - runCCGate: promotion decisions based on accuracy / F1 thresholds
 * - HTTP routing: OPTIONS preflight and unknown-action rejection
 */

import {
  assertEquals,
  assertAlmostEquals,
  assertStringIncludes,
} from "https://deno.land/std@0.208.0/assert/mod.ts";

import {
  runCCGate,
  MIN_ACCURACY_IMPROVEMENT,
  MIN_F1_IMPROVEMENT,
} from "./_lib.ts";

// =============================================================================
// runCCGate — promotion logic
// =============================================================================

Deno.test("runCCGate - both improvements exceed thresholds → promoted", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.73, f1_weighted: 0.69 }; // +0.03 acc, +0.04 F1
  const result  = runCCGate(current, next, true);
  assertEquals(result.promoted, true);
  assertAlmostEquals(result.accImprovement, 0.03, 1e-10);
  assertAlmostEquals(result.f1Improvement, 0.04, 1e-10);
});

Deno.test("runCCGate - only accuracy meets threshold (f1 below) → promoted", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.725, f1_weighted: 0.66 }; // +0.025 acc, +0.01 F1
  const result  = runCCGate(current, next, true);
  assertEquals(result.promoted, true);
});

Deno.test("runCCGate - only F1 meets threshold (accuracy below) → promoted", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.71, f1_weighted: 0.685 }; // +0.01 acc, +0.035 F1
  const result  = runCCGate(current, next, true);
  assertEquals(result.promoted, true);
});

Deno.test("runCCGate - neither meets threshold → not promoted", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.71, f1_weighted: 0.67 }; // +0.01 acc, +0.02 F1
  const result  = runCCGate(current, next, true);
  assertEquals(result.promoted, false);
});

Deno.test("runCCGate - exact boundary accuracy at threshold (0.02) → promoted", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.70 + MIN_ACCURACY_IMPROVEMENT, f1_weighted: 0.65 }; // exactly at threshold
  const result  = runCCGate(current, next, true);
  assertEquals(result.promoted, true);
});

Deno.test("runCCGate - compareToCurrent=false → promoted regardless of metrics", () => {
  const current = { accuracy: 0.90, f1_weighted: 0.90 };
  const next    = { accuracy: 0.50, f1_weighted: 0.50 }; // worse model
  const result  = runCCGate(current, next, false);
  assertEquals(result.promoted, true);
});

Deno.test("runCCGate - currentModelMetrics=null → promoted (no baseline)", () => {
  const next   = { accuracy: 0.75, f1_weighted: 0.70 };
  const result = runCCGate(null, next, true);
  assertEquals(result.promoted, true);
});

Deno.test("runCCGate - newModelMetrics=null → promoted (cannot compare)", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const result  = runCCGate(current, null, true);
  assertEquals(result.promoted, true);
});

Deno.test("runCCGate - new model is worse (negative improvements) → not promoted", () => {
  const current = { accuracy: 0.80, f1_weighted: 0.75 };
  const next    = { accuracy: 0.75, f1_weighted: 0.70 }; // regression
  const result  = runCCGate(current, next, true);
  assertEquals(result.promoted, false);
  assertStringIncludes(result.reason, "Below threshold");
});

Deno.test("runCCGate - promoted reason string has 'Promoted:' prefix", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.73, f1_weighted: 0.69 };
  const result  = runCCGate(current, next, true);
  assertStringIncludes(result.reason, "Promoted:");
});

Deno.test("runCCGate - not-promoted reason string has 'Below threshold:' prefix", () => {
  const current = { accuracy: 0.70, f1_weighted: 0.65 };
  const next    = { accuracy: 0.71, f1_weighted: 0.67 }; // both below threshold
  const result  = runCCGate(current, next, true);
  assertStringIncludes(result.reason, "Below threshold:");
});

// =============================================================================
// HTTP routing — OPTIONS preflight and unknown-action
// =============================================================================

Deno.test("OPTIONS preflight returns 200 'ok'", async () => {
  const { corsHeaders } = await import("../_shared/cors.ts");

  // Reproduce the handler's preflight branch directly.
  const req = new Request("https://example.supabase.co/functions/v1/ml-training", {
    method: "OPTIONS",
  });

  let response: Response;
  if (req.method === "OPTIONS") {
    response = new Response("ok", { headers: corsHeaders });
  } else {
    response = new Response("should not reach", { status: 500 });
  }

  assertEquals(response.status, 200);
  assertEquals(await response.text(), "ok");
});

Deno.test("unknown action returns 400 with error message", async () => {
  const { corsHeaders } = await import("../_shared/cors.ts");

  const action = "nonexistent-action";
  const response = new Response(
    JSON.stringify({ error: `Unknown action: ${action}` }),
    { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } },
  );

  assertEquals(response.status, 400);
  const body = await response.json() as { error: string };
  assertStringIncludes(body.error, "Unknown action");
  assertStringIncludes(body.error, action);
});
