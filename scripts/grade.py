#!/usr/bin/env python3
"""
Core grading engine for the arithmetic CI autograder.
"""

import argparse
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

#  Data structures

@dataclass
class TestCase:
    """
    Represents a single question/answer pair within a module.

    Attributes:
        question: The raw question string as it appears in answers.txt.
        expected: The correct integer answer.
        submitted: The integer submitted by the student, or None if blank or invalid.
    """
    question: str
    expected: int
    submitted: Optional[int] = None

    @property
    def is_correct(self) -> bool:
        return self.submitted is not None and self.submitted == self.expected

    @property
    def status_emoji(self) -> str:
        if self.submitted is None:
            return "⬜"   # unanswered
        return "✅" if self.is_correct else "❌"


@dataclass
class ModuleResult:
    """
    Represents the aggregated results for one test module.

    Attributes:
        name: The module name.
        cases: List of test cases for the module.
    """
    name: str
    cases: List[TestCase] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.cases if c.is_correct)

    @property
    def total(self) -> int:
        return len(self.cases)

    @property
    def failed(self) -> int:
        return self.total - self.passed

#  Parsing helpers

def parse_answers(answers_path: Path) -> dict:
    """
    Parse the student's answers file into a dictionary.

    Args:
        answers_path: Path to the student's answers file.

    Returns:
        Dictionary mapping normalized question strings to submitted integer answers or None.
    """
    answers = {}

    with open(answers_path, "r") as f:
        for raw_line in f:
            line = raw_line.strip()

            # Skip comments and blank lines
            if not line or line.startswith("#"):
                continue

            # Ignore lines that do not contain an answer separator
            if "=" not in line:
                continue

            # Split question and answer parts
            question_part, _, answer_part = line.partition("=")
            question = question_part.strip()
            answer_str = answer_part.strip()

            # Store None for blank answers, int otherwise
            if answer_str == "":
                answers[question] = None
            else:
                try:
                    answers[question] = int(answer_str)
                except ValueError:
                    # Treat non-numeric answers as invalid
                    answers[question] = None

    return answers


def load_module(module_dir: Path) -> List[TestCase]:
    """
    Load a test module from a directory containing input and expected output files.

    Args:
        module_dir: Path to a module directory.

    Returns:
        List of TestCase objects for the module.
    """
    inputs_path   = module_dir / "inputs.txt"
    expected_path = module_dir / "expected_outputs.txt"

    def read_data_lines(path: Path) -> List[str]:
        """
        Read non-comment, non-blank lines from a file.

        Args:
            path: Path to the file.

        Returns:
            List of valid lines from the file.
        """
        lines = []
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    lines.append(stripped)
        return lines

    input_lines    = read_data_lines(inputs_path)
    expected_lines = read_data_lines(expected_path)

    if len(input_lines) != len(expected_lines):
        raise ValueError(
            f"Module '{module_dir.name}': inputs.txt has {len(input_lines)} lines "
            f"but expected_outputs.txt has {len(expected_lines)} lines. They must match."
        )

    cases = []
    for inp, exp in zip(input_lines, expected_lines):
        # Determine the operator symbol from the module name
        operator_symbol = {
            "addition":       "+",
            "subtraction":    "-",
            "multiplication": "*",
            "division":       "/",
        }.get(module_dir.name, "?")

        parts = inp.split()
        if len(parts) == 2:
            question = f"{parts[0]} {operator_symbol} {parts[1]}"
        else:
            question = inp  # fallback: use raw line as question key

        cases.append(TestCase(
            question=question,
            expected=int(exp),
        ))

    return cases


def discover_modules(tests_dir: Path) -> List[Path]:
    """
    Discover all valid test modules inside the tests directory.

    Args:
        tests_dir: Path to the tests directory.

    Returns:
        List of valid module directories.
    """
    modules = []
    for entry in sorted(tests_dir.iterdir()):
        if entry.is_dir():
            has_inputs   = (entry / "inputs.txt").exists()
            has_expected = (entry / "expected_outputs.txt").exists()
            if has_inputs and has_expected:
                modules.append(entry)
            else:
                print(
                    f"[warn] Skipping '{entry.name}': missing inputs.txt "
                    f"or expected_outputs.txt",
                    file=sys.stderr,
                )
    return modules


#  Grader

