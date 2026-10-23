# Tests — what to write, and what not to

Read before writing tests, or before adding code to something that has none. The universal rules live
in `skills/code-craft/SKILL.md`. On any conflict, SKILL.md wins.

## The loop, and where it's worth the ceremony

Red → green → refactor: write the failing test, make it pass minimally, then clean up with the test
holding you. The value isn't ritual — it's that **you have seen the test fail**, which is the only
proof it can fail. A test written after the code, never observed red, may assert nothing at all; this
is the most common defect in a test suite, and it is invisible.

Full TDD earns its cost where the behavior is specifiable up front: parsers, calculations, state
machines, anything with edge cases you can enumerate. It gets in the way while exploring an unknown
API or a UI's shape — there, spike first, then write the tests that pin what you learned before you
call it done. Either order is fine; shipping untested logic is not.

**For a bug, reproduce it with a failing test before fixing it when safe and feasible.** Confirm
that it fails for the reported mechanism, then use it as the regression guard. If reproduction is
unsafe or the codebase cannot support it, use the traces or simulation established by
`sde-agents:root-cause`, state the limitation, and verify the changed behavior as directly as the
environment permits. Do not claim a regression was reproduced when it was only inferred.

## What deserves a test

- **Behavior at the boundary**: empty, one, many, maximum; zero, negative, null; the error path.
  A function tested only on its happy path is tested only where it works.
- **The bug you just fixed** — see above.
- **The invariant a reader would violate.** If the code has a "keep these in sync" comment, the test
  is what makes it true instead of hopeful.
- **The failure handling itself**: a timeout fires, a retry backs off, the breaker opens, the
  transaction rolls back. Untested resiliency code is decoration
  (`sde-agents:backend-craft` requires this).
- Contracts at the seams — the served shape matches the spec, the serialized form round-trips.

## What not to test

- Getters, setters, and framework wiring — that tests the framework.
- Private functions directly. Test them through the public surface, or they cement an implementation
  you wanted freedom to change.
- Implementation detail: "calls method X then Y" locks in a call sequence rather than a result. When a
  pure refactor breaks a test, the test was asserting the wrong thing.
- Mocking what you own. A mock of your own database asserts your assumptions, not reality — use a
  real ephemeral instance (`sde-agents:backend-craft`). Mock the *external* boundary you can't run.
- Line coverage as a target. It measures execution, not assertion; 100% coverage with no meaningful
  assertions is achievable and worthless. Use it to find untested *areas*, never as a goal.

## Tests that stay useful

- **The name states the behavior**: `test_expired_token_is_rejected`, not `test_auth_2`. A failing
  test's name should tell you what broke without opening the file.
- **One reason to fail per test.** Five assertions about five behaviors means a failure tells you
  little; the first failure also hides the rest.
- **Arrange–act–assert**, visibly. A test whose setup is twenty lines of shared fixture is a test
  nobody will fix when it breaks.
- **No shared mutable state or ordering dependence** — tests must pass in any order and in parallel.
  A suite with a hidden order dependency fails randomly later, and the flake costs more than the
  test ever saved.
- **Deterministic**: inject the clock and the random source, don't sleep. `sleep` in a test is a
  race you decided to lose slowly. Freeze time, control the seed.
- **Fakes over mocks** where you can: an in-memory implementation of a small interface reads better
  and breaks less than a stack of `when(...).thenReturn(...)`.
- A flaky test is a broken test. Fix it or delete it — a suite people re-run until green teaches
  everyone to ignore red, which costs you the next real failure.
- **Guard non-executable artifacts structurally, never by substring count.** When the guarded
  content cannot run in the test environment — a playbook, shell helper, deployment script — a
  bare substring count over the whole file is not protection: matches elsewhere in the file keep
  the assertion green with the entire guarded block deleted, and for such content that test was
  its only automated protection. Parse the artifact and assert on its structure, then prove the
  guard by deleting the block and watching the test fail.
- **A fixture that runs a real external command pins every host setting that decides what the
  command prints**, in the fixture's own local configuration, before asserting on its output.
  Reproduce the hostile setting and record the before/after rather than assuming the default is
  safe. Tests that mock or synthesize that output have no host configuration to inherit.

## Verify

Run the suite and paste the command with the result count. Then confirm the tests are load-bearing:
break the code deliberately (invert a condition) and check that a test fails. A suite that stays
green when the logic is wrong is the most expensive kind of unverified.
