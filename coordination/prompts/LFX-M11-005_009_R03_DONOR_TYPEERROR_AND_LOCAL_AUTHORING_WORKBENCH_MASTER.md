# LFX-M11-005 + LFX-M11-009 | R03 donor TypeError repair and genuine local candidate authoring | MASTER HANDOFF

**Execution:** ONE consolidated Codex work package. **Authority:** repo-root `TASKS.md` only. This document is a handoff, NOT a second task tracker/new milestone and NOT permission to work on another repository.

**Only permitted repo:** `Sekiph82/Match3-Level-Factory`
**Only permitted local root:** `C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory`
**Verified starting GitHub main (2026-10-21):** `313b7410a5329df22f277c775a69ae2e01a5b269`. Re-read live HEAD and `TASKS.md` before operations and fast-forward only if safe. No force push, no new clone/worktree.

## A. R02 accepted source baseline: do not restart

R01 and R02 already built:
- seeded bounded donor `campaign_generation_workbench.py` + isolated subprocess worker, JSON/SHA artifacts, cancel/resume, duplicate comparison, Editor-only `CampaignGenerationWorkbenchWindow.cs`;
- `campaign_goal_contract.py` pinned donor vocabulary diagnosis and **separate** Factory-authored `sample.score` preview *proposals*. Donor originals are unchanged and no UltraGem->Factory/Engine goal semantics mapping was claimed;
- 34/34 focused and 249/249 full Python tests PASS on owner's Windows CPython 3.12.10, **historical results only**. Unity EditMode, GUI and build **NOT_RUN**.

R02 actual donor pilot: 5 profiles × 2 attempts, seed `510000 + profileIndex*100000 + attemptIndex`, 6×6, three colors, two policy runs, 12 moves, 60 s donor timeout, 0.95 near-duplicate threshold: **10 attempts, 4 donor outputs, 6 failed donor subprocess attempts** with exact error `TypeError: '<' not supported between instances of 'str' and 'NoneType'`. Observed donor target identifiers: `ultragem.goal.combo_55`, `ultragem.goal.nzapper` and `ultragem.score` twice (unranked placeholder). Four separately authored local score-goal alternatives failed `SAMPLE_GEM_BINDING_REQUIRED`, `SAMPLE_CELL_MECHANIC_UNSUPPORTED` and/or profile capability checks. **0 locally authorable unique, 0/500 actual Engine-qualified campaign levels, no owner approvals.**

R02 report: https://drive.google.com/file/d/1KJRbbhl1N38DAkmtCsauxPjsAdHr34-Q/view
R02 proof: https://drive.google.com/file/d/1K5bPITvrzPb3jZSFc9eo2gw3xNhOx6C_/view
Prior handoff: `coordination/prompts/LFX-M11-005_009_CAMPAIGN_GOAL_COMPATIBILITY_R02_HANDOFF.md`.

## B. Fix the FIRST demonstrable problem: donor str/None TypeError

1. Reproduce **each of the six actual recorded R02 failed seed/profile/config combinations** in a bounded, isolated, project-local run with authentic Python traceback including exact file/function/line/stack and the original input provenance. Do not assume the bug is `genlevels` or `gemengine` until traceback locates it.
2. Inspect `Tools/UltraGem/scoregames.py`, `gemengine.py`, `genlevels.py`, `factory_pipeline.py` plus **already pinned** `Tools/UltraGem/upstream/**` against the preserved donor SHA `0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12`. Do not fetch, fork or modify an external repo. Document the exact Python 3.12/NumPy/SciPy compatibility or mixed-type issue *if* proven.
3. Make the **smallest semantically safe, backward-compatible adaptation inside this repo** with a deterministic explicit sort/comparison contract where supported. Do not introduce a catch-all that suppresses donor failure, invent comparator order, silently substitute `None`, alter donor statistics, obscure provenance or certify a previously failing seed as playable.
4. If the correct donor algorithm semantics cannot be established from pinned source, **leave the underlying error BLOCKED**, add actionable typed diagnostics to workbench and exact negative tests. In either case keep the original R02 failures unchanged in their historical ZIP; do not rewrite old records or checkpoints.
5. Pin before/after reference outputs/hashes for known-good seeds and new negative fixtures for the original failing seeds, regress deterministic RNG preservation, donor score/ranking results and bounded timing. State separately `DONOR_EXECUTION_FIXED` versus `GOAL_CONTRACT_RESOLVED` (one does NOT imply the other). For every subprocess failure capture a redacted traceback safely, without credentials or 2MB log dumps.

## C. Fix the SECOND real blocker: genuine locally authorable preview boards, NOT goal relabeling

The donor boards have `ultragem.color.*`/spawn/locks/specials/holes that the local `LevelDraftUnitySampleAdapter` cannot simply ingest, even when independently authored `sample.score` goals are inserted.