def run_grader(answers_path: Path, tests_dir: Path) -> List[ModuleResult]:
    """
    Run the main grading workflow.

    Args:
        answers_path: Path to the student's answers file.
        tests_dir: Path to the tests directory.

    Returns:
        List of ModuleResult objects, one per module.
    """
    # Parse submitted answers
    submitted = parse_answers(answers_path)

    # Discover available test modules
    module_dirs = discover_modules(tests_dir)
    if not module_dirs:
        print(f"[error] No valid test modules found in '{tests_dir}'.", file=sys.stderr)
        sys.exit(2)

    results = []

    # Grade each module independently
    for mod_dir in module_dirs:
        cases = load_module(mod_dir)

        for case in cases:
            # Match each question against the student's submitted answers
            case.submitted = submitted.get(case.question, None)

        results.append(ModuleResult(name=mod_dir.name, cases=cases))

    return results


#  Output renderers

def render_terminal(results: List[ModuleResult]) -> None:
    """
    Print a human-readable grading summary to stdout.

    Args:
        results: List of module results.
    """
    total_passed = 0
    total_cases  = 0

    for mod in results:
        print(f"\n{'─'*40}")
        print(f"  Module: {mod.name.upper()}  ({mod.passed}/{mod.total})")
        print(f"{'─'*40}")
        for case in mod.cases:
            submitted_str = str(case.submitted) if case.submitted is not None else "(blank)"
            print(
                f"  {case.status_emoji}  {case.question} = "
                f"{submitted_str}   [expected: {case.expected}]"
            )
        total_passed += mod.passed
        total_cases  += mod.total

    print(f"\n{'═'*40}")
    pct = int(100 * total_passed / total_cases) if total_cases else 0
    print(f"  FINAL GRADE: {total_passed}/{total_cases}  ({pct}%)")
    print(f"{'═'*40}\n")


def render_github_summary(results: List[ModuleResult], summary_path: str) -> None:
    """
    Write a Markdown summary to the GitHub Actions summary file.

    Args:
        results: List of module results.
        summary_path: Path to the GitHub summary file.
    """
    lines = []
    total_passed = sum(m.passed for m in results)
    total_cases  = sum(m.total  for m in results)
    pct = int(100 * total_passed / total_cases) if total_cases else 0

    # Add summary header
    lines.append("# Arithmetic CI — Test Results\n")
    lines.append(f"**Final Grade: {total_passed}/{total_cases} ({pct}%)**\n")

    # Add per-module result tables
    for mod in results:
        mod_pct = int(100 * mod.passed / mod.total) if mod.total else 0
        lines.append(f"\n## {mod.name.capitalize()}  —  {mod.passed}/{mod.total} ({mod_pct}%)\n")
        lines.append("| Question | Your Answer | Expected | Result |")
        lines.append("|----------|-------------|----------|--------|")
        for case in mod.cases:
            submitted_str = str(case.submitted) if case.submitted is not None else "*(blank)*"
            lines.append(
                f"| `{case.question}` | {submitted_str} | {case.expected} | {case.status_emoji} |"
            )

    # Add footer message
    if total_passed == total_cases:
        lines.append("\n---\n> **Perfect score! All test cases passed.**")
    elif total_passed == 0:
        lines.append("\n---\n> Fill in your answers in `answers.txt` and push again.")
    else:
        lines.append(f"\n---\n> Keep going — {total_cases - total_passed} question(s) still need work.")

    with open(summary_path, "a") as f:   # append as recommended by GitHub
        f.write("\n".join(lines) + "\n")

#  Entry point

def main():
    """
    Parse arguments, run the grader, and exit with the appropriate status code.
    """
    parser = argparse.ArgumentParser(
        description="Arithmetic CI autograder — compares answers.txt against test modules."
    )
    parser.add_argument(
        "--answers",
        type=Path,
        default=Path("answers.txt"),
        help="Path to the student's answers file (default: answers.txt)",
    )
    parser.add_argument(
        "--tests-dir",
        type=Path,
        default=Path("tests"),
        help="Path to the tests directory containing module subdirs (default: tests/)",
    )
    args = parser.parse_args()

    # Validate input paths before processing
    if not args.answers.exists():
        print(f"[error] Answers file not found: {args.answers}", file=sys.stderr)
        sys.exit(2)
    if not args.tests_dir.is_dir():
        print(f"[error] Tests directory not found: {args.tests_dir}", file=sys.stderr)
        sys.exit(2)

    # Run grading
    results = run_grader(args.answers, args.tests_dir)

    # Print terminal output
    render_terminal(results)

    # Write GitHub Actions summary if available
    github_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if github_summary:
        render_github_summary(results, github_summary)

    # Exit with failure if any answer is incorrect
    total_passed = sum(m.passed for m in results)
    total_cases  = sum(m.total  for m in results)
    sys.exit(0 if total_passed == total_cases else 1)


if __name__ == "__main__":
    main()