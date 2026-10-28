"""Adversarial cases for AXLE verify_proof.

Each case gives the honest claim (formal_statement, with `sorry`) and a
candidate file that tries to "prove" it by cheating. A sound checker must
reject every case marked expect="reject" and accept every expect="accept".
"""

CASES = [
    # ---- controls: honest proofs that must be accepted ----
    dict(
        name="control_honest",
        expect="accept",
        statement="theorem t (a b : Nat) : a + b = b + a := by sorry",
        content="theorem t (a b : Nat) : a + b = b + a := by omega",
    ),
    dict(
        name="control_helper_lemma",
        expect="accept",
        statement="theorem t (n : Nat) : n + 0 = n := by sorry",
        content="theorem helper (n : Nat) : n = n + 0 := rfl\ntheorem t (n : Nat) : n + 0 = n := (helper n).symm",
    ),

    # ---- classic cheats ----
    dict(
        name="sorry",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="theorem t : 2 + 2 = 5 := by sorry",
    ),
    dict(
        name="custom_axiom",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="axiom cheat : False\ntheorem t : 2 + 2 = 5 := cheat.elim",
    ),
    dict(
        name="sorry_hidden_in_macro",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content='macro "trust_me" : tactic => `(tactic| sorry)\ntheorem t : 2 + 2 = 5 := by trust_me',
    ),
    dict(
        name="sorry_in_helper",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="theorem helper : 2 + 2 = 5 := by sorry\ntheorem t : 2 + 2 = 5 := helper",
    ),
    dict(
        name="native_decide_true_claim",
        expect="reject",  # uses Lean.ofReduceBool, outside the standard axioms
        statement="theorem t : 10 * 10 = 100 := by sorry",
        content="theorem t : 10 * 10 = 100 := by native_decide",
    ),

    # ---- statement substitution ----
    dict(
        name="weaker_statement_same_name",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="theorem t : 2 + 2 = 4 := rfl",
    ),
    dict(
        name="extra_hypothesis",
        expect="reject",
        statement="theorem t (n : Nat) : n < 10 := by sorry",
        content="theorem t (n : Nat) (h : n < 5) : n < 10 := by omega",
    ),
    dict(
        name="namespace_shadow",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="namespace X\ntheorem t : 2 + 2 = 4 := rfl\nend X\nopen X",
    ),

    # ---- changing what the statement MEANS ----
    dict(
        name="redefine_def_in_statement",
        expect="reject",
        statement="def secret : Nat := 1\ntheorem t : secret = 2 := by sorry",
        content="def secret : Nat := 2\ntheorem t : secret = 2 := rfl",
    ),
    dict(
        name="instance_override_add",
        expect="reject",
        statement="theorem t : (2 : Nat) + 3 = 6 := by sorry",
        content=(
            "instance (priority := high) cheatAdd : Add Nat := ⟨Nat.mul⟩\n"
            "theorem t : (2 : Nat) + 3 = 6 := by decide"
        ),
    ),
    dict(
        name="macro_rules_rewrite_plus",
        expect="reject",
        statement="theorem t : (2 : Nat) + 3 = 6 := by sorry",
        content=(
            "macro_rules | `($a + $b) => `(Nat.mul $a $b)\n"
            "theorem t : (2 : Nat) + 3 = 6 := by decide"
        ),
    ),
    dict(
        name="notation_override",
        expect="reject",
        statement="theorem t : (2 : Nat) + 3 = 6 := by sorry",
        content=(
            'local infixl:65 (priority := high) " + " => Nat.mul\n'
            "theorem t : (2 : Nat) + 3 = 6 := by decide"
        ),
    ),
    dict(
        name="redefine_False",
        expect="reject",
        statement="theorem t : False := by sorry",
        content="def False : Prop := True\ntheorem t : False := trivial",
    ),

    # ---- bypassing the kernel ----
    dict(
        name="skip_kernel_tc_option",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="set_option debug.skipKernelTC true in\ntheorem t : 2 + 2 = 5 := by decide",
    ),
    dict(
        name="unsafe_cast",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="unsafe def bad : 2 + 2 = 5 := unsafeCast ()\n@[implemented_by bad] opaque t : 2 + 2 = 5",
    ),
    dict(
        name="opaque_proof",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="opaque t : 2 + 2 = 5",
    ),
    dict(
        name="exit_early",
        expect="reject",
        statement="theorem t : 2 + 2 = 5 := by sorry",
        content="#exit\ntheorem t : 2 + 2 = 5 := by decide",
    ),
]
