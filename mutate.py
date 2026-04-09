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
    result = subprocess.run(
        ["snforge", "test"],
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

# ===== SUMMARY PER MUTATOR =====

def color_score(score):
    if score >= 90:
        return color(f"{score:.2f}%", Colors.GREEN)
    elif score >= 70:
        return color(f"{score:.2f}%", Colors.YELLOW)
    else:
        return color(f"{score:.2f}%", Colors.RED)
    

def print_summary(name, total, compiled, caught):
    uncaught = compiled - caught
    invalid = total - compiled

    score = (caught / compiled * 100) if compiled > 0 else 0

    if (invalid>0):
        print(f"[{name}]",color(f"{invalid} invalid mutant(s) skipped (compile error)", Colors.GREY))
        
    if score>0: 
        print(
            color(f"[{name}] mutated {compiled} → caught {caught}/{compiled}",Colors.PURPLE + Colors.BOLD),
            color(f"  | {color('score', Colors.GREY)}: {color_score(score)}%", Colors.BOLD )
        )
    else:
        print(color(f"[{name}] mutated {compiled} → caught {caught}/{compiled}",Colors.PURPLE + Colors.BOLD))

# ===== AM-REM =====
def mutate_as_rem():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "AS-REM"

    print(color("\n--- Running AS-REM (Assert Removal) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" not in line:
            continue

        total += 1
        mutated_lines = lines.copy()
        mutated_lines[i] = "let _ = 0;"

        with open(TARGET_FILE, "w") as f:
            f.write("\n".join(mutated_lines))

        output = run_snforge()
        status, compiled, caught = process_result(output, compiled, caught)

        print(f"[{name}] {line.strip()} -> removed  => {status}")

        if "Uncaught" in status:
            category = get_category(name)
            if category:
                uncaught_by_category[category] += 1

        shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== AM-REL =====
def mutate_as_flip():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "AS-FLIP"

    print(color("\n--- Running AM-FLIP (Assert Relational Flip) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" not in line:
            continue

        matches = list(re.finditer(r"(==|!=)", line))

        for m in matches:
            total += 1

            start, end = m.span()
            op = m.group()
            new_op = "!=" if op == "==" else "=="

            mutated = line[:start] + new_op + line[end:]
            mutated_lines = lines.copy()
            mutated_lines[i] = mutated

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated_lines))

            output = run_snforge()
            status, compiled, caught = process_result(output, compiled, caught)

            if 'error' in output.lower():
                print(f"[{name}] ", color(f"{line.strip()} -> {mutated.strip()}  => {status}", Colors.GREY))
            else:
                print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                category = get_category(name)
                if category:
                    uncaught_by_category[category] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== OP-cmp =====
def mutate_op_cmp():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "OP-CMP"

    print(color("\n--- Running OP-CMP (Comparision Operator Mutation) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" in line:
            continue

        matches = list(re.finditer(r"(==|!=)", line))

        for m in matches:
            total += 1

            start, end = m.span()
            op = m.group()
            new_op = "!=" if op == "==" else "=="

            mutated = line[:start] + new_op + line[end:]
            mutated_lines = lines.copy()
            mutated_lines[i] = mutated

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated_lines))

            output = run_snforge()
            status, compiled, caught = process_result(output, compiled, caught)

            if 'error' in output.lower():
                print(f"[{name}] ", color(f"{line.strip()} -> {mutated.strip()}  => {status}", Colors.GREY))
            else:
                print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                category = get_category(name)
                if category:
                    uncaught_by_category[category] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== OP-ARI =====
def mutate_op_ari():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "OP-ARI"

    print(color("\n--- Running OP-ARI (Arithmetic Operator Mutation) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" in line:
            continue

        matches = list(re.finditer(r"(\+|-)", line))

        for m in matches:
            total += 1

            start, end = m.span()
            op = m.group()
            new_op = "-" if op == "+" else "+"

            mutated = line[:start] + new_op + line[end:]
            mutated_lines = lines.copy()
            mutated_lines[i] = mutated

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated_lines))

            output = run_snforge()
            status, compiled, caught = process_result(output, compiled, caught)

            if 'error' in output.lower():
                print(f"[{name}]", color(f"{line.strip()} -> {mutated.strip()}  => {status}", Colors.GREY))
            else:
                print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                category = get_category(name)
                if category:
                    uncaught_by_category[category] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== OP-ASG =====
def mutate_op_asg():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "OP-ASG"

    print(color("\n--- Running OP-ASG (Assignment Operator Mutation) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        if "assert" in line:
            continue

        matches = list(re.finditer(r"(\+=|-=)", line))

        for m in matches:
            total += 1

            start, end = m.span()
            mutated = line[:start] + "=" + line[end:]
            mutated_lines = lines.copy()
            mutated_lines[i] = mutated

            with open(TARGET_FILE, "w") as f:
                f.write("\n".join(mutated_lines))

            output = run_snforge()
            status, compiled, caught = process_result(output, compiled, caught)

            if 'error' in output.lower():
                print(f"[{name}] ", color(f"{line.strip()} -> {mutated.strip()}  => {status}", Colors.GREY))
            else:
                print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                category = get_category(name)
                if category:
                    uncaught_by_category[category] += 1

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== MAIN =====
def main():
    print(color("\n🚀 Starting Cairo Mutation Testing...\n", Colors.BOLD))
    start_time = time.time()

    shutil.copy(TARGET_FILE, BACKUP_FILE)

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
    invalid = total - compiled
    score = (caught / compiled * 100) if compiled > 0 else 0

    score_str = color(f"{score:.2f}%", Colors.GREEN)
    if score < 80:
        score_str = color(score_str, Colors.YELLOW)
    if score < 50:
        score_str = color(score_str, Colors.RED)
    

    # ===== TABLE SUMMARY =====
    print(color("\n=== MUTATION SUMMARY ===", Colors.CYAN))

    w1 = 18
    w2 = 12

    border = "+" + "-"*w1 + "+" + "-"*w2 + "+"

    def pad(val, width):
        return f"{val:<{width}}"

    print(border)
    print(f"| {pad('Metric', w1-2)} | {pad('Value', w2-2)} |")
    print(border)

    print(f"| {pad('Valid Mutants', w1-2)} | {pad(str(compiled), w2-2)} |")

    print(f"| {pad('Caught', w1-2)} | {color(pad(str(caught), w2-2), Colors.GREEN)} |")

    print(f"| {pad('Uncaught', w1-2)} | {color(pad(str(uncaught), w2-2), Colors.RED)} |")

    print(f"| {pad('Score', w1-2)} | {color(pad(f'{score:.2f}%', w2-2), Colors.BOLD)} |")

    print(border)

    end_time = time.time()
    duration = end_time - start_time
    print(color(f"\nMutation Analysis Completed in : {duration:.2f}s", Colors.CYAN))

    # ===== NOTES =====
    total_uncaught = sum(uncaught_by_category.values())

    if total_uncaught > 0:
        print(f"\n{color('⚑ Suggested Improvements:', Colors.YELLOW)} \n")
        print(f"Uncaught Mutations: {total_uncaught}\n")

        for category, count in uncaught_by_category.items():
            if count == 0:
                continue

            print(f"{category.lower()} ({count}):")
            
            if category == "ASSERT / VALIDATION":
                print("  Assertions were removed or altered without affecting test outcomes")
                print("  → consider testing failure paths and invalid inputs\n")

            elif category == "ARITHMETIC LOGIC":
                print("  arithmetic changes did not affect test results")
                print("  → consider testing boundary values and calculations\n")

            elif category == "CONDITIONAL LOGIC":
                print("  conditional changes did not affect test results")
                print("  → consider testing alternate branches\n")

            elif category == "STATE UPDATES":
                print("  state updates were not strictly validated")
                print("  → consider asserting state transitions\n")

        


if __name__ == "__main__":
    main()