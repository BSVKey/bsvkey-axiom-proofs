import Mathlib

/-!
# Negative control: a buggy price rule must be rejected

Same claim as proofs/02_paywall_pricing.lean, but the price rounds the 3%
margin DOWN instead of up. The claim "price covers cost plus 3%" is then
false (cost 1 gives price 1, not enough), so AXLE must refuse this file
and `disprove` should find the counterexample.
-/

namespace BSVKey.PaywallBug

def withMargin (cost : Nat) : Nat := cost * 103 / 100

def price (cost floor : Nat) : Nat := max floor (withMargin cost)

theorem price_covers_margin (cost : Nat) : 100 * price cost 0 ≥ 103 * cost := by
  unfold price withMargin; omega

end BSVKey.PaywallBug
