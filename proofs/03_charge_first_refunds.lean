import Mathlib

/-!
# 03 Charge first, refund after: refunds can never exceed the charge

Model of the Paywall Cloud charge-first flow: the buyer is charged up front,
and any number of partial refunds may follow. A refund that would push total
refunds past the charge is refused.

Proven: whatever refund requests arrive, in any order, total refunded never
exceeds the amount charged, and the merchant's net is never negative.
-/

namespace BSVKey.Refunds

structure Order where
  charged : Nat
  refunded : Nat

def requestRefund (o : Order) (amt : Nat) : Order :=
  if o.refunded + amt ≤ o.charged then { o with refunded := o.refunded + amt } else o

def processAll (o : Order) : List Nat → Order
  | [] => o
  | a :: as => processAll (requestRefund o a) as

def Valid (o : Order) : Prop := o.refunded ≤ o.charged

theorem requestRefund_valid (o : Order) (amt : Nat) (h : Valid o) :
    Valid (requestRefund o amt) := by
  unfold requestRefund Valid at *
  split
  · simp; omega
  · exact h

theorem processAll_valid (o : Order) (rs : List Nat) (h : Valid o) :
    Valid (processAll o rs) := by
  induction rs generalizing o with
  | nil => exact h
  | cons r rs ih => exact ih _ (requestRefund_valid o r h)

theorem charge_unchanged (o : Order) (rs : List Nat) :
    (processAll o rs).charged = o.charged := by
  induction rs generalizing o with
  | nil => rfl
  | cons r rs ih =>
    simp only [processAll]; rw [ih]
    unfold requestRefund; split <;> rfl

/-- Starting from a fresh charge, the merchant keeps a non-negative net. -/
theorem fresh_order_safe (charge : Nat) (rs : List Nat) :
    (processAll ⟨charge, 0⟩ rs).refunded ≤ charge := by
  have h := processAll_valid ⟨charge, 0⟩ rs (by simp [Valid])
  have hc := charge_unchanged ⟨charge, 0⟩ rs
  unfold Valid at h; rw [hc] at h; exact h

end BSVKey.Refunds
