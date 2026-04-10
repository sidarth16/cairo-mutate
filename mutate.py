import argparse
import os
import re
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_ROOT = SCRIPT_DIR / "src"

TARGET_FILE = None
BACKUP_FILE = None
RUN_TIMEOUT_SECONDS = 30

# ===== BACKUP TRACKING =====
backups = set()
restored = False


# ===== COLORS =====
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


def set_target_file(file_path):
    global TARGET_FILE, BACKUP_FILE
    TARGET_FILE = file_path
    BACKUP_FILE = Path(str(file_path) + ".bak")


# ===== SAFE RESTORE =====
def restore_all_files(verbose=False):
    global restored

    if restored:
        return

    for original, backup in backups:
        if backup.exists():
            shutil.copy(backup, original)

    restored = True
    if verbose and backups:
        print(color("\n✔ Restored original files", Colors.GREEN))


def cleanup_backups():
    for _, backup in backups:
        if backup.exists():
            backup.unlink()


def handle_interrupt(sig, frame):
    print(color("\n\n⚠ Interrupted! Restoring files...", Colors.YELLOW))
    restore_all_files(verbose=True)
    cleanup_backups()
    sys.exit(1)


signal.signal(signal.SIGINT, handle_interrupt)
signal.signal(signal.SIGTERM, handle_interrupt)


# ===== CATEGORY TRACKING =====
uncaught_by_category = {
    "ASSERT / VALIDATION": 0,
    "ARITHMETIC LOGIC": 0,
    "CONDITIONAL LOGIC": 0,
    "STATE UPDATES": 0,
}


def get_category(name):
    if name in ["AS-REM", "AS-FLIP"]:
        return "ASSERT / VALIDATION"
    if name == "OP-ARI":
        return "ARITHMETIC LOGIC"
    if name == "OP-CMP":
        return "CONDITIONAL LOGIC"
    if name == "OP-ASG":
        return "STATE UPDATES"
    return None


# ===== RUN TEST =====
def run_snforge(timeout_seconds):
    env = os.environ.copy()
    env["PATH"] = f"{os.path.expanduser('~')}/.asdf/shims:{env.get('PATH', '')}"
    try:
        result = subprocess.run(
            ["snforge", "test"],
            cwd=SCRIPT_DIR,
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


# ===== RESULT =====
def process_result(output, compiled, caught, timed_out=False):
    if timed_out:
        return color("Timeout", Colors.YELLOW), compiled, caught

    if "error" in output.lower():
        return color("Compile Error", Colors.GREY), compiled, caught

    compiled += 1

    if "[FAIL]" in output:
        caught += 1
        return color("✔ Caught", Colors.GREEN), compiled, caught

    return color("✘ Uncaught", Colors.RED), compiled, caught


# ===== SCORE COLOR =====
def color_score(score):
    if score >= 90:
        return color(f"{score:.2f}%", Colors.GREEN)
    elif score >= 70:
        return color(f"{score:.2f}%", Colors.YELLOW)
    else:
        return color(f"{score:.2f}%", Colors.RED)


# ===== LINE RENDERING =====
def render_mutant_line(name, line_no, before, after, status, timed_out=False):
    prefix = f"[{name}] L{line_no}: {before} → {after} => "
    if "Compile Error" in status:
        return color(prefix + "Compile Error", Colors.GREY)
    if timed_out:
        return color(prefix, Colors.GREY) + color("Timeout", Colors.YELLOW)
    return prefix + status


# ===== SUMMARY =====
def print_summary(name, total, compiled, caught, timeout_count=0):
    uncaught = compiled - caught
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
            color(f" | {color('score', Colors.GREY)}: {color_score(score)}", Colors.BOLD),
        )
    else:
        print(color(f"[{name}] no valid mutations", Colors.PURPLE + Colors.BOLD))


def file_label(file_path):
    try:
        return str(file_path.relative_to(SCRIPT_DIR))
    except ValueError:
        return file_path.name


