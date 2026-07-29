"""Deterministic synthetic usage and billing generator."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from platform_cost.io import atomic_write_csv, atomic_write_json, sha256_file

MONEY = Decimal("0.01")


@dataclass(frozen=True)
class CostDataConfig:
    seed: int = 20260728
    days: int = 60
    workloads: int = 12
    start_date: date = date(2025, 1, 1)

    def validate(self) -> None:
        if self.days < 21:
            raise ValueError("days must be at least 21 for anomaly baselines")
        if self.workloads < 4:
            raise ValueError("workloads must be at least 4")


TEAMS = ("analytics", "data_platform", "finance_data", "ml_engineering")
SERVICES = ("batch_compute", "sql_warehouse", "streaming", "feature_pipeline")


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))


def generate_cost_dataset(output_dir: Path, config: CostDataConfig) -> dict[str, object]:
    """Generate fictional platform telemetry and corresponding billing lines."""
    config.validate()
    rng = random.Random(config.seed)
    usage_rows: list[dict[str, str]] = []
    billing_rows: list[dict[str, str]] = []
    anomaly_dates: list[str] = []

    for index in range(1, config.workloads + 1):
        workload_id = f"W{index:03d}"
        team = TEAMS[(index - 1) % len(TEAMS)]
        service = SERVICES[(index - 1) % len(SERVICES)]
        environment = "prod" if index % 3 else "dev"
        owner_tag = "" if index == config.workloads else f"{team}@example.test"
        retention_days = 365 if index in {5, 10} else rng.choice((30, 60, 90))
        base_compute = Decimal(rng.randint(30, 95))
        base_storage = Decimal(rng.randint(180, 900))
        if index in {5, 10}:
            base_storage = max(base_storage, Decimal("650"))
        low_utilization = index in {4, 8}

        for day_index in range(config.days):
            usage_date = config.start_date + timedelta(days=day_index)
            weekday_factor = Decimal("0.78") if usage_date.weekday() >= 5 else Decimal("1")
            compute_units = (
                base_compute
                * weekday_factor
                * Decimal(str(rng.uniform(0.88, 1.12)))
            )
            if index == 3 and day_index in {24, 47}:
                compute_units *= Decimal("4.80")
                anomaly_dates.append(usage_date.isoformat())
            runtime_hours = Decimal(str(rng.uniform(8, 20)))
            if low_utilization:
                cpu_p95 = Decimal(str(rng.uniform(12, 23)))
                memory_p95 = Decimal(str(rng.uniform(17, 30)))
            else:
                cpu_p95 = Decimal(str(rng.uniform(43, 82)))
                memory_p95 = Decimal(str(rng.uniform(45, 84)))
            storage_gb = base_storage + Decimal(day_index) * Decimal(str(index / 8))
            requests_million = Decimal(str(rng.uniform(0.15, 5.5)))
            data_scanned_gb = compute_units * Decimal(str(rng.uniform(2.0, 5.0)))

            usage_rows.append(
                {
                    "usage_date": usage_date.isoformat(),
                    "workload_id": workload_id,
                    "workload_name": f"{service.replace('_', ' ').title()} {index:02d}",
                    "team": team,
                    "environment": environment,
                    "service": service,
                    "owner_tag": owner_tag,
                    "cpu_p95_pct": str(cpu_p95.quantize(MONEY)),
                    "memory_p95_pct": str(memory_p95.quantize(MONEY)),
                    "runtime_hours": str(runtime_hours.quantize(MONEY)),
                    "compute_units": str(compute_units.quantize(MONEY)),
                    "storage_gb": str(storage_gb.quantize(MONEY)),
                    "retention_days": str(retention_days),
                    "requests_million": str(requests_million.quantize(MONEY)),
                    "data_scanned_gb": str(data_scanned_gb.quantize(MONEY)),
                }
            )

            costs = {
                "compute": compute_units * Decimal("0.42"),
                "storage": storage_gb * Decimal("0.021") / Decimal("30"),
                "network": data_scanned_gb * Decimal("0.008"),
            }
            for sku, cost in costs.items():
                billing_rows.append(
                    {
                        "billing_date": usage_date.isoformat(),
                        "line_item_id": f"L{index:03d}-{day_index:03d}-{sku}",
                        "workload_id": workload_id,
                        "team_tag": "" if index % 5 == 0 else team,
                        "owner_tag": owner_tag,
                        "sku": sku,
                        "usage_quantity": (
                            str(compute_units.quantize(MONEY))
                            if sku == "compute"
                            else str(
                                (
                                    storage_gb if sku == "storage" else data_scanned_gb
                                ).quantize(MONEY)
                            )
                        ),
                        "cost": _money(cost),
                        "currency": "CAD",
                    }
                )

    for day_index in range(config.days):
        usage_date = config.start_date + timedelta(days=day_index)
        shared_cost = Decimal("18.00") + Decimal(str((day_index % 7) * 0.35))
        billing_rows.append(
            {
                "billing_date": usage_date.isoformat(),
                "line_item_id": f"SHARED-{day_index:03d}",
                "workload_id": "SHARED",
                "team_tag": "",
                "owner_tag": "platform-shared@example.test",
                "sku": "shared_observability",
                "usage_quantity": "1.00",
                "cost": _money(shared_cost),
                "currency": "CAD",
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_csv(output_dir / "usage.csv", usage_rows, tuple(usage_rows[0]))
    atomic_write_csv(output_dir / "billing.csv", billing_rows, tuple(billing_rows[0]))
    serialized_config = asdict(config)
    serialized_config["start_date"] = config.start_date.isoformat()
    manifest: dict[str, object] = {
        "dataset": "synthetic_data_platform_cost_demo",
        "synthetic": True,
        "config": serialized_config,
        "usage_rows": len(usage_rows),
        "billing_rows": len(billing_rows),
        "intentional_cost_spike_dates_for_w003": sorted(anomaly_dates),
        "low_utilization_workloads": ["W004", "W008"],
        "long_retention_workloads": [
            item for item in ("W005", "W010") if int(item[1:]) <= config.workloads
        ],
        "checksums": {
            "usage.csv": sha256_file(output_dir / "usage.csv"),
            "billing.csv": sha256_file(output_dir / "billing.csv"),
        },
    }
    atomic_write_json(output_dir / "generator_manifest.json", manifest)
    return manifest
