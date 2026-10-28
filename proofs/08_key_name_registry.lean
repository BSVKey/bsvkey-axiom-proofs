import Mathlib

/-!
# 08 .key names: one name, one owner

Model of the BSVKey .key name registry: a registration succeeds only if the
name is not already taken. Transfers need the current owner.

Proven: every name in the registry has exactly one owner after any sequence
of registrations, and a stranger can never transfer someone else's name.
-/

namespace BSVKey.Names

abbrev Registry := List (String × String)  -- (name, owner)

def taken (r : Registry) (n : String) : Bool := r.any (fun e => e.1 = n)

def register (r : Registry) (n owner : String) : Registry :=
  if taken r n then r else (n, owner) :: r

def registerAll (r : Registry) : List (String × String) → Registry
  | [] => r
  | (n, o) :: rest => registerAll (register r n o) rest

/-- Names in the registry are unique. -/
def Unique (r : Registry) : Prop := (r.map Prod.fst).Nodup

theorem register_unique (r : Registry) (n o : String) (h : Unique r) :
    Unique (register r n o) := by
  unfold register Unique at *
  split
  · exact h
  · rename_i ht
    simp only [List.map_cons, List.nodup_cons]
    refine ⟨?_, h⟩
    simp only [taken, List.any_eq_true, decide_eq_true_eq, not_exists, not_and] at ht
    simp only [List.mem_map, not_exists, not_and]
    intro e he hfe
    exact ht e he hfe

theorem registerAll_unique (r : Registry) (xs : List (String × String)) (h : Unique r) :
    Unique (registerAll r xs) := by
  induction xs generalizing r with
  | nil => exact h
  | cons x xs ih => obtain ⟨n, o⟩ := x; exact ih _ (register_unique r n o h)

/-- Starting from an empty registry, no name ever has two owners. -/
theorem no_double_owner (xs : List (String × String)) : Unique (registerAll [] xs) :=
  registerAll_unique [] xs (by simp [Unique])

/-- Transfer requires the caller to be the current owner. -/
def transfer (r : Registry) (n caller newOwner : String) : Registry :=
  r.map (fun e => if e.1 = n ∧ e.2 = caller then (n, newOwner) else e)

theorem stranger_cannot_transfer (r : Registry) (n caller newOwner : String)
    (h : ∀ e ∈ r, e.1 = n → e.2 ≠ caller) : transfer r n caller newOwner = r := by
  unfold transfer
  conv_rhs => rw [← List.map_id r]
  apply List.map_congr_left
  intro e he
  simp only [id]
  split
  · rename_i hc; exact absurd hc.2 (h e he hc.1)
  · rfl

end BSVKey.Names