def format_score_value(compiled, caught):
    score = (caught / compiled * 100) if compiled > 0 else 0
    return score


def print_filewise_table(results):
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
        score = format_score_value(compiled, caught)
        total_compiled += compiled
        total_caught += caught
        rows.append({
            "file": file_label(item["file"]),
            "mutants": str(compiled),
            "caught": str(caught),
            "uncaught": str(uncaught),
            "score": f"{score:.2f}%",
            "compiled": compiled,
            "is_total": False,
        })

    total_uncaught = total_compiled - total_caught
    total_score = format_score_value(total_compiled, total_caught)
    rows.append({
        "file": "Total",
        "mutants": str(total_compiled),
        "caught": str(total_caught),
        "uncaught": str(total_uncaught),
        "score": f"{total_score:.2f}%",
        "compiled": total_compiled,
        "is_total": True,
    })

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
            score = float(value.rstrip('%'))
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
    header_row = { "file": "File", "mutants": "Mutants", "caught": "Caught", "uncaught": "Uncaught", "score": "Score", "compiled": 0, "is_total": False }
    header_cells = [f" {h:<{widths[idx]}} " for idx, h in enumerate(headers)]
    print("|" + "|".join(color(cell, Colors.BOLD) for cell in header_cells) + "|")
    print(border("-"))
    for row in rows[:-1]:
        print(render_row(row))
    print(border("-"))
    print(render_row(rows[-1]))
    print(border("-"))


def ensure_backup(file_path):
    backup_path = Path(str(file_path) + ".bak")
    if not backup_path.exists():
        shutil.copy(file_path, backup_path)
    backups.add((file_path, backup_path))
    return backup_path


def mutate_as_rem():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = timeouts = 0
    name = "AS-RM"

    print(color("\n--- AS-REM (Assert Removal) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" not in line:
            continue

        total += 1
        mutated = lines.copy()
        mutated[i] = "let _ = 0;"

        with open(TARGET_FILE, "w") as f:
            f.write("\n".join(mutated))

        output, timed_out = run_snforge(RUN_TIMEOUT_SECONDS)
        status, compiled, caught = process_result(output, compiled, caught, timed_out)
        if timed_out:
            timeouts += 1

        print(render_mutant_line(name, i + 1, line.strip(), "let _ = 0;", status, timed_out))

        if "Uncaught" in status:
            uncaught_by_category["ASSERT / VALIDATION"] += 1

        shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught, timeouts)
    return total, compiled, caught, timeouts


def mutate_as_flip():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = timeouts = 0
    name = "AS-FLIP"
    flips = {
        "==": "!=",
        "!=": "==",
        ">": "<",
        "<": ">",
        ">=": "<=",
        "<=": ">=",
    }

    print(color("\n--- AS-FLIP (Assert Condition Flip) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" not in line:
            continue

        for m in re.finditer(r"(>=|<=|==|!=|>|<)", line):
            total += 1
            start, end = m.span()
            op = m.group()
            new_op = flips[op]

            mutated = lines.copy()
            mutated[i] = line[:start] + new_op + line[end:]

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated))

            output, timed_out = run_snforge(RUN_TIMEOUT_SECONDS)
            status, compiled, caught = process_result(output, compiled, caught, timed_out)
            if timed_out:
                timeouts += 1

            print(render_mutant_line(name, i + 1, line.strip(), mutated[i].strip(), status, timed_out))

            if "Uncaught" in status:
                uncaught_by_category["ASSERT / VALIDATION"] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught, timeouts)
    return total, compiled, caught, timeouts


