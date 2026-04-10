from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    PURPLE = "\033[95m"
    GREY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def color(text, c):
    return f"{c}{text}{Colors.RESET}"


@dataclass
class MutationContext:
    project_root: Path
    source_root: Path
    run_timeout_seconds: int = 30
    test_cmd: list[str] = field(default_factory=lambda: ["snforge", "test"])
    verbose: int = 0
    target_file: Path | None = None
    backup_file: Path | None = None
    backups: set[tuple[Path, Path]] = field(default_factory=set)
    restored: bool = False
    uncaught_by_category: dict[str, int] = field(
        default_factory=lambda: {
            "ASSERT / VALIDATION": 0,
            "ARITHMETIC LOGIC": 0,
            "CONDITIONAL LOGIC": 0,
            "STATE UPDATES": 0,
        }
    )

    def set_target_file(self, file_path: Path) -> None:
        self.target_file = file_path
        self.backup_file = Path(str(file_path) + ".bak")

    def ensure_backup(self, file_path: Path) -> Path:
        backup_path = Path(str(file_path) + ".bak")
        if not backup_path.exists():
            shutil.copy(file_path, backup_path)
        self.backups.add((file_path, backup_path))
        return backup_path

    def restore_all_files(self, verbose: bool = False) -> None:
        if self.restored:
            return

        for original, backup in self.backups:
            if backup.exists():
                shutil.copy(backup, original)

        self.restored = True
        if verbose and self.backups:
            print(color("\n✔ Restored original files", Colors.GREEN))

    def cleanup_backups(self) -> None:
        for _, backup in self.backups:
            if backup.exists():
                backup.unlink()

    def handle_interrupt(self, sig, frame) -> None:
        print(color("\n\n⚠ Interrupted! Restoring files...", Colors.YELLOW))
        self.restore_all_files(verbose=True)
        self.cleanup_backups()
        sys.exit(1)

    def should_print_sections(self) -> bool:
        return self.verbose >= 1

    def should_print_mutants(self) -> bool:
        return self.verbose >= 2

    def get_category(self, name: str):
        if name in ["AS-REM", "AS-FLIP"]:
            return "ASSERT / VALIDATION"
        if name == "OP-ARI":
            return "ARITHMETIC LOGIC"
        if name == "OP-EQ":
            return "CONDITIONAL LOGIC"
        if name == "OP-ASG":
            return "STATE UPDATES"
        return None

    def run_snforge(self, timeout_seconds: int | None = None):
        timeout_seconds = timeout_seconds or self.run_timeout_seconds
        env = os.environ.copy()
        env["PATH"] = f"{os.path.expanduser('~')}/.asdf/shims:{env.get('PATH', '')}"
        try:
            result = subprocess.run(
                self.test_cmd,
                cwd=self.project_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            return result.stdout + result.stderr, False
        except subprocess.TimeoutExpired as exc:
            def normalize(value):
                if value is None:
                    return ""
                if isinstance(value, bytes):
                    return value.decode("utf-8", errors="replace")
                return value

            output = normalize(exc.stdout) + normalize(exc.stderr)
            return output, True

    def process_result(self, output, compiled, caught, timed_out=False):
        if timed_out:
            return color("Timeout", Colors.YELLOW), compiled, caught

        if "error" in output.lower():
            return color("Compile Error", Colors.GREY), compiled, caught

        compiled += 1

        if "[FAIL]" in output:
            caught += 1
            return color("✔ Caught", Colors.GREEN), compiled, caught

        return color("✘ Uncaught", Colors.RED), compiled, caught

    def color_score(self, score):
        if score >= 90:
            return color(f"{score:.2f}%", Colors.GREEN)
        if score >= 70:
            return color(f"{score:.2f}%", Colors.YELLOW)
        return color(f"{score:.2f}%", Colors.RED)

    def render_mutant_line(self, name, line_no, before, after, status, timed_out=False):
        prefix = f"[{name}] L{line_no}: {before} → {after} => "
        if "Compile Error" in status:
            return color(prefix + "Compile Error", Colors.GREY)
        if timed_out:
            return color(prefix, Colors.GREY) + color("Timeout", Colors.YELLOW)
        return prefix + status

    def print_summary(self, name, total, compiled, caught, timeout_count=0):
        if self.verbose < 1:
            return

        invalid = total - compiled - timeout_count
        skipped = invalid + timeout_count
        score = (caught / compiled * 100) if compiled > 0 else 0

        if skipped > 0:
            parts = []
            if invalid > 0:
                parts.append(f"{invalid} compile error")
            if timeout_count > 0:
                parts.append(f"{timeout_count} timeout")
            print(color(f"[{name}] {skipped} skipped ({', '.join(parts)})", Colors.GREY))

        if compiled > 0:
            print(
                color(
                    f"[{name}] mutated {compiled} → caught {caught}/{compiled}",
                    Colors.PURPLE + Colors.BOLD,
                ),
                color(f" | {color('score', Colors.GREY)}: {self.color_score(score)}", Colors.BOLD),
            )
        else:
            print(color(f"[{name}] no valid mutations", Colors.PURPLE + Colors.BOLD))

    def file_label(self, file_path: Path) -> str:
        try:
            return str(file_path.relative_to(self.project_root))
        except ValueError:
            return file_path.name

    def format_score_value(self, compiled, caught):
        return (caught / compiled * 100) if compiled > 0 else 0

    def print_filewise_table(self, results):
        if not results:
            return

        headers = ["File", "Mutants", "Caught", "Uncaught", "Score"]
        rows = []

        total_compiled = 0
        total_caught = 0

        for item in results:
            compiled = item["compiled"]
            caught = item["caught"]
            uncaught = compiled - caught
            score = self.format_score_value(compiled, caught)
            total_compiled += compiled
            total_caught += caught
            rows.append(
                {
                    "file": self.file_label(item["file"]),
                    "mutants": str(compiled),
                    "caught": str(caught),
                    "uncaught": str(uncaught),
                    "score": f"{score:.2f}%",
                    "compiled": compiled,
                    "is_total": False,
                }
            )

        total_uncaught = total_compiled - total_caught
        total_score = self.format_score_value(total_compiled, total_caught)
        rows.append(
            {
                "file": "Total",
                "mutants": str(total_compiled),
                "caught": str(total_caught),
                "uncaught": str(total_uncaught),
                "score": f"{total_score:.2f}%",
                "compiled": total_compiled,
                "is_total": True,
            }
        )

        widths = [len(h) for h in headers]
        for row in rows:
            values = [row["file"], row["mutants"], row["caught"], row["uncaught"], row["score"]]
            for idx, cell in enumerate(values):
                widths[idx] = max(widths[idx], len(cell))

        def border(char="-"):
            return "+" + "+".join(char * (width + 2) for width in widths) + "+"

        def score_color(score, compiled):
            if compiled == 0:
                return Colors.GREY
            if score >= 90:
                return Colors.GREEN
            if score >= 70:
                return Colors.YELLOW
            return Colors.RED

        def render_cell(idx, value, row):
            padded = f"{value:<{widths[idx]}}"

            if idx == 2:
                return color(f" {padded} ", Colors.GREEN)
            if idx == 3:
                return color(f" {padded} ", Colors.RED)
            if idx == 4:
                score = float(value.rstrip("%"))
                if row["is_total"]:
                    return color(f" {padded} ", Colors.BOLD + score_color(score, row["compiled"]))
                return color(f" {padded} ", score_color(score, row["compiled"]))

            if row["is_total"]:
                return color(f" {padded} ", Colors.BOLD)
            return f" {padded} "

        def render_row(row):
            values = [row["file"], row["mutants"], row["caught"], row["uncaught"], row["score"]]
            cells = [render_cell(idx, value, row) for idx, value in enumerate(values)]
            return "|" + "|".join(cells) + "|"

        print(color("\n➤ Mutation Report", Colors.CYAN + Colors.BOLD))
        print(border("-"))
        header_cells = [f" {h:<{widths[idx]}} " for idx, h in enumerate(headers)]
        print("|" + "|".join(color(cell, Colors.BOLD) for cell in header_cells) + "|")
        print(border("-"))
        for row in rows[:-1]:
            print(render_row(row))
        print(border("-"))
        print(render_row(rows[-1]))
        print(border("-"))

    def discover_cairo_files(self):
        if not self.source_root.exists():
            return []
        return sorted([path for path in self.source_root.rglob("*.cairo") if path.is_file()])
