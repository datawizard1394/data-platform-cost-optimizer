from __future__ import annotations

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from platform_cost.analyzer import CostAnalyzer, _allocate_cents
from platform_cost.generator import CostDataConfig, generate_cost_dataset
from platform_cost.io import read_csv


class CostAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.input_dir = root / "input"
        self.output_dir = root / "reports"
        self.generator_manifest = generate_cost_dataset(
            self.input_dir,
            CostDataConfig(seed=20260728, days=60, workloads=12),
        )
        self.analyzer = CostAnalyzer()

    def run_analysis(self) -> dict[str, object]:
        return self.analyzer.run(
            self.input_dir / "usage.csv",
            self.input_dir / "billing.csv",
            self.output_dir,
        )

    def test_largest_remainder_allocation_is_exact(self) -> None:
        allocated = _allocate_cents(
            Decimal("10.00"),
            {"alpha": Decimal("1"), "beta": Decimal("1"), "gamma": Decimal("1")},
        )
        self.assertEqual(sum(allocated.values()), Decimal("10.00"))
        self.assertEqual(allocated["alpha"], Decimal("3.34"))

    def test_showback_reconciles_exactly_to_billing(self) -> None:
        summary = self.run_analysis()
        showback = read_csv(self.output_dir / "team_showback.csv")
        showback_total = sum(
            (Decimal(row["total_cost"]) for row in showback),
            Decimal("0.00"),
        )

        self.assertEqual(
            showback_total,
            Decimal(summary["total_billed_cost"]),
        )
        self.assertEqual(summary["allocation_difference"], "0.00")
        self.assertGreater(summary["untagged_line_item_count"], 0)

    def test_injected_spikes_are_detected(self) -> None:
        self.run_analysis()
        anomalies = read_csv(self.output_dir / "cost_anomalies.csv")
        detected_dates = {
            row["usage_date"]
            for row in anomalies
            if row["workload_id"] == "W003"
        }

        self.assertTrue(
            set(self.generator_manifest["intentional_cost_spike_dates_for_w003"])
            <= detected_dates
        )

    def test_recommendations_cover_distinct_cost_levers(self) -> None:
        summary = self.run_analysis()
        recommendations = read_csv(self.output_dir / "recommendations.csv")
        categories = {row["category"] for row in recommendations}
        rightsized = {
            row["workload_id"]
            for row in recommendations
            if row["category"] == "RIGHTSIZE_COMPUTE"
        }
        retention = {
            row["workload_id"]
            for row in recommendations
            if row["category"] == "OPTIMIZE_RETENTION"
        }

        self.assertIn("SCHEDULE_NONPROD", categories)
        self.assertEqual(rightsized, {"W004", "W008"})
        self.assertEqual(retention, {"W005", "W010"})
        self.assertGreater(Decimal(summary["modeled_monthly_savings"]), 0)
        self.assertTrue(all(row["requires_validation"] == "true" for row in recommendations))

    def test_rerun_is_byte_idempotent(self) -> None:
        first = self.run_analysis()
        output_paths = [
            self.output_dir / "team_showback.csv",
            self.output_dir / "cost_anomalies.csv",
            self.output_dir / "recommendations.csv",
            self.output_dir / "summary.json",
        ]
        first_bytes = {path.name: path.read_bytes() for path in output_paths}
        second = self.run_analysis()

        self.assertEqual(first, second)
        self.assertEqual(
            first_bytes,
            {path.name: path.read_bytes() for path in output_paths},
        )

    def test_unknown_billing_workload_fails_fast(self) -> None:
        billing_path = self.input_dir / "billing.csv"
        with billing_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            fieldnames = tuple(rows[0])
        rows[0]["workload_id"] = "UNKNOWN"
        with billing_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaisesRegex(ValueError, "unknown workloads"):
            self.run_analysis()


if __name__ == "__main__":
    unittest.main()

