import argparse
import shlex
import signal
import sys
import time
from pathlib import Path

from mutators import DEFAULT_MUTATORS, MUTATOR_REGISTRY
from mutators.common import Colors, MutationContext, color


def normalize_mutator_name(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def resolve_mutators(spec: str | None):
    if not spec or spec.strip().lower() == "all":
        return [MUTATOR_REGISTRY[name] for name in DEFAULT_MUTATORS]

    selected = []
    seen = set()
    for raw_name in spec.split(","):
        name = normalize_mutator_name(raw_name)
        if not name:
            continue
        if name not in MUTATOR_REGISTRY:
            raise ValueError(f"Unknown mutator: {raw_name.strip()}")
        if name not in seen:
            selected.append(MUTATOR_REGISTRY[name])
            seen.add(name)
    return selected


def list_mutators():
    rows = [MUTATOR_REGISTRY[name] for name in DEFAULT_MUTATORS]
    code_width = max(len(item["label"]) for item in rows)
    name_width = max(len(item["description"]) for item in rows)

    print(color("\nAvailable Mutators : \n", Colors.CYAN + Colors.BOLD))
    print(color(f"{'CODE':<{code_width}}  {'DESCRIPTION':<{name_width}}", Colors.GREY + Colors.BOLD))
    print(color(f"{'-' * code_width}  {'-' * name_width}", Colors.GREY))
    for name in DEFAULT_MUTATORS:
        info = MUTATOR_REGISTRY[name]
        code = color(info["label"], Colors.CYAN + Colors.BOLD)
        print(f"{code:<{code_width + 9}}  {info['description']:<{name_width}}")


def run_project_check(ctx, label):
    output, timed_out = ctx.run_snforge(ctx.run_timeout_seconds)

    if timed_out:
        print(color(f"{label}: timeout", Colors.YELLOW + Colors.BOLD))
        return False

    if "error" in output.lower() or "[FAIL]" in output:
        print(color(f"{label}: failed", Colors.RED + Colors.BOLD))
        return False

    print(color(f"{label}: passed", Colors.GREEN + Colors.BOLD))
    return True


def resolve_target_files(project_root: Path, source_root: Path, file_arg: str | None):
    if not file_arg:
        if not source_root.exists():
            return []
        return sorted([path for path in source_root.rglob("*.cairo") if path.is_file()])

    file_path = Path(file_arg).expanduser()
    if not file_path.is_absolute():
        file_path = (project_root / file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"Target file not found: {file_path}")
    if file_path.suffix != ".cairo":
        raise ValueError(f"Target file must be a .cairo file: {file_path}")
    return [file_path]


def mutate_file(ctx, file_path, selected_mutators, file_index=None, file_total=None):
    previous_target = ctx.target_file
    previous_backup = ctx.backup_file

    ctx.set_target_file(file_path)
    ctx.ensure_backup(ctx.target_file)

    try:
        progress = ""
        if file_index is not None and file_total is not None:
            progress = f" ({file_index}/{file_total})"
        if ctx.should_print_sections():
            print(color(f"\n▶ Mutating {ctx.file_label(file_path)}{progress}", Colors.YELLOW + Colors.BOLD))

        file_total = file_compiled = file_caught = file_timeouts = 0

        for info in selected_mutators:
            t, c, ca, to = info["fn"](ctx)
            file_total += t
            file_compiled += c
            file_caught += ca
            file_timeouts += to

        if ctx.should_print_sections():
            print(color(f"\n ✔ Finished mutating {ctx.file_label(file_path)}{progress}", Colors.GREY))

        return {
            "file": file_path,
            "total": file_total,
            "compiled": file_compiled,
            "caught": file_caught,
            "timeouts": file_timeouts,
        }
    finally:
        ctx.target_file = previous_target
        ctx.backup_file = previous_backup


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cairo-mutate",
        description="Cairo mutation testing",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target Starknet project root containing Scarb.toml and src/",
    )
    parser.add_argument(
        "--file",
        help="Mutate a single Cairo file relative to the project root, e.g. src/lib.cairo",
    )
    parser.add_argument(
        "--test-cmd",
        default="snforge test",
        help='Test command to run for each mutant, e.g. "snforge test"',
    )
    parser.add_argument(
        "--mutators",
        default="all",
        help="Comma-separated mutators to run, e.g. as_rem,op_eq,op_ari",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for each test command run",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Run snforge test before and after mutation to verify the project stays healthy",
    )
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v summaries, -vv full mutant logs)",
    )
    parser.add_argument(
        "--list-mutators",
        action="store_true",
        help="List available mutators and exit",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list_mutators:
        list_mutators()
        return

    try:
        selected_mutators = resolve_mutators(args.mutators)
    except ValueError as exc:
        parser.error(str(exc))

    project_root = Path(args.target).expanduser().resolve()
    test_cmd = shlex.split(args.test_cmd)

    ctx = MutationContext(
        project_root=project_root,
        source_root=project_root / "src",
        run_timeout_seconds=args.timeout,
        test_cmd=test_cmd,
        verbose=args.v,
    )

    signal.signal(signal.SIGINT, ctx.handle_interrupt)
    signal.signal(signal.SIGTERM, ctx.handle_interrupt)

    start_time = time.time()
    try:
        if ctx.should_print_sections():
            print(color("\n🚀 Starting Cairo Mutation Testing...\n", Colors.BOLD))
        else:
            print(color("Mutation testing in progress...", Colors.GREY))

        if args.safe:
            print(color("Running preflight project check...", Colors.GREY))
            if not run_project_check(ctx, "Preflight check"):
                raise SystemExit(1)

        try:
            cairo_files = resolve_target_files(project_root, ctx.source_root, args.file)
        except (FileNotFoundError, ValueError) as exc:
            parser.error(str(exc))

        if not cairo_files:
            print(color("No cairo files found under src/", Colors.GREY))
            return
        if args.file:
            print(color(f"Target file: {ctx.file_label(cairo_files[0])}", Colors.GREY))
        else:
            print(color(f"Found {len(cairo_files)} cairo files under {ctx.source_root.relative_to(ctx.project_root) if ctx.source_root.is_relative_to(ctx.project_root) else ctx.source_root}", Colors.GREY))

        results = []
        total_files = len(cairo_files)
        for index, file_path in enumerate(cairo_files, start=1):
            results.append(mutate_file(ctx, file_path, selected_mutators, index, total_files))

        compiled = sum(item["compiled"] for item in results)
        caught = sum(item["caught"] for item in results)
        timeouts = sum(item.get("timeouts", 0) for item in results)
        score = (caught / compiled * 100) if compiled > 0 else 0

        ctx.print_filewise_table(results)

        print(f"Final Mutation Score : {ctx.color_score(score)}")
        if timeouts > 0:
            print(color(f"Timeouts          : {timeouts}", Colors.YELLOW + Colors.BOLD))
    finally:
        ctx.restore_all_files()
        ctx.cleanup_backups()
        if args.safe:
            print(color("Running postflight project check...", Colors.GREY))
            if not run_project_check(ctx, "Postflight check"):
                raise SystemExit(1)
        duration = time.time() - start_time
        print(color(f"\nCompleted in {duration:.2f}s", Colors.BLUE))


if __name__ == "__main__":
    main()
