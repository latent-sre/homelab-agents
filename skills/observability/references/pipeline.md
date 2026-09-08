# Collection — scrapes, exporters, and the agent pipeline

Read before writing a scrape config, an Alloy/OTel pipeline, or adding an exporter. The universal
rules live in `skills/observability/SKILL.md`. On any conflict, SKILL.md wins.

## Scraping

```yaml
scrape_configs:
  - job_name: paperless
    scrape_interval: 30s          # match the resolution you actually need
    scrape_timeout: 10s           # MUST be < scrape_interval
    static_configs:
      - targets: ["paperless:8000"]
    relabel_configs:              # keep labels bounded and meaningful
      - source_labels: [__address__]
        target_label: instance
```

- **Scrape interval is a cost decision**: it multiplies series × retention. 15–30s is plenty for a
  lab; 5s buys resolution nobody looks at and disk you'll run out of.
- **`scrape_timeout` must be less than `scrape_interval`**, or scrapes overlap and the target gets
  hammered while data goes missing.
- **Every rate query's window must exceed this interval** by several multiples — the two settings
  are coupled, and a `[1m]` rate on a 60s scrape is the most common empty-graph cause
  (`promql.md`).
- Use service discovery (docker/file SD) over hand-listed targets where the platform offers it, so a
  new container is monitored by existing config rather than by remembering to edit it.
- **Drop noisy metrics at ingest** with `metric_relabel_configs` when an exporter ships thousands of
  series you'll never query. Cheaper than storing them and deciding later.

## Exporters, in rough order of value for a lab

`node_exporter` (host CPU/memory/disk/network — the saturation signal), `cadvisor` or Docker metrics
(per-container resources), the reverse proxy's own metrics (the single best view of user-visible
errors and latency), `blackbox_exporter` (probe the URL a user actually hits, from outside — this is
the one that catches "everything is fine internally but the site is down"), plus per-service
exporters (Postgres, Redis) only when you have a question they answer.

**A custom textfile-collector script is often better than an exporter.** `node_exporter`'s textfile
collector reads any file of metrics you write, which makes a backup's `last_success_timestamp` a
three-line addition to the backup script — the highest-value metric in the lab for the least
machinery.

## Agent pipeline (Alloy / OpenTelemetry)

The pipeline is receive → process → export. Two things go wrong in it, both silently:

- **Batching and queue limits.** An exporter whose queue fills **drops data**, and the drop is only
  visible in the agent's *own* metrics. Scrape the agent itself, and alert on its export failures —
  otherwise the outage you can't see is the monitoring's.
- **Tail sampling is stateful and lossy by design.** Sampling decisions wait for a trace to
  complete; a `decision_wait` shorter than your slowest span drops exactly the slow traces you
  wanted, and a full sampling buffer drops traces silently. If you sample, verify a known-slow
  request survives.

Other pipeline rules worth stating once: pin the agent's version like any other image; keep
processing minimal (parse and drop, don't transform semantics — a transform is code nobody reviews);
format Alloy with `alloy fmt --test <file>` when checking style, then validate component
configuration with `alloy validate <path>` using the deployed version and matching stability and
community-component settings. Formatting checks syntax and layout, not component correctness.
Use `promtool check config <file>` for Prometheus. Treat reload as an apply under
`sde-agents:homelab-engineer`'s tiers, then observe a known signal reaching its destination and
inspect component/export errors. Static validation does not prove ingestion.

## Traces — optional, and honest about it

Traces answer "which hop was slow" across services. In a lab with a handful of services and a
request id already in every log line (`sde-agents:backend-craft`), logs plus metrics usually answer
it faster and cheaper. Adopt tracing when you actually have a multi-hop latency question you can't
answer otherwise; otherwise the collector, storage, and sampling machinery is cost without coverage.
If you do: use the OTel semantic conventions for span and attribute names rather than inventing
them, propagate context at every boundary (a broken chain makes traces useless), and keep attribute
cardinality in mind — the same budget as metric labels.

## Verify

The target shows **up** in Prometheus, the metric appears with the labels you expect, and one real
query against it returns data — paste it. A scrape config that loads cleanly but exposes nothing is
not verified; nor is an agent whose own metrics you never looked at.
