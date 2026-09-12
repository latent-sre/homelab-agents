#!/usr/bin/env python3
"""Error-budget arithmetic for an SLO window — the numbers behind references/alerting.md.

Why a script: the burn-rate table in that reference is only meaningful against a specific target and
window, and the conversions (a "99.9% monthly" target into minutes you can actually spend, an
observed success rate into how much of the budget is already gone, a burn rate into time-to-
exhaustion) are the kind of arithmetic that gets done wrong in your head at 3 a.m. and then quoted
as fact in an incident.

Pure standard library, no network, no clock: every input is an argument, so the same inputs always
produce the same output and the result can be pasted into a packet as evidence.

    python3 error_budget.py --target 99.9 --window-days 30
    python3 error_budget.py --target 99.9 --window-days 30 --observed 99.95
    python3 error_budget.py --target 99.9 --window-days 30 --observed 99.0 --elapsed-hours 12

Read the burn rate as "budget consumed per unit time, relative to spending it evenly": 1x exhausts
the budget exactly at the end of the window, 14.4x exhausts a 30-day budget in about two days.
"""
from __future__ import annotations

import argparse
import math
import sys


def budget_minutes(target_percent: float, window_days: float) -> float:
    """Allowed unavailability in minutes for a target over a window."""
    return window_days * 24 * 60 * (100.0 - target_percent) / 100.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute an SLO error budget, its consumption, and the burn rate.",
    )
    parser.add_argument(
        "--target", type=float, required=True,
        help="SLO target as a percentage, e.g. 99.9",
    )
    parser.add_argument(
        "--window-days", type=float, required=True,
        help="SLO window in days, e.g. 30",
    )
    parser.add_argument(
        "--observed", type=float,
        help="Observed success rate as a percentage over the elapsed period, e.g. 99.95",
    )
    parser.add_argument(
        "--elapsed-hours", type=float,
        help="Hours elapsed in the window so far (defaults to the whole window). "
             "Only meaningful with --observed.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # Reject the inputs whose results would be nonsense rather than printing a confident number:
    # a target outside (0, 100] has no budget interpretation, and a non-positive window has no rate.
    if not 0 < args.target <= 100:
        print("error: --target must be greater than 0 and at most 100", file=sys.stderr)
        return 2
    # NaN bypasses a positivity comparison; non-finite durations cannot define a budget window.
    if not math.isfinite(args.window_days) or args.window_days <= 0:
        print("error: --window-days must be finite and positive", file=sys.stderr)
        return 2
    if args.observed is not None and not 0 <= args.observed <= 100:
        print("error: --observed must be between 0 and 100", file=sys.stderr)
        return 2
    if args.elapsed_hours is not None and (
        not math.isfinite(args.elapsed_hours) or args.elapsed_hours <= 0
    ):
        print("error: --elapsed-hours must be finite and positive", file=sys.stderr)
        return 2

    window_hours = args.window_days * 24
    total_budget = budget_minutes(args.target, args.window_days)

    print(f"Target            {args.target}% over {args.window_days:g} days")
    print(f"Error budget      {total_budget:.1f} min ({total_budget / 60:.2f} h) of allowed failure")

    if args.observed is None:
        print("\nPass --observed to see consumption and burn rate.")
        return 0

    elapsed_hours = args.elapsed_hours if args.elapsed_hours is not None else window_hours
    if elapsed_hours > window_hours:
        print(
            f"warning: --elapsed-hours {elapsed_hours:g} exceeds the {window_hours:g}h window; "
            f"treating it as the full window",
            file=sys.stderr,
        )
        elapsed_hours = window_hours

    # Failure minutes actually spent so far, and the same figure as a share of the whole budget.
    failure_minutes = elapsed_hours * 60 * (100.0 - args.observed) / 100.0

    # A 100% target is a ZERO budget, so both ratios below are 0/0 for a perfect run. Guarding only
    # the denominator (`x if total else inf`) made a flawless month report "BUDGET EXHAUSTED", which
    # is the script asserting an outage that did not happen -- worse than no output. Zero failure
    # against a zero budget is zero consumption; any failure at all against a zero budget really is
    # unbounded, and that is the only case that should read as infinite.
    if total_budget:
        consumed_fraction = failure_minutes / total_budget
    else:
        consumed_fraction = 0.0 if failure_minutes == 0 else float("inf")

    # Burn rate compares the observed failure share against the target's allowance. 1x means
    # spending the budget exactly evenly across the window.
    allowed_fraction = (100.0 - args.target) / 100.0
    observed_fraction = (100.0 - args.observed) / 100.0
    if allowed_fraction:
        burn_rate = observed_fraction / allowed_fraction
    else:
        burn_rate = 0.0 if observed_fraction == 0 else float("inf")

    consumed_text = "n/a (zero budget)" if consumed_fraction == float("inf") \
        else f"{consumed_fraction * 100:.1f}% of the window's budget"
    burn_text = "unbounded (zero budget)" if burn_rate == float("inf") else f"{burn_rate:.2f}x"

    print(f"Elapsed           {elapsed_hours:g} h of {window_hours:g} h")
    print(f"Observed          {args.observed}% success -> {failure_minutes:.1f} min of failure")
    print(f"Budget consumed   {consumed_text}")
    print(f"Burn rate         {burn_text}")

    if burn_rate <= 0:
        print("Status            no failure observed — budget untouched")
    # Equivalent decimal inputs can land just above 1 after float subtraction and division.
    # Ignore that rounding residue without declaring an unfinished window's target achieved.
    elif math.isclose(consumed_fraction, 1.0, rel_tol=1e-12):
        print("Status            BUDGET EXHAUSTED — allowance reached, not exceeded; no budget remains")
    elif consumed_fraction > 1:
        print("Status            BUDGET EXHAUSTED — the target is already missed for this window")
    else:
        remaining_minutes = total_budget - failure_minutes
        # At the current rate, how long until the rest of the budget is gone.
        spend_per_hour = failure_minutes / elapsed_hours
        hours_left = remaining_minutes / spend_per_hour if spend_per_hour else float("inf")
        print(f"Remaining         {remaining_minutes:.1f} min")
        if hours_left == float("inf"):
            print("Status            not burning")
        else:
            print(
                f"Status            at this rate the budget is gone in {hours_left:.1f} h "
                f"({hours_left / 24:.1f} days)"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
