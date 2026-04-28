<h1 align="center"><b>Cairo-Mutate</b></h1>

<p align="center">
  <b>Mutation testing for Starknet contracts</b><br>
  <i>Test What Your Tests Miss</i><br><br>
  <a href="https://giveth.io/project/mutation-testing-framework-for-cairo-and-solidity">
    Support this project on Giveth
  </a>
</p>

---
<div align="center">
  <img src="https://raw.githubusercontent.com/sidarth16/cairo-mutate/main/assets/logo.png"
       alt="cairo-mutate"  
       style="width: 280px; border-radius: 10px;"  />
</div>

<p align="center">
  <img src="https://img.shields.io/badge/license-MIT-green" />
  <a href="https://pypi.org/project/cairo-mutate/">
    <img src="https://img.shields.io/pypi/v/cairo-mutate?color=orange&label=PyPI" />
  </a>
  <!-- <img src="https://img.shields.io/badge/python-3.x-blue" /> -->
  <a href="https://pepy.tech/projects/cairo-mutate">
    <img src="https://static.pepy.tech/personalized-badge/cairo-mutate?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads" />
  </a>
</p>

---

**cairo-mutate** brings mutation testing to Starknet, giving developers a measurable signal of test quality.

Find weak tests, missing edge cases, and false confidence from high coverage.

Instead of asking:

> “Do the tests pass? What is the coverage?”

it asks:

> “If the contract were wrong, would the tests notice?”

The tool mutates contract code, reruns the test suite, and measures how many injected faults are actually caught.

It introduces a proactive security layer for Starknet by injecting controlled faults into Cairo contracts and verifying whether existing test suites can detect them.


Mutation helps uncover:
- weak assertions
- missing edge cases
- broken invariants
- brittle state checks
- false confidence from high coverage

Even a test suite with 100% coverage can still miss important behavioural invariants. `cairo-mutate` helps reveal that gap by checking whether tests fail when those invariants are broken.

`cairo-mutate` moves confidence from post-deployment audits to development-time validation.


### Current Status (MVP)
A stable, string-based mutation engine with file-wise reporting, safe restore behavior, timeout handling, and a CLI that can run against any Starknet project root.

---

## Quick Demo

```bash
cairo-mutate demo_staking_protocol -v
```

Expected output:

<img src="https://raw.githubusercontent.com/sidarth16/cairo-mutate/main/assets/demo-out.png"
       alt="sample-output"  
       style="width: 440px; border-radius: 10px;"  />

> Screenshot shows part of the `-v` output for readability. Use `-vv` for the full mutation log.

---

## Requirements

- Python 3.10+
- `snforge`
- `scarb` `2.14.0` or newer

If your shell resolves the wrong `scarb`, use the asdf shim path:

```bash
env PATH="$HOME/.asdf/shims:$PATH" snforge test
```

---

## Installation

### Install from PyPI

Create a virtual environment and install the published package:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install cairo-mutate
```

### Install from Source

Clone the repository and install it in editable mode:

```bash
git clone https://github.com/sidarth16/cairo-mutate
cd cairo-mutate

# create venv
python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

The CLI entrypoint is `cairo-mutate`.

When working from source, this is implemented via [`mutate.py`](./mutate.py).

---

## Use Cases

- Evaluate test strength before deployment  
- Detect missing assertions and edge cases  
- Improve confidence in contract invariants  
- Demonstrate test quality in audits and grants  

---

## Features

- Scans a Starknet project and mutates Cairo files under `src/`
- Applies one mutation at a time for precise fault isolation
- Runs a configurable test command, defaulting to `snforge test`
- Built-in timeout handling, to safely skip long-running or stuck mutations
- Classifies each mutant as:
  - `✔ Caught`
  - `✘ Uncaught`
  - `Compile Error`
  - `Timeout`
- Restores original files automatically after each run
- Cleans up backups on exit, interrupt, or termination
- Prints file-wise mutation scores along with a final mutation score
- Supports multiple output modes: quiet, summary, and full trace modes

Works on any Starknet project with `Scarb.toml`, `src/`, and `snforge` tests.

---

## Mutators

The current MVP uses the following mutators:


