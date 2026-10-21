# LFX-M11-005 + LFX-M11-009 R04 | Local-authoring recovery and real Unity Studio verification

**One cohesive Codex handoff, not a new milestone.** Only `Sekiph82/Match3-Level-Factory`, only local `C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory`. Do NOT operate in MATCH3_ENGINE, Visual UI Factory or any other game repo. ROOT `TASKS.md` is the **single task tracker**.

**MANDATORY PRE-FROZEN INDEPENDENT AUDIT:** https://github.com/Sekiph82/Match3-Level-Factory/blob/main/coordination/audits/LFX-M11-005_009_R04_FROZEN_AUDIT_CRITERIA_V01.md . Before implementation confirm the criteria were already published and the audit is NOT a report of PASS. Codex must deliver evidence permitting independent ChatGPT gate-by-gate review B00–B12. A Codex assertion alone never earns independent PASS.

## 0. Exact R03 starting evidence, do not start over

R03 implementation SHA: `667e8b9f7f55eb3812ca502d8c44fe2ac54139f4`. R03 independently audited at https://github.com/Sekiph82/Match3-Level-Factory/blob/main/coordination/audits/LFX-M11-005_009_R03_INDEPENDENT_AUDIT_20261021_V01.md . R03 audit-only commits may have advanced GitHub main; **read current main HEAD and root TASKS** and fast-forward the one existing local project before editing. Don't reset protected local owner files.

Proven R03 achievements:
- Removed actual mixed None/string diagnostic sorting error in `campaign_goal_contract.py`. Six historical R02 failures now lead to **10/10 donor original outputs**, four formerly working donor draft SHA hashes unchanged. Donor goal equivalence **still NOT established**.
- Added **independent original Factory-local** `factory_local_authoring.py`: project-local unique files, Studio sample palette, `sample.score`, entirely active 8×8 preview boards, 25/25 distinct sample-schema-compatible local previews from five games. They are **NOT campaign content, Engine moves/WIN, approved game difficulty or release**.
- Raw logs in R03 ZIP support reported Windows CPython 3.12.10 **43/43 focused** and **258/258 full** passing source tests. Actual Unity Editor C# compilation/EditMode/manual GUI was **NOT_RUN**.
- R03 auditor **FULL NOT MET**, concrete blocking gates: **A08** missing *local* cancel/atomic checkpoint/resume/recovery; **A10** Unity GUI/EditMode not run; pre/post owner-state evidence limited. **LFX-M11-005=IN_PROGRESS**, **LFX-M11-009=BLOCKED**, external **ENG-M24=BLOCKED**, 0/500 real Engine-qualified campaign levels.
- R03 original report: https://drive.google.com/file/d/1KSUZvIxss5IqaSJkJAuTGwC7-3og59Ft/view ; proof ZIP: https://drive.google.com/file/d/17_Z4nA5r4t_ZcTgelyn8EPkExTTLNSf0/view . Do not rewrite either.

## 1. Primary development task: integrated original-local batch recovery

Inspect existing `Tools/UltraGem/factory_local_authoring.py`, `campaign_generation_workbench.py`, current tests, `LevelDraftStudioWindow.cs`, `CampaignGenerationWorkbenchWindow.cs`, the editor asmdef and sample adapter BEFORE editing.

Extend the existing original Factory-local generator, **not donor result/derived goal remapping**, to support:
- Project-root-only unique run folders, explicit start + bounded configuration, stop request, progress status, durable cancellation and **resume in same run**, preserving previously saved candidate bytes;
- Atomic and bounded checkpoint with configuration, source revision, profile, seed, completed attempts, exact raw file SHA; validate full event sequence, file presence/absence/hash/canonical LevelDraft schema and ownership before resume;
- Crash-safe recovery after candidate file write but before checkpoint commit; valid orphan can only be adopted by exact recomputation/hash/provenance, otherwise fail closed; reject stale version/tampered config, malicious paths, extra files and invalid YAML/JSON;
- Never silently delete/overwrite R01–R03 output, approval files, `.meta` or Unity settings. No uncontrolled temporary data. Keep existing max 50 drafts/run and max 10/profile until independently measured reason to change limits; don't launch 500 candidates or mark 500 achieved;
- deterministic rerun proves byte-identical **content manifest** for equal source/config/seed, excluding wall-clock/log fields; distinct seed must represent source-backed real structural variation, not renaming only;
- preserve exact donor/derived/original-local provenance and separation, near-duplicate screens, four prior successful donor SHA matches, no new Engine goal mapping, no fake WIN/solvability.

