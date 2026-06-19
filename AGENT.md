# AGENT.md

This file is for agents reading the repository on behalf of a user.
本文件面向代用户阅读仓库的 Agent。
Agents may respond in the user's preferred language.
智能体可以用用户偏好的语言提问和回复。

## 1. Read First

Read these in order:

1. [README.md](./README.md) or [README.zh-CN.md](./README.zh-CN.md)
2. [SUPPORT.md](./SUPPORT.md)
3. [ROADMAP.md](./ROADMAP.md)
4. [examples/detection_contract.yaml](./examples/detection_contract.yaml)
5. `src/tensorfence/core/contracts.py`
6. `src/tensorfence/core/validation.py`
7. `src/tensorfence/cli.py`
8. `src/tensorfence/core/report.py`
9. `src/tensorfence/core/templates.py`
10. `tests/unit/test_contract.py`

## 2. Ask These Questions In Order

### Question 1: What kind of work is this?

| Choice | Meaning | Where to look next |
| --- | --- | --- |
| A | Docs, README, templates, or onboarding | `README*.md`, `AGENT.md`, `CONTRIBUTING*.md`, `.github/ISSUE_TEMPLATE/*` |
| B | Contract, schema, or validation | `src/tensorfence/core/contracts.py`, `src/tensorfence/core/validation.py` |
| C | CLI, summary text, or user-facing output | `src/tensorfence/cli.py`, `src/tensorfence/core/report.py` |
| D | Runtime adapter or stage comparison | Ask for the exact failure stage first |

If the user chooses D or does not know:

- ask for the model family and task
- ask for the source framework and export path
- ask for the target runtime and target device
- ask for one failing sample or one expected output example
- ask for `python -m tensorfence doctor` output if they can run it

### Question 2: Which stage is drifting?

| Choice | Meaning | Where to look next |
| --- | --- | --- |
| A | Preprocess | `README*.md`, `examples/detection_contract.yaml`, `src/tensorfence/core/contracts.py`, `src/tensorfence/core/validation.py` |
| B | Decode | `examples/detection_contract.yaml`, `src/tensorfence/core/contracts.py`, `src/tensorfence/core/validation.py` |
| C | NMS | `examples/detection_contract.yaml`, `src/tensorfence/core/contracts.py`, `src/tensorfence/core/validation.py` |
| D | Quantization | `examples/detection_contract.yaml`, `src/tensorfence/core/contracts.py`, `src/tensorfence/core/validation.py` |
| E | Runtime | `README*.md`, `src/tensorfence/cli.py`, `src/tensorfence/core/report.py` |
| F | Unknown | Ask for the first stage where framework output and RKNN output diverge |

If the user chooses F or does not know:

- ask where the output first stops matching
- ask whether framework output, ONNX output, or RKNN output is available
- ask for the exact input shape, layout, color order, and normalization
- ask for one output tensor example if available

### Question 3: What artifacts do we have?

| Choice | Meaning | What to request |
| --- | --- | --- |
| A | A contract file already exists | Ask for the YAML or the path |
| B | Only model files exist | Ask for the contract fields and a failing sample |
| C | Only screenshots / outputs exist | Ask for the exact command and runtime versions |
| D | Nothing useful yet | Ask for the minimal reproduction first |

If the user chooses D or does not know:

- tell them to start from `examples/detection_contract.yaml`
- ask them to run `tensorfence doctor`
- ask them to paste the smallest reproducible contract or command

## 3. After You Get Answers, Edit Here

| Change needed | Files to edit or add | What to change |
| --- | --- | --- |
| README or onboarding | `README.md`, `README.zh-CN.md`, `AGENT.md` | Keep the symptom-driven intro, quick start, contract example, and agent guidance aligned |
| Templates | `.github/ISSUE_TEMPLATE/*`, `.github/pull_request_template.md` | Keep questions bilingual and ask for model family, framework, runtime, stage, and reproduction |
| Contract schema | `src/tensorfence/core/contracts.py` | Add or rename fields in the Pydantic models |
| Validation rules | `src/tensorfence/core/validation.py` | Add explicit mismatch checks and keep error messages concrete |
| CLI flow | `src/tensorfence/cli.py` | Update commands, argument names, and quick-start assumptions |
| Human-readable output | `src/tensorfence/core/report.py` | Update validation summaries and diff text |
| Sample templates | `src/tensorfence/core/templates.py` | Keep sample contract text aligned with the schema |
| Sample contract | `examples/detection_contract.yaml` | Keep the sample minimal and aligned with the current schema |
| Regression coverage | `tests/unit/test_contract.py` | Add one test for each new field, rule, or CLI behavior change |

## 4. Working Rules

- Do not guess input layout, color order, resize mode, or activation placement.
- Do not add runtime logic into contract validation files.
- Prefer changing docs and validation before adding new adapters.
- If a user only gives a repo link, start with README, AGENT, and the sample contract.
- If a task is blocked by missing facts, ask the smallest possible question set and stop there.

## Useful Commands

```bash
python -m unittest discover -s tests
python -c "import sys; sys.path.insert(0, 'src'); from tensorfence.cli import main; raise SystemExit(main(['doctor']))"
python -c "import sys; sys.path.insert(0, 'src'); from tensorfence.cli import main; raise SystemExit(main(['check-contract', 'examples/detection_contract.yaml']))"
```
