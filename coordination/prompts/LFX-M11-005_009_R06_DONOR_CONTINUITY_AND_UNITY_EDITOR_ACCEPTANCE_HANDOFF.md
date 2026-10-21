# LFX-M11-005 + LFX-M11-009 R06 | Close only the remaining donor replay and Unity acceptance gates

**One consolidated Codex execution handoff, NOT another milestone and NOT an Engine task.** In scope ONLY `Sekiph82/Match3-Level-Factory`. Owner's existing local root: `C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory`. Root `TASKS.md` is the only task authority. **Do not edit/test/clone MATCH3_ENGINE, Visual Factory or other game repos.**

**MANDATORY PRE-FROZEN R06 INDEPENDENT AUDIT V01:**
https://github.com/Sekiph82/Match3-Level-Factory/blob/main/coordination/audits/LFX-M11-005_009_R06_FROZEN_AUDIT_CRITERIA_V01.md

**Prior independent R05 audit:**
https://github.com/Sekiph82/Match3-Level-Factory/blob/main/coordination/audits/LFX-M11-005_009_R05_INDEPENDENT_AUDIT_20261021_V01.md

**Actual R05 tested commit:** `f1a70ce200376f91b8a554a695bea26a2ddddfc4`. Audit and handoff documentation may now be newer than tested code. Before editing, inspect actual remote main and root TASKS; update the **existing** local checkout via safe fast-forward, preserving uncommitted Unity files.

## R05 work is complete: do not reimplement it

Independent R05 audit of the actual 85-file/90,080-byte ZIP verified **83/83** SHA+size manifest entries, CRC PASS, real cancel/resume/crash/orphan/tamper retained JSON snapshots and SHA, tracked owner-file pre/post equality. Windows CPython 3.12.10 raw logs: **25 PASS / 1 real OS symlink SKIP focused**; **283 PASS / 1 real symlink SKIP full** (189.558 s runner). Earlier failed focused assertion and corrected rerun are both preserved. The recovery features work as sample-preview source functionality, but no Unity/Engine proof.

**Frozen R05 verdict = NOT MET** only because these four critical gates weren't completed: C01 historical donor replay; C07 real Unity Editor compile and focused EditMode; C08 real Unity Workbench GUI check; C09 bounded donor pilot. Existing OS symlink operation remains explicitly SKIP despite the passed injected boundary.

**Further issue identified by independent auditor:** `Tools/UltraGem/Artifacts/.../capture_sessions.py` archived in the R05 ZIP terminated with `EXIT_CODE=1` because its final informational summary tries `x["status"]` on a ledger event with only `event`. This does not invalidate retained 5 session archives (independently verified); however a reusable evidence capture utility must not be advertised as clean before fixing or retiring this bug. Historical log/ZIP are immutable.

## Workstream A: bounded REAL historical donor continuity

Use the already pinned `JohannesBuchner/ultragem` source in this Factory checkout and the unchanged `campaign_goal_contract.py`, `campaign_generation_workbench.py`, `factory_pipeline.py`. Reproduce EXACT R02 configuration 5 profiles × 2 attempts (6×6, 3 colors, 2 runs, 12 moves, 60s candidate timeout, threshold .95; seeds 510000/510001, 610000/610001, 710000/710001, 810000/810001, 910000/910001) **once**, using bounded project-local run folders and subprocess timeouts. Do NOT use R04/R05 original-local sample outputs as substitutes.

Provide original *donor* draft bytes, reference-only metrics, SHA, profile and seed for each trial, plus a four-row comparison against immutable R02 four successful draft SHA values (510000, 610001, 710001, 910001), which R03 said match. Distinguish donor generation from rejected local goal proposals and official Engine campaign playability. If actual donor outputs fail, retain source traceback/seed and report exact FAIL; do not rename goals or make them PASS. No 500-item campaigns or artificial certified gameplay.

## Workstream B: clean evidence capture tooling without changing old archives

The original R05 ZIP has `capture_sessions.py` under the original ignored project Artifacts folder, NOT necessarily tracked code. Inspect it in-place as read-only and make a narrow, tested, project-local replacement **only where necessary and explicitly reusable**, fixing the final print that assumes all ledger entries have `status` (a `CANCEL_REQUESTED` event does not). Add a negative regression for mixed event/status entries and ensure **actual capture process EXIT_CODE=0**; preserve old archived EXIT_CODE=1 log unchanged. Do not treat a pretty-print bug as a recovery-engine failure.

