"""Showback, anomaly detection, and modeled optimization recommendations."""

from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import median

from platform_cost.io import (
    atomic_write_csv,
    atomic_write_json,
    read_csv,
    sha256_file,
)

MONEY = Decimal("0.01")
SHOWBACK_FIELDS = (
    "team",
    "direct_cost",
    "allocated_shared_cost",
    "total_cost",
    "percent_of_total",
)
ANOMALY_FIELDS = (
    "usage_date",
    "workload_id",
    "workload_name",
    "actual_cost",
    "baseline_median",
    "mad",
    "threshold",
    "variance_pct",
    "severity",
)
RECOMMENDATION_FIELDS = (
    "recommendation_id",
    "workload_id",
    "workload_name",
    "team",
    "category",
    "evidence",
    "recommended_action",
    "modeled_monthly_savings",
    "assumption",
    "confidence",
    "requires_validation",
)


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def _allocate_cents(
    amount: Decimal,
    weights: dict[str, Decimal],
) -> dict[str, Decimal]:
    """Allocate an amount exactly using the largest-remainder method."""
    if amount < 0:
        raise ValueError("allocation amount cannot be negative")
    total_weight = sum(weights.values(), Decimal("0"))
    if not weights or total_weight <= 0:
        raise ValueError("positive allocation weights are required")
    exact = {key: amount * weight / total_weight for key, weight in weights.items()}
    allocated = {
        key: value.quantize(MONEY, rounding=ROUND_DOWN) for key, value in exact.items()
    }
    remaining_cents = int(
        (amount.quantize(MONEY) - sum(allocated.values())) / MONEY
    )
    order = sorted(
        exact,
        key=lambda key: (-(exact[key] - allocated[key]), key),
    )
    for key in order[:remaining_cents]:
        allocated[key] += MONEY
    return allocated


