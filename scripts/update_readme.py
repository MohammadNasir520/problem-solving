#!/usr/bin/env python3
import datetime
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

START_MARKER = "<!-- DAILY-LOG:START -->"
END_MARKER = "<!-- DAILY-LOG:END -->"

DAY_DIR_RE = re.compile(r"^day(\d+)-(\d{2}:\d{2}:\d{4})$")


def read_problem_link(day_dir: Path) -> str:
    question_path = day_dir / "question.txt"
    if not question_path.exists():
        return "N/A"
    content = question_path.read_text(encoding="utf-8").strip()
    return content or "N/A"


def as_link(text: str, target: str) -> str:
    if text == "N/A" or target == "N/A":
        return "N/A"
    return f"[{text}]({target})"


def build_rows() -> list[str]:
    rows = []
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir():
            continue
        match = DAY_DIR_RE.match(entry.name)
        if not match:
            continue
        day_num = int(match.group(1))
        date_str = match.group(2)
        problem = read_problem_link(entry)
        solutions = sorted(entry.glob("*.cpp"))
        solution = solutions[0].relative_to(ROOT).as_posix() if solutions else "N/A"
        input_file = entry / "input.txt"
        output_file = entry / "output.txt"
        input_path = input_file.relative_to(ROOT).as_posix() if input_file.exists() else "N/A"
        output_path = output_file.relative_to(ROOT).as_posix() if output_file.exists() else "N/A"

        problem_cell = as_link(problem, problem) if problem.startswith("http") else problem
        solution_cell = as_link(solution, solution)
        input_cell = as_link(input_path, input_path)
        output_cell = as_link(output_path, output_path)

        rows.append(
            (
                day_num,
                f"| day{day_num} | {date_str} | {problem_cell} | {solution_cell} | {input_cell} | {output_cell} |",
            )
        )

    rows.sort(key=lambda r: r[0])
    return [row for _, row in rows]


def render_log() -> str:
    today = datetime.date.today().isoformat()
    header = [
        f"{START_MARKER}",
        f"Last updated: {today}",
        "",
        "| Day | Date | Problem | Solution | Input | Output |",
        "| --- | ---- | ------- | -------- | ----- | ------ |",
    ]
    rows = build_rows()
    if not rows:
        rows = ["| - | - | - | - | - | - |"]
    footer = [f"{END_MARKER}"]
    return "\n".join(header + rows + footer)


def update_readme() -> None:
    content = README.read_text(encoding="utf-8")
    if START_MARKER not in content or END_MARKER not in content:
        raise SystemExit("Daily log markers not found in README.md")

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    new_content = pattern.sub(render_log(), content)
    README.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    update_readme()