If impossible to add any lifecycle feature safely, record exact limitation and associated failed criterion; do not hand-wave it as covered by donor workbench's separate old checkpoint.

## 2. Unity Editor source integration and real UI proof

Extend the **existing** Campaign Generation Workbench window's Factory-local controls to offer a safe local cancellation/resume mechanism, progress, unambiguous donor vs derived vs original-local preview status, and SHA-verified selection. Avoid second disconnected GUI.

Attempt actual Unity 6000.6.5f1 C# compilation + focused EditMode tests for THIS project if the editor is available and doing so does NOT launch prohibited ADB/Android or interfere with an existing different project/editor. Do not bypass or kill another project's Unity process. If safe runtime unavailable, leave Unity compile/GUI `NOT_RUN` and document exact blocker and minimal owner-manual steps.

For a **real** interactive GUI PASS, record owner-verifiable Unity window opened, five-profile input, local Start/Stop/Resume, progress, loaded local preview, source type distinction and deliberately corrupted hash rejected. C# source scan/mock screenshots cannot count. Do NOT generate a synthetic screenshot claiming to be Unity UI.

## 3. Required tests and evidence

Write and execute focused positive and negative tests for cancel-before-start, cancel midway, resume preserving byte-identical prior outputs, fail-safe unexpected crash at each write boundary, stale hash/schema/seed/version, partial artifact, path traversal/symlink, wrong profile, stale donor source, duplicate content/near duplicate, cross-game contamination, signed/Engine/owner false-pass denial. Maintain the existing 43 R03 test coverage and entire Python suite; run exact Windows CPython 3.12.10 project-local commands.

Run measured small pilots (not 500): original 25 local sample drafts (5 each/title) and one or two distinct supported board dimension/palette settings. Record SHA, actual no-fill/underfill, every profile and timing. These remain **sample-only previews** not campaign levels. Re-check frozen R03 root-cause seeds if code touches donor/goal pipeline, ensuring no regression.

Evidence MUST include **original complete unabridged per-test runner output and exact command/env/version/source SHA**; Git diff and pre/post local git status; metadata/source hash inventory; canceled/resumed folder with manifest & negative tamper receipts; actual Unity compile/EditMode log and manual GUI evidence if executed; one CRC-tested ZIP and SHA256 manifest. No one-line PASS-only test summary.

## 4. Safety, publication, and report

Use only existing local repository and unique project-local artifacts. Do NOT create clones/worktrees; do NOT touch another repo, GitHub Actions, ADB/Android Emulator, Windows Player build, R2, live remote writer, IAP/ads/production tokens, billable provider, AppData/TEMP/disk cleanup.

Protect pre-existing `ProjectSettings/ProjectSettings.asset`, `ProjectSettings/PackageManagerSettings.asset` and preview `.meta` files. Never stage or reset those owner changes. Do not blanket-clean any directory. Git push only tested safe code to `main`, no force/tag. Synchronize local `main` with `origin/main` without losing user changes. Update **only the relevant entries** in root `TASKS.md` with actual R04 results; never promote M11/M14 release or Engine.

Create **one final Codex report** in existing Level Factory `02_CODEX_LOGS` Drive folder, and **one evidence ZIP** in `05_EVIDENCE`. Give exact Git SHA, test results and log link, full B00–B12 self-assessment (not independent audit), any P0/P1/P2 blockers. Do not ask for approval after each subtask; continue through the entire cohesive fix and QA package unless an actual owner-only safety action is unavoidable.

**Core outcome:** Reliable local batch start/cancel/checkpoint/resume plus real safe Unity Studio QA if feasible; else explicit NOT_RUN for that gate. Progress in locally compatible drafts is separate from **0/500 Engine-qualified**. This handoff does not alter MATCH3_ENGINE.
