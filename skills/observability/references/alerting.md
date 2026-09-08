# Alerting — rules, thresholds, and burn rates at lab scale

Read before writing an alert rule, choosing a threshold, or setting up routing. The universal rules
live in `skills/observability/SKILL.md`. On any conflict, SKILL.md wins.

## An alert rule, annotated

```yaml
groups:
  - name: paperless
    rules:
      - alert: PaperlessDown
        expr: up{job="paperless"} == 0
        for: 5m                     # survive a scrape blip; short enough to matter
        labels:
          severity: page            # page | ticket — see routing below
        annotations:
          summary: "Paperless has been unreachable for 5m"
          description: "Documents cannot be uploaded or searched."
          runbook_url: "https://git.lan/lab/docs/runbooks/paperless.md"

      # The monitoring-broke case. Without this, every rule above silently stops firing
      # when the target disappears, and the dashboard just goes quiet.
      - alert: PaperlessMetricsMissing
        expr: absent(up{job="paperless"})
        for: 15m
        labels: { severity: ticket }
        annotations:
          summary: "No metrics from paperless at all — scrape target missing"
          runbook_url: "https://git.lan/lab/docs/runbooks/monitoring.md"

      # The highest-value lab alert class: a job that silently stopped succeeding.
      - alert: BackupStale
        expr: time() - backup_last_success_timestamp_seconds > 26 * 3600
        for: 10m
        labels: { severity: page }
        annotations:
          summary: "{{ $labels.job }} backup is over 26h old ({{ $labels }})"
          description: "Restore capability is degrading with every hour."
          runbook_url: "https://git.lan/lab/docs/runbooks/backups.md"
```

Four things that rule set gets right and most don't: a `for:` that isn't zero, a recovery link for
these household-critical examples, an `absent()` companion so a dead target can't hide, and a
staleness alert on the job whose failure is otherwise silent (26h, not 24h — a daily job that runs
at a slightly different time must not page every morning). A lightweight service without a runbook
still needs an actionable annotation, but it may name the first action and owner inline.

The backup metric must identify each required target/dataset. Preserve that identity in the rule
and notification: a fresh target must not clear a different target's stale backup. The Paperless
absence rule watches only Paperless; add a separate absence check for each expected backup
identity, or compare an expected-backup inventory with observed series. A broad `absent(metric)`
cannot detect one missing target while another target still reports the metric.

## Thresholds you can defend

- Derive it from something observed: the p99 you actually see, the disk fill rate you measured, the
  job's real cadence plus slack. A number nobody can explain gets silenced the first time it's
  noisy, and a silenced alert is worse than no alert because it still reads as coverage.
- **Percentages lie on small numbers.** A 50% error rate over two requests is one failed request.
  Gate ratio alerts on a minimum volume, or alert on absolute counts for low-traffic services —
  most home-lab services are low-traffic.
- **Time-based beats rate-based for scheduled work.** "Hasn't succeeded in N hours" is robust; "error
  rate of the backup job" is zero when the job doesn't run at all.
- Certificate and disk alerts get *lead time*, not a cliff: "expires in 14 days" and "will be full
  in 4 days at the current rate" (`predict_linear`) both leave room to act.

## Routing and noise

- Two severities are enough in a one-operator lab: **page** (wake me) and **ticket** (tell me
  tomorrow). More tiers than you have distinct responses is decoration.
- **Group by service** so one failing service is one notification, not twenty. Set `group_wait`/
  `group_interval` so a flapping service can't produce a burst.
- **Inhibition beats willpower**: when the shared dependency alert is firing (DNS, proxy, storage),
  inhibit the dependents' alerts — otherwise a single root cause pages you eight times and the real
  one is buried.
- Silence deliberately and with an expiry, during planned work. An open-ended silence is how an
  alert dies quietly.
- **Grafana-managed alerting warning**: applying a notification-policy tree via provisioning
  **replaces the whole tree**, not the entries you listed. Provision the full policy or none of it;
  a partial file silently deletes the routes it doesn't mention.

## SLO burn rates — when they're worth it

An error budget is the allowed unreliability over a window (99.9% over 30 days = ~43 minutes). A
burn-rate alert fires on *how fast* you're consuming it, so a brief total outage and a long partial
degradation both surface, and small blips don't.

**Bind the window and the threshold as a unit** — they are one decision, and a threshold copied
without its window is meaningless:

| Window | Burn rate | Meaning | Severity |
|---|---|---|---|
| 1h | > 14.4× | budget gone in ~2 days at this rate | page |
| 6h | > 6× | serious sustained burn | page |
| 3d | > 1× | slow leak, will exhaust the window | ticket |

Pair a short and a long window on the same rule (short catches the spike, long confirms it isn't a
blip) — that pairing is the whole point of the pattern.

**Honestly: most lab services don't need this.** It presumes a target you're managing to and a
rotation to page. Reach for it for the one or two services where a genuine target exists (the
household-facing thing everyone notices), and let "it's down", "the backup is stale", and "the
certificate expires soon" carry the rest. `scripts/error_budget.py` does the arithmetic when you do
want the numbers.

## Verify the rule fires

`promtool check rules` proves it parses; it does not prove it fires. Force the condition (stop a test
container, add a temporary rule with an always-true expression, or `promtool test rules` with a
crafted series) and watch it move through pending → firing → resolved. A rule that has only ever
evaluated to zero is unverified, and the first time it's needed is the wrong time to find out.
