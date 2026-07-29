# Cost analysis runbook

This runbook covers the synthetic local demonstration. Real ownership,
thresholds, and approval paths must be defined with engineering and finance.

## Successful analysis

- `allocation_difference` equals `0.00`;
- total billed and showback reconciled cost match;
- input and output checksums are present;
- the period matches the expected billing export boundary; and
- every recommendation states an assumption and requires validation.

## Allocation mismatch

1. Stop report publication.
2. Confirm currency and decimal precision are consistent.
3. Check for unknown workloads, duplicate billing line IDs, and incomplete
   period extracts.
4. Compare direct, shared, allocated, and rounded amounts.
5. Add a failing allocation fixture before changing the algorithm.
6. Regenerate in an isolated directory and require exact reconciliation.

Never hide a difference in an “adjustment” bucket without documented ownership.

## Cost anomaly response

1. Confirm the billing line is not a correction or delayed invoice.
2. Compare usage dimensions: compute, runtime, scan volume, storage, and requests.
3. Correlate with releases, backfills, incidents, and business events.
4. Contact the canonical workload owner.
5. Classify as expected, one-off, recurring regression, or data error.
6. Record the outcome so production thresholds can be backtested.

This demo reports only; it does not page or change infrastructure.

## Recommendation review

For each candidate:

1. Validate the metric window and workload criticality.
2. Confirm reservations, commitments, minimums, and contract pricing.
3. Test one change in a non-production/canary environment.
4. Measure latency, throughput, failures, and cost before/after.
5. Capture engineering effort and rollback cost.
6. Require owner and finance approval before treating savings as forecast.

Do not add overlapping opportunity values without modeling their interaction.

## Missing tags

Use canonical metadata to keep showback usable, but open governance work for the
underlying tag gap. Track untagged cost and line count over time. Blocking
production workloads solely for tag completeness is an organizational policy
decision outside this demo.

## Suggested production controls

- immutable billing export ingestion with late-arrival handling;
- currency and invoice-period contracts;
- semantic ownership mapping with effective dates;
- budget and forecast variance;
- anomaly outcome feedback;
- recommendation lifecycle from proposed to validated, accepted, implemented,
  verified, or rejected; and
- realized savings measured against a reviewed baseline.

