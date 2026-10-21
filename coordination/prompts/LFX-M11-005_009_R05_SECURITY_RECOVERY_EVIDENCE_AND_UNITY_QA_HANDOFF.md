# LFX-M11-005 + LFX-M11-009 R05 | Close strict R04 audit gaps without restarting source work

**Single, cohesive Codex handoff, NOT a new milestone.** Work ONLY in `Sekiph82/Match3-Level-Factory` using the owner's **existing** checkout `C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory`. **ONLY root `TASKS.md` is the canonical task tracker.** Other repos, including MATCH3_ENGINE and Visual UI Factory, are out of scope.

**MANDATORY PRE-FROZEN R05 INDEPENDENT AUDIT V01:**
https://github.com/Sekiph82/Match3-Level-Factory/blob/main/coordination/audits/LFX-M11-005_009_R05_FROZEN_INDEPENDENT_AUDIT_V01.md

**Actual R04 independent audit (NOT MET):**
https://github.com/Sekiph82/Match3-Level-Factory/blob/main/coordination/audits/LFX-M11-005_009_R04_INDEPENDENT_AUDIT_20261021_V01.md

Freeze/verify R05 C00–C14 criteria **before** code or execution; don't change them after receiving results. Provide code/log/evidence for EVERY criterion. Short owner reporting, one consolidated delivery, do not stop at each minor subtask.

## 0. Baseline to KEEP, never repeat/restart

R04 source and tracker implementation SHA: `09615b733fb3f3373567bccc67db8285c02be4e6`. R04 evidence ZIP:
https://drive.google.com/file/d/1UjZErB1GwlPvL9ifjq3Mkk_-btlW-TNv/view

R04 facts independently checked: actual 58-entry ZIP, 57/57 complete manifest SHA+size, CRC PASS, real 10/10 authentic PNGs with matching persisted draft JSON/canonical SHA plus one contact sheet, full Windows Python 269 tests (268 PASS, 1 SKIP; 109.847 sec), focused 19 (18 PASS, 1 SKIP); earlier real `WinError 5` failure retained, with bounded atomic replace retry source fix. Two 5-profile authoring configurations (6×6/3-color, 8×8/4-color) are sample-only board previews, **not gameplay**.

Pre-frozen R04 V02 strict verdict: **6 PASS, 2 FAIL, 3 BLOCKED, 3 NOT_RUN**, overall **INDEPENDENT_NOT_MET**. Exactly avoid restarting R01–R04, adding another preflight-only module, regenerating ten PNGs without reason, making a second workbench UI, or artificially producing 500 layouts. Focus on the concrete holes.

## 1. P1, R04 B03 FAIL: separate and truly execute security tests

Inspect `Tools/UltraGem/factory_local_authoring.py`, `Tools/UltraGem/tests/test_factory_local_recovery_visual.py`, `test_factory_local_authoring.py`, `factory_local_preview.py` and the actual R04 failed+final logs.

The current `test_stale_source_partial_path_traversal_and_symlink_are_rejected` combines *different requirements* in one unit test. On Windows, inability to create the symlink means `self.skipTest` marks **the whole test SKIP**, including the earlier stale source, partial-file and traversal checks.

- Refactor into genuinely independent test methods with their own PASS/FAIL/SKIP: stale source revision, partial artifact, path traversal, symlink directory, absolute/symlink parent, stale checkpoint/config, foreign profile/seed, extra file.
- Real Windows symlink test may be **SKIP only for its own test** when the OS denies symlink creation. If OS privileges are missing, do **not** change OS Developer Mode, privilege settings or permissions behind the owner's back. Add a separately labelled injected `Path.is_symlink` boundary unit test for fail-closed business logic; **mock PASS is NOT real Windows symlink PASS**. State it as an external OS permission limitation until an authorized real test is possible.
- Add deterministic fault injections to atomic filesystem boundaries: Windows `PermissionError` WinError 5/32 transient retries, terminal repeated failure, checkpoint/manifest crash windows, interruption before candidate write, after artifact-before-checkpoint, after checkpoint-before-manifest, exact orphan restore, corrupt/hash-different orphan rejection. Test that neither source artifact nor prior checkpoint can be overwritten on terminal error and no non-atomic fallback runs.
- Ensure R04 genuine intermittent `WinError 5` original traceback remains preserved as negative evidence and fix remains proved by actual tests. Avoid broad catch-alls that convert errors to `PASS`. Keep all test runs fully bounded in unique project-local folders and retain trace outputs.

## 2. P1, R04 B11 FAIL: preserve real cancel/resume/crash run evidence

R04 ZIP had completed `cli-smoke` and two pilot runs but **no standalone preserved CANCELLED→RESUMED or controlled CRASH→RECOVERED raw run folders**. In-memory or temporary `unittest` test outputs are insufficient for strict owner audit.

