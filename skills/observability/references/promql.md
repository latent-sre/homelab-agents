# PromQL — the shapes that come up, and the traps

Read before writing a PromQL query, a recording rule, or metric arithmetic. The universal rules live
in `skills/observability/SKILL.md`. On any conflict, SKILL.md wins.

## The four query shapes that cover most needs

```promql
# 1. Rate of a counter — ALWAYS rate() before aggregating, never the raw counter
sum(rate(http_requests_total[5m])) by (service)

# 2. Error ratio — the numerator's label set must be a subset of the denominator's
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
  / sum(rate(http_requests_total[5m])) by (service)

# 3. Latency percentile from a histogram — by (le) is mandatory
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))

# 4. Staleness of each backup target/dataset — retain the series identity
time() - backup_last_success_timestamp_seconds > 26 * 3600
```

The backup metric must expose a stable identity for every required target/dataset. Keep those
labels: `max ... by (job)` lets one recent backup hide another target's stale backup under the
same job. Aggregate only redundant reports of the same backup obligation, retaining all labels
that distinguish obligations. A missing series requires a separate expected-inventory check;
a threshold cannot alert on a series that is absent.

## Traps, in the order people hit them

- **`rate()` on a gauge is meaningless**, and a raw counter on a graph only ever goes up. `rate()`
  and `increase()` are for counters; `avg_over_time()`/`max_over_time()` are for gauges.
- **Aggregate after `rate()`, never before.** `rate(sum(...))` is wrong — a counter reset in any
  series corrupts the sum. `sum(rate(...))` is right.
- **The range must exceed the scrape interval, comfortably.** `rate(x[1m])` with a 60s scrape often
  has one point and returns nothing. Rule of thumb: at least 4× the interval — `[5m]` for a 15s or
  30s scrape.
- **Division by zero yields no data, not zero.** An error-ratio panel goes blank on an idle service,
  which reads as "healthy" and hides a service receiving no traffic at all. Guard it, or pair the
  panel with a traffic panel so blank is distinguishable from fine.
- **Binary operators match on the full label set.** If the numerator carries a label the denominator
  lacks, you get an empty result. Use `on(...)`/`ignoring(...)` deliberately; `group_left` when a
  many-to-one join is genuinely intended.
- **`histogram_quantile` needs the `le` label**, and interpolates *within* buckets: with coarse
  buckets your p99 is an artifact of bucket boundaries, not a measurement. Choose bucket edges
  around the latencies you care about before trusting the number.
- **Averaging percentiles across instances is arithmetically wrong** (`avg(histogram_quantile(...))`
  means nothing). Aggregate the buckets, then take the quantile — as in shape 3.
- **`absent()` is how you alert on something that stopped existing.** A target that disappears emits
  no metrics, so every threshold on it silently stops firing: `absent(up{job="x"})` catches the case
  where the *monitoring* broke, which is the failure mode that hides all the others.
- **`up == 0` and "no data" are different.** `up` exists only while the scrape target is configured;
  remove the target and even `up` is gone.

## Recording rules

Precompute what's expensive and reused (a ratio a dashboard hits on every refresh; a long-window
aggregate). Name them by what they are: `job:http_requests:error_ratio5m` — the `level:metric:ops`
convention keeps a rule distinguishable from a raw metric at a glance. Rules add cost on every
evaluation interval, so add them for queries that are slow *and* frequent, not on principle.

Validate before reload: `promtool check rules <file>`, and `promtool test rules` when the arithmetic
is worth pinning with a unit test — which it is for anything driving an alert.
