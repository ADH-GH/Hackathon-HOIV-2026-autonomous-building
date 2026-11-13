"""Command line.

    python -m building_ops run <data_dir> [--out decisions.jsonl] [--actions actions.jsonl]
    python -m building_ops inspect <data_dir>
    python -m building_ops check decisions.jsonl
    python -m building_ops report decisions.jsonl [--actions actions.jsonl] [--out out/report.html]
    python -m building_ops dashboard <data_dir> decisions.jsonl [--actions actions.jsonl] [--out out/dashboard.html]
    python -m building_ops sample [--out out/sample]
"""
from __future__ import annotations

import argparse
import json
import sys

from .check import check
from .dashboard import build as build_dashboard
from .dataset import Dataset, inspect
from .pipeline import run
from .report import build
from .sample import write_sample


def main() -> None:
    ap = argparse.ArgumentParser(prog="building_ops", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="write decisions.jsonl for one data directory")
    r.add_argument("data_dir")
    r.add_argument("--out", default="decisions.jsonl")
    r.add_argument("--actions", default=None, help="also write the simulated action trail")
    i = sub.add_parser("inspect", help="list files, columns, row counts and blank shares")
    i.add_argument("data_dir")
    c = sub.add_parser("check", help="check a decisions file against the contract and the autonomy rules")
    c.add_argument("decisions")
    p = sub.add_parser("report", help="write the decision viewer as one HTML file")
    p.add_argument("decisions")
    p.add_argument("--actions", default=None)
    p.add_argument("--out", default="out/report.html")
    d = sub.add_parser("dashboard", help="write the dashboard with every case and its evidence as one HTML file")
    d.add_argument("data_dir")
    d.add_argument("decisions")
    d.add_argument("--actions", default=None)
    d.add_argument("--out", default="out/dashboard.html")
    s = sub.add_parser("sample", help="write hand-made sample decisions and their viewer, labelled as sample")
    s.add_argument("--out", default="out/sample")
    args = ap.parse_args()
    if args.cmd == "run":
        run(args.data_dir, args.out, args.actions)
    elif args.cmd == "check":
        result = check(args.decisions)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        sys.exit(0 if result["ok"] else 1)
    elif args.cmd == "report":
        print(build(args.decisions, args.out, args.actions))
    elif args.cmd == "dashboard":
        print(build_dashboard(args.data_dir, args.decisions, args.out, args.actions))
    elif args.cmd == "sample":
        print(write_sample(args.out))
    else:
        print(json.dumps(inspect(Dataset(args.data_dir)), indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
