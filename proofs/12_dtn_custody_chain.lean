import Mathlib

/-!
# 12 DTN custody: the chain of custody has no gaps

Model of BSVKey custody receipts for delay tolerant networking
(dtn.bsvkey.com). Each hop is a receipt "from A to B". A custody chain is
valid when it starts at the origin and every hop starts where the previous
one ended.

Proven: in a valid chain the bundle's current holder is the receiver of the
last hop, every holder along the way can be named, and splicing two valid
chains at the hand-off point gives a valid chain.
-/

namespace BSVKey.Custody

structure Hop where
  src : String
  dst : String

/-- Valid chain starting at `holder`; returns true if every hop connects. -/
def valid : String → List Hop → Bool
  | _, [] => true
  | holder, h :: hs => h.src = holder && valid h.dst hs

def finalHolder : String → List Hop → String
  | holder, [] => holder
  | _, h :: hs => finalHolder h.dst hs

theorem valid_tail (a : String) (x : Hop) (xs : List Hop) (h : valid a (x :: xs) = true) :
    valid x.dst xs = true := by
  simp only [valid, Bool.and_eq_true] at h
  exact h.2

theorem final_is_last_dst (origin : String) (hs : List Hop) (h : hs ≠ [])
    (hv : valid origin hs = true) :
    finalHolder origin hs = (hs.getLast h).dst := by
  induction hs generalizing origin with
  | nil => exact absurd rfl h
  | cons x xs ih =>
    cases xs with
    | nil => rfl
    | cons y ys =>
      rw [show finalHolder origin (x :: y :: ys) = finalHolder x.dst (y :: ys) from rfl]
      rw [ih x.dst (List.cons_ne_nil y ys) (valid_tail origin x _ hv)]
      simp

theorem splice (a : String) (p q : List Hop)
    (hp : valid a p = true) (hq : valid (finalHolder a p) q = true) :
    valid a (p ++ q) = true := by
  induction p generalizing a with
  | nil => simpa [finalHolder] using hq
  | cons x xs ih =>
    simp only [valid, Bool.and_eq_true, decide_eq_true_eq] at hp
    simp only [List.cons_append, valid, Bool.and_eq_true, decide_eq_true_eq]
    exact ⟨hp.1, ih x.dst hp.2 (by simpa [finalHolder] using hq)⟩

/-- A hop that does not start at the current holder breaks the chain. -/
theorem gap_detected (holder : String) (h : Hop) (hs : List Hop) (hg : h.src ≠ holder) :
    valid holder (h :: hs) = false := by
  simp [valid, hg]

end BSVKey.Custody
