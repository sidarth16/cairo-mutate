import re
import shutil
import subprocess

TARGET_FILE = "src/lib.cairo"

# ===== COLORS =====
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
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
    return result.returncode, result.stdout + result.stderr

# ===== INFERENCE LAYER =====
def analyze_mutation(original_line):
    line = original_line.lower()

    if any(k in line for k in ["caller", "owner", "admin"]):
        return ("Authorization Check", "HIGH",
                "Authorization logic may not be properly tested")

    if "assert" in line:
        return ("Invariant", "CRITICAL",
                "Invariant not enforced by tests")

    if any(op in line for op in [">", "<", ">=", "<="]):
        return ("Boundary Condition", "MEDIUM",
                "Edge cases may not be covered")

    return ("Generic Logic", "LOW",
            "Condition not validated by tests")

# ===== OPERATOR MUTATIONS =====
OP_MUTATIONS = {
    "==": ["!=", ">", "<", ">=", "<="],
    "!=": ["==", ">", "<", ">=", "<="],
    ">": ["<", ">=", "<=", "==", "!="],
    "<": [">", ">=", "<=", "==", "!="],
    ">=": [">", "<", "<=", "==", "!="],
    "<=": ["<", ">", ">=", "==", "!="],
}

# ===== MUTATORS =====

def comment_out(line):
    if line.strip().startswith("//"):
        return line
    return "// " + line

def mutate_asserts():
    with open(TARGET_FILE, "r") as f:
        original = f.read()

    lines = original.split("\n")
    matches = [(i, l) for i, l in enumerate(lines) if "assert" in l]

    total = len(matches)
    compiled = 0
    caught = 0

    print(color("\n--- Running mutator RR (Assertion Removal) ---", Colors.CYAN))

    for idx, (i, line) in enumerate(matches):
        mutated_lines = lines.copy()
        mutated_lines[i] = comment_out(line)

        mutated_code = "\n".join(mutated_lines)

        shutil.copy(TARGET_FILE, TARGET_FILE + ".bak")
        with open(TARGET_FILE, "w") as f:
            f.write(mutated_code)

        code, output = run_snforge()

        if "error" in output.lower():
            status = "Compilation Failed"
            status_col = color(status, Colors.YELLOW)
        else:
            compiled += 1
            if "[FAIL]" in output or "failed" in output.lower():
                status = "Caught"
                status_col = color(status, Colors.GREEN)
                caught += 1
            else:
                status = "Uncaught"
                status_col = color(status, Colors.RED)

        print(f"[{color('RR', Colors.BOLD)}] {line.strip()} -> // {line.strip()} : {status_col}")

        if status == "Uncaught":
            t, sev, msg = analyze_mutation(line)
            print(color(f"   ↳ {t} | {sev} | {msg}", Colors.YELLOW))

        shutil.copy(TARGET_FILE + ".bak", TARGET_FILE)

    print(color(f"\nmutator RR : mutated {total} ({caught} caught out of {compiled} that compiled)\n", Colors.BOLD))
    return total, caught


def mutate_operators():
    with open(TARGET_FILE, "r") as f:
        original = f.read()

    lines = original.split("\n")

    total = 0
    compiled = 0
    caught = 0

    print(color("\n--- Running mutator RO (Operator Mutation) ---", Colors.CYAN))

    for i, line in enumerate(lines):
        for op, replacements in OP_MUTATIONS.items():
            if op in line:
                for rep in replacements:
                    total += 1

                    mutated_line = line.replace(op, rep, 1)
                    mutated_lines = lines.copy()
                    mutated_lines[i] = mutated_line

                    mutated_code = "\n".join(mutated_lines)

                    shutil.copy(TARGET_FILE, TARGET_FILE + ".bak")
                    with open(TARGET_FILE, "w") as f:
                        f.write(mutated_code)

                    code, output = run_snforge()

                    if "error" in output.lower():
                        status = "Compilation Failed"
                        status_col = color(status, Colors.YELLOW)
                    else:
                        compiled += 1
                        if "[FAIL]" in output or "failed" in output.lower():
                            status = "Caught"
                            status_col = color(status, Colors.GREEN)
                            caught += 1
                        else:
                            status = "Uncaught"
                            status_col = color(status, Colors.RED)

                    print(
                        f"[{color('RO', Colors.BOLD)}] "
                        f"{color(line.strip(), Colors.CYAN)} "
                        f"-> {color(mutated_line.strip(), Colors.YELLOW)} : "
                        f"{status_col}"
                    )

                    if status == "Uncaught":
                        t, sev, msg = analyze_mutation(line)
                        print(color(f"   ↳ {t} | {sev} | {msg}", Colors.YELLOW))

                    shutil.copy(TARGET_FILE + ".bak", TARGET_FILE)

    print(color(f"\nmutator RO : mutated {total} ({caught} caught out of {compiled} that compiled)\n", Colors.BOLD))
    return total, caught


# ===== MAIN =====
def main():
    print(color("\n🚀 Starting Cairo Mutation Testing...\n", Colors.BOLD))

    total_all = 0
    caught_all = 0

    t, c = mutate_asserts()
    total_all += t
    caught_all += c

    t, c = mutate_operators()
    total_all += t
    caught_all += c

    print(color("=== FINAL SUMMARY ===", Colors.CYAN))

    print(f"Total Mutations : {total_all}")
    print(f"Caught          : {color(str(caught_all), Colors.GREEN)}")
    print(f"Uncaught        : {color(str(total_all - caught_all), Colors.RED)}")

    if total_all > 0:
        score = (caught_all / total_all) * 100
    else:
        score = 0

    print(f"Score           : {color(f'{score:.2f}%', Colors.BOLD)}")
    print("\nDone \n")


if __name__ == "__main__":
    main()