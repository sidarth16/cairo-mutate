# cairo-mutate

`cairo-mutate` is a mutation-testing tool for Starknet/Cairo contracts.

It brings mutation testing to Starknet, giving developers a measurable signal of test quality.

This is a focused tool for the Starknet ecosystem, built to make test quality visible instead of assumed.

This is one of the first mutation testing tools built specifically for the Starknet ecosystem.

Instead of asking “do the tests pass?”, it asks:

> if the contract were wrong, would the tests notice?

It deliberately breaks contract code, reruns the test suite, and shows how many of those injected faults your tests actually catch.

That makes `cairo-mutate` useful for finding weak assertions, missing edge cases, brittle state checks, and places where a test suite looks healthy but does not really protect contract behavior.

Even a test suite with 100% coverage can still miss important contract invariants.
`cairo-mutate` helps reveal that gap by checking whether the tests fail when those invariants are broken.

This is the current MVP: a stable, string-based mutation engine with file-wise reporting, safe restore behavior, timeout handling, and a CLI that can run against any Starknet project root.

## Quick Demo

```bash
cairo-mutate demo_staking_protocol -v
```

Expected flow:

```text
Found 2 Cairo files
▶ Mutating src/vault.cairo
▶ Mutating src/stake_vault.cairo

Final Mutation Score: 61.54%
Completed in 41.71s
```

## Use Cases

- Evaluate test suite strength before deployment
- Detect missing assertions and edge cases
- Improve confidence in contract invariants
- Demonstrate test quality in audits and grant reviews

## Features

- Scans a Starknet project and mutates Cairo files under `src/`
- Applies one mutation at a time
- Runs a configurable test command, defaulting to `snforge test`
- Classifies each mutant as:
  - `✔ Caught`
  - `✘ Uncaught`
  - `Compile Error`
  - `Timeout`
- Restores original files automatically after each run
- Cleans up backups on exit, interrupt, or termination
- Prints file-wise mutation scores plus a final mutation score
- Supports quiet, summary, and full trace modes

Works on any Starknet project with `Scarb.toml`, `src/`, and `snforge` tests.

## Mutators

The current MVP uses the following mutators:

- `AS-REM` - Assert removal
- `AS-FLIP` - Assert condition flip
- `OP-EQ` - Equality operator mutation
- `OP-ARI` - Arithmetic operator mutation
- `OP-ASG` - Assignment operator mutation

### What each one means

- `AS-REM`: replaces an `assert` body with a no-op. This checks whether your tests depend on the assertion actually enforcing invariants.
- `AS-FLIP`: flips assertion comparisons, such as `== ↔ !=` and `> ↔ <`. This checks whether tests catch broken validation logic.
- `OP-EQ`: flips equality and inequality operators outside `assert` expressions.
- `OP-ARI`: flips arithmetic operators like `+ ↔ -` outside assertions.
- `OP-ASG`: mutates assignment-style operations such as `+=` and `-=` into plain assignment behavior.

These mutators are intentionally string-based for V1. That keeps the tool fast and easy to understand while we build the Cairo-aware AST version later.

## Why This Matters For Starknet

Starknet projects need more than passing tests. They need confidence that the tests actually catch broken permissions, broken state transitions, and broken invariants.

Even a suite with 100% coverage can still miss the invariants that matter most.
`cairo-mutate` is built to expose that gap.

`cairo-mutate` turns that into a measurable workflow:

- inject a fault
- rerun the suite
- record whether the test caught it
- score the test suite by mutation resistance

That makes the tool useful as a developer aid, a CI signal, and a reviewer-friendly demo for Starknet ecosystem grants.

## CLI

The intended entrypoint is `cairo-mutate`.

```bash
cairo-mutate <target> [OPTIONS]
```

`<target>` is the Starknet project root that contains `Scarb.toml` and `src/`.

### Options

- `--test-cmd "snforge test"`  
  Custom test command to run after each mutant.
- `--mutators as_rem,as_flip,op_eq`  
  Limit the run to specific mutators.
- `--timeout 20`  
  Timeout in seconds for each test command run.
- `--safe`  
  Run the project test command before mutation starts and again after restore.
- `-v`  
  Print mutator/file summaries.
- `-vv`  
  Print full line-by-line mutant logs.
- `--list-mutators`  
  Show the available mutators and exit.

### Verbosity modes

- No `-v`: report-only mode. Prints the final report and summary footer.
- `-v`: prints file start/finish markers, file counts, and per-mutator summaries.
- `-vv`: prints the full mutant log for each mutation, plus summaries and the final report.

### Usage

```bash
cairo-mutate <target> [OPTIONS]
```

Examples:

```bash
cairo-mutate demo_staking_protocol --safe -v
cairo-mutate demo_staking_protocol --test-cmd "snforge test" --timeout 20 -vv
cairo-mutate demo_staking_protocol --mutators as_rem,as_flip,op_eq --safe
cairo-mutate --list-mutators
```

## Output Style

Example mutant line:

```text
[AS-FLIP] L43: assert(amount != 0, 'amount must be > 0'); → assert(amount == 0, 'amount must be > 0'); => ✔ Caught
```

Example skipped summary:

```text
[OP-ARI] 4 skipped (2 compile error, 2 timeout)
```

Example file-wise report:

