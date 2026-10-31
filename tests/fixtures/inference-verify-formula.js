// Copied byte for byte from the Inference Broker's public receipt verifier,
// https://inference.bsvkey.com/js/verify.js (2026-10-30). The broker bills with
// the same frozen formula. tools/row16_published.mjs checks this copy against
// the Lean model in proofs/16_failed_calls.lean, and with --live checks that
// the served file still contains exactly this function.
function computeChargeSats(r) {
  const hi = r.hiddenInputTokens || 0, ho = r.hiddenOutputTokens || 0;
  const tokenSats = Math.ceil(((r.inputTokens + hi) * r.rateInPer1k + (r.outputTokens + ho) * r.rateOutPer1k) / 1000);
  const gross = tokenSats + (r.webSearchSats || 0);
  return Math.max(r.minChargeSats, Math.ceil((gross * (100 - (r.discountPct || 0))) / 100));
}