**Must maintain two separate source lines:**
- **DONOR ORIGINAL:** preserve exact donor generated board and goal fields, schema-valid but fail closed for unsupported gameplay semantics; donor difficulty always reference-only, NEVER a WIN.
- **ORIGINAL FACTORY-LOCAL AUTHORING:** inspect existing `LevelDraftStudioWindow.cs`, `LevelDraftUnitySampleAdapter.cs`, `GameProfileCatalog.cs`, existing original `tutorial_templates.py` and `LevelDraft` types. If those prove a usable local sample authoring contract, implement **a bounded deterministic locally authored board generator**, not a remapper for donor boards. Use only confirmed sample gem IDs/palette, active-cell and `sample.score` or verified `sample.glass` semantics, supported dimensions and target counts/turn budget. Give it **distinct** `sourceRepository/sourceKind/sourceRevision`, configuration and seed provenance. New authored boards must have meaningful structural differences (not renamed IDs/seeds/color aliases, trivial changes of score count, or copies of one fixture).
- Record exact local Studio↔SampleAdapter compatibility and strict `leveldraft.loads_strict` roundtrip/SHA; if possible exercise existing **local Unity sample adapter** in Editor tests. This is **local authoring compatibility only**, not canonical Engine gameplay.
- Explicitly handle the sample adapter's prohibition of inactive cells, locks, specials and unsupported obstacles. Do not invent support or mark any disabled mechanic as accepted. Do not copy licensed/donor level data or ship any third-party game art.
- Store independent local authored drafts in unique, project-local output paths, separate from donor samples and separate from derived-goal-only proposals; preserve old R01/R02 runs and owner approvals unchanged.
- If existing local contract cannot honestly support 100 varied drafts/profile, document measured ceiling and underfill rather than manufacturing 500 samples. **Do not create another preflight-only status file instead of a working generator.**

**Separate counters required:** donor attempts, donor successful outputs, donor failures by reason, unresolved donor-goal count, donor-to-preview goal proposals, locally authored genuine boards, locally compatible unique boards, near-duplicates/rejections, owner-reviewed, owner-approved, Engine-qualified campaign (STAYS **0/500**). No relabeled donor result qualifies as original local board.

## D. One integrated UI and human review

Extend current Unity **Editor-only** Campaign Generation Workbench, not a second disconnected UI:
- Show donor and independent Factory-original generated sets side by side, source/goal semantics explicitly separated.
- Display exact failure traceback summary and `TypeError` cause with no fake catch-all SUCCESS; visually distinguish `SOURCE_FAILED`, `LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY`, `ENGINE_NOT_RUN`.
- Configurable small-batch seed, board dimensions/goal budgets within proven local sample constraints; bounded time/work quota; cancellation/resume and SHA/tamper checks.
- Inspect generated board/goal/structure; reference only, never auto-approve, never publish or export signed game packs.
- Build on the existing Editor window and test conventions. Where Unity Editor runs can be safely conducted without launching or invoking prohibited Android/ADB or other-project processes, compile and run focused EditMode, recording exact test counts. If not safely possible, mark Unity GUI/compile **NOT_RUN**, explain concrete blocker and give owner-only reproducible steps. Source-level static checks do not constitute GUI PASS.

## E. Verification: small, real, independent, bounded

Run **one integrated R03 package**, not 10 microtasks. Mandatory tests for: six original failing seed cases; baseline good donor seed equivalence; traceback-based regression; fixed or still blocked mixed comparator; color/source proof; Original Factory-local generation genuinely distinct by structure and goals; 5-profile separation; unsupported-mask/lock/obstacle rejection; duplicate/near-duplicate screening across chunks; invalid schema; checkpoint resume/tamper; output SHA manifest; deterministic reruns; no false Engine/owner/R2 claims.

Execute the focused Python tests and the **whole** `Tools/UltraGem/tests` regression on the actual owner's Windows CPython 3.12.10 checkout. Run a measured real donor pilot **first** on the prior six failing seeds (preserving prior evidence) and a separate bounded original local-authoring pilot (e.g. 5–10/profile maximum) with exact counts per profile. Scale to 100/profile only after proven resource, source diversity and local policy feasibility; never launch 500 blind. Timeouts must be bounded and recorded.

Prior working R02 run is immutable. No donor array manipulation can turn `ultragem.goal.*` into approved Engine `sample.score`; no new canonical Engine solver, FIVE BOTS, WIN, release, data-driven user commerce/ads or Owner PASS may be claimed.

## F. Scope and delivery, owner rules

- **ONLY** `Match3-Level-Factory`. Do **not** access/code/test MATCH3_ENGINE, Visual/UI Factory or games. `ENG-M24=BLOCKED` is ONLY a dependency note.
- No new clone/worktree, no Actions, no ADB/Android emulator, no Player build, no R2/production/cloud publish, no creds, no paid cloud, no disk/AppData/TEMP cleanup. Treat Windows Git/Unity `ProjectSettings.asset`, `PackageManagerSettings.asset`, preview `.meta` and existing user files as protected; never discard/reset/commit preexisting dirty files.
- No real output beyond bounded project-local paths and explicitly approved connected Google Drive evidence. Do not create project noise via unbounded caches or backups.
- Root `TASKS.md` is the **single tracker**. Update only existing LFX-M11-005/009 and genuinely affected existing tasks with evidence; statuses reflect reality. R01/R02 work is not restarted.
- One final redacted SHA-verified report in Level Factory `02_CODEX_LOGS`, one evidence ZIP in `05_EVIDENCE`. Include code/commit SHA, test Python/Unity environment, TypeError exact root cause/status, old and new donor attempts, local original-authoring candidate counts, 500-level deficit, GUI run evidence, safety summary and blocks.
- Push safe tested code to GitHub `main` normally, fast-forward same local main checkout and verify local `HEAD == origin/main`. No tag. Do not ask for task-by-task approvals. Stop only if a genuine owner-authority or unsafe-operation blocker cannot be safely resolved.

**R03 definition of success:** prove/fix donor TypeError as far as pinned source allows, deliver functioning standalone-but-integrated *original Factory-local candidate creation and inspection* under strict sample constraints, test it genuinely, and preserve **Engine-qualified 0/500** until independently accepted Engine validation. An honest partial result with exact blockers is acceptable; an inflated score is not.