```text
➤ Mutation Report
| File              | Mutants | Caught | Uncaught | Score  |
| src/vault.cairo   | 8       | 5      | 3        | 62.50% |
| src/stake_vault.cairo | 5   | 3      | 2        | 60.00% |
| Total             | 13      | 8      | 5        | 61.54% |
```

Example footer:

```text
Final Mutation Score : 61.54%
Timeouts             : 7
Completed in 41.71s
```

## Demo Project

The repository includes [`demo_staking_protocol/`](./demo_staking_protocol), a small Starknet `snforge` project used to demonstrate the tool.

It contains two independent contracts:

- `Vault` - anyone can deposit, owner can withdraw
- `StakeVault` - deposits are allowed anytime, withdrawals are gated by unlock time

This pairing gives the mutation engine a more interesting story than a single toy contract:

- one contract tests permissions
- the other tests time-gated state transitions
- the test suite can catch different classes of mistakes

That makes the demo more useful for reviewers and more realistic for mutation analysis.

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/cairo-mutate
cd cairo-mutate
```

Or install locally and use the CLI:

```bash
pip install -e .
cairo-mutate <target>
```

The CLI entrypoint is `cairo-mutate`.

When working from source, this is implemented via [`mutate.py`](./mutate.py).

## Where It Fits

`cairo-mutate` is designed to sit alongside existing Starknet tooling:

- run after writing tests
- run before audits
- run in CI for test quality checks

## Requirements

- Python 3.10+
- `snforge`
- `scarb` `2.14.0` or newer

If your shell resolves the wrong `scarb`, use the asdf shim path:

```bash
env PATH="$HOME/.asdf/shims:$PATH" snforge test
```

## Safety Behavior

`cairo-mutate` edits files in place, so it is designed to be safe by default:

- backs up each target file before mutation begins
- restores originals after each mutant
- restores on normal exit
- restores on `SIGINT` and `SIGTERM`
- removes backup files after the run

If a run is interrupted, the script restores the original source files before exiting.

### Safe Mode

Use `--safe` when you want an extra project-health check around the mutation pass.

With safe mode enabled, the tool:

- runs the test command before mutation starts
- aborts early if the project is already failing
- restores files after the mutation pass
- runs the test command again after restore
- fails the command if the restored project no longer passes

This is useful for CI, PR checks, and grant demos where you want to prove that the project was healthy before mutation and still healthy afterward.

## Current Limitations

This is still an MVP, so a few limits are intentional:

- mutations are string-based, not AST-based
- `OP-REL` is intentionally postponed for now because it is noisy without AST-aware matching
- the tool focuses on `src/` files
- the current engine is tuned for practicality and clarity, not full Cairo syntax coverage

Those limits are part of the plan, not a bug. The next major step is a Cairo-aware parser and AST-based mutation layer.

## Roadmap

### V1 (Current)

Stable string-based mutation engine with:

- modular mutator files
- configurable test command
- timeout support
- safe restore behavior
- file-wise reporting
- quiet / summary / verbose modes

### V2 (Next)

Cairo-aware AST mutation engine with:

- parser and source spans
- safer rewrites
- fewer false positives from string matching
- more precise comparison and arithmetic mutations
- cleaner expansion into static analysis and later symbolic reasoning

### Vision

A full mutation and analysis framework for Starknet contracts.

## What We Tightened

These are the design choices that make the MVP feel deliberate instead of noisy:

- Mutations are scoped to `src/` so the tool does not wander into tests, backups, or unrelated files.
- `AS-REM` and `AS-FLIP` focus on assertion logic, which keeps the signal centered on contract validation.
- `OP-EQ` is narrow by design and only targets equality / inequality, which matches the detector name.
- `OP-REL` was intentionally held back from the MVP because string-based matching caused too much compile-error noise.
- Compile errors and timeouts are excluded from the mutation score, so the score reflects only meaningful test executions.
- Backups and restore logic ensure source files are always put back even if the run is interrupted.
- The CLI supports `--test-cmd`, `--mutators`, `--timeout`, and `--safe`, so the tool adapts to different Starknet projects without code changes.
- `-v` and `-vv` give controlled visibility, which prevents the output from feeling frozen while still allowing deep inspection.
- File start/finish markers, line numbers, and the file-wise table all make it easier to understand exactly what happened in a run.

These choices reduce false positives, reduce false negatives caused by ambiguous matching, and make the output easier for users and reviewers to trust.

## Why This Is More Than A Simple Script

This project now behaves like a small developer tool rather than a one-off experiment:

- modular mutators make the code easier to extend and review
- progress markers keep runs from feeling frozen
- safe mode validates the project before and after mutation
- timeout handling prevents one bad mutant from blocking the entire run
- file-wise scoring makes the output easier to compare across contracts
- demo contracts show different bug classes instead of a single toy example

That is the difference between “it runs” and “it is ready to show reviewers.”

## Project Layout

- [`mutate.py`](./mutate.py) - root CLI orchestrator
- [`mutators/`](./mutators) - one file per mutator plus shared runtime helpers
- [`demo_staking_protocol/`](./demo_staking_protocol) - standalone Starknet demo project

## Commit Story

The repo keeps a staged build history in `code-bkp/` and a suggested commit sequence in `commit-plan.txt`.

That history is intentional: it shows the tool evolving from a prototype into a usable MVP rather than appearing fully formed.
