# LFX-M11-005 + LFX-M11-009 R04 | Independent Frozen Audit V01

**Audit date:** 2026-10-21. **Evaluated published code HEAD:** `09615b733fb3f3373567bccc67db8285c02be4e6`. **Strict overall verdict: FAIL / INDEPENDENT_NOT_MET.** This document applies the owner-approved, already-frozen **14-gate V02** rubric without changing its criteria: `coordination/audits/LFX-M11-005_009_R04_FROZEN_AUDIT_CRITERIA_V02.md`. Root `TASKS.md` remains the only task tracker. Do not mark milestone PASS.

**Original evidence:** [Codex R04 report](https://drive.google.com/file/d/1NywRdeKO8Ei8zYlycdUU7MX3SxXuIEim/view) ; [R04 evidence ZIP](https://drive.google.com/file/d/1UjZErB1GwlPvL9ifjq3Mkk_-btlW-TNv/view) ; [actual board contact sheet](https://drive.google.com/file/d/1yPmoBvkpyHX17PknaAyUwlCiyUorkco2/view).

## Independent examination performed

- Verified actual GitHub `main` SHA `09615b733fb3f3373567bccc67db8285c02be4e6` and R04 commits `3e2654d53dcbfaf80444769d23c0811190922f96`, `0fbcb5ae6f5a05e4d05470a8544e7573f12cbb18` (only Level Factory files; final commit updates `TASKS.md`).
- Acquired actual R04 ZIP **629,824 bytes**. Independently calculated ZIP **SHA-256 `b6c7205321eb2c40bfa3dc78e5941a361b41887d36d25c26aeff62306c748968`**, **58 entries**, **CRC no bad entry**, **57/57** source/evidence entries match every recorded size and SHA-256 in `sha256-manifest.json`, zero unlisted payload paths. These facts are **byte-integrity proof, not gameplay**.
- Verified **10/10 PNG** file SHA/size vs `visual-manifest.json`; independently verified **10/10 persisted draft raw SHA** and, using the project's `LevelDraft` canonical key/cell/goal order, **10/10 canonical draft SHA**. Five profiles, **two per profile**, 5×6x6/3 colors and 5×8x8/4 colors; real labelled contact sheet SHA matches `4188f8aa59f3f8630ef5d4cc7babee8466df1cf2040eff5db1dba0210e45f2fc`. Visual layout inspected. No actual Unity screenshot or Engine gameplay.
- Inspected source `factory_local_authoring.py`, `factory_local_preview.py`, `CampaignGenerationWorkbenchWindow.cs` and test scripts in actual ZIP; checked R04 GitHub commit paths. Existing donor/proposal file blob IDs stated unchanged; original actual R03 donor sample was not rerun here.
- Inspected **raw full `unittest -v` output**: 269 test entries = **268 ok + 1 skipped**, `Ran 269 tests in 109.847s`, 0 reported FAIL/ERROR in final. Focused test log: **18 ok + 1 skipped** in 1.849s. Crucially, the ZIP ALSO preserves an earlier real focused run **FAILED (errors=1, skipped=1)** caused by Windows `PermissionError [WinError 5]` in `os.replace` during checkpoint update. R04 added a bounded atomic-replace retry fix, after which focused/full tests pass. This initial failure must not be erased from audit history.
- Inspected skipped test `test_stale_source_partial_path_traversal_and_symlink_are_rejected`: creates a project-local symlink after its earlier assertions, and `self.skipTest(...)` makes **the entire test report SKIP**, even though preceding checks may have executed. Thus independent complete coverage of bundled symlink and earlier assertions does **not** exist. Split tests for future audit.
- Local cancel/resume/determinism/crash-injection unit tests exist and passed, but the supplied deliverable ZIP retains only **COMPLETED** persisted `cli-smoke` and two completed `pilot-*` run folders; it lacks separate retained **CANCELLED → RESUMED** and crash-recovery session input/output trace artifacts sufficient for the frozen B11 independent end-to-end evidence.
- Auditor did **not** run Windows CPython 3.12.10, start Unity Editor or interact with GUI. Local pre-state hashes and other-project side effects cannot be independently inferred from a final current-state manifest.

## Frozen V02 strict gate matrix

| Gate | Verdict | Evidence, and unmet part where applicable |
|---|---|---|
| **B00** | **BLOCKED** | GitHub source scope and final HEAD verified. `prepost-git-status.txt` begins with a narrative rather than a timestamped full starting path/hash snapshot; protected owner files only have current hashes; no independent observer of other local repositories or prohibited process history. |
| **B01** | **BLOCKED** | R03 donor/proposal source blob IDs unchanged, regression suite passed and old archives retained. Frozen criterion additionally requires R02's six seeds still give 10 outputs and old 4 matching hashes: **not freshly rerun in R04**, so not full PASS. |
| **B02** | **PASS (source + test logs)** | Original-local start, cancel request, SHA sealed checkpoint/event chain, exact orphan recomputation and resume implemented; finished donor flow unchanged. |
| **B03** | **FAIL** | One symlink/security test SKIPPED as a whole on Windows. Some earlier checks in that same test run but do not independently count as PASS. Initial Windows checkpoint atomic-replace **WinError 5** reproduced and patched, but controlled fault-injection at all demanded crash boundaries/retry exhaustion is missing. Frozen full positive/negative matrix NOT MET. |
| **B04** | **BLOCKED** | Project-local confinement and <=50/<=10 guard visible in source; outputs contained in project `Artifacts`. Before/after original bytes of protected `ProjectSettings` / `.meta` and old artifacts were not independently matched, and no independently retained unexpected-temp inventory proving zero external effects. |
| **B05** | **PASS (sample-only)** | Factory-original local authoring distinct from donor/derived and finite; 10/10 saved canonical SHA/expected sample palette profiles. No fake gameplay/owner acceptance; real C# adapter not run. |
| **B06** | **NOT_RUN (actual Editor integration)** | C# Start/Cancel/Resume/sha-checked inspection source present; no actual compilation/Editor integration execution. Do not claim this integrated GUI works from code and Python tests alone. |
| **B07** | **NOT_RUN** | Unity 6000.6.5f1 actual C# build and EditMode missing. Owner no-ADB rule preserved. |
| **B08** | **NOT_RUN** | No actual Unity workbench GUI/manual Start/Cancel/Resume/preview/tamper visual interaction. Contact-sheet PNG does not substitute. |
| **B09** | **PASS (raw runner evidence)** | Complete per-test logs, Python version/commands and original 268 passed, 1 explicitly documented skipped case; an earlier WinError failure log also preserved. Auditor has verified evidence, NOT independently rerun owner Windows. |
| **B10** | **PASS (bounded prototype)** | Two real saved configurations with five profiles each, elapsed 0.050446s and 0.058765s reported in pilot receipt, SHA checked; cancel/resume vs uninterrupted manifest equality shown in passed unit test source/log. Goals/mechanics are identical sample `sample.score` only; no Engine WIN/difficulty. |
| **B11** | **FAIL (strict retained-session evidence)** | ZIP CRC, manifests, complete raw Python test logs all PASS, but no preserved standalone cancelled/resumed/crash-recovery session artifacts and trace IDs independent of in-test transient temporary files. Frozen criterion requires actual distinct persisted cancel/resume records. |
| **B12** | **PASS (Git/Drive status)** | Published normal `main`, `TASKS.md` update and one Codex final report + ZIP. `LFX-M11-005=IN_PROGRESS`, `LFX-M11-009=BLOCKED`, `ENG-M24=BLOCKED`, `0/500` accurate. No release authorization. |
| **B13** | **PASS (actual image evidence)** | Ten labelled real original-local board PNGs + contact-sheet from saved JSON. All individual and contact PNG SHA, 10 original raw and canonical draft hashes match; direct owner-viewable Drive link provided, correctly labelled as non-Unity/non-Engine preview. |

**Totals: 6 PASS, 2 FAIL, 3 BLOCKED, 3 NOT_RUN (14 total).** By frozen owner criteria, **R04 full independent acceptance FAIL / NOT MET**; no milestone, Factory version or Engine release PASS is warranted.

## Concrete defects and remediation

**P1-01, B03 FAIL:** Unexecuted Windows symlink security scenario is bundled in a single compound test. Make stale-source, partial-file, parent-path traversal and real-symlink checks **separate tests**. Symlink requires a valid owner-permitted privilege environment; if unavailable, retain an explicit NOT_RUN for that threat and add a testable deterministic injected path/symlink probe **without representing the synthetic probe as OS-level validation**. Expand crash boundary / reproducible transient WinError 5 and permanent replace failure tests with original output preservation.

**P1-02, B11 FAIL:** Archive must retain two actual independent project-local sessions: one `CANCELLED` then `RESUMED/COMPLETED` whose original draft bytes/manifest survive; one controlled `crash_after_artifact` and a successfully adopted exact orphan. Provide before/after checkpoint/events/progress, canonical SHA manifest, per-session commands/timestamps and failures for tampered cases. Do not regenerate or overwrite historical evidence.

**P1-03, B06–B08 NOT_RUN:** Real Unity Editor 6000.6.5f1 compilation, EditMode and real operator GUI prove code+UI. Do **not** defeat explicit ADB restrictions or launch prohibited other-project Unity. If safe authority/procedure is unavailable, keep NOT_RUN and provide a short owner-only safe test checklist. PNG artwork is **PASS B13 only**.

**P2-04, B00/B04 BLOCKED:** Supply bounded timestamped original and final `git status`, complete protected-owner-file before/after SHA and file-size listing, exact source SHA, and actual external-operation audit trace where available. Do not claim omniscient proof that another repo or process was untouched.

**P2-05, B01 BLOCKED:** Reuse R03 immutable donor evidence, but for full frozen requirement run only the six historical source/output checks in a bounded, non-publishing replay if authorized and safe; otherwise report dependency as NOT_RUN. Do not repeat historical full donor campaign or redefine GOAL/WIN.

## Final acceptance

**R04 delivered functional progress**: crash-safe checkpoint and preview source, Python regression evidence, ten authentic boards and a clear contact sheet. **R04 is not independently PASS** because B03/B11 need test/evidence remediation and B06–B08 require real Unity execution. **Current commercial/campaign status remains exactly** `LFX-M11-005 IN_PROGRESS`, `LFX-M11-009 BLOCKED`, `ENG-M24 BLOCKED`, **0/500 Engine-qualified**. Do not change root TASKS from this audit alone.
