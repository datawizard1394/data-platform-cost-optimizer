# ADR 0001: Prefer exact allocation and explainable heuristics

- **Status:** Accepted
- **Date:** 2026-07-28

## Context

A cost optimizer can create false confidence if allocations do not reconcile or
recommendations hide their assumptions. The portfolio must demonstrate
financial arithmetic and prioritization without pretending to automate real
cloud decisions.

## Decision

Use canonical workload metadata for direct attribution, allocate shared spend
with deterministic largest remainder, and fail if showback differs from billing.
Use a rolling median/MAD detector and simple recommendation rules whose evidence,
percentage assumption, confidence, and validation requirement appear in every
row.

## Consequences

Benefits:

- total ownership reconciles exactly to the cent;
- results can be explained to engineering and finance;
- tag gaps remain measurable;
- recommendations are testable and reproducible; and
- no third-party service or credentials are required.

Trade-offs:

- direct-cost share may not match causal consumption of shared services;
- heuristic opportunities can overlap;
- MAD lacks rich seasonality and context; and
- modeled savings omit commercial discounts and implementation costs.

## Rejected alternative

An opaque prediction model was rejected for this reference because synthetic
training data would not establish credible accuracy and would make
recommendations less interview-defensible.

