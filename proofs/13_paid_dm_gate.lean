import Mathlib

/-!
# 13 Paid DMs and the Contact Gauge: no message without payment

Model of BSVKey Paid DMs and gauge.bsvkey.com. The recipient sets a price;
a message is delivered only if it carries a confirmed payment of at least
that price to the recipient's address.

Proven: every delivered message was paid in full, to the right address,
and raising the price can only reduce what gets through.
-/

namespace BSVKey.PaidDM

structure Msg where
  sats : Nat
  payTo : String
  confirmed : Bool

def admit (price : Nat) (inbox : String) (m : Msg) : Bool :=
  m.confirmed && decide (m.payTo = inbox) && decide (price ≤ m.sats)

def deliver (price : Nat) (inbox : String) (ms : List Msg) : List Msg :=
  ms.filter (admit price inbox)

theorem delivered_paid (price : Nat) (inbox : String) (ms : List Msg) :
    ∀ m ∈ deliver price inbox ms,
      m.confirmed = true ∧ m.payTo = inbox ∧ price ≤ m.sats := by
  intro m hm
  simp only [deliver, List.mem_filter, admit, Bool.and_eq_true, decide_eq_true_eq] at hm
  exact ⟨hm.2.1.1, hm.2.1.2, hm.2.2⟩

theorem higher_price_fewer (p q : Nat) (inbox : String) (ms : List Msg) (h : p ≤ q) :
    ∀ m ∈ deliver q inbox ms, m ∈ deliver p inbox ms := by
  intro m hm
  simp only [deliver, List.mem_filter, admit, Bool.and_eq_true, decide_eq_true_eq] at hm ⊢
  exact ⟨hm.1, ⟨hm.2.1.1, hm.2.1.2⟩, le_trans h hm.2.2⟩

/-- Revenue from delivered messages is at least price times count. -/
theorem revenue_floor (price : Nat) (inbox : String) (ms : List Msg) :
    price * (deliver price inbox ms).length ≤ ((deliver price inbox ms).map Msg.sats).sum := by
  have key : ∀ l : List Msg, (∀ m ∈ l, price ≤ m.sats) →
      price * l.length ≤ (l.map Msg.sats).sum := by
    intro l hl
    induction l with
    | nil => simp
    | cons x xs ih =>
      simp only [List.length_cons, List.map_cons, List.sum_cons]
      have hx := hl x (by simp)
      have hxs := ih (fun m hm => hl m (by simp [hm]))
      rw [Nat.mul_succ]; omega
  exact key _ (fun m hm => (delivered_paid price inbox ms m hm).2.2)

end BSVKey.PaidDM
