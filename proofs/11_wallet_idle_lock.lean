import Mathlib

/-!
# 11 Wallet session: the 15 minute idle lock

Model of the bsvkey.com wallet session: the key unlocks per tab and locks
after 900 seconds without activity. Activity resets the timer only while
unlocked; once locked, only an explicit unlock reopens it.

Proven: an idle session is locked by 900 seconds, activity inside the window
keeps it open, and once locked no amount of waiting or activity unlocks it.
-/

namespace BSVKey.Session

def idleLimit : Nat := 900

structure Session where
  lastActive : Nat
  locked : Bool

/-- Time passes to `now`. -/
def tick (s : Session) (now : Nat) : Session :=
  if now ≥ s.lastActive + idleLimit then { s with locked := true } else s

/-- User activity at time `now`; ignored once locked. -/
def activity (s : Session) (now : Nat) : Session :=
  if s.locked then s else { s with lastActive := now }

inductive Event
  | tick (now : Nat)
  | act (now : Nat)

def apply (s : Session) : Event → Session
  | .tick n => tick s n
  | .act n => activity s n

def run (s : Session) : List Event → Session
  | [] => s
  | e :: es => run (apply s e) es

theorem idle_locks (s : Session) (now : Nat) (h : now ≥ s.lastActive + 900) :
    (tick s now).locked = true := by
  unfold tick idleLimit; simp [h]

theorem active_stays_open (s : Session) (now : Nat)
    (hu : s.locked = false) (h : now < s.lastActive + 900) :
    (tick s now).locked = false := by
  unfold tick idleLimit
  have : ¬ now ≥ s.lastActive + 900 := by omega
  simp [this, hu]

/-- Once locked, no ticks or activity can unlock the session. -/
theorem lock_is_sticky (s : Session) (es : List Event) (h : s.locked = true) :
    (run s es).locked = true := by
  induction es generalizing s with
  | nil => exact h
  | cons e es ih =>
    apply ih
    cases e with
    | tick n => show (tick s n).locked = true; unfold tick; split <;> simp_all
    | act n => show (activity s n).locked = true; unfold activity; simp_all

end BSVKey.Session