| Code 	| Abbr 	| Desc |
|---	|---	|---
| `AS-REM` 	| Assert removal 	| replaces an `assert` body with a no-op
| `AS-FLIP` 	| Assert condition flip 	| flips assertion comparisons, such as `== ↔ !=` and `> ↔ <`	|
| `OP-EQ` 	| Equality operator mutation 	| flips equality and inequality operators outside `assert` expressions.	|
| `OP-ARI` 	|  Arithmetic operator mutation 	| flips arithmetic operators like `+ ↔ - ↔ * ↔ / ↔ %`	|
| `OP-ASG` 	| Assignment operator mutation 	| mutates assignment-style operations such as `+=` and `-=` into plain assignment behavior	|


These mutators are intentionally string-based for V1. That keeps the tool fast and easy to understand while we build the Cairo-aware AST version later.

---

## Why Mutation Testing?

Passing tests ≠ correct behavior.

`cairo-mutate` measures whether your tests actually detect broken logic, permissions, and invariants.

---

## CLI

The intended entrypoint is `cairo-mutate`.

```bash
cairo-mutate <target> [OPTIONS]
```

`<target>` is the Starknet project root that contains `Scarb.toml` and `src/`.

### Options

- `--test-cmd "snforge test"`  
  Custom test command to run after each mutant.
- `--file src/lib.cairo`  
  Mutate a single Cairo file relative to the project root.
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

Examples:

```bash
cairo-mutate demo_staking_protocol --file src/lib.cairo --safe -v
cairo-mutate demo_staking_protocol --safe -v
cairo-mutate demo_staking_protocol --test-cmd "snforge test" --timeout 20 -vv
cairo-mutate demo_staking_protocol --mutators as_rem,as_flip,op_eq --safe
cairo-mutate --list-mutators
```

### Output Style

Example mutant line:

<img src="https://raw.githubusercontent.com/sidarth16/cairo-mutate/main/assets/line.png"
     alt="mutant-line"
     style="width: 770px;" />

Example skipped summary:

<img src="https://raw.githubusercontent.com/sidarth16/cairo-mutate/main/assets/skip.png"
     alt="skip-summary"
     style="width: 350px;" />

Example file-wise report:

<img src="https://raw.githubusercontent.com/sidarth16/cairo-mutate/main/assets/report.png"
     alt="report-summary"
     style="width: 450px;" />

---

## Demo Project

The repository includes [`demo_staking_protocol/`](./demo_staking_protocol), a small Starknet `snforge` project used to demonstrate the tool.

It contains two contracts (`Vault`, `StakeVault`) to demonstrate mutation testing on permissions and time-based logic.

### Coverage vs Mutation

The demo project reports high test coverage:

- Line Coverage: **97%**
- Function Coverage: **100%**

But mutation testing reveals a different picture:

- Mutation Score: **65%**

This means many injected faults were **not detected by the test suite**, despite near-complete coverage.

> High coverage does not guarantee strong tests — mutation testing exposes that gap.

---

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

---

## Where It Fits

`cairo-mutate` is designed to sit alongside existing Starknet tooling:

- After writing tests
- Before audits
- In CI pipeline for test quality checks

---

## Current Limitations

This is still an MVP, so a few limits are intentional:

- mutations are string-based, not AST-based
- the tool focuses on `src/` files
- the current engine is tuned for practicality and clarity, not full Cairo syntax coverage

Those limits are part of the plan, not a bug. The next major step is a Cairo-aware parser and AST-based mutation layer.

---

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

---

## Project Layout

- [`mutate.py`](./mutate.py) - root CLI orchestrator
- [`mutators/`](./mutators) - one file per mutator plus shared runtime helpers
- [`demo_staking_protocol/`](./demo_staking_protocol) - standalone Starknet demo project


---

## Author

**Sidarth S**<br/>
*Security Engineer & builder of cairo-mutate*

Focused on improving test quality and security tooling for Starknet.

- GitHub: https://github.com/sidarth16
- Portfolio: https://sidarthx0.vercel.app

---

## License

cairo-mutate is released under the MIT License.

© 2026 — Built for developers who care about test quality, correctness, and security.<br>
Commercial use is allowed. If you use cairo-mutate in tooling, research, or audits, attribution is appreciated — for example, mentioning “Powered by cairo-mutate” in your documentation or repository.

Let’s build openly and raise the standard for testing in Starknet

---

## Support & Updates

Cairo-Mutate is actively evolving — expect improvements in mutation quality, deeper Cairo integration, and CI-ready workflows.

- Report issues or request features on GitHub  
- Share feedback from real-world usage  
- Contributions and discussions are welcome  

Follow the project and track progress on the repository.

---

**Tests shouldn’t just pass — they should prove correctness.**
