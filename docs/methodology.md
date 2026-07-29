# Methodology

## Input contracts

### usage.csv

One row per workload per day with:

- canonical workload ID, name, team, environment, service, and owner;
- CPU and memory p95 percentages;
- runtime hours and compute units;
- storage GB and declared retention days; and
- request and scan volume.

### billing.csv

One row per fictional billable SKU per workload/day plus one shared platform line
per day. Monetary values are CAD decimal strings rounded to cents.

The analyzer rejects non-shared billing workload IDs that do not exist in usage
metadata.

## Attribution and showback

Canonical usage metadata is the attribution authority for direct spend.
Incomplete `team_tag` or `owner_tag` values remain measurable but do not force
otherwise attributable cost into an “unknown” bucket.

Shared observability cost uses direct-cost share:

```text
team_weight = team_direct_cost / all_direct_cost
exact_allocation = shared_cost × team_weight
```

Flooring can leave fractional cents. The largest-remainder method distributes
those cents deterministically, ensuring:

```text
sum(team total cost) == sum(all billing cost)
```

## Anomalies

The detector is workload-specific and uses only prior observations. The first 14
days form the minimum baseline. Median absolute deviation resists a previous
spike better than mean and standard deviation.

Limitations:

- no weekday/weekend-specific baseline;
- no holiday, release, or business-event context;
- no minimum persistence duration; and
- no correction for multiple comparisons.

Operational deployment should backtest precision/recall, route findings through
owners, and tune thresholds by workload criticality.

## Recommendations

Savings are normalized from the observed period to 30 days, then multiplied by
an explicit category factor. They ignore discounts, commitments, taxes, growth,
engineering effort, migration cost, and interaction between recommendations.

The output is a prioritized hypothesis backlog. It does not resize, delete,
schedule, purchase, or modify any resource.

## Data-quality evidence

The summary records:

- input and output SHA-256 checksums;
- billed, direct, shared, reconciled, and difference amounts;
- untagged line count and cost;
- period boundaries; and
- anomaly/recommendation counts.

The deterministic seed allows reviewers to reproduce every value.

