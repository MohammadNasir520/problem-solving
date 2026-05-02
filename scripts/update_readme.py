#!/usr/bin/env python3
import datetime
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

START_MARKER = "<!-- DAILY-LOG:START -->"
END_MARKER = "<!-- DAILY-LOG:END -->"
SUMMARY_START = "<!-- SUMMARY:START -->"
SUMMARY_END = "<!-- SUMMARY:END -->"

DAY_DIR_RE = re.compile(r"^day(\d+)-(\d{2}:\d{2}:\d{4})$")
CF_URL_RE = re.compile(r"codeforces\.com/problemset/problem/(\d+)/([A-Z]\d*)", re.IGNORECASE)


def read_question(day_dir: Path) -> str:
    question_path = day_dir / "question.txt"
    if not question_path.exists():
        return "N/A"
    return question_path.read_text(encoding="utf-8").strip() or "N/A"


def problem_cell(url: str) -> str:
    if url == "N/A":
        return "N/A"
    if not url.startswith("http"):
        return url
    match = CF_URL_RE.search(url)
    if match:
        name = f"{match.group(1)}{match.group(2)}"
        return f"[{name}]({url})"
    return f"[Problem]({url})"


def as_link(path: str) -> str:
    return f"[{Path(path).name}]({path})" if path != "N/A" else "N/A"


def build_entries() -> list[dict]:
    entries = []
    for entry in sorted(ROOT.iterdir()):
        if not entry.is_dir():
            continue
        match = DAY_DIR_RE.match(entry.name)
        if not match:
            continue
        day_num = int(match.group(1))
        date_str = match.group(2)
        url = read_question(entry)
        solutions = sorted(entry.glob("*.cpp"))
        solution = solutions[0].relative_to(ROOT).as_posix() if solutions else "N/A"
        input_file = entry / "input.txt"
        output_file = entry / "output.txt"
        input_path = input_file.relative_to(ROOT).as_posix() if input_file.exists() else "N/A"
        output_path = output_file.relative_to(ROOT).as_posix() if output_file.exists() else "N/A"
        entries.append({
            "day_num": day_num,
            "date_str": date_str,
            "url": url,
            "solution": solution,
            "input_path": input_path,
            "output_path": output_path,
            "folder": entry.name,
        })
    entries.sort(key=lambda e: e["day_num"])
    return entries


def build_rows() -> list[str]:
    rows = []
    for e in build_entries():
        folder_link = f"[Day {e['day_num']}]({e['folder']}/)"
        rows.append(
            f"| {folder_link} | {e['date_str']} | {problem_cell(e['url'])} "
            f"| {as_link(e['solution'])} | {as_link(e['input_path'])} | {as_link(e['output_path'])} |"
        )
    return rows


def parse_date(date_str: str) -> datetime.date:
    d, m, y = date_str.split(":")
    return datetime.date(int(y), int(m), int(d))


def git_active_dates() -> set[datetime.date]:
    result = subprocess.run(
        ["git", "log", "--format=%ad", "--date=short"],
        cwd=ROOT, capture_output=True, text=True,
    )
    dates = set()
    for line in result.stdout.splitlines():
        line = line.strip()
        if line:
            dates.add(datetime.date.fromisoformat(line))
    return dates


def compute_streaks(active_dates: set) -> tuple[int, int]:
    if not active_dates:
        return 0, 0
    today = datetime.date.today()
    sorted_dates = sorted(active_dates)

    longest = current = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    # current streak: start from today, or yesterday if today has no activity yet
    cursor = today if today in active_dates else today - datetime.timedelta(days=1)
    streak = 0
    while cursor in active_dates:
        streak += 1
        cursor -= datetime.timedelta(days=1)

    return streak, longest


SVG_FILE = ROOT / "activity.svg"

CELL = 11   # px
GAP  = 2    # px
STEP = CELL + GAP
LEFT_PAD = 28  # space for day labels
TOP_PAD  = 18  # space for month labels
COLOR_ACTIVE   = "#26a641"
COLOR_INACTIVE = "#ebedf0"
COLOR_LABEL    = "#57606a"


def build_weeks() -> list[list[datetime.date]]:
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday() + 7 * 11)
    weeks, cursor = [], start
    while cursor <= datetime.date.today():
        weeks.append([cursor + datetime.timedelta(days=i) for i in range(7)])
        cursor += datetime.timedelta(weeks=1)
    return weeks