If no new runtime capture is needed, a tiny reusable verification/export script with identical meaningful status accounting and an executed smoke is acceptable. No huge new framework, no duplicate task tracker, no disk-cleanup.

## Workstream C: actual Unity Editor verification, only if permitted and safe

Owner explicitly forbids ADB, Android Emulator, Android builds and extra/paid workloads. Unity **desktop Editor** does not automatically confer permission to run any Android/ADB command.

1. Determine from **process metadata only**, without launching new software or changing project settings, whether owner has already opened Unity 6000.6.5f1 in **this exact Level Factory project**. Do not hijack another running Unity project or kill an existing instance.
2. If the correct project Editor is owner-opened and an entirely desktop-only verification path is safe, perform **actual C# compile and focused Editor EditMode** via legitimate Editor GUI/Test Runner, then run a small **real** Campaign Workbench operator workflow: start local 1–2 previews/profile, progress, cancel/resume, original/derived/Factory-local separation, select board preview, tamper SHA in a **new disposable test run only**, observe refusal, retain genuine screenshots/raw Editor/Test Runner logs. NEVER label a Python-generated preview as a Unity screenshot.
3. If no owner-opened Editor exists or an operation might launch ADB, **STOP THIS WORKSTREAM ONLY** and mark `UNITY_EDITOR_NOT_RUN_OWNER_ACTION_REQUIRED`. Give the owner an exact concise checklist to manually open the **existing Level Factory project** in desktop-only mode, not another project; do NOT auto-start batchmode/editor, ADB/Android SDK or Unity Hub without separate permission. Continue/finish the bounded donor and evidence workstreams. Do not create another preflight-only milestone to avoid this blockage.
4. If safe Editor testing reveals a real C# bug, fix **only the confirmed problem** in this repo, add focused regression, and retest if safe. Do not touch Engine or invent gameplay solver.

The frozen R06 full independent verdict must still be **NOT MET** if Unity or genuine OS symlink criteria remain unrun. Never relax the audit after seeing the logs.

## Scope, test evidence and final delivery

- Required tests: focused changed-source unit tests + full Windows CPython 3.12.10 `Tools/UltraGem/tests`, full `unittest -v` original stdout/stderr, exact command/elapsed/python version/source SHA, no masked failure; real donor smoke logged separately, and actual Unity logs only if genuinely run. Preserve all earlier failures and archived R05 ZIP.
- Real Windows symlink test can remain isolated SKIP when OS doesn't permit; **do not** enable Developer Mode or change permissions without owner authorization. Keep separately labelled mocked boundary PASS, never fake real symlink PASS.
- No new clones/worktrees, GitHub Actions, ADB/Android, Player builds, R2 writes, production/cloud deployment, ads/IAP/credentials, third-party credit spend, arbitrary TEMP/AppData cleanup, owner-local .meta or ProjectSettings modifications. Preserve the entire existing R01–R05 history and board PNGs.
- Capture before/after timestamped git status, branch/HEAD and protected local file SHA; publish only safe tested source changes and truthful LFX-M11-005/009 entries in root `TASKS.md`, normal push to `main`, verify local `HEAD == origin/main` without clearing unrelated dirty files.
- Upload ONE final Codex report to existing Level Factory `02_CODEX_LOGS` and ONE complete CRC/SHA evidence ZIP to `05_EVIDENCE`, each with direct verified Drive URLs. Include a 13-row **D00–D12** self-assessment **not** claimed as independent ChatGPT review. Link all genuine Unity screenshots if present and exact blocker if not.
- Explicit authority guard: `LFX-M11-005=IN_PROGRESS`, `LFX-M11-009=BLOCKED`, external `ENG-M24=BLOCKED`, **0/500 Engine-qualified**. The output of R06 is an auditable donor and editor acceptance attempt, NOT a new completed milestone, WIN, playable content pack or release.

**EXECUTION RULE:** Complete Workstreams A+B together without task-by-task handoffs. Workstream C depends on safe owner-opened Unity Editor; never halt all productive work to chase an unsafe Unity launch. No needless recurrence of already closed R01–R05 code and no false PASS.