class CostAnalyzer:
    """Analyze fictional telemetry and billing with explicit heuristic assumptions."""

    def run(
        self,
        usage_path: Path,
        billing_path: Path,
        output_dir: Path,
    ) -> dict[str, object]:
        usage = read_csv(usage_path)
        billing = read_csv(billing_path)
        if not usage or not billing:
            raise ValueError("usage and billing inputs must be non-empty")

        metadata: dict[str, dict[str, str]] = {}
        for row in usage:
            metadata[row["workload_id"]] = row
        missing_workload_ids = sorted(
            {
                row["workload_id"]
                for row in billing
                if row["workload_id"] != "SHARED"
                and row["workload_id"] not in metadata
            }
        )
        if missing_workload_ids:
            raise ValueError(
                f"billing contains unknown workloads: {','.join(missing_workload_ids)}"
            )

        showback, allocation_metrics = self._build_showback(billing, metadata)
        anomalies = self._detect_anomalies(billing, metadata)
        recommendations = self._recommend(usage, billing, metadata)
        output_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_csv(output_dir / "team_showback.csv", showback, SHOWBACK_FIELDS)
        atomic_write_csv(output_dir / "cost_anomalies.csv", anomalies, ANOMALY_FIELDS)
        atomic_write_csv(
            output_dir / "recommendations.csv",
            recommendations,
            RECOMMENDATION_FIELDS,
        )

        dates = sorted({row["billing_date"] for row in billing})
        modeled_monthly_savings = sum(
            (
                Decimal(row["modeled_monthly_savings"])
                for row in recommendations
            ),
            Decimal("0.00"),
        )
        summary: dict[str, object] = {
            "analysis": "synthetic_data_platform_cost_optimizer",
            "synthetic": True,
            "currency": "CAD",
            "period": {
                "start": dates[0],
                "end": dates[-1],
                "days": len(dates),
            },
            **allocation_metrics,
            "team_count": len(showback),
            "anomaly_count": len(anomalies),
            "recommendation_count": len(recommendations),
            "modeled_monthly_savings": _money(modeled_monthly_savings),
            "disclaimer": (
                "Modeled synthetic opportunities only; validate performance, "
                "contracts, architecture, and business risk before action."
            ),
            "assumptions": [
                "Shared observability cost is allocated by each team's direct-cost share.",
                "Anomalies use a 14-day rolling median and median absolute deviation.",
                "Rightsizing models 25% of normalized monthly compute cost.",
                "Retention optimization models 40% of normalized monthly storage cost.",
                "Non-production scheduling models 15% of normalized monthly compute cost.",
            ],
            "input_checksums": {
                "usage.csv": sha256_file(usage_path),
                "billing.csv": sha256_file(billing_path),
            },
        }
        atomic_write_json(output_dir / "summary.json", summary)
        summary["output_checksums"] = {
            "team_showback.csv": sha256_file(output_dir / "team_showback.csv"),
            "cost_anomalies.csv": sha256_file(output_dir / "cost_anomalies.csv"),
            "recommendations.csv": sha256_file(output_dir / "recommendations.csv"),
        }
        atomic_write_json(output_dir / "summary.json", summary)
        return summary

    def _build_showback(
        self,
        billing: list[dict[str, str]],
        metadata: dict[str, dict[str, str]],
    ) -> tuple[list[dict[str, str]], dict[str, object]]:
        direct: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        shared = Decimal("0.00")
        total = Decimal("0.00")
        untagged_cost = Decimal("0.00")
        untagged_count = 0
        for row in billing:
            cost = Decimal(row["cost"])
            total += cost
            if row["workload_id"] == "SHARED":
                shared += cost
                continue
            team = metadata[row["workload_id"]]["team"]
            direct[team] += cost
            if not row["team_tag"] or not row["owner_tag"]:
                untagged_cost += cost
                untagged_count += 1

        allocated_shared = _allocate_cents(shared, dict(direct))
        showback: list[dict[str, str]] = []
        for team in sorted(direct):
            team_total = direct[team] + allocated_shared[team]
            showback.append(
                {
                    "team": team,
                    "direct_cost": _money(direct[team]),
                    "allocated_shared_cost": _money(allocated_shared[team]),
                    "total_cost": _money(team_total),
                    "percent_of_total": str(
                        (team_total / total * 100).quantize(MONEY)
                    ),
                }
            )
        reconciled_total = sum(
            (Decimal(row["total_cost"]) for row in showback),
            Decimal("0.00"),
        )
        if reconciled_total != total.quantize(MONEY):
            raise ArithmeticError("showback allocation does not reconcile to billing")
        return showback, {
            "total_billed_cost": _money(total),
            "direct_cost": _money(total - shared),
            "shared_cost_allocated": _money(shared),
            "showback_reconciled_cost": _money(reconciled_total),
            "allocation_difference": _money(total - reconciled_total),
            "untagged_line_item_count": untagged_count,
            "untagged_line_item_cost": _money(untagged_cost),
        }

    def _detect_anomalies(
        self,
        billing: list[dict[str, str]],
        metadata: dict[str, dict[str, str]],
    ) -> list[dict[str, str]]:
        daily_cost: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0.00"))
        )
        for row in billing:
            if row["workload_id"] != "SHARED":
                daily_cost[row["workload_id"]][row["billing_date"]] += Decimal(
                    row["cost"]
                )

        anomalies: list[dict[str, str]] = []
        for workload_id, by_date in sorted(daily_cost.items()):
            ordered = sorted(by_date.items())
            for index in range(14, len(ordered)):
                usage_date, actual = ordered[index]
                window = [value for _, value in ordered[index - 14 : index]]
                baseline = Decimal(str(median(window)))
                deviations = [abs(value - baseline) for value in window]
                mad = Decimal(str(median(deviations)))
                robust_band = mad * Decimal("1.4826") * Decimal("3")
                threshold = baseline + max(robust_band, Decimal("10.00"))
                if actual > threshold:
                    variance_pct = (
                        (actual - baseline) / baseline * 100
                        if baseline
                        else Decimal("0")
                    )
                    anomalies.append(
                        {
                            "usage_date": usage_date,
                            "workload_id": workload_id,
                            "workload_name": metadata[workload_id]["workload_name"],
                            "actual_cost": _money(actual),
                            "baseline_median": _money(baseline),
                            "mad": _money(mad),
                            "threshold": _money(threshold),
                            "variance_pct": str(variance_pct.quantize(MONEY)),
                            "severity": (
                                "HIGH"
                                if actual > threshold * Decimal("1.75")
                                else "MEDIUM"
                            ),
                        }
                    )
        return anomalies

    def _recommend(
        self,
        usage: list[dict[str, str]],
        billing: list[dict[str, str]],
        metadata: dict[str, dict[str, str]],
    ) -> list[dict[str, str]]:
        usage_by_workload: dict[str, list[dict[str, str]]] = defaultdict(list)
        cost_by_workload_sku: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0.00"))
        )
        for row in usage:
            usage_by_workload[row["workload_id"]].append(row)
        for row in billing:
            if row["workload_id"] != "SHARED":
                cost_by_workload_sku[row["workload_id"]][row["sku"]] += Decimal(
                    row["cost"]
                )

        recommendations: list[dict[str, str]] = []

        def add(
            workload_id: str,
            meta: dict[str, str],
            category: str,
            evidence: str,
            action: str,
            savings: Decimal,
            assumption: str,
            confidence: str,
        ) -> None:
            recommendations.append(
                {
                    "recommendation_id": f"REC-{len(recommendations) + 1:03d}",
                    "workload_id": workload_id,
                    "workload_name": meta["workload_name"],
                    "team": meta["team"],
                    "category": category,
                    "evidence": evidence,
                    "recommended_action": action,
                    "modeled_monthly_savings": _money(savings),
                    "assumption": assumption,
                    "confidence": confidence,
                    "requires_validation": "true",
                }
            )

        for workload_id, rows in sorted(usage_by_workload.items()):
            days = len({row["usage_date"] for row in rows})
            meta = metadata[workload_id]
            average_cpu = sum(Decimal(row["cpu_p95_pct"]) for row in rows) / len(rows)
            average_memory = sum(
                Decimal(row["memory_p95_pct"]) for row in rows
            ) / len(rows)
            average_storage = sum(
                Decimal(row["storage_gb"]) for row in rows
            ) / len(rows)
            average_runtime = sum(
                Decimal(row["runtime_hours"]) for row in rows
            ) / len(rows)
            monthly_factor = Decimal("30") / days
            compute_monthly = (
                cost_by_workload_sku[workload_id]["compute"] * monthly_factor
            )
            storage_monthly = (
                cost_by_workload_sku[workload_id]["storage"] * monthly_factor
            )

            if average_cpu < 35 and average_memory < 40:
                add(
                    workload_id,
                    meta,
                    "RIGHTSIZE_COMPUTE",
                    (
                        f"mean cpu_p95={average_cpu.quantize(MONEY)}%; "
                        f"mean memory_p95={average_memory.quantize(MONEY)}%"
                    ),
                    "Benchmark the next smaller compute tier under peak workload.",
                    compute_monthly * Decimal("0.25"),
                    "25% of normalized monthly compute spend",
                    "MEDIUM",
                )
            if int(meta["retention_days"]) > 90 and average_storage > 500:
                add(
                    workload_id,
                    meta,
                    "OPTIMIZE_RETENTION",
                    (
                        f"retention={meta['retention_days']} days; "
                        f"mean storage={average_storage.quantize(MONEY)} GB"
                    ),
                    "Validate policy, then tier or expire data beyond the hot window.",
                    storage_monthly * Decimal("0.40"),
                    "40% of normalized monthly storage spend",
                    "MEDIUM",
                )
            if meta["environment"] != "prod" and average_runtime > 10:
                add(
                    workload_id,
                    meta,
                    "SCHEDULE_NONPROD",
                    (
                        f"environment={meta['environment']}; "
                        f"mean runtime={average_runtime.quantize(MONEY)} h/day"
                    ),
                    "Test an off-hours shutdown schedule with owner opt-out.",
                    compute_monthly * Decimal("0.15"),
                    "15% of normalized monthly compute spend",
                    "LOW",
                )
        recommendations.sort(
            key=lambda row: (
                -Decimal(row["modeled_monthly_savings"]),
                row["recommendation_id"],
            )
        )
        return recommendations
