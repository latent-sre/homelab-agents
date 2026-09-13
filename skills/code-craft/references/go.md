# Go — errors, lifetimes, contracts, and the traps that stay green

Read before writing Go. The universal rules live in `skills/code-craft/SKILL.md`. On any conflict,
SKILL.md wins; the repository's own conventions and declared Go version outrank both.

## Establish the version and package contract

- **Read `go.mod` before reasoning about language behavior.** Its `go` directive selects the
  language version and gates version-dependent semantics. Do not infer semantics from whichever
  toolchain happens to be on PATH.
- **Keep packages cohesive and names specific.** A package called `util`, `common`, or `helpers`
  usually hides unrelated responsibilities. The package name should tell a caller what capability
  it imports.
- **Keep the exported surface smaller than the implementation.** Export only what another package
  needs; document every exported identifier as a caller-facing contract.
- **Prefer a concrete return type and define a small interface at the consumer.** Returning an
  interface commits every caller to the abstraction before a consumer has demonstrated one.
- **Make the zero value useful where practical.** When construction is required, make invalid states
  unrepresentable where possible; otherwise document the constructor requirement and validate its
  inputs. An exported type can legitimately require a constructor when that contract is explicit.

## Errors are values — decide what becomes API

- **Add operation context on the way up, and wrap deliberately.**
  `fmt.Errorf("load config %s: %w", path, err)` lets callers use `errors.Is` and `errors.As`, so the
  underlying error becomes part of the package API. Use `%w` only when that commitment is intended;
  otherwise translate to a domain error or preserve context without exposing the implementation
  cause. Matching error strings is never a control-flow contract.
- Use a sentinel for a stable condition with no additional data; use a typed error when callers need
  structured fields. Keep error strings lowercase and without terminal punctuation so wrapping
  composes cleanly.
- **Never `_ =` an error you have not reasoned about.** Check `Close`, `Flush`, `Sync`, `Commit`,
  encoders, and buffered writers — finalization is where data-loss errors often surface.
- **A nil pointer stored in an error interface is not a nil error.** Return the literal `nil` on
  success; never convert a possibly nil `*MyError` into `error`.
- **A nil error is not necessarily a valid result.** When an API can return `(nil, nil)`, define and
  check whether that pair means absent, invalid, or programmer error.
- `panic` is for a broken invariant or programmer error, not ordinary request, validation,
  dependency, or startup failure. `recover` works only when called directly by a deferred function
  in the panicking goroutine. Recover only at a boundary you own, preserve the stack, and implement
  that boundary's declared failure policy; `net/http` already recovers handler panics.

## Context and cancellation are part of the call contract

- Pass `context.Context` as the first parameter of request-scoped or cancelable work; do not store it
  in a long-lived struct or use it as an optional-arguments bag.
- Never pass a nil context. Derive from the caller, and call every returned cancel function — usually
  `defer cancel()` immediately after successful construction — so timers and children are released.
- **Propagation is not compliance.** Pass the context to network, database, subprocess, or other
  cancellation-aware calls, and select on `ctx.Done()` in waits and loops you own. A
  threaded-through context that nothing observes does not cancel anything.
- Context values carry request-scoped metadata crossing API boundaries, not configuration,
  dependencies, or ordinary function parameters. Use private key types to avoid collisions.

## Concurrency: ownership, synchronization, and a defined end

- **Every goroutine needs an owner, a stop condition, and a join point.** A goroutine blocked on a
  channel is not garbage-collected. Bound fan-out; propagate the first meaningful error; wait for
  every child before returning from the scope that owns it.
- **Serialize every shared write.** Transfer ownership through channels or protect state with
  `sync`/`sync/atomic`; neither approach is universally better. An ordinary map, slice header, or
  interface value is not safe for concurrent mutation.
- Do not copy a type whose documentation prohibits copying after first use, or a struct containing
  one. Common examples include mutexes, `WaitGroup`, `Cond`, `Once`, and typed atomics. Use pointer
  receivers consistently for stateful types; `go vet`'s copy-lock checks are tripwires, not a
  substitute for understanding ownership.
- A goroutine's exit does not by itself synchronize its writes with another goroutine. Establish a
  happens-before edge with a channel, lock, wait primitive, or atomic operation before consuming
  its result.
