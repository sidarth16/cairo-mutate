import shutil
import subprocess
import re
import time
import os
import signal
import sys

TARGET_FILE = "src/lib.cairo"
BACKUP_FILE = TARGET_FILE + ".bak"

# ===== BACKUP TRACKING =====
backups = set()
restored = False

# ===== COLORS =====
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    PURPLE = "\033[95m"
    GREY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def color(text, c):
    return f"{c}{text}{Colors.RESET}"

# ===== SAFE RESTORE =====
def restore_all_files():
    global restored

    if restored:
        return
    
    for original, backup in backups:
        if os.path.exists(backup):
            shutil.copy(backup, original)
    restored = True
    if backups:
        print(color("\n✔ Restored original files", Colors.GREEN))

def cleanup_backups():
    for _, backup in backups:
        if os.path.exists(backup):
            os.remove(backup)

def handle_interrupt(sig, frame):
    print(color("\n\n⚠ Interrupted! Restoring files...", Colors.YELLOW))
    restore_all_files()
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
def run_snforge():
    env = os.environ.copy()
    env["PATH"] = f"{os.path.expanduser('~')}/.asdf/shims:{env.get('PATH', '')}"
    result = subprocess.run(
        ["snforge", "test"],
        env=env,
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

# ===== RESULT =====
def process_result(output, compiled, caught):
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

# ===== SUMMARY =====
def print_summary(name, total, compiled, caught):
    uncaught = compiled - caught
    invalid = total - compiled
    score = (caught / compiled * 100) if compiled > 0 else 0

    if invalid > 0:
        print(f"[{name}]", color(f"{invalid} skipped (compile error)", Colors.GREY))

    if compiled > 0:
        print(
            color(f"[{name}] mutated {compiled} → caught {caught}/{compiled}", Colors.PURPLE + Colors.BOLD),
            color(f" | {color('score', Colors.GREY)}: {color_score(score)}", Colors.BOLD)
        )
    else:
        print(color(f"[{name}] no valid mutations", Colors.PURPLE + Colors.BOLD))

# ===== MUTATORS =====
def mutate_as_rem():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "AS-REM"

    print(color("\n--- Running AS-REM ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" not in line:
            continue

        total += 1
        mutated = lines.copy()
        mutated[i] = "let _ = 0;"

        with open(TARGET_FILE, "w") as f:
            f.write("\n".join(mutated))

        output = run_snforge()
        status, compiled, caught = process_result(output, compiled, caught)

        print(f"[{name}] {line.strip()} -> removed  => {status}")

        if "Uncaught" in status:
            uncaught_by_category["ASSERT / VALIDATION"] += 1

        shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught


def mutate_as_flip():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "AS-FLIP"

    print(color("\n--- Running AS-FLIP ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" not in line:
            continue

        for m in re.finditer(r"(==|!=)", line):
            total += 1
            start, end = m.span()
            op = m.group()
            new_op = "!=" if op == "==" else "=="

            mutated = lines.copy()
            mutated[i] = line[:start] + new_op + line[end:]

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated))

            output = run_snforge()
            status, compiled, caught = process_result(output, compiled, caught)

            print(f"[{name}] {line.strip()} => {status}")

            if "Uncaught" in status:
                uncaught_by_category["ASSERT / VALIDATION"] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught


def mutate_generic(name, pattern, transform):
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0

    print(color(f"\n--- Running {name} ---", Colors.CYAN))

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

            output = run_snforge()
            status, compiled, caught = process_result(output, compiled, caught)

            print(f"[{name}] {line.strip()} => {status}")

            if "Uncaught" in status:
                cat = get_category(name)
                if cat:
                    uncaught_by_category[cat] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught


def mutate_op_cmp():
    return mutate_generic("OP-CMP", r"(==|!=)", lambda op: "!=" if op == "==" else "==")


def mutate_op_ari():
    return mutate_generic("OP-ARI", r"(\+|-)", lambda op: "-" if op == "+" else "+")


def mutate_op_asg():
    return mutate_generic("OP-ASG", r"(\+=|-=)", lambda op: "=")

# ===== MAIN =====
def main():
    print(color("\n🚀 Starting Cairo Mutation Testing...\n", Colors.BOLD))
    start_time = time.time()

    # Create backup ONCE
    if not os.path.exists(BACKUP_FILE):
        shutil.copy(TARGET_FILE, BACKUP_FILE)
    backups.add((TARGET_FILE, BACKUP_FILE))

    total = compiled = caught = 0

    for fn in [
        mutate_as_rem,
        mutate_as_flip,
        mutate_op_cmp,
        mutate_op_ari,
        mutate_op_asg,
    ]:
        t, c, ca = fn()
        total += t
        compiled += c
        caught += ca

    uncaught = compiled - caught
    score = (caught / compiled * 100) if compiled > 0 else 0

    print(color("\n=== MUTATION SUMMARY ===", Colors.CYAN))
    print(f"\nValid Mutants : {compiled}")
    print(f"Caught        : {caught}")
    print(f"Uncaught      : {uncaught}")
    print(f"Score         : {color_score(score)}")

    duration = time.time() - start_time
    print(color(f"\nCompleted in {duration:.2f}s\n", Colors.CYAN))


if __name__ == "__main__":
    try:
        main()
    finally:
        restore_all_files()
        cleanup_backups()
