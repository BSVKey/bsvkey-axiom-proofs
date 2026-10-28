import Mathlib

/-!
# 04 Governor AI spend firewall: the cap is never exceeded

Model of governor.bsvkey.com: each AI request carries a cost; the Governor
approves it only if spend so far plus this cost stays within the cap, and
blocks it otherwise. A kill switch blocks everything.

Proven: for any stream of requests, spend never passes the cap, and a
killed Governor approves nothing and changes nothing.
-/

namespace BSVKey.Governor

structure Gov where
  cap : Nat
  spent : Nat
  killed : Bool

def approve (g : Gov) (cost : Nat) : Bool :=
  !g.killed && g.spent + cost ≤ g.cap

def handle (g : Gov) (cost : Nat) : Gov :=
  if approve g cost then { g with spent := g.spent + cost } else g

def handleAll (g : Gov) : List Nat → Gov
  | [] => g
  | c :: cs => handleAll (handle g c) cs

theorem handle_within_cap (g : Gov) (cost : Nat) (h : g.spent ≤ g.cap) :
    (handle g cost).spent ≤ (handle g cost).cap := by
  unfold handle approve
  split
  · rename_i hd; simp at hd ⊢; omega
  · exact h

theorem handle_cap_fixed (g : Gov) (cost : Nat) : (handle g cost).cap = g.cap := by
  unfold handle; split <;> rfl

theorem handle_killed_fixed (g : Gov) (cost : Nat) : (handle g cost).killed = g.killed := by
  unfold handle; split <;> rfl

/-- No stream of requests can push spend past the cap. -/
theorem never_over_cap (g : Gov) (cs : List Nat) (h : g.spent ≤ g.cap) :
    (handleAll g cs).spent ≤ g.cap := by
  induction cs generalizing g with
  | nil => exact h
  | cons c cs ih =>
    simp only [handleAll]
    have h1 := handle_within_cap g c h
    rw [handle_cap_fixed] at h1
    have := ih (handle g c) (by rw [handle_cap_fixed]; exact h1)
    rwa [handle_cap_fixed] at this

/-- With the kill switch on, every request is blocked. -/
theorem killed_blocks_all (g : Gov) (cs : List Nat) (hk : g.killed = true) :
    handleAll g cs = g := by
  induction cs generalizing g with
  | nil => rfl
  | cons c cs ih =>
    simp only [handleAll]
    have : handle g c = g := by unfold handle approve; simp [hk]
    rw [this]; exact ih g hk

end BSVKey.Governor
