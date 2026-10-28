import Mathlib

/-!
# 09 Receipt hash chain: history cannot be rewritten

Model of BSVKey receipts linked into a hash chain: each new head is
H(previous head, receipt). We assume H is collision resistant, modelled as
injective, and never outputs the empty head 0.

Proven: two chains with the same head are the same chain, so changing,
removing, inserting or reordering any receipt changes the head that was
anchored on Bitcoin BSV.

This is a model under an idealised hash. It does not prove SHA-256 is
collision resistant.
-/

namespace BSVKey.HashChain

variable (H : Nat → Nat → Nat)

def head : List Nat → Nat
  | [] => 0
  | r :: rs => H (head rs) r

theorem head_determines_chain
    (hinj : ∀ a b c d, H a b = H c d → a = c ∧ b = d)
    (hnz : ∀ a b, H a b ≠ 0) :
    ∀ l₁ l₂ : List Nat, head H l₁ = head H l₂ → l₁ = l₂ := by
  intro l₁
  induction l₁ with
  | nil =>
    intro l₂ h
    cases l₂ with
    | nil => rfl
    | cons r rs => exact absurd h.symm (hnz _ _)
  | cons r rs ih =>
    intro l₂ h
    cases l₂ with
    | nil => exact absurd h (hnz _ _)
    | cons r' rs' =>
      obtain ⟨h1, h2⟩ := hinj _ _ _ _ h
      rw [ih rs' h1, h2]

/-- Tampering with any receipt is detected by the anchored head. -/
theorem tamper_detected
    (hinj : ∀ a b c d, H a b = H c d → a = c ∧ b = d)
    (hnz : ∀ a b, H a b ≠ 0)
    (l₁ l₂ : List Nat) (hne : l₁ ≠ l₂) : head H l₁ ≠ head H l₂ :=
  fun h => hne (head_determines_chain H hinj hnz l₁ l₂ h)

end BSVKey.HashChain
