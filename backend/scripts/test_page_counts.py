"""Run a bounded live-model page-count matrix; retain every attempt and failure."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--counts", type=int, nargs="+", default=[5, 10, 15, 20])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", help="Override only the isolated test accounts' model")
    args = parser.parse_args()
    if any(n < 5 or n > 20 for n in args.counts):
        parser.error("Counts must be between 5 and 20")
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve().parent
    source = script / "fixtures/page_count_source.txt"
    summary = {
        "started_at": datetime.now(UTC).isoformat(),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "audience_profile": "academic",
        "requested_model": args.model,
        "cases": [],
    }
    for count in args.counts:
        folder = root / f"pages-{count}"
        folder.mkdir()
        print(f"Starting {count}-page live test", flush=True)
        with (folder / "run.log").open("w", encoding="utf-8") as log:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script / "test_live_api.py"),
                    "--url",
                    args.url,
                    "--page-count",
                    str(count),
                    "--duration-minutes",
                    str(count),
                    "--audience-profile",
                    "academic",
                    "--personal-model",
                    "--upload-source",
                    "--source-file",
                    str(source),
                    "--output-dir",
                    str(folder),
                ]
                + (["--model", args.model] if args.model else []),
                stdout=log,
                stderr=log,
                check=False,
            )
        report_file = folder / "report.json"
        report = json.loads(report_file.read_text(encoding="utf-8")) if report_file.exists() else {}
        result = {
            key: report.get(key)
            for key in (
                "requested_pages",
                "project_id",
                "personal_model",
                "outline_pages",
                "ready_pages",
                "failed_pages",
                "exported_pages",
                "outline_seconds",
                "deck_seconds",
                "pptx_bytes",
                "pptx_verified",
                "personal_key_removed",
                "failure_type",
                "failure_message",
            )
        }
        result["passed"] = completed.returncode == 0 and report.get("passed", False)
        result["warning_count"] = (
            None
            if "quality_issues" not in report
            else sum(i["severity"] == "warning" for i in report.get("quality_issues", []))
        )
        result["error_count"] = (
            None
            if "quality_issues" not in report
            else sum(i["severity"] == "error" for i in report.get("quality_issues", []))
        )
        summary["cases"].append(result)
        (root / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False), flush=True)
    summary["completed_at"] = datetime.now(UTC).isoformat()
    (root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0 if all(case["passed"] for case in summary["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
