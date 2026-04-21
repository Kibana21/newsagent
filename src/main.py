from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from src.graph import build_graph


def validate_env() -> None:
    required = ["GOOGLE_APPLICATION_CREDENTIALS", "TAVILY_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    creds = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    if not Path(creds).is_file():
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS points to {creds} but file does not exist", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--query", default="latest breakthroughs, releases, and news in Generative AI")
    p.add_argument("--days", type=int, default=2)
    p.add_argument("--output", default="reports")
    p.add_argument("--mode", default="daily", choices=["daily", "monthly"])
    args = p.parse_args()

    validate_env()

    if args.mode == "monthly":
        from src.monthly import run as run_monthly
        result = run_monthly()
        print(f"Monthly digest: {result}")
        return

    Path(args.output).mkdir(parents=True, exist_ok=True)
    Path("state").mkdir(parents=True, exist_ok=True)

    graph = build_graph()
    final_state = graph.invoke({
        "search_query": args.query,
        "days": args.days,
        "mode": args.mode,
    })

    today = date.today().isoformat()
    (Path(args.output) / f"{today}_report.md").write_text(final_state.get("final_report", ""))
    (Path("state") / f"{today}_state.json").write_text(json.dumps(final_state, indent=2, default=str))
    print(f"Done. Email log: {final_state.get('email_log')}")


if __name__ == "__main__":
    main()
