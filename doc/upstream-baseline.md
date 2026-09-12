# Terminal-Bench assignment upstream baseline

Recorded: 2026-09-13 (Asia/Shanghai)

## Repository

- Canonical repository: `https://github.com/harbor-framework/terminal-bench.git`
- Frozen commit: `e2995b93b0a46edee7bc9942ea5622411a6d5bb9`
- Commit timestamp: `2026-09-11T13:50:57-07:00`
- Commit subject: `Fix archive/build-cython-ext planarity dependency drift (#1955)`
- Local checkout: `/Users/grailor/Documents/Work/terminal-bench-3-interview-task/repository`
- Checkout method: shallow clone with blob filtering (`--depth 1 --filter=blob:none`)

## Current CI trial defaults

Source: `.github/harbor-run-defaults.yml` at the frozen commit.

- Standard trials per agent: 3
- Standard and cheat backend: `modal`
- Oracle/Nop validation backend: `modal`
- Trial analysis: enabled
- Analysis model alias: `sonnet`

Agent matrix:

| Agent | Model | Reasoning effort | Additional environment |
|---|---|---|---|
| `claude-code` | `anthropic/claude-opus-5` | `max` | `CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000` |
| `codex` | `openai/gpt-5.6-sol` | `xhigh` | none |

## Current task format findings

The canonical repository is now named `terminal-bench`, although its contribution call and assignment refer to Terminal-Bench 3. The current guide requires each task to contain:

```text
tasks/<task-name>/
├── README.md
├── instruction.md
├── task.toml
├── environment/
├── solution/
└── tests/
```

Important differences from older summaries:

- Metadata explanations moved from `task.toml` into human-written sections of the task `README.md`.
- `task.toml` uses `network_mode = "public"`; explicit legacy `allow_internet = true` is rejected by a current static check.
- Separate verifier mode is mandatory.
- Python packages installed directly in Dockerfiles/scripts must be pinned.
- Canonical versions are currently `pytest==9.1.1` and `pytest-json-ctrf==0.5.2`.
- Discrete verifier cases must emit CTRF at `/logs/verifier/ctrf.json`.
- Rewards must be binary on every reachable path.
- Agent-produced code executed by the verifier must run unprivileged and must not be able to reach the reward channel.
- Artifacts should contain only agent-produced content; fixed truth belongs in the verifier image.

## Implementation rubric

The current implementation rubric contains 35 named criteria:

1. verifiable
2. solvable
3. difficult
4. interesting
5. outcome_verified
6. anti_cheat_robustness
7. task_security
8. functional_verification
9. deterministic_reproducible
10. essential_difficulty
11. test_instruction_alignment
12. novel
13. agentic
14. reviewable
15. instruction_concision
16. solution_quality
17. separate_verifier_configured
18. environment_hygiene
19. structured_data_schema
20. typos
21. difficulty_explanation_quality
22. solution_explanation_quality
23. verification_explanation_quality
24. category_and_tags
25. task_name
26. resource_configuration
27. task_readme
28. expert_time_estimate
29. task_toml_schema
30. no_extraneous_files
31. artifact_efficiency
32. verifier_execution_isolation
33. ctrf_reporting
34. do_not_modify_enforced
35. binary_reward

Note: reviewer prose still refers to 30 criteria; use the rubric file itself as source of truth and recount before final validation.

## Static checks present at baseline

- `check-allow-internet.sh`
- `check-canary.sh`
- `check-compose-host-binds.sh`
- `check-dockerfile-platform.sh`
- `check-dockerfile-references.sh`
- `check-dockerfile-sanity.sh`
- `check-gpu-types.sh`
- `check-instruction-suffix.sh`
- `check-no-allow-internet-true.sh`
- `check-nproc.sh`
- `check-pip-pinning.sh`
- `check-pytest-version.sh`
- `check-separate-verifier.sh`
- `check-task-absolute-path.sh`
- `check-task-fields.sh`
- `check-task-package-name.sh`
- `check-task-slug.sh`
- `check-task-timeout.sh`
- `check-test-file-references.sh`
- `check-test-sh-sanity.sh`
- `check-trial-network-fetch.sh`
- `check-verifier-tooling-baked.sh`

## Local environment status

- Git: `2.54.0`
- `uv`: installed at `/opt/homebrew/bin/uv`
- Docker CLI: `29.5.3`
- Docker daemon: unavailable at baseline (`permission denied` on the user Docker socket)
- Harbor: not installed at baseline

## Immediate blockers and next actions

1. Select a domain aligned with the candidate's genuine expertise.
2. Compare three task candidates against all existing task names and the proposal rubric.
3. Start Docker Desktop or otherwise restore access to the Docker daemon before implementation validation.
4. Install the repository-compatible Harbor release only after checking workflow/version pins.
5. Do not run formal trials until the task revision is frozen and local validation is green.