- **`defer` runs at function exit, not block exit.** A defer inside a long loop retains resources
  until the containing function returns. Extract one iteration into a function or close explicitly.
  Defer arguments also evaluate immediately; do not pass `time.Now()` expecting exit time.
- Timer behavior is version-dependent and selected by the **main module's** `go` directive, with a
  `GODEBUG` override. Go 1.23 semantics allow unreferenced timers to be collected and use
  synchronous timer channels; earlier semantics require the old stop, possible drain, and reset
  discipline. Reuse a timer only when lifecycle or measured allocation pressure requires it.
- On Go 1.25 or later, `WaitGroup.Go` can pair task accounting for work that cannot panic. It does
  not replace ownership, cancellation, error propagation, or the rule that reuse starts only after
  the prior `Wait` has returned.

## Aliasing, copies, and version-sensitive loops

- **Slices share backing arrays.** `b := a[:2]` followed by `append(b, x)` can overwrite data visible
  through `a`. Clone when ownership crosses an API or concurrent boundary and the caller keeps its
  copy.
- **Maps are reference-like and iteration order is unspecified.** Never use iteration order as
  output order; collect and sort keys when determinism is part of the contract.
- **Struct assignment copies the value.** A value-receiver mutation changes only the copy. Use a
  pointer receiver when the method mutates, and keep receiver choice consistent across the type.
- Loop-variable capture follows both the module language version and the declaration form. In Go
  1.22+ modules, variables declared by the loop (`:=`) get a new variable per iteration; older
  modules reuse them. A pre-existing variable assigned with `=` is still reused, including in
  `for _, value = range values`. Read `go.mod` and the loop before removing a capture copy.

## Generics, interfaces, and reflection

- Start with concrete code. Add a type parameter when the algorithm or data structure is genuinely
  identical across element types — common examples are slices, maps, channels, and reusable
  containers.
- If the operation only calls methods, use an interface. Replacing `io.Reader` with a type parameter
  adds ceremony without adding behavior or speed.
- Do not force unlike implementations through one generic constraint. Different behavior belongs
  behind an interface; operations that fundamentally depend on runtime shape may legitimately use
  reflection at a narrow, tested boundary.
- Keep constraints as small as the operations require. A public constraint is part of the public
  API and should not expose implementation-only type sets.

## Standard-library boundaries that commonly leak resources

### `net/http`

- Reuse `http.Client` and its `Transport`; they are safe for concurrent use and own connection
  pools. Constructing one per request defeats reuse.
- Every outbound request gets the caller's context and a finite deadline through that context,
  `Client.Timeout`, or both. A zero `Client.Timeout` is unbounded and its nonzero budget includes
  connection setup, redirects, and response-body reads.
- When `Do` succeeds, close `resp.Body`. Consume it to EOF only when the body is bounded and
  connection reuse matters; do not blindly drain an untrusted or unbounded response. Limit bytes
  before decoding.
- Use an explicit `http.Server` with deliberate `ReadHeaderTimeout`, `WriteTimeout`, and
  `IdleTimeout`. Add `ReadTimeout` only when one deadline fits the entire request, including
  uploads. Long-lived streams need their own write-deadline and heartbeat policy.
- `MaxHeaderBytes` does not limit a request body. Wrap untrusted bodies with `http.MaxBytesReader`
  before decoding and test requests exactly at and over the limit.
- Propagate `r.Context()` into downstream HTTP, database, and owned blocking work. Shut the server
  down with a deadline-bearing context and wait for `Shutdown`; coordinate hijacked and WebSocket
  connections separately because graceful shutdown does not wait for them.
- Handlers run concurrently. Do not retain or use `ResponseWriter` or `Request.Body` after
  `ServeHTTP` returns. Join request-scoped goroutines before returning, or explicitly transfer them
  to a longer-lived owner with its own cancellation and join policy.
- Handler tests use `httptest` and assert status, headers, body shape, and cancellation — not only
  the happy-path payload.

### `database/sql`

- `*sql.DB` is a concurrency-safe connection pool, not one connection. Open and reuse it; an open
  may not establish a connection, so use `PingContext` when startup must prove connectivity. Set a
  deliberate maximum-open budget when database capacity is bounded, and observe `DB.Stats` before
  tuning idle or lifetime settings.
