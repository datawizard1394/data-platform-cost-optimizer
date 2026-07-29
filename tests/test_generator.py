from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from platform_cost.generator import CostDataConfig, generate_cost_dataset
from platform_cost.io import sha256_file


class CostGeneratorTests(unittest.TestCase):
    def test_same_seed_is_byte_deterministic(self) -> None:
        config = CostDataConfig(seed=15, days=30, workloads=8)
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_path = Path(first)
            second_path = Path(second)
            first_manifest = generate_cost_dataset(first_path, config)
            second_manifest = generate_cost_dataset(second_path, config)

            self.assertEqual(first_manifest, second_manifest)
            for name in ("usage.csv", "billing.csv"):
                self.assertEqual(
                    sha256_file(first_path / name),
                    sha256_file(second_path / name),
                )

    def test_manifest_discloses_synthetic_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = generate_cost_dataset(
                Path(directory),
                CostDataConfig(seed=5, days=30, workloads=12),
            )

        self.assertTrue(manifest["synthetic"])
        self.assertEqual(manifest["low_utilization_workloads"], ["W004", "W008"])
        self.assertEqual(manifest["long_retention_workloads"], ["W005", "W010"])
        self.assertGreater(
            len(manifest["intentional_cost_spike_dates_for_w003"]),
            0,
        )

    def test_short_baseline_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CostDataConfig(days=14).validate()


if __name__ == "__main__":
    unittest.main()

