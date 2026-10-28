import Mathlib

/-!
# 07 Name Market: a trade is all or nothing

Model of the trustless BSVKey Name Market. A trade settles in one atomic
transaction: either the name moves to the buyer and the asking price moves
to the seller, or nothing moves.

Proven: there is no outcome where the buyer gets the name without paying, or
the seller is paid without giving up the name, and money is conserved.
-/

namespace BSVKey.NameMarket

structure State where
  owner : String
  sellerSats : Nat
  buyerSats : Nat

/-- Settle a listing. Valid only if the current owner is the seller, the
seller signed, and the buyer can pay. Otherwise the state is unchanged. -/
def settle (s : State) (seller buyer : String) (price : Nat) (sellerSigned : Bool) : State :=
  if s.owner = seller ∧ sellerSigned = true ∧ price ≤ s.buyerSats then
    ⟨buyer, s.sellerSats + price, s.buyerSats - price⟩
  else s

theorem atomic (s : State) (seller buyer : String) (price : Nat) (sig : Bool) :
    let s' := settle s seller buyer price sig
    (s'.owner = buyer ∧ s'.sellerSats = s.sellerSats + price ∧ s'.buyerSats + price = s.buyerSats)
    ∨ s' = s := by
  simp only [settle]
  split
  · left; rename_i h; simp; omega
  · right; rfl

theorem money_conserved (s : State) (seller buyer : String) (price : Nat) (sig : Bool) :
    (settle s seller buyer price sig).sellerSats + (settle s seller buyer price sig).buyerSats
      = s.sellerSats + s.buyerSats := by
  unfold settle; split
  · rename_i h; simp; omega
  · rfl

/-- Without the seller's signature, the name never moves. -/
theorem no_sig_no_move (s : State) (seller buyer : String) (price : Nat) :
    settle s seller buyer price false = s := by
  simp [settle]

/-- A buyer who cannot pay never gets the name. -/
theorem must_pay (s : State) (seller buyer : String) (price : Nat) (sig : Bool)
    (h : s.buyerSats < price) : settle s seller buyer price sig = s := by
  unfold settle; split
  · rename_i h'; omega
  · rfl

end BSVKey.NameMarket
