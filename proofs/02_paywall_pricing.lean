import Mathlib

/-!
# 02 Paywall pricing: price floor and 3% margin

Model of the BSVKey Paywall Cloud price rule: the charged price is the larger
of a fixed floor and the upstream cost plus a 3% margin, rounded up to whole
satoshis.

Proven: the price is never below the floor, always covers cost plus 3%, never
overshoots by a whole satoshi beyond what the rule needs, and never falls when
cost rises.
-/

namespace BSVKey.Paywall

/-- Cost plus 3%, rounded up to whole satoshis. -/
def withMargin (cost : Nat) : Nat := (cost * 103 + 99) / 100

def price (cost floor : Nat) : Nat := max floor (withMargin cost)

theorem price_ge_floor (cost floor : Nat) : price cost floor ≥ floor := by
  unfold price; omega

theorem price_covers_margin (cost floor : Nat) : 100 * price cost floor ≥ 103 * cost := by
  unfold price withMargin; omega

/-- Rounding up adds less than one satoshi over the exact 3% figure. -/
theorem margin_tight (cost : Nat) : 100 * withMargin cost < 103 * cost + 100 := by
  unfold withMargin; omega

theorem price_monotone (c₁ c₂ floor : Nat) (h : c₁ ≤ c₂) :
    price c₁ floor ≤ price c₂ floor := by
  unfold price withMargin; omega

end BSVKey.Paywall