def activity_svg(active_dates: set) -> str:
    today = datetime.date.today()
    weeks = build_weeks()
    n = len(weeks)
    width  = LEFT_PAD + n * STEP + GAP
    height = TOP_PAD + 7 * STEP + GAP
    font = "10px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'  <style>text {{ font: {font}; fill: {COLOR_LABEL}; }}</style>',
    ]

    # month labels — appear on the column where the 1st of the month falls
    seen_months: set = set()
    for i, week in enumerate(weeks):
        for day in week:
            if day <= today and day.day == 1 and day.month not in seen_months:
                x = LEFT_PAD + i * STEP
                lines.append(f'  <text x="{x}" y="12">{day.strftime("%b")}</text>')
                seen_months.add(day.month)
                break

    # day labels — all 7 days
    for dow, label in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        y = TOP_PAD + dow * STEP + CELL
        lines.append(f'  <text x="0" y="{y}" text-anchor="start">{label}</text>')

    # cells
    for i, week in enumerate(weeks):
        for dow, day in enumerate(week):
            if day > today:
                continue
            x = LEFT_PAD + i * STEP
            y = TOP_PAD + dow * STEP
            color = COLOR_ACTIVE if day in active_dates else COLOR_INACTIVE
            title = day.strftime("%B %d, %Y")
            lines.append(
                f'  <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{color}">'
                f'<title>{title}</title></rect>'
            )

    lines.append("</svg>")
    return "\n".join(lines)


def activity_grid(active_dates: set, date_to_folder=None) -> str:
    today = datetime.date.today()
    weeks = build_weeks()

    col_labels: list[str | None] = []
    for week in weeks:
        label = None
        for day in week:
            if day <= today and day.day == 1:
                label = day.strftime("%b")
                break
        col_labels.append(label)
    if col_labels and col_labels[0] is None:
        col_labels[0] = weeks[0][0].strftime("%b")

    month_spans: list[list] = []
    for label in col_labels:
        if label is None:
            month_spans[-1][1] += 1
        else:
            month_spans.append([label, 1])

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    rows = ['<table border="0" cellspacing="2" cellpadding="0">']

    rows.append("  <tr>")
    rows.append('    <td width="28"></td>')
    for label, span in month_spans:
        text = f"<sub>{label}</sub>" if span >= 2 else ""
        rows.append(f'    <td colspan="{span}">{text}</td>')
    rows.append("  </tr>")

    for dow, name in enumerate(day_names):
        rows.append("  <tr>")
        rows.append(f'    <td align="right"><sub>{name}&nbsp;</sub></td>')
        for week in weeks:
            day = week[dow]
            if day > today:
                rows.append('    <td></td>')
            else:
                title = day.strftime("%B %d, %Y")
                if day in active_dates:
                    raw = date_to_folder.get(day, "") if date_to_folder else ""
                    href = quote(raw, safe="/") if raw else "#"
                    rows.append(f'    <td><a href="{href}" title="{title}">🟩</a></td>')
                else:
                    rows.append(f'    <td><a href="#" title="{title}">⬜</a></td>')
        rows.append("  </tr>")

    rows.append("</table>")
    return "\n".join(rows)


def render_summary() -> str:
    entries = build_entries()
    total = len(entries)
    cf_count = sum(1 for e in entries if CF_URL_RE.search(e["url"]))

    # activity grid driven by git push dates
    active_dates = git_active_dates()
    days_active = len(active_dates)
    current_streak, longest_streak = compute_streaks(active_dates)

    # map each active date to its first matching day folder (for click links)
    date_to_folder: dict = {}
    for e in entries:
        d = parse_date(e["date_str"])
        if d not in date_to_folder:
            date_to_folder[d] = e["folder"] + "/"

    stats = "\n".join([
        f"| 📝 Total Solved | 📅 Days Active | 🔥 Current Streak | ⚡ Longest Streak | 🏷️ Codeforces |",
        f"| :------------: | :-----------: | :---------------: | :---------------: | :-----------: |",
        f"| {total} | {days_active} | {current_streak} days | {longest_streak} days | {cf_count} |",
    ])

    grid = activity_grid(active_dates, date_to_folder)

    lines = [SUMMARY_START, stats, "", grid, SUMMARY_END]
    return "\n".join(lines)


def render_log() -> str:
    today = datetime.date.today().strftime("%d %b %Y")
    rows = build_rows()
    total = len(rows)
    if not rows:
        rows = ["| - | - | - | - | - | - |"]

    header = [
        START_MARKER,
        f"Last updated: {today}",
        "",
        "| Day | Date | Problem | Solution | Input | Output |",
        "| :-: | :--: | ------- | -------- | :---: | :----: |",
    ]
    footer = [END_MARKER]
    return "\n".join(header + rows + footer)


def update_readme() -> None:
    content = README.read_text(encoding="utf-8")
    if START_MARKER not in content or END_MARKER not in content:
        raise SystemExit("Daily log markers not found in README.md")

    log_pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    new_content = log_pattern.sub(render_log(), content)

    if SUMMARY_START in new_content and SUMMARY_END in new_content:
        summary_pattern = re.compile(
            re.escape(SUMMARY_START) + r".*?" + re.escape(SUMMARY_END),
            re.DOTALL,
        )
        new_content = summary_pattern.sub(render_summary(), new_content)

    README.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    update_readme()
