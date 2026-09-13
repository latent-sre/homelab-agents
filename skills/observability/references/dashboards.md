# Dashboards — built for the incident, provisioned as code

Read before building a Grafana dashboard or wiring provisioning. The universal rules live in
`skills/observability/SKILL.md`. On any conflict, SKILL.md wins.

## Layout: the incident questions, in reading order

Build a dedicated service dashboard only when `SKILL.md`'s recurring-question predicate fires;
otherwise use the shared overview, probe, or alert. A dedicated dashboard reads top to bottom:

1. **Is it up?** — a stat panel per instance, green/red, plus uptime. Answerable in one second.
2. **Is it erroring?** — error rate and error ratio; the ratio panel paired with a traffic panel so
   "no data" can't be mistaken for "no errors" (see `promql.md` on division by zero).
3. **Is it slow?** — p50/p95/p99 from histogram buckets, one panel, three series.
4. **Is it saturated?** — CPU, memory, disk, and the resource specific to this service (queue depth,
   connection pool, worker saturation).
5. **What is it saying?** — a log panel filtered to this service's errors, so the jump from graph to
   log line doesn't require a second tab.

A panel per **question**, not per available metric. The exporter offers hundreds; a dashboard with
forty panels is unreadable exactly when it matters, and the fix is deleting panels.

## Panel hygiene

- **Units on every axis** (`s`, `bytes`, `reqps`, `percentunit`) — an unlabeled axis is a number
  nobody can act on, and `percent` vs `percentunit` (0–100 vs 0–1) is the classic silent wrongness.
- **Thresholds where the color means something specific**, tied to the alert threshold. When the
  panel turns red at the same number the alert fires at, the dashboard and the pager agree.
- Legends: name the series (`{{service}}`), don't dump the full label set.
- **Time range and interval as variables** (`$__rate_interval` in rate queries) so the same panel is
  honest at 5 minutes and at 7 days. Hard-coded `[5m]` in a rate over a 30-day view is a lie.
- Template variables for service/host/instance rather than one dashboard per instance.
- Set the dashboard's default range to what you actually use in an incident — usually 1h or 6h, not
  Grafana's default.

## Provisioned as code

A dashboard edited in the browser lives in Grafana's database and survives container replacement
when that storage persists. Keep JSON in the lab repo for review and reproducible provisioning:

```yaml
# /etc/grafana/provisioning/dashboards/lab.yaml
apiVersion: 1
providers:
  - name: lab
    type: file
    updateIntervalSeconds: 30
    allowUiUpdates: false        # UI edits would silently diverge from the repo
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

- `allowUiUpdates: false` blocks saving UI changes to a provisioned dashboard; it does not detect
  all provisioning or runtime drift. Iterate in the UI, then **export the JSON back to the repo**
  and provision the reviewed file — that export is part of the change, not a follow-up.
- Strip the `id` field and pin a stable `uid` before committing, so the same file imports cleanly
  into a rebuilt Grafana and links to it keep working.
- Datasource names come from a variable or a provisioned datasource `uid`; a dashboard with a
  hard-coded datasource id breaks on a rebuild.
- Provisioning **alerting** policies is different and dangerous — a provisioned notification-policy
  tree replaces the whole tree (see `alerting.md`).

## Verify

Import the file into the running Grafana and look at it with real data. A dashboard whose panels
show "No data" is not finished — either the query is wrong or the metric doesn't exist, and both are
findings. Applying it (import, provisioning reload, container restart) is an apply under
`sde-agents:homelab-engineer`'s tiers.
