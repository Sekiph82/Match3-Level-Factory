# LFX-M11-005 / LFX-M11-009 R03: Frozen Independent Audit Criteria V01

Frozen 2026-10-21, **before receiving R03 execution results**. This is an evaluation rubric, not a task tracker or a PASS. Root `TASKS.md` is the ONLY task tracker. This rubric applies solely to `Sekiph82/Match3-Level-Factory`, handoff `coordination/prompts/LFX-M11-005_009_R03_DONOR_TYPEERROR_AND_LOCAL_AUTHORING_WORKBENCH_MASTER.md`.

## Result protocol

Each gate must be independently marked **PASS / FAIL / BLOCKED / NOT_RUN**. Narrative test totals alone are **REPORTED, NOT INDEPENDENTLY VERIFIED**. Every runtime PASS needs source commit SHA, exact commands, environment versions, original full execution logs, failure/skip names, duration and negative controls. Every artifact PASS needs original file hashes, complete manifest and independently verified ZIP CRC. Source scans do not qualify as Unity Editor interaction or actual gameplay tests. Every gate below is mandatory for **R03 full independent PASS**. If any is absent or blocked, overall **R03 NOT MET** (partial source improvements may still be reported).

| Gate | Immutable acceptance requirement |
|---|---|
| A00 | Exact Level Factory repo and source SHA, pre/post Git status; protected local owner files unchanged; no other repos modified. |
| A01 | Reproduce or independently explain **each of the six actual R02 failing donor seeds**, exact config and source, with complete Python traceback including function and line numbers. Exception message alone does NOT pass. |
| A02 | Correct proven root cause with a minimal donor-compatible adaptation; no invented goal mapping, substituted data, hidden exceptions or silent changes in scoring/RNG. Record BLOCKED if semantics cannot be established. |
| A03 | Earlier good-seed source SHA/output comparison and all six bad-seed results; old R01/R02 evidence remains immutable. |
| A04 | Exact preservation of donor originals; separately authored local goal proposals each carry unique source-to-derived SHA chain and no inherited WIN, target meaning or difficulty. |
| A05 | Actually implement/run **independent original Factory-local board creation** using existing proven Studio/sample adapter contract, not recoloring or goal swapping donor boards. True local-compatible output is evidenced or legitimately blocked. |
| A06 | Strict schema and sample adapter constraints: valid palette, active cells, goal types, move bounds; explicitly reject unsupported holes/locks/specials/obstacles and unknown profiles. |
| A07 | Separate counters for donor attempts, donor successes/failures, derived goals, independently authored local boards, locally compatible unique, reviewed, approved and Engine-qualified; exact/near duplicates across seeds and titles rejected. |
| A08 | Deterministic source and output SHA under repeated bounded runs, checkpoints, pause/resume, tamper, stale source, timeout, path safety and cancellation all verified by positive and negative cases. |
| A09 | A real measured **small donor pilot** and a separately measured original-local candidate pilot with seed-by-profile outcomes, actual elapsed time, rejected counts and underfill. Do NOT blindly launch 500 candidates. |
| A10 | Real Unity 6000.6.5f1 Editor compile, focused EditMode, and manual GUI start/progress/cancel/resume/source-vs-local/preview interaction evidence. Otherwise mark NOT_RUN/BLOCKED; source-only checks are insufficient. |
| A11 | Focused and complete Python 3.12.10 Windows regression with **raw, unabridged** runner log or per-test XML, exact commands and timings. Mock-based tests must be distinguished from actual donor/Unity runtime. |
| A12 | Independently verify ZIP CRC, SHA256 entry manifests, source provenance and artifact trace, and preserve previous evidence without modification. |
| A13 | Engine ENG-M24 and approved 5-bot/WIN are external. **0/500 Engine-qualified** remains until separately proven. No fake release PASS/owner approval, tags or production. |
| A14 | One verified Drive final report plus evidence ZIP; root TASKS only updated for real results; no other-repo change, ADB, Android emulator, Player build, GitHub Actions, R2 write or disk cleanup. |

## Required independent audit deliverable

Produce a separate source+evidence audit with one row per A00-A14: verdict, source or evidence file, reproduction steps and defects. Identify P0/P1/P2 concerns, actual issues and source fixes needed; distinguish builder-reported Windows PASS from audit-verified artifact facts. Explicitly state full PASS only if **all fifteen gates pass**, otherwise **NOT MET**, and provide exact missing evidence and remediation order. No retroactive changes to this frozen V01 after R03 results.
