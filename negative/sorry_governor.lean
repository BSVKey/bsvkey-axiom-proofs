import Mathlib

/-!
# Negative control: an unfinished proof must be rejected

A `sorry` is Lean's "trust me" placeholder. A checker that accepted it would
make every receipt in this repo worthless, so AXLE must refuse this file.
-/

namespace BSVKey.GovernorSorry

theorem cap_never_exceeded (cap spent cost : Nat) (h : spent ≤ cap) :
    spent + cost ≤ cap := by
  sorry

end BSVKey.GovernorSorry
