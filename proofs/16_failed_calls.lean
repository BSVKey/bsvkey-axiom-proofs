import Mathlib

/-!
# 16 Inference broker: failed and partial calls

Row 05 bills two token counts and says nothing about how a call ends. This
row models the end of a call as the broker handles it:

* `done`: the answer finished.
* `timeout`: the broker's own watchdog cut the stream; what was delivered is
  billed and the answer is flagged as truncated.
* `providerError`: the model provider failed; the call returns 502 and is
  not charged, even if some tokens already reached the buyer.

Billed output is the delivered output plus hidden tokens (reasoning the meter
cannot see), and hidden output never exceeds the buyer's allowance. Every
charged call has a minimum charge, so unlike row 05's bare `bill`, a
zero-token call that is charged costs the minimum, not zero.

Proven: a provider error is free; a timeout costs exactly what a finished call
with the same delivered tokens costs; cutting a call short never costs more
than finishing it; the charge is bounded by delivered tokens plus the
allowance; and every charged call costs at least the minimum.
Discounts and web-search fees are not modelled.
-/

namespace BSVKey.FailedCalls

structure Price where
  inMsat : Nat   -- millisatoshis per input token
  outMsat : Nat  -- millisatoshis per output token
  minSats : Nat  -- minimum charge for any charged call

/-- Tokens behind one call: what the meter saw plus hidden provider tokens. -/
structure Usage where
  input : Nat
  delivered : Nat  -- output tokens that reached the buyer
  hiddenIn : Nat
  hiddenOut : Nat

inductive Outcome where
  | done (u : Usage)
  | timeout (u : Usage)
  | providerError (u : Usage)

def msat (p : Price) (u : Usage) : Nat :=
  (u.input + u.hiddenIn) * p.inMsat + (u.delivered + u.hiddenOut) * p.outMsat

/-- Whole satoshis, rounded up, never below the minimum. -/
def tokenCharge (p : Price) (u : Usage) : Nat := max p.minSats ((msat p u + 999) / 1000)

def charge (p : Price) : Outcome → Nat
  | .done u => tokenCharge p u
  | .timeout u => tokenCharge p u
  | .providerError _ => 0

theorem provider_error_free (p : Price) (u : Usage) :
    charge p (.providerError u) = 0 := rfl

theorem timeout_same_as_done (p : Price) (u : Usage) :
    charge p (.timeout u) = charge p (.done u) := rfl

theorem charged_at_least_min (p : Price) (u : Usage) :
    p.minSats ≤ charge p (.done u) ∧ p.minSats ≤ charge p (.timeout u) := by
  simp [charge, tokenCharge]

theorem zero_tokens_cost_min (p : Price) :
    charge p (.done ⟨0, 0, 0, 0⟩) = p.minSats := by
  simp [charge, tokenCharge, msat]

theorem charge_covers_cost (p : Price) (u : Usage) :
    1000 * charge p (.done u) ≥ msat p u := by
  simp only [charge, tokenCharge]
  have := le_max_right p.minSats ((msat p u + 999) / 1000)
  omega

/-- Cutting a call short (fewer delivered and hidden tokens) never costs more
than letting it finish. -/
theorem cut_short_le_finished (p : Price) (cut full : Usage)
    (hi : cut.input = full.input) (hhi : cut.hiddenIn ≤ full.hiddenIn)
    (hd : cut.delivered ≤ full.delivered) (hho : cut.hiddenOut ≤ full.hiddenOut) :
    charge p (.timeout cut) ≤ charge p (.done full) := by
  simp only [charge, tokenCharge]
  have : msat p cut ≤ msat p full := by
    unfold msat
    rw [hi]
    exact Nat.add_le_add (Nat.mul_le_mul_right _ (by omega))
      (Nat.mul_le_mul_right _ (by omega))
  exact max_le_max (le_refl _) (Nat.div_le_div_right (by omega))

/-- The bill is bounded by what was delivered plus the buyer's allowance for
hidden output: tokens neither delivered nor allowed are never charged. -/
theorem charge_le_delivered_plus_allowance (p : Price) (u : Usage) (allowance : Nat)
    (h : u.hiddenOut ≤ allowance) :
    charge p (.timeout u) ≤
      max p.minSats
        (((u.input + u.hiddenIn) * p.inMsat + (u.delivered + allowance) * p.outMsat + 999) / 1000) := by
  simp only [charge, tokenCharge, msat]
  have : (u.delivered + u.hiddenOut) * p.outMsat ≤ (u.delivered + allowance) * p.outMsat :=
    Nat.mul_le_mul_right _ (by omega)
  exact max_le_max (le_refl _) (Nat.div_le_div_right (by omega))

end BSVKey.FailedCalls
