import shutil
import subprocess
import re
import time

TARGET_FILE = "src/lib.cairo"
BACKUP_FILE = TARGET_FILE + ".bak"

# ===== COLORS =====
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    PURPLE = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def color(text, c):
    return f"{c}{text}{Colors.RESET}"

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
        return color("Compilation Failed", Colors.YELLOW), compiled, caught

    compiled += 1
    # print(output)
    if "[FAIL]" in output:
        caught += 1
        return color("Caught", Colors.GREEN), compiled, caught

    return color("Uncaught", Colors.RED), compiled, caught

# ===== INFERENCE =====
def analyze(line):
    l = line.lower()
    if "assert" in l:
        return "Invariant | CRITICAL"
    if any(k in l for k in ["owner", "admin", "caller"]):
        return "Authorization | HIGH"
    return "Logic | LOW"

def print_inference(line):
    print(color(f"   ↳ {analyze(line)}", Colors.YELLOW))

# ===== SUMMARY =====
def print_summary(name, total, compiled, caught):
    uncaught = compiled - caught
    invalid = total - compiled

    print(color(
        f"[{name}] mutated {total} ({caught}/{compiled} caught, {invalid} invalid)",
        Colors.PURPLE + Colors.BOLD
    ))

# ===== AM-REM =====
def mutate_am_rem():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "AM-REM"

    print(color("\n--- Running AM-REM (Assert Removal)---", Colors.CYAN))

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

        print(f"[{name}] {line.strip()} -> let _ = 0;  => {status}")

        if "Uncaught" in status:
            print_inference(line)

        shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== AM-REL =====
def mutate_am_rel():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "AM-REL"

    print(color("\n--- Running AM-REL (Assert Relational Flip) ---", Colors.CYAN))

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

            print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                print_inference(line)

            shutil.copy(BACKUP_FILE, TARGET_FILE)

    print_summary(name, total, compiled, caught)
    return total, compiled, caught

# ===== OP-REL =====
def mutate_op_rel():
    with open(TARGET_FILE) as f:
        lines = f.read().split("\n")

    total = compiled = caught = 0
    name = "OP-REL"

    print(color("\n--- Running OP-REL (Relational Operator Mutation) ---", Colors.CYAN))

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

            print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                print_inference(line)

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

            print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                print_inference(line)

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

            print(f"[{name}] {line.strip()} -> {mutated.strip()}  => {status}")

            if "Uncaught" in status:
                print_inference(line)

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
        mutate_am_rem,
        mutate_am_rel,
        mutate_op_rel,
        mutate_op_ari,
        mutate_op_asg,
    ]:
        t, c, ca = fn()
        total += t
        compiled += c
        caught += ca

    uncaught = compiled - caught
    invalid = total - compiled

    print(color("\n=== MUTATION SUMMARY ===", Colors.CYAN))
    print(f"Total Mutants      : {total}")
    print(f"Valid Mutants      : {compiled}")
    print(f"  Caught           : {color(str(caught), Colors.GREEN)}")
    print(f"  Uncaught         : {color(str(uncaught), Colors.RED)}")
    print(f"Invalid Mutants    : {color(str(invalid), Colors.YELLOW)}")

    score = (caught / compiled * 100) if compiled > 0 else 0
    print(f"Score (valid only) : {color(f'{score:.2f}%', Colors.BOLD)}")

    end_time = time.time()
    duration = end_time - start_time
    print(color(f"\nMutation Analysis Completed in : {duration:.2f}s", Colors.CYAN))


if __name__ == "__main__":
    main()