# Parity definition (step 0.4)

Date: 2026-10-03. Status: **draft**. Finalized in DEC-015 (step 1.1).

## Definition

The new path has parity with the current flow when it gives the **same verification results** and **no regression in the baseline outcome**. Same model, same number of prompts and same reasoning are not required.

## Metric classes

| Class | Metrics | Role in decisions |
|---|---|---|
| Hard requirement | Correctness and verification results; reliability (schema validity, no policy violations, no permission violations) | Must hold |
| Optimization | Cost, latency | Trade-offs allowed if outcome and verification hold |
| Diagnostic | Review iterations | Informs, does not decide |

## Where the numbers come from

| Side | Source |
|---|---|
| Current flow | The private baseline file kept outside this repo (3 to 5 past tasks; "unknown" where not recorded) |
| New path | `RunRecord` JSONL (`adws/runs/`) plus the gate results |

## Rules

- Compare per task, not by averages. With 3 to 5 tasks and non-deterministic models, read results as direction.
- A task with an "unknown" baseline value is excluded from that metric, not guessed.
- A hard-requirement failure is a stop, whatever the optimization metrics show.

## Open

- Acceptable margin on the directional metrics for the Phase 2 gate (decision #5). Answer before Phase 2 ends.
