# PowerShell — write for the 5.1/7 divide

Read before writing PowerShell. The universal rules live in `skills/code-craft/SKILL.md`. On any
conflict, SKILL.md wins; the repository's own conventions outrank both.

Windows PowerShell 5.1 and PowerShell 7+ are different languages wearing one name. State which one
a script targets at its top — half the traps below are one-sided.

## Function shape

```powershell
function Get-Thing {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$Name,
        [int]$Count = 1
    )
    # approved verb (Get-Verb) + singular noun; comment-based help above the function
}
```

- Approved verbs (`Get-Verb`), `[CmdletBinding()]`, and typed, validated params
  (`[ValidateSet()]`, `[ValidateNotNullOrEmpty()]`) — validation at the boundary beats checks
  scattered through the body.
- State-changing functions declare `SupportsShouldProcess`, which buys `-WhatIf`/`-Confirm` from
  the runtime instead of a hand-rolled dry-run flag.

## Error handling

- For PowerShell cmdlets, `$ErrorActionPreference = 'Stop'` (or `-ErrorAction Stop` per call)
  makes non-terminating errors catchable; wrap risky work in `try/catch`.
- For native executables, check `$LASTEXITCODE` immediately and interpret the executable's exit
  contract before another native command overwrites it. `try/catch` and `Stop` alone do not
  reliably catch native failures on Windows PowerShell 5.1 or default PowerShell 7 settings.
  For a command whose contract is zero-success/nonzero-failure:

  ```powershell
  & docker version
  $commandExit = $LASTEXITCODE
  if ($commandExit -ne 0) { throw "docker failed with exit code $commandExit" }
  # Dependent steps begin only after this check.
  ```

  PowerShell 7.4+ can instead opt into `$PSNativeCommandUseErrorActionPreference = $true` with
  `Stop`; the feature was experimental in 7.3. Version-gate that choice and handle programs with
  meaningful nonzero success statuses explicitly. Neither stderr output nor a later `$?` is a
  substitute for the command's own exit status.
- `Write-Error` for non-terminating context; `throw` for real failures; in a `catch`, re-throw
  with `$PSCmdlet.ThrowTerminatingError($PSItem)` so the error names your cmdlet as its source.

## Output and the pipeline

- Emit objects, not formatted text (`[pscustomobject]@{ ... }`) and let the caller format —
  `Format-*` belongs only at the end of a display pipeline, because formatted output is
  unparseable downstream.
- Never `Write-Host` for data; it bypasses the pipeline. Data is output;
  `Write-Verbose`/`Write-Information` carry diagnostics.

## Correctness traps

- **`$null` on the LEFT**: `if ($null -eq $x)`. With `$x` on the left, comparing an array against
  `$null` *filters the array* instead of testing it — the condition is silently wrong.
- Splatting for many parameters: `$p = @{ Name = 'x'; Count = 2 }; Get-Thing @p`.
- 5.1 vs 7: `??`, `?.`, the ternary, and `ForEach-Object -Parallel` are 7-only; on 5.1, `2>&1`
  across a native executable wraps each stderr line in an ErrorRecord and flips `$?` even on
  success.
- A Windows-PowerShell-only module used from PS 7 (`Import-Module <name> -UseWindowsPowerShell`)
  proxies through a 5.1 session and returns **deserialized** objects — properties only, no live
  methods.

## Cross-platform (PS 7 on Linux too)

- No hardcoded separators: `Join-Path`, `[IO.Path]::DirectorySeparatorChar`, and
  `[IO.Path]::PathSeparator` for PATH-style lists.
- Branch OS-specific work on the automatic variables `$IsWindows` / `$IsLinux` / `$IsMacOS`.
- Linux is case-sensitive for file paths *and* environment-variable names (`$env:Path` ≠
  `$env:PATH`) — match exact case.

## Secrets and signing

- Secrets come from a vault at run time — SecretManagement + SecretStore (`Get-Secret`), or
  whatever store the repository already uses — never baked into scripts, parameters, or
  transcripts; pass credential objects, not plaintext.
- Where an execution policy or Constrained Language Mode is enforced, sign
  (`Set-AuthenticodeSignature`) — unsigned automation on a locked-down host fails at the worst
  time.

## Quality gate and tests

- Pass `PSScriptAnalyzer` with Error severity failing the build. Rules that earn their keep:
  `PSUseApprovedVerbs`, `PSAvoidUsingCmdletAliases`, `PSUseShouldProcessForStateChangingFunctions`,
  `PSAvoidUsingInvokeExpression`, `PSAvoidUsingPlainTextForPassword`,
  `PSAvoidUsingConvertToSecureStringWithPlainText`.
- Test with Pester 5, which runs **Discovery, then Run** as separate phases: bare code inside
  `Describe` executes during Discovery. Generate test data in `BeforeDiscovery` and pass it through
  `-ForEach`/`-TestCases`; put execution setup in `BeforeAll`/`BeforeEach`. Use `$script:` only when
  that shared lifetime is intentional, not as the default bridge between phases. Mock assertions
  use `Should -Invoke`. [Pester's data-driven tests](https://pester.dev/docs/usage/data-driven-tests)
  own the phase-data contract; the tests-first process lives in [tdd.md](tdd.md).
