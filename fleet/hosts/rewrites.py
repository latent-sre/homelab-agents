"""Host prose projections as data, with the match count every rewrite must land.

A generated adapter is prose the canonical file no longer owns: each rewrite replaces a
Claude-only authority claim with what the target host can actually enforce. The failure mode this
module exists to close is **the silent no-op**. When a canonical sentence is reworded, a rewrite
that targeted it stops matching, the generator still succeeds, the adapter is regenerated without
the correction, and byte-drift validation cannot see it -- because the committed adapter was
produced with the same miss (PR #141 finding, recorded again in the machinery-rewrite decision).
Anchoring one rewrite at a time was the old fix; a count on every rewrite closes the class.

Two expectations, and no third:

- an **exact integer**: an anchored rewrite targeting a specific canonical sentence. It lands
  that many times across one full generation run, over every document of every host. Rewording
  the sentence changes the count and fails generation.
- `AT_LEAST_ONE`: a pattern translation (a namespace token, a plugin-root path) that applies
  wherever it appears, so its total moves with ordinary prose edits. It must still fire
  somewhere, because a pattern that matches nothing anywhere is dead code that reads as a
  control.

There is deliberately no "zero or more" expectation. A rewrite whose corpus-wide count is zero is
not cautious, it is dead: delete it, or fix the anchor it lost.

The count is checked over the whole run rather than per document because a rewrite legitimately
applies to a varying set of documents, and per-document counts would need an escape hatch that
re-opens the class.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

# The expectation for a pattern translation whose total moves with ordinary prose edits.
AT_LEAST_ONE: Final = "at-least-one"

HOSTS: Final = ("codex", "copilot", "portable")


class RewriteError(ValueError):
    """A rewrite table is malformed, or a run did not land the counts it declared."""


@dataclass(frozen=True)
class Rewrite:
    """One projection from canonical prose to what a host can enforce.

    `id` is the stable handle a test asserts on and a mismatch names. `why` is what a reader
    needs before weakening it: the authority claim that would otherwise survive into an adapter
    whose host cannot honour it.
    """

    id: str
    why: str
    find: str
    # One replacement; one per host when the honest statement differs by host control; or, for a
    # pattern translation, a function of the match (a namespace token keeps its own name).
    replace: (
        str | Mapping[str, str | Callable[[re.Match[str]], str]] | Callable[[re.Match[str]], str]
    )
    expect: int | str
    regex: bool = False
    dotall: bool = False
    multiline: bool = False
    # Empty means every host / every document; otherwise the rewrite is scoped to these.
    hosts: tuple[str, ...] = ()
    agents: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id:
            raise RewriteError("a rewrite must carry an id")
        if not self.why:
            raise RewriteError(f"rewrite {self.id} must say why it exists")
        if self.expect != AT_LEAST_ONE and not (isinstance(self.expect, int) and self.expect > 0):
            # Zero is the dead rewrite this module exists to surface; it is never a valid
            # expectation, so it cannot be declared as one.
            raise RewriteError(
                f"rewrite {self.id} expects {self.expect!r}; expected a positive count or "
                f"{AT_LEAST_ONE!r}"
            )
        declared = self.replace if isinstance(self.replace, Mapping) else ()
        for host in (*self.hosts, *declared):
            if host not in HOSTS:
                raise RewriteError(f"rewrite {self.id} names unknown host {host!r}")

    def applies_to(self, *, host: str, agent: str | None) -> bool:
        if self.hosts and host not in self.hosts:
            return False
        # An agent-scoped rewrite never touches a skill or a resource, which carry no agent.
        return not self.agents or agent in self.agents

    def replacement_for(self, host: str) -> str | Callable[[re.Match[str]], str]:
        if isinstance(self.replace, Mapping):
            try:
                return self.replace[host]
            except KeyError:  # a scoped rewrite reaching a host it has no honest statement for
                raise RewriteError(
                    f"rewrite {self.id} has no replacement for host {host!r}"
                ) from None
        return self.replace

    def apply(self, text: str, *, host: str) -> tuple[str, int]:
        """Return the rewritten text and how many times it landed."""
        replacement = self.replacement_for(host)
        if callable(replacement):
            if not self.regex:
                raise RewriteError(f"rewrite {self.id} computes a replacement but is not a regex")
            return re.subn(self.find, replacement, text, flags=self._flags())
        if not self.regex:
            found = text.count(self.find)
            return (text.replace(self.find, replacement) if found else text), found
        # The replacement is table data, not a template: a backslash or a \\1 in honest prose
        # must survive verbatim rather than be read as a group reference.
        return re.subn(self.find, lambda _match: replacement, text, flags=self._flags())

    def _flags(self) -> int:
        flags = 0
        if self.dotall:
            flags |= re.DOTALL
        if self.multiline:
            flags |= re.MULTILINE
        return flags


@dataclass
class Ledger:
    """What each rewrite actually landed across one generation run.

    Rewrites are applied per document; only the total is judged, so a rewrite may legitimately
    skip a document that never carried its anchor.
    """

    applied: Counter[str] = field(default_factory=Counter)

    def record(self, rewrite: Rewrite, count: int) -> None:
        # Counter omits an id it never saw; seeding zero keeps a rewrite that matched nothing
        # visible to `verify`, which is the whole point of the ledger.
        self.applied[rewrite.id] += count

    def counts(self) -> dict[str, int]:
        return dict(self.applied)

    def shortfalls(self, rewrites: Iterable[Rewrite]) -> list[str]:
        """Every rewrite whose run total disagrees with the count it declared."""
        problems: list[str] = []
        for rewrite in rewrites:
            landed = self.applied.get(rewrite.id, 0)
            if rewrite.expect == AT_LEAST_ONE:
                if landed == 0:
                    problems.append(
                        f"{rewrite.id}: matched nothing in the whole fleet. A pattern that "
                        f"translates nothing is dead code reading as a control -- delete it, or "
                        f"fix the form it lost. Why it exists: {rewrite.why}"
                    )
                continue
            if landed != rewrite.expect:
                # The two directions need different repairs, and guessing wrong costs a
                # correction: too few means an anchor was lost and must be re-anchored; too many
                # usually means a legitimate new occurrence, which is reviewed and then counted.
                if landed < rewrite.expect:
                    repair = (
                        "Canonical text this rewrite anchors on was reworded or removed without "
                        "the rewrite following, so an adapter would ship without that correction "
                        "and byte-drift validation could not see it. Re-anchor the rewrite on the "
                        "new wording, or delete it if what it corrected is gone."
                    )
                else:
                    repair = (
                        "The rewrite matched more places than the table expects. Read the new "
                        "occurrences: if each genuinely needs this projection, raise `expect` to "
                        "the new total; if one was duplicated or matched by accident, fix the "
                        "canonical text instead. Do not weaken the rewrite to silence this."
                    )
                problems.append(
                    f"{rewrite.id}: landed {landed} time(s), the table declares "
                    f"{rewrite.expect}. {repair} Why it exists: {rewrite.why}"
                )
        return problems


def check_table(rewrites: Iterable[Rewrite]) -> None:
    """Reject a table that cannot be judged: a duplicate id makes two rewrites share one count."""
    seen: set[str] = set()
    for rewrite in rewrites:
        if rewrite.id in seen:
            raise RewriteError(f"rewrite id declared twice: {rewrite.id}")
        seen.add(rewrite.id)


def apply_rewrites(
    text: str,
    rewrites: Iterable[Rewrite],
    *,
    host: str,
    agent: str | None = None,
    ledger: Ledger | None = None,
) -> str:
    """Apply every rewrite scoped to this host and document, in table order.

    Order is the table's, and it is load-bearing: an earlier rewrite's output is a later one's
    input, exactly as the hand-written chain read.
    """
    if host not in HOSTS:
        raise RewriteError(f"unknown adapter host {host!r}")
    for rewrite in rewrites:
        if not rewrite.applies_to(host=host, agent=agent):
            continue
        text, landed = rewrite.apply(text, host=host)
        if ledger is not None:
            ledger.record(rewrite, landed)
    return text
