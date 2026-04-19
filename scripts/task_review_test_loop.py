from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_COMMANDS = [
    "pytest tests/ -q",
    "ruff check src tests scripts",
    "mypy src tests scripts",
]


@dataclass
class TaskRow:
    task_id: str
    task: str
    status: str
    priority: str
    owner: str
    branch: str
    notes: str
    line_index: int


def parse_task_rows(lines: list[str]) -> list[TaskRow]:
    rows: list[TaskRow] = []
    for index, line in enumerate(lines):
        if not line.startswith("| ST-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        rows.append(
            TaskRow(
                task_id=cells[0],
                task=cells[1],
                status=cells[2],
                priority=cells[3],
                owner=cells[4],
                branch=cells[5],
                notes=cells[6],
                line_index=index,
            )
        )
    return rows


def format_row(row: TaskRow) -> str:
    return (
        f"| {row.task_id} | {row.task} | {row.status} | {row.priority} | {row.owner} "
        f"| {row.branch} | {row.notes} |"
    )


def write_task_row(lines: list[str], row: TaskRow) -> None:
    lines[row.line_index] = format_row(row)


def load_board(path: Path) -> tuple[list[str], list[TaskRow]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = parse_task_rows(lines)
    if not rows:
        raise RuntimeError(f"No task rows found in {path}")
    return lines, rows


def save_board(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_quality_gate(commands: list[str]) -> bool:
    print("\nRunning review/test gate...")
    for command in commands:
        print(f"\n$ {command}")
        result = subprocess.run(command, shell=True, check=False)
        if result.returncode != 0:
            print(f"Gate failed on: {command}")
            return False
    print("\nGate passed.")
    return True


def pick_next_task(rows: list[TaskRow]) -> TaskRow | None:
    for row in rows:
        if row.status != "Done":
            return row
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Loop through tasks: after each implementation, "
            "run review + tests until all done"
        )
    )
    parser.add_argument(
        "--tasks-file",
        default="docs/tasks.md",
        help="Path to task board markdown file",
    )
    parser.add_argument(
        "--owner",
        default="Codex",
        help="Owner to set when claiming a planned task",
    )
    parser.add_argument(
        "--command",
        action="append",
        dest="commands",
        default=None,
        help="Quality gate command (can be repeated). Defaults: pytest, ruff, mypy",
    )
    args = parser.parse_args()

    commands = args.commands if args.commands else DEFAULT_COMMANDS
    tasks_path = Path(args.tasks_file)

    if not tasks_path.exists():
        raise FileNotFoundError(f"Task board not found: {tasks_path}")

    while True:
        lines, rows = load_board(tasks_path)
        current = pick_next_task(rows)
        if current is None:
            print("All tasks are Done.")
            return 0

        print(f"\nCurrent task: {current.task_id} [{current.status}] - {current.task}")

        if current.status == "Planned":
            current.status = "In Progress"
            if current.owner == "Unassigned":
                current.owner = args.owner
            write_task_row(lines, current)
            save_board(tasks_path, lines)
            print(f"Marked {current.task_id} as In Progress (owner={current.owner}).")

        if current.status in {"In Progress", "Blocked", "Review"}:
            input(
                "Finish implementation/update for this task, then press Enter "
                "to run review + tests..."
            )

        gate_ok = run_quality_gate(commands)

        lines, rows = load_board(tasks_path)
        refreshed = next(row for row in rows if row.task_id == current.task_id)

        if gate_ok:
            refreshed.status = "Done"
            if refreshed.owner == "Unassigned":
                refreshed.owner = args.owner
            write_task_row(lines, refreshed)
            save_board(tasks_path, lines)
            print(f"Marked {refreshed.task_id} as Done.")
            continue

        refreshed.status = "Review"
        if refreshed.owner == "Unassigned":
            refreshed.owner = args.owner
        write_task_row(lines, refreshed)
        save_board(tasks_path, lines)
        print(
            f"Marked {refreshed.task_id} as Review. "
            "Fix issues, then press Enter next round to re-run gate."
        )


if __name__ == "__main__":
    raise SystemExit(main())
