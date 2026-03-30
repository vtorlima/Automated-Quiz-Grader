#Arithmetic CI — Automated Quiz Grader

A minimal but fully-featured **CI autograder** built on GitHub Actions.  
Students edit a single text file, push, and instantly see their grade in the **Actions → Job Summary** tab.

## How it works

```
answers.txt  --push-->  GitHub Actions  -->  grade.py  -->  Job Summary
      ^                                          ^
  (you edit this)                       (compares against tests/)
```

1. Open this repo in **GitHub Codespaces** (or clone it locally).
2. Edit `answers.txt` — fill in the answer after each `=`.
3. **Commit and push**.
4. Go to the **Actions tab** -> click the latest run -> see the **Summary** panel with your results table and final grade.


## Repository structure

```
.
├── answers.txt                   <- EDIT THIS - your quiz submission
├── scripts/
│   └── grade.py                  <- grading engine (auto-discovers modules)
├── tests/
│   ├── addition/
│   │   ├── inputs.txt            <- operand pairs for addition questions
│   │   └── expected_outputs.txt  <- correct answers, one per line
│   ├── subtraction/
│   │   ├── inputs.txt
│   │   └── expected_outputs.txt
│   ├── multiplication/
│   │   ├── inputs.txt
│   │   └── expected_outputs.txt
│   └── division/
│       ├── inputs.txt
│       └── expected_outputs.txt
├── .github/
│   └── workflows/
│       └── grade.yml             <- CI pipeline definition
└── .devcontainer/
    └── devcontainer.json         <- Codespaces environment config
```

## Adding new test modules

The grader **auto-discovers** modules, no code changes needed.  
To add a new operation (e.g. modulo):

```bash
mkdir tests/modulo
echo "# inputs: left right" > tests/modulo/inputs.txt
echo "10 3"                 >> tests/modulo/inputs.txt
echo "1"                    > tests/modulo/expected_outputs.txt
```

Push, and the next CI run will automatically include the new module.  
This is the core extensibility principle: **new test cases = new files, nothing else.**

## Running locally

```bash
python scripts/grade.py --answers answers.txt --tests-dir tests/
```

## Design notes

This project demonstrates the same structural patterns found in CI testing pipelines for larger codebases:

| Pattern | This project | Larger CI systems |
|---|---|---|
| Input/output test pairs | `inputs.txt` + `expected_outputs.txt` per module | Input files compared against reference outputs |
| Auto-discovery | `tests/*/` directories scanned automatically | pytest, ctest, etc. discover test files |
| Structured reporting | GitHub Job Summary with Markdown tables | JUnit XML, Allure, etc. |
| Fail-fast + full report | `continue-on-error` + gate step | Common CI pattern |
| Environment pinning | Python 3.11 in workflow + devcontainer | Reproducible CI environments |