- Using the existing R04 CLI/session API, create **a unique project-local evidence run set** with a moderately sized real local batch (e.g. 3–5 per profile bounded; minimum one profile with >=3 candidates so mid-cancel visible). Save the actual initial config, source SHA, pre-cancel checkpoint, first candidate JSON, `CANCELLED` checkpoint/event/progress, resume command and completed checkpoint, original draft raw + canonical SHA, final output manifest, and comparison with a separate uninterrupted same-config run. Record a command ledger with timestamps, every status and SHA. These should be **real original Factory-local sample boards**, not mock data or donor games.
- Separately generate a deliberate crash **after draft file is created but before the checkpoint write** by the built-in controlled fault injection, archive pre-crash checkpoint + orphan bytes + traceback, resume/recovery checkpoint/event `CANDIDATE_RECOVERED`; include deliberate altered orphan and stale checkpoint **negative runs** showing explicit failure with original bytes unchanged.
- Persist these actual run states into one new dedicated R05 project-local evidence directory before assembling the ZIP; use source hash manifests and ZIP CRC verification, not a text assertion `2/2 PASSED`.
- NEVER rewrite or clean the R01–R04 `Artifacts` evidence or owner's existing files. Do not scan/delete unrelated TEMP, cache, AppData, worktrees or user folders.

## 3. P2, audit provenance and donor continuity

- Capture timestamped actual pre/post `git status --porcelain=v1` and HEAD, narrow exact protected owner-local `ProjectSettings.asset`/`PackageManagerSettings.asset`/preview `.meta` SHA256 snapshots **before and after** with a clear diff. Do NOT stage, reset or auto-generate `.meta` changes. Only observer data that truly exists may be claimed; unrelated repository inspection is NOT authorized.
- Re-verify **only the six historical source-backed R02 donor seeds** and the four original successful donor draft SHA values, with exact pinned R03 donor revision/config and bounded runs IF safe. Otherwise record `NOT_RUN` and avoid an unnecessary repeat of full 500-level work. Genuine source-draft hashes must not change due to Factory-local authoring changes. Preserve old R02/R03 evidence immutable.
- Make a precise P0/P1/P2 error inventory after these checks; acknowledge where an external requirement is untestable. Do not update M11/ENG status merely because Python tests pass.

## 4. P1, R04 B06–B08 NOT_RUN: Unity Editor proof, safely or not at all

- Current Unity 6000.6.5f1 is installed, but previous R04 reported **no active Unity Editor process** and did NOT launch batchmode because automatic ADB side effects could not be safely ruled out under the owner's standing explicit ADB/Android prohibition.
- Source inspect actual `Assets/Match3Factory/Editor/CampaignGenerationWorkbenchWindow.cs`, `LevelDraftStudioWindow.cs`, assembly/test paths. Fix narrow obvious static C# bugs if provable without running prohibited processes, with tests/source evidence.
- If an **already owner-opened and specifically THIS-project Unity Editor** can be safely used, perform actual Editor compile, focused EditMode and manual Workbench UI Start/Cancel/Resume/source-vs-local/preview/SHA tamper checks. Preserve original raw Editor log, test case names, screenshots/video where genuinely captured and full title/seed/path provenance.
- **Do not launch another Unity process, batchmode, ADB, emulator, Android SDK or other-project Editor without a separately established owner-authorized safe procedure.** Never kill/change other-project Unity sessions. If no safe editor path is available, **B06-B08 remain NOT_RUN**, describe one minimally scoped owner-only manual verification recipe in final report. Do NOT manufacture Unity PASS, UI screenshots or gameplay video from Python-generated board PNGs.
- The prior **10 original board PNGs/contact sheet are ALREADY verified**: reuse stable Drive links and JSON/PNG SHA mapping. They do not substitute for Unity testing and do not need regenerating without a real data change.

## 5. Tests, no commercial release, one consolidated evidence/report

- Windows CPython 3.12.10 focused tests and entire `Tools/UltraGem/tests` regression, exact invocation/version/test-by-test `-v` raw stdout/stderr, elapsed seconds, original failures, remaining SKIPs and their precise **individual** reason. An OS symlink SKIP is acceptable to disclose but does NOT satisfy real symlink acceptance.
- Real bounded independent Factory-original batch creation; measure actual wall time for each and use canonical SHA integrity. Validate source provenance and separately keep donor originals, goal-only proposals and original Factory local assets; no rename-only duplicates counted as campaign levels.
- Revalidate actual ZIP full manifest each file SHA/size + CRC and `TASKS.md` statuses. Provide **one final R05 report** in Level Factory existing Drive `02_CODEX_LOGS` and **one evidence ZIP** in `05_EVIDENCE`. Include C00–C14 self-assessment; ChatGPT will later independently re-audit raw evidence. Upload only the final evidence, not intermediate experiments.
- Publish only safe tested changes and truthful existing **LFX-M11-005/009** `TASKS.md` updates on GitHub `main`, no new branch/worktree/reclone/force push or new milestone. Synchronize same owner-local checkout so `HEAD==origin/main`, preserving user-local dirty files.
- No GitHub Actions, ADB, emulator, Player build, R2/prod writers, fees, tokens/ads/IAP, network deployment or disk/TEMP cleaning.
- **Absolute claim firewall:** ENG-M24 is external and BLOCKED. Local preview boards are NOT canonical Engine puzzles, no five accepted bots/WIN/replay, no production difficulty certification or owner approval. `LFX-M11-005=IN_PROGRESS`, `LFX-M11-009=BLOCKED`, **0/500 Engine-qualified campaign levels** unless authoritative independent gates are actually completed elsewhere.

**R05 deliverable:** Close the concrete R04 symlink-skip grouping, explicit fault boundary tests and retained live cancel/resume/crash proof; present honest Unity status without bypassing owner safety. Avoid unnecessary milestone loops. Do not request task-by-task approval; provide one complete auditable delivery with actual source SHA and raw evidence.
