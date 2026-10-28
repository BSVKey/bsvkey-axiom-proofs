import Mathlib

/-!
# 10 Merkle batch anchoring: one root commits to every leaf

Model of anchoring many receipts in one Bitcoin BSV transaction through a
Merkle root. Leaf and node hashes are domain separated (different tags, as
in the receipt tool in this repo), modelled as injective with disjoint
ranges.

Proven: two batches with the same root are identical, leaf for leaf and in
the same shape; and every leaf in a batch has an inclusion path that climbs
to the anchored root.

This is a model under idealised hashes. It does not prove SHA-256 is
collision resistant.
-/

namespace BSVKey.Merkle

inductive Tree
  | leaf : Nat → Tree
  | node : Tree → Tree → Tree
  deriving DecidableEq

variable (L : Nat → Nat) (N : Nat → Nat → Nat)

def root : Tree → Nat
  | .leaf x => L x
  | .node a b => N (root a) (root b)

theorem root_binding
    (hL : ∀ x y, L x = L y → x = y)
    (hN : ∀ a b c d, N a b = N c d → a = c ∧ b = d)
    (hsep : ∀ x a b, L x ≠ N a b) :
    ∀ t₁ t₂ : Tree, root L N t₁ = root L N t₂ → t₁ = t₂ := by
  intro t₁
  induction t₁ with
  | leaf x =>
    intro t₂ h
    cases t₂ with
    | leaf y => rw [hL x y h]
    | node a b => exact absurd h (hsep _ _ _)
  | node a b iha ihb =>
    intro t₂ h
    cases t₂ with
    | leaf y => exact absurd h.symm (hsep _ _ _)
    | node c d =>
      obtain ⟨h1, h2⟩ := hN _ _ _ _ h
      rw [iha c h1, ihb d h2]

/-- An inclusion path: at each level, the sibling hash and which side it is on. -/
def climb (h : Nat) : List (Bool × Nat) → Nat
  | [] => h
  | (true, s) :: rest => climb (N s h) rest   -- sibling on the left
  | (false, s) :: rest => climb (N h s) rest  -- sibling on the right

inductive Mem : Nat → Tree → Prop
  | here (x : Nat) : Mem x (.leaf x)
  | left {x : Nat} {a : Tree} (b : Tree) : Mem x a → Mem x (.node a b)
  | right {x : Nat} (a : Tree) {b : Tree} : Mem x b → Mem x (.node a b)

theorem climb_append (h : Nat) (p q : List (Bool × Nat)) :
    climb N h (p ++ q) = climb N (climb N h p) q := by
  induction p generalizing h with
  | nil => rfl
  | cons e p ih => obtain ⟨b, s⟩ := e; cases b <;> simp [climb, ih]

/-- Every leaf of a tree has an inclusion path that climbs to the tree's root. -/
theorem path_exists (x : Nat) (t : Tree) (hm : Mem x t) :
    ∃ p : List (Bool × Nat), climb N (L x) p = root L N t := by
  induction hm with
  | here => exact ⟨[], rfl⟩
  | left b _ ih =>
    obtain ⟨p, hp⟩ := ih
    exact ⟨p ++ [(false, root L N b)], by rw [climb_append, hp]; rfl⟩
  | right a _ ih =>
    obtain ⟨p, hp⟩ := ih
    exact ⟨p ++ [(true, root L N a)], by rw [climb_append, hp]; rfl⟩

end BSVKey.Merkle
