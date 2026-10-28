import Mathlib

/-!
# 05 Inference broker: per-token billing is fair

Model of the BSV Inference Broker bill: input and output tokens are each
billed at a per-token price (in millisatoshis), and the total is rounded up
to whole satoshis.

Proven: splitting a job into pieces never costs the buyer less than the
honest whole-job figure minus rounding, billing is monotone in tokens, and
a zero-token request is free.
-/

namespace BSVKey.Metering

structure Price where
  inMsat : Nat   -- millisatoshis per input token
  outMsat : Nat  -- millisatoshis per output token

def msat (p : Price) (tin tout : Nat) : Nat := tin * p.inMsat + tout * p.outMsat

/-- Bill in whole satoshis, rounded up. -/
def bill (p : Price) (tin tout : Nat) : Nat := (msat p tin tout + 999) / 1000

theorem msat_additive (p : Price) (a b c d : Nat) :
    msat p (a + c) (b + d) = msat p a b + msat p c d := by
  unfold msat; ring

theorem bill_covers_cost (p : Price) (tin tout : Nat) :
    1000 * bill p tin tout ≥ msat p tin tout := by
  unfold bill; omega

theorem bill_zero (p : Price) : bill p 0 0 = 0 := by
  simp [bill, msat]

theorem bill_monotone (p : Price) (a b c d : Nat) (h1 : a ≤ c) (h2 : b ≤ d) :
    bill p a b ≤ bill p c d := by
  unfold bill
  have : msat p a b ≤ msat p c d := by
    unfold msat
    exact Nat.add_le_add (Nat.mul_le_mul_right _ h1) (Nat.mul_le_mul_right _ h2)
  omega

/-- Splitting a job in two costs at most one satoshi more than billing it whole. -/
theorem split_overhead (p : Price) (a b c d : Nat) :
    bill p a b + bill p c d ≤ bill p (a + c) (b + d) + 1 := by
  unfold bill; rw [msat_additive]; omega

end BSVKey.Metering
