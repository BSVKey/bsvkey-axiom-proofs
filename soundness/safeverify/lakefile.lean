import Lake
open Lake DSL

-- Replaces SafeVerify's own lakefile (Lean 4.27.0) so that it builds on Lean 4.35.0
-- and can read 4.35.0 .olean files. Used by the `checkers` CI job on the commit in
-- COMMIT. Mathlib is dropped (the checker does not import it); Cli moves to v4.35.0.
-- patch.py fixes the one source change Lean >= 4.30 needs (SafeVerify#25).
package SafeVerify

require Cli from git
  "https://github.com/leanprover/lean4-cli.git" @ "v4.35.0"

@[default_target]
lean_lib SafeVerify

lean_exe safe_verify where
  root := `Main
  supportInterpreter := true