def mutate_generic(name, pattern, transform):
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = timeouts = 0

    full_name = {
        "OP-CMP": "OP-CMP (Comparison Operator Mutation)",
        "OP-ARI": "OP-ARI (Arithmetic Operator Mutation)",
        "OP-ASG": "OP-ASG (Assignment Operator Mutation)",
    }.get(name, name)
    print(color(f"\n--- {full_name} ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" in line:
            continue

        for m in re.finditer(pattern, line):
            total += 1
            start, end = m.span()
            op = m.group()

            mutated = lines.copy()
            mutated[i] = line[:start] + transform(op) + line[end:]

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated))

            output, timed_out = run_snforge(RUN_TIMEOUT_SECONDS)
            status, compiled, caught = process_result(output, compiled, caught, timed_out)
            if timed_out:
                timeouts += 1

            print(render_mutant_line(name, i + 1, line.strip(), mutated[i].strip(), status, timed_out))

            if "Uncaught" in status:
                cat = get_category(name)
                if cat:
                    uncaught_by_category[cat] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught, timeouts)
    return total, compiled, caught, timeouts


def mutate_op_cmp():
    return mutate_generic("OP-CMP", r"(==|!=)", lambda op: "!=" if op == "==" else "==")


def mutate_op_ari():
    return mutate_generic("OP-ARI", r"(\+|-)", lambda op: "-" if op == "+" else "+")


def mutate_op_asg():
    return mutate_generic("OP-ASG", r"(\+=|-=)", lambda op: "=")


def mutate_file(file_path):
    global TARGET_FILE, BACKUP_FILE

    previous_target = TARGET_FILE
    previous_backup = BACKUP_FILE

    set_target_file(file_path)
    ensure_backup(TARGET_FILE)

    try:
        print(color(f"\n▶ Mutating {file_label(file_path)}", Colors.YELLOW + Colors.BOLD))

        file_total = file_compiled = file_caught = file_timeouts = 0

        for fn in [
            mutate_as_rem,
            mutate_as_flip,
            mutate_op_cmp,
            mutate_op_ari,
            mutate_op_asg,
        ]:
            t, c, ca, to = fn()
            file_total += t
            file_compiled += c
            file_caught += ca
            file_timeouts += to

        print(color(f"\n ✔ Finished mutating {file_label(file_path)}", Colors.GREY))

        return {
            "file": file_path,
            "total": file_total,
            "compiled": file_compiled,
            "caught": file_caught,
            "timeouts": file_timeouts,
        }
    finally:
        TARGET_FILE = previous_target
        BACKUP_FILE = previous_backup


def discover_cairo_files():
    if not SOURCE_ROOT.exists():
        return []
    return sorted(
        [path for path in SOURCE_ROOT.rglob("*.cairo") if path.is_file()]
    )


# ===== MAIN =====
def main():
    global RUN_TIMEOUT_SECONDS
    parser = argparse.ArgumentParser(description="Cairo mutation testing with timeout support")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds for each snforge run")
    args = parser.parse_args()
    RUN_TIMEOUT_SECONDS = args.timeout

    print(color("\n🚀 Starting Cairo Mutation Testing...\n", Colors.BOLD))
    start_time = time.time()

    cairo_files = discover_cairo_files()
    if not cairo_files:
        print(color("No .cairo files found under src/", Colors.GREY))
        return

    results = []
    for file_path in cairo_files:
        results.append(mutate_file(file_path))

    total = sum(item["total"] for item in results)
    compiled = sum(item["compiled"] for item in results)
    caught = sum(item["caught"] for item in results)
    timeouts = sum(item.get("timeouts", 0) for item in results)
    uncaught = compiled - caught
    score = (caught / compiled * 100) if compiled > 0 else 0

    print_filewise_table(results)

    duration = time.time() - start_time
    print(f"Final Mutation Score : {color_score(score)}")
    if timeouts > 0:
        print(color(f"Timeout mutants    : {timeouts}", Colors.YELLOW + Colors.BOLD))
    print(color(f"\nCompleted in {duration:.2f}s", Colors.BLUE if hasattr(Colors, "BLUE") else Colors.CYAN))


if __name__ == "__main__":
    try:
        main()
    finally:
        restore_all_files()
        cleanup_backups()
