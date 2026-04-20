from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$", flags=re.MULTILINE)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_report_path(output_dir: Path) -> Path:
    hits: list[tuple[str, int, Path]] = []
    for path in output_dir.glob("weekly_indices_review_*.md"):
        match = REPORT_RE.match(path.name)
        if match:
            hits.append((match.group(1), int(match.group(2) or "0"), path))
    if not hits:
        raise FileNotFoundError("No weekly_indices_review_*.md file found")
    hits.sort(key=lambda x: (x[0], x[1]))
    return hits[-1][2]


def token_from_report(report_path: Path) -> str:
    match = REPORT_RE.match(report_path.name)
    if not match:
        raise RuntimeError(f"Unexpected report filename: {report_path.name}")
    return match.group(1)


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def extract_section(md_text: str, section_number: int) -> str:
    matches = list(SECTION_RE.finditer(md_text))
    for idx, match in enumerate(matches):
        if int(match.group(1)) == section_number:
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md_text)
            return md_text[start:end]
    raise RuntimeError(f"Section {section_number} not found in report")


def extract_first_table_first_column(section_text: str) -> list[str]:
    lines = section_text.splitlines()
    in_table = False
    values: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            if not in_table:
                in_table = True
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            if cells[0].lower() == "exposure":
                continue
            values.append(cells[0])
        elif in_table:
            break
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report_path = latest_report_path(output_dir)
    token = token_from_report(report_path)
    ranking_path = output_dir / f"index_candidate_ranking_{token}.json"
    if not ranking_path.exists():
        raise FileNotFoundError(f"Missing ranking artifact: {ranking_path}")

    report_text = report_path.read_text(encoding="utf-8")
    ranking = _read_json(ranking_path)

    section4 = extract_section(report_text, 4)
    section11 = extract_section(report_text, 11)
    section16 = extract_section(report_text, 16)

    report_board_names = {normalize_name(name) for name in extract_first_table_first_column(section4)}
    artifact_board_names = {
        normalize_name(str(row.get("public_index_name")))
        for row in ranking.get("candidates", [])
        if row.get("publish")
    }
    if report_board_names != artifact_board_names:
        raise RuntimeError(
            "Section 4 board entries do not reconcile with publish=true ranking entries. "
            f"report={sorted(report_board_names)} artifact={sorted(artifact_board_names)}"
        )

    unpublished = [row for row in ranking.get("candidates", []) if not row.get("publish")]
    unpublished.sort(key=lambda row: (-float(row.get("challenger_score") or row.get("score") or 0.0), row.get("public_index_name") or ""))
    if unpublished:
        strongest = unpublished[0]
        strongest_name = normalize_name(str(strongest.get("public_index_name") or ""))
        strongest_proxy = normalize_name(str(strongest.get("primary_proxy") or ""))
        section11_lower = normalize_name(section11)
        section16_lower = normalize_name(section16)
        if strongest_name not in section11_lower and strongest_proxy not in section11_lower and strongest_name not in section16_lower and strongest_proxy not in section16_lower:
            raise RuntimeError(
                "Strongest omitted challenger is not visible in section 11 or section 16. "
                f"candidate={strongest.get('public_index_name')} proxy={strongest.get('primary_proxy')}"
            )

    print(
        f"REPORT_ARTIFACT_ALIGNMENT_OK | report={report_path.name} | ranking={ranking_path.name} | token={token}"
    )


if __name__ == "__main__":
    main()
