/**
 * Pure logic for the ml-training edge function.
 * Extracted here so it can be unit-tested without the Deno serve() runtime.
 */

// ---------------------------------------------------------------------------
// Champion/Challenger thresholds
// ---------------------------------------------------------------------------
export const MIN_ACCURACY_IMPROVEMENT = 0.02 // 2 percentage-point improvement
export const MIN_F1_IMPROVEMENT = 0.03       // 3 percentage-point improvement

// ---------------------------------------------------------------------------
// C/C gate — pure function, no I/O
// ---------------------------------------------------------------------------
export interface CCGateResult {
  promoted: boolean
  reason: string
  accImprovement: number
  f1Improvement: number
}

export function runCCGate(
  currentModelMetrics: Record<string, number> | null,
  newModelMetrics: Record<string, number> | null,
  compareToCurrent: boolean,
): CCGateResult {
  if (!compareToCurrent || !currentModelMetrics || !newModelMetrics) {
    return {
      promoted: true,
      reason: 'No current model to compare against — auto-promoting',
      accImprovement: 0,
      f1Improvement: 0,
    }
  }

  const oldAcc = currentModelMetrics.accuracy ?? 0
  const newAcc = newModelMetrics.accuracy ?? 0
  const oldF1 = currentModelMetrics.f1_weighted ?? 0
  const newF1 = newModelMetrics.f1_weighted ?? 0

  const accImprovement = newAcc - oldAcc
  const f1Improvement = newF1 - oldF1

  const meetsAccuracy = accImprovement >= MIN_ACCURACY_IMPROVEMENT
  const meetsF1 = f1Improvement >= MIN_F1_IMPROVEMENT

  if (meetsAccuracy || meetsF1) {
    return {
      promoted: true,
      reason:
        `Promoted: accuracy ${accImprovement >= 0 ? '+' : ''}${(accImprovement * 100).toFixed(1)}%` +
        `, F1 ${f1Improvement >= 0 ? '+' : ''}${(f1Improvement * 100).toFixed(1)}%`,
      accImprovement,
      f1Improvement,
    }
  }

  return {
    promoted: false,
    reason:
      `Below threshold: accuracy ${accImprovement >= 0 ? '+' : ''}${(accImprovement * 100).toFixed(1)}%` +
      ` (need +${(MIN_ACCURACY_IMPROVEMENT * 100).toFixed(0)}%)` +
      `, F1 ${f1Improvement >= 0 ? '+' : ''}${(f1Improvement * 100).toFixed(1)}%` +
      ` (need +${(MIN_F1_IMPROVEMENT * 100).toFixed(0)}%)`,
    accImprovement,
    f1Improvement,
  }
}
