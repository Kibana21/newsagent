from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from src.graph import build_graph
from src.render import to_html


def validate_env() -> None:
    required = ["GOOGLE_APPLICATION_CREDENTIALS"]
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
    out = Path(args.output)

    full_md = final_state.get("final_report", "")
    dev_md = final_state.get("dev_report", "")
    biz_md = final_state.get("biz_report", "")

    (out / f"{today}_full.md").write_text(full_md)
    (out / f"{today}_dev.md").write_text(dev_md)
    (out / f"{today}_biz.md").write_text(biz_md)
    (out / f"{today}_full.html").write_text(to_html(full_md, "full"))
    (out / f"{today}_dev.html").write_text(to_html(dev_md, "dev"))
    (out / f"{today}_biz.html").write_text(to_html(biz_md, "biz"))

    (Path("state") / f"{today}_state.json").write_text(json.dumps(final_state, indent=2, default=str))
    print(f"Done — reports saved:")
    print(f"  {out}/{today}_full.md / .html  (combined)")
    print(f"  {out}/{today}_dev.md  / .html  (developers)")
    print(f"  {out}/{today}_biz.md  / .html  (business)")
    print(f"Email log: {final_state.get('email_log')}")


if __name__ == "__main__":
    main()
