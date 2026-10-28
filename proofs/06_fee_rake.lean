import Mathlib

/-!
# 06 Fee rake: the split always adds up

Model of a BSVKey fee rake (as in BSV Scribe): a fee in basis points is
taken from each payment and the rest goes to the seller.

Proven: seller share plus fee is exactly the payment (nothing lost or
invented), the fee never exceeds the payment, and a 0 bps rake is free.
-/

namespace BSVKey.Rake

def fee (amount bps : Nat) : Nat := amount * bps / 10000

def sellerShare (amount bps : Nat) : Nat := amount - fee amount bps

theorem fee_le_amount (amount bps : Nat) (h : bps ≤ 10000) : fee amount bps ≤ amount := by
  unfold fee
  calc amount * bps / 10000 ≤ amount * 10000 / 10000 :=
        Nat.div_le_div_right (Nat.mul_le_mul_left _ h)
    _ = amount := by simp

theorem split_exact (amount bps : Nat) (h : bps ≤ 10000) :
    sellerShare amount bps + fee amount bps = amount := by
  unfold sellerShare
  have := fee_le_amount amount bps h
  omega

theorem zero_rake (amount : Nat) : fee amount 0 = 0 := by simp [fee]

theorem fee_monotone (a b bps : Nat) (h : a ≤ b) : fee a bps ≤ fee b bps := by
  unfold fee
  exact Nat.div_le_div_right (Nat.mul_le_mul_right _ h)

end BSVKey.Rake
