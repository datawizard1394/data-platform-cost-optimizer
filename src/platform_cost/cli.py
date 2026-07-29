"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from platform_cost.analyzer import CostAnalyzer
from platform_cost.generator import CostDataConfig, generate_cost_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="platform-cost",
        description="Run the synthetic data-platform cost optimization demo.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=20260728)
    generate.add_argument("--days", type=int, default=60)
    generate.add_argument("--workloads", type=int, default=12)
    generate.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=date(2025, 1, 1),
    )

    analyze = commands.add_parser("analyze")
    analyze.add_argument("--usage", type=Path, required=True)
    analyze.add_argument("--billing", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)

    demo = commands.add_parser("demo")
    demo.add_argument("--workspace", type=Path, required=True)
    demo.add_argument("--seed", type=int, default=20260728)
    demo.add_argument("--days", type=int, default=60)
    demo.add_argument("--workloads", type=int, default=12)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        result = generate_cost_dataset(
            args.output,
            CostDataConfig(
                seed=args.seed,
                days=args.days,
                workloads=args.workloads,
                start_date=args.start_date,
            ),
        )
    elif args.command == "analyze":
        result = CostAnalyzer().run(args.usage, args.billing, args.output)
    else:
        input_dir = args.workspace / "input"
        output_dir = args.workspace / "reports"
        generate_cost_dataset(
            input_dir,
            CostDataConfig(
                seed=args.seed,
                days=args.days,
                workloads=args.workloads,
            ),
        )
        result = CostAnalyzer().run(
            input_dir / "usage.csv",
            input_dir / "billing.csv",
            output_dir,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

