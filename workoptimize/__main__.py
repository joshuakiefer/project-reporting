"""CLI entry point for WorkOptimize AI."""

import argparse
import sys
from pathlib import Path

from workoptimize import __version__, __app_name__
from workoptimize.config.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="workoptimize",
        description=f"{__app_name__} v{__version__} — AI-powered work optimization assistant",
    )
    parser.add_argument(
        "--version", action="version", version=f"{__app_name__} {__version__}"
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to config.yaml (default: ./config.yaml or ~/.workoptimize/config.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command (default)
    run_parser = subparsers.add_parser("run", help="Start the optimization assistant")
    run_parser.add_argument(
        "--no-encrypt", action="store_true",
        help="Disable encryption (not recommended)",
    )

    # Report command
    subparsers.add_parser("report", help="Show optimization report from tracked patterns")

    # Ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question about your current screen")
    ask_parser.add_argument("question", nargs="+", help="Your question")

    # Automate command
    auto_parser = subparsers.add_parser(
        "automate", help="Generate automation for a detected pattern"
    )
    auto_parser.add_argument(
        "--pattern", type=int, default=0,
        help="Index of the pattern to automate (from report)",
    )

    args = parser.parse_args()

    settings = Settings.load(args.config)

    if args.command is None or args.command == "run":
        if hasattr(args, "no_encrypt") and args.no_encrypt:
            settings.security.encrypt_at_rest = False

        from workoptimize.app import WorkOptimizeApp
        app = WorkOptimizeApp(settings)
        app.run()

    elif args.command == "report":
        from workoptimize.app import WorkOptimizeApp
        app = WorkOptimizeApp(settings)
        report = app.get_optimization_report()
        _print_report(report)

    elif args.command == "ask":
        from workoptimize.app import WorkOptimizeApp
        question = " ".join(args.question)
        app = WorkOptimizeApp(settings)
        answer = app.ask_question(question)
        print(f"\n{answer}\n")

    elif args.command == "automate":
        from workoptimize.app import WorkOptimizeApp
        app = WorkOptimizeApp(settings)
        result = app.build_automation(args.pattern)
        print(f"\n{result}\n")


def _print_report(report: dict) -> None:
    """Pretty-print the optimization report."""
    print(f"\n{'='*60}")
    print(f"  WorkOptimize AI — Optimization Report")
    print(f"{'='*60}\n")

    print(f"Total observations: {report.get('total_observations', 0)}")
    print(f"Patterns detected: {report.get('patterns_detected', 0)}")
    print(f"High-value automations: {report.get('high_value_automations', 0)}")

    breakdown = report.get("activity_breakdown", [])
    if breakdown:
        print(f"\n--- Activity Breakdown ---")
        for item in breakdown:
            print(f"  {item['app_category']:20s} | {item['activity_type']:15s} | {item['count']} observations")

    recommendations = report.get("top_recommendations", [])
    if recommendations:
        print(f"\n--- Top Recommendations ---")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n  {i}. [{rec['potential'].upper()}] {rec['description']}")
            if rec.get("suggestion"):
                print(f"     Suggestion: {rec['suggestion']}")
            print(f"     Observed: {rec['occurrences']} times")
    else:
        print("\nNo automation recommendations yet. Keep working and patterns will emerge!")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