- Use context-aware query methods. For multiple rows, close `Rows`, iterate with `Next`/`Scan`, and
  check `Rows.Err`; otherwise a mid-stream failure can look like a clean end. For `QueryRowContext`,
  always check `Scan` because the query error is deferred until then.
- Pass untrusted values as query arguments; never build SQL by formatting or concatenating values.
  When a structural identifier cannot be parameterized, map it through an explicit allowlist.
- A transaction uses only its `*sql.Tx` methods until `Commit` or `Rollback`. Calling `sql.DB`
  methods mid-transaction can run outside the transaction and produce inconsistent results or
  deadlock.
- Defer `Rollback` immediately after a successful begin, then check `Commit`; rollback after a
  successful commit is a harmless no-op. Discard transaction results when commit fails.
- Prefer pooled `DB` operations. If a dedicated `*sql.Conn` is necessary, close it to return it to
  the pool. Close prepared statements when their owner is done; transaction completion closes
  transaction-bound statements.

## Tests and tooling that prove the right property

- Table-driven tests get named subtests; helpers call `t.Helper`; resources use `t.Cleanup` and
  `t.TempDir`. On Go 1.24 or later, `t.Context()` supplies a context canceled before cleanup; on
  older versions, derive a test-scoped context and register its cancel function with cleanup.
- Tests that mutate process-wide state — environment variables, working directory, global loggers,
  singleton registries — do not run in parallel. `t.Setenv` restores state but cannot make that
  state goroutine-local.
- Fuzz parsers, decoders, protocol boundaries, and other functions whose input space is hostile or
  combinatorial. Targets stay fast, deterministic, independent of persistent shared state, and
  never retain or mutate engine-provided input. Seed compact edge cases and preserve minimized
  failures as ordinary regressions.
- On Go 1.25 or later, `testing/synctest` can make time-dependent concurrency tests deterministic
  and detect owned-goroutine deadlocks. Use fakes at external-I/O boundaries, which the synthetic
  scheduler cannot treat as durably blocked.
- Run the race detector on concurrent code and realistic exercised paths. It detects only races
  that execute, requires a supported platform/toolchain, and does not prove unexecuted paths safe.
- Use `gofmt` as the formatting authority and `go vet` for its targeted correctness checks. Run the
  repository's chosen broader linter when present; do not introduce a competing linter in a scoped
  change.
- Benchmarks need a decision threshold and allocation evidence. A faster number with more retained
  memory, changed results, or no stable baseline is not an improvement.

## Verify

Run the repository's declared commands first. For an ordinary module, the baseline evidence is:

```text
go build ./...
go vet ./...
gofmt -l .
go test ./...
```

`gofmt -l .` must print nothing. Add `go test ./... -race` for concurrent code on a supported
race-detector environment. Add a bounded fuzz run for a changed parser or hostile-input boundary.
For goroutine lifetimes, exercise cancellation and assert every owned goroutine joins before the
test deadline; a timeout is a failure signal, while a passing bounded test is evidence for the
paths it executed, not a mathematical proof.

## Primary evidence anchors

The rules above are distilled from stable language and standard-library contracts:

- Go memory model: <https://go.dev/ref/mem>
- Go code review comments: <https://go.dev/wiki/CodeReviewComments>
- Contexts and structs: <https://go.dev/blog/context-and-structs>
- Error wrapping and API commitments: <https://go.dev/blog/go1.13-errors>
- When to use generics: <https://go.dev/blog/when-generics>
- `net/http` package contract: <https://pkg.go.dev/net/http>
- Database query guidance: <https://go.dev/doc/database/querying>
- SQL-injection avoidance: <https://go.dev/doc/database/sql-injection>
- Database transaction guidance: <https://go.dev/doc/database/execute-transactions>
- Database connection-pool guidance: <https://go.dev/doc/database/manage-connections>
- Race detector limits: <https://go.dev/doc/articles/race_detector>
- Go fuzzing: <https://go.dev/doc/security/fuzz/>
- Go 1.22 loop semantics: <https://go.dev/doc/go1.22>
- Go 1.23 timer semantics: <https://go.dev/wiki/Go123Timer>
- Go 1.25 concurrency-testing additions: <https://go.dev/doc/go1.25>
