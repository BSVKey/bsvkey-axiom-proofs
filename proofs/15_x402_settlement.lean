import Mathlib

/-!
# 15 x402 settlement: nothing is served before the node accepts payment

Model of the x402 flow in the BSV Inference Broker and Paywall: a request
moves through quoted, paid, accepted (a Bitcoin BSV node accepted the
transaction) and served. A rejected payment ends the request.

Proven: no run of the state machine reaches "served" without passing
"accepted", and a rejected request is never served.
-/

namespace BSVKey.X402

inductive St
  | quoted | paid | accepted | served | rejected
  deriving DecidableEq

inductive Ev
  | pay | nodeAccept | nodeReject | serve

def step : St → Ev → St
  | .quoted, .pay => .paid
  | .paid, .nodeAccept => .accepted
  | .paid, .nodeReject => .rejected
  | .accepted, .serve => .served
  | s, _ => s

def trace (s : St) : List Ev → List St
  | [] => [s]
  | e :: es => s :: trace (step s e) es

def final (s : St) : List Ev → St
  | [] => s
  | e :: es => final (step s e) es

theorem serve_needs_accept (s : St) (e : Ev) (h : step s e = .served) :
    s = .accepted ∨ s = .served := by
  cases s <;> cases e <;> simp_all [step]

/-- Starting from a fresh quote, reaching "served" means "accepted" was visited. -/
theorem served_implies_accepted (es : List Ev) (h : final .quoted es = .served) :
    St.accepted ∈ trace .quoted es := by
  have key : ∀ (s : St) (es : List Ev), s ≠ .served → final s es = .served →
      St.accepted ∈ trace s es := by
    intro s es
    induction es generalizing s with
    | nil => intro hs hf; exact absurd hf hs
    | cons e es ih =>
      intro hs hf
      simp only [trace, List.mem_cons]
      by_cases ha : s = .accepted
      · left; exact ha.symm
      · right
        apply ih (step s e) _ hf
        intro hstep
        rcases serve_needs_accept s e hstep with h1 | h1
        · exact ha h1
        · exact hs h1
  exact key .quoted es (by decide) h

theorem rejected_is_final (es : List Ev) : final .rejected es = .rejected := by
  induction es with
  | nil => rfl
  | cons e es ih => cases e <;> exact ih

end BSVKey.X402
