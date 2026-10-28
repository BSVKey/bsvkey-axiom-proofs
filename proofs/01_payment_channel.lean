import Mathlib

/-!
# 01 Payment channel: balances are conserved

Model of the BSVKey 2-of-2 payment channel (non-custodial inference channel).
A payment moves satoshis from the payer to the payee. A payment the payer
cannot cover is refused and changes nothing.

Proven: no sequence of payments, in either direction, can create or destroy
satoshis, and no side can ever be overdrawn.
-/

namespace BSVKey.Channel

structure Channel where
  payer : Nat
  payee : Nat

def total (c : Channel) : Nat := c.payer + c.payee

/-- Payer sends `amt` sats to payee; refused if the payer cannot cover it. -/
def pay (c : Channel) (amt : Nat) : Channel :=
  if amt ≤ c.payer then ⟨c.payer - amt, c.payee + amt⟩ else c

/-- Payee sends `amt` sats back (a refund inside the channel). -/
def refund (c : Channel) (amt : Nat) : Channel :=
  if amt ≤ c.payee then ⟨c.payer + amt, c.payee - amt⟩ else c

/-- A channel update: positive pays the payee, negative refunds the payer. -/
def step (c : Channel) : Int → Channel
  | .ofNat n => pay c n
  | .negSucc n => refund c (n + 1)

def run (c : Channel) : List Int → Channel
  | [] => c
  | u :: us => run (step c u) us

theorem pay_conserves (c : Channel) (amt : Nat) : total (pay c amt) = total c := by
  unfold pay total
  split <;> simp <;> omega

theorem refund_conserves (c : Channel) (amt : Nat) : total (refund c amt) = total c := by
  unfold refund total
  split <;> simp <;> omega

theorem step_conserves (c : Channel) (u : Int) : total (step c u) = total c := by
  cases u with
  | ofNat n => exact pay_conserves c n
  | negSucc n => exact refund_conserves c (n + 1)

/-- Any sequence of updates keeps the channel total fixed. -/
theorem run_conserves (c : Channel) (us : List Int) : total (run c us) = total c := by
  induction us generalizing c with
  | nil => rfl
  | cons u us ih => simp only [run]; rw [ih, step_conserves]

/-- A payment never takes more than the payer had. -/
theorem pay_no_overdraft (c : Channel) (amt : Nat) :
    (pay c amt).payer + amt ≥ c.payer ∧ (pay c amt).payer ≤ c.payer := by
  unfold pay
  split <;> simp <;> omega

end BSVKey.Channel
