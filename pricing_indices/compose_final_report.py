from __future__ import annotations

import argparse
import re
from pathlib import Path

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")
SECTION_HEADER_RE = re.compile(r"^##\s+(\d+)\.\s+.*$", flags=re.MULTILINE)

TARGET_SECTION_FILES = {
    4: "section4_index_opportunity_board_{token}.md",
    7: "section7_equity_curve_{token}.md",
    11: "section11_best_new_index_opportunities_{token}.md",
    15: "section15_holdings_and_cash_{token}.md",
    16: "section16_continuity_input_{token}.md",
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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


def find_section_bounds(text: str, section_number: int) -> tuple[int, int]:
    matches = list(SECTION_HEADER_RE.finditer(text))
    start_idx = None
    end_idx = None
    for i, match in enumerate(matches):
        num = int(match.group(1))
        if num == section_number:
            start_idx = match.start()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            break
    if start_idx is None or end_idx is None:
        raise RuntimeError(f"Section {section_number} not found in report")
    return start_idx, end_idx


def replace_section(text: str, section_number: int, replacement: str) -> str:
    start_idx, end_idx = find_section_bounds(text, section_number)
    prefix = text[:start_idx].rstrip()
    suffix = text[end_idx:].lstrip()
    parts = [prefix, replacement.strip(), suffix]
    return "\n\n".join(part for part in parts if part)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--in-place", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    report_path = Path(args.report_path) if args.report_path else latest_report_path(output_dir)
    if not report_path.exists():
        raise FileNotFoundError(f"Missing report file: {report_path}")

    token = token_from_report(report_path)
    assembled_dir = output_dir / "assembled"
    original_text = _read_text(report_path)
    composed_text = original_text

    for section_number, template in TARGET_SECTION_FILES.items():
        section_path = assembled_dir / template.format(token=token)
        if not section_path.exists():
            raise FileNotFoundError(f"Missing assembled section block: {section_path}")
        replacement = _read_text(section_path)
        composed_text = replace_section(composed_text, section_number, replacement)

    preview_path = assembled_dir / f"{report_path.stem}_composed_preview.md"
    _write_text(preview_path, composed_text)

    if args.in_place:
        _write_text(report_path, composed_text)

    print(
        f"REPORT_COMPOSER_OK | report={report_path.name} | token={token} | "
        f"preview={preview_path.name} | in_place={'yes' if args.in_place else 'no'}"
    )


if __name__ == "__main__":
    main()
