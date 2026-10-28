import Mathlib

/-!
# 14 Reserve receipts: solvency is preserved

Model of BSVKey Reserve Receipts (proof of reserves). A custodian holds
reserves and owes each customer a balance. Withdrawals pay out of both;
deposits add to both. A withdrawal larger than the customer's balance is
refused.

Proven: if reserves cover all balances at the start, they still cover them
after any sequence of deposits and withdrawals.
-/

namespace BSVKey.Reserves

structure Book where
  reserves : Nat
  balances : List Nat

def liabilities (b : Book) : Nat := b.balances.sum

def Solvent (b : Book) : Prop := liabilities b ≤ b.reserves

/-- Customer `i` deposits `amt`. -/
def deposit (b : Book) (i amt : Nat) : Book :=
  if h : i < b.balances.length then
    ⟨b.reserves + amt, b.balances.set i (b.balances[i] + amt)⟩
  else b

/-- Customer `i` withdraws `amt`; refused if it exceeds their balance. -/
def withdraw (b : Book) (i amt : Nat) : Book :=
  if h : i < b.balances.length then
    if amt ≤ b.balances[i] then
      ⟨b.reserves - amt, b.balances.set i (b.balances[i] - amt)⟩
    else b
  else b

theorem sum_set (l : List Nat) (i : Nat) (h : i < l.length) (v : Nat) :
    (l.set i v).sum + l[i] = l.sum + v := by
  induction l generalizing i with
  | nil => simp at h
  | cons x xs ih =>
    cases i with
    | zero => simp; omega
    | succ j =>
      simp only [List.set_cons_succ, List.sum_cons, List.getElem_cons_succ]
      have := ih j (by simpa using h)
      omega

theorem deposit_solvent (b : Book) (i amt : Nat) (h : Solvent b) : Solvent (deposit b i amt) := by
  unfold deposit
  split
  · rename_i hi
    unfold Solvent liabilities at *
    have := sum_set b.balances i hi (b.balances[i] + amt)
    simp only at *
    omega
  · exact h

theorem withdraw_solvent (b : Book) (i amt : Nat) (h : Solvent b) : Solvent (withdraw b i amt) := by
  unfold withdraw
  split
  · rename_i hi
    split
    · rename_i ha
      unfold Solvent liabilities at *
      have hs := sum_set b.balances i hi (b.balances[i] - amt)
      have hle : b.balances[i] ≤ b.balances.sum := by
        have := sum_set b.balances i hi 0
        omega
      simp only at *
      omega
    · exact h
  · exact h

inductive Op
  | dep (i amt : Nat)
  | wd (i amt : Nat)

def runOps (b : Book) : List Op → Book
  | [] => b
  | .dep i a :: rest => runOps (deposit b i a) rest
  | .wd i a :: rest => runOps (withdraw b i a) rest

theorem always_solvent (b : Book) (ops : List Op) (h : Solvent b) : Solvent (runOps b ops) := by
  induction ops generalizing b with
  | nil => exact h
  | cons op rest ih =>
    cases op with
    | dep i a => exact ih _ (deposit_solvent b i a h)
    | wd i a => exact ih _ (withdraw_solvent b i a h)

end BSVKey.Reserves
