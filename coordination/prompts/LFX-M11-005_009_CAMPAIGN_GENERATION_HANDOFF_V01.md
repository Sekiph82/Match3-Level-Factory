# LFX-M11-005 + LFX-M11-009 | Five-game campaign candidate generation | Codex handoff V01

> **Authoritative tracker: root `TASKS.md` only.** This document is a one-time execution handoff, not another task tracker, a new milestone, or evidence of completed work.
>
> **Strict scope:** ONLY `Sekiph82/Match3-Level-Factory`. Do not access, modify, clone or run tests in MATCH3_ENGINE, MATCH3-Visual-UI-Factory or any game repository. ENG-M24 is an external unaccepted dependency, not a task to perform in this handoff.

## 0. Project and verified starting point

- Repository: https://github.com/Sekiph82/Match3-Level-Factory
- Owner's sole permitted local project root:
  `C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory`
- Baseline at drafting: `ab72de3db8271526dea839835c1156b1055e5af9` on `main` (re-read live `origin/main` and root `TASKS.md` before editing; do not assume baseline remains HEAD).
- Current Python evidence at baseline: 215/215 PASS on owner's Windows CPython 3.12.10; this is historical, not a result for the new changes.
- Current accepted **real campaign** coverage: **0/500**. Existing test fixtures, donor fixtures, legacy LevelSO assets, relabeled LevelDraft JSON and synthetic tutorials must never be counted as accepted campaign levels.
- Relevant existing tasks: **LFX-M11-005** bulk test / 100-level content and **LFX-M11-009** first 100 levels / quality; treat their connected generation, dedupe, review and Studio integration as **one cohesive milestone-wide work package**, not one task at a time.
- Other LFX-M00..M14 source exists; do not reimplement, reset statuses, replay completed milestones, or create another offline preflight that merely repeats BLOCKED flags.
- ENG-M24 final SDK/accepted schema and actual Engine replay/WIN/five-bot validation are **BLOCKED**. No automatic PASS or v1.0 release.

## 1. Primary outcome

**Build real, usable, bounded, reproducible batch generation and inspection functionality inside the Level Factory** aimed at preparing *up to* 100 genuinely distinct reference LevelDraft candidates for EACH of five profiles, without fabricating gameplay authority:

`Coral_Rescue`, `Garage_Legends`, `Dino_Islands`, `The_Fractured_Realms`, `Wonder_Pop`.

The business target is 5 × 100. Count and report separately:

1. `generatedReferenceCandidates`: actual generated source-backed candidate attempts that pass strict schema and local prefilters;
2. `uniqueOwnerReviewCandidates`: distinct candidates passing defined exact/near-duplicate screens and ready for manual inspection, **not** certified playable levels;
3. `ownerApprovedCandidates`: only if explicit authentic owner decisions with traceable evidence exist, never inferred;
4. `engineQualifiedCampaignLevels`: remain **0** until actual accepted ENG-M24 SDK execution, independent bots/replay and owner acceptance occur.

Never rename input IDs or increment seeds only to hit 500. If the generator cannot produce 500 genuine eligible candidates within a bounded resource budget, report actual counts, reasons and deficits, not artificial success. A clear underfill result is correct.

## 2. Reuse the EXISTING architecture, not a new generator fork

Inspect current source/tests FIRST (do not assume implementation gaps without checking):

- `Tools/UltraGem/factory_pipeline.py`, `genlevels.py`, `scoregames.py`, `gemengine.py`, `leveldraft.py`
- `candidate_diversity.py`, `candidate_mutations.py`, `candidate_ranking.py`
- `reference_review_workflow.py`, `reference_features.py`, `reference_thresholds.py`, `reference_tuning.py`
- `profile_compatibility.py`, `seed_matrix.py`, `reference_batch_explanation.py`
- `tutorial_templates.py`, `m11_milestone_qualification.py`, `preview_pack.py`
- Unity `Assets/Match3Factory/Editor/LevelDraftStudioWindow.cs` and existing UI/preview adapters, tests and assembly boundaries.

Protect donor license/provenance and pinned upstream revision. The adapted UltraGem reference code is **not the canonical Match3 rules engine**. Do not copy unlicensed third-party content, introduce a second production gameplay resolver, or equate donor score/ranking with real difficulty/solvability.

## 3. Implement a coherent batch generator

- Add the **minimum** necessary production source and tests to invoke the existing seeded donor pipeline repeatedly with documented, bounded budgets, explicit cancellation/timeout, and a reproducible selection policy. Use safe chunking because existing functions have small batch limits (for example 16 candidate calls, 64 comparison items); do not silently raise safeguards to accommodate 500.
- Support per-profile configuration for allowed board dimensions, piece/color sets, goal families, difficulty **hypothesis** bands, hole masks, locks and obstacle coverage **only where represented by actual existing supported source contracts**. Never synthesize Engine-supported advanced mechanics on speculation.
- Support irregular boards and barriers only via legitimate existing LevelDraft/donor contract semantics; reject impossible/unrepresented configurations. If a profile cannot support a proposed dimension/shape/mechanic, record `UNSUPPORTED_OR_BLOCKED` rather than making it up.
- Generate independently seeded **source-backed** candidates while preserving each original donor seed/config/revision. No mutation or randomized visual dressing of a fixture counts as an independently generated puzzle without a source-backed generation event.
- Provenance of deterministic modifications, if any, must be separate from `sourceGenerated` and labelled `REFERENCE_MUTATION_ONLY`; source-backed and mutated counts must never silently merge.
- Candidate acceptance predicates: strict `leveldraft.validate`, canonical JSON roundtrip and SHA256; profile compatibility diagnosis; origin/donor seed evidence; exact duplicate and near-duplicate detection; active-cell/obstacle/lock coverage checks; unranked/rejected-candidate explanations. Reuse `candidate_diversity` semantics and add a scalable deterministic cross-batch catalogue index where existing 64-item helpers are insufficient.
- Similarity must ignore name/ID/seed/theme labels and superficial interchangeable color renaming, while preserving real board structure/goals/obstacles. Cross-profile clones must be counted distinctly by ownership if required for review, but not falsely claimed to be distinct **gameplay structures**.
- Avoid a loophole where changing goal-count-only or small incidental cosmetic values makes every candidate distinct. Report structural and semantic diversity statistics separately, with explicit thresholds and false-positive/false-negative limitations.
- Keep source arrays and manual approvals unchanged. Do not mutate accepted original PNGs, existing approvals, source donor files or release artifacts.

## 4. Real workbench integration

Expose batch generation and inspection **through the existing LevelDraft Studio / Factory workflow**, not just standalone tests or a status-only JSON script. Ensure at minimum:

- profile, seed range and budget selection, desired count, cancel/stop, progress, resumable partial run and refusal of unsafe parameter budgets;
- readable generated/rejected/near-duplicate queue, board preview, goal/shape/obstacle diagnostics, source and hash;
- operator selection/export of **reference-only** candidates without altering legacy autosaves; no automatic bulk approval or production pack signing;
- practical accessibility/responsive layout and consistent Unity Editor-only assembly scope.

If Unity Editor UI integration cannot be genuinely run/verified in the permitted environment, implement the source integration, run only permitted source-level tests, record `GUI_NOT_RUN` for actual interaction and provide minimal user verification steps. Do not fake screenshots or claim a manual GUI PASS.

## 5. Deterministic artifact and audit outputs

Use an explicitly dedicated, uniquely named output location **under the permitted project root**; no overwriting prior output. Ensure bounded files/memory and include SHA256 manifest, per-profile roster, configuration/version/seed, attempted/accepted/rejected records with reason codes, structural/semantic duplicate references, reference score observations, failure/timeout details, and a recovery/resume checkpoint that **revalidates** hashes and source revisions. Keep production artifacts separate from donor references, fixture datasets, test logs and candidate review assets.

No secrets, cloud writes, signed or production manifests, remote pointer switches, IAP/ads/reward grants or owner approval mutation. Existing content must not be deleted automatically.

## 6. Tests and explicit outcome gates

Work on the whole source/UI pipeline and test it as ONE batch:

- exact determinism: same inputs + pinned source result in byte-identical eligible output manifest; changed real board config produces meaningful differentiation;
- 5-profile namespaces, legitimate board/mask bounds, profile/schema rejection, no false Engine capability;
- duplicate IDs, repeated seeds, cloned boards, renamed colors, goal-only gaming, near duplicates across chunks, cancel/resume, crash-safe outputs, stale/tampered checkpoint hash, resource ceilings and invalid JSON;
- invalid/missing donor or SDK dependency returns honest `FAIL` / `BLOCKED` / `UNKNOWN`, never `WIN` or certified difficulty;
- a bounded actual donor smoke generating new reference candidates, not just renamed fixture samples; batch test with reproducible seed and measured elapsed time;
- new Python focused tests and **entire** `Tools/UltraGem/tests` regression. Only perform Unity Editor EditMode if safe and necessary, not Windows Player/Android/ADB. Distinguish `PASS`, `FAIL`, `SKIP`, `NOT_RUN`, `BLOCKED`.

Avoid full 500-candidate expensive generation without a measured small pilot and hard time/budget bounds. If 5 × 100 can safely be produced, retain them in evidence as **source-backed reference candidates only**, never as 500 Engine-qualified campaign levels.

## 7. Scope, storage and Git hygiene (OWNER RULE)

- **ONLY** this project's local root for code/build/test/output. No separate clones, detached worktrees, persistent TEMP/AppData artifacts or another repository. If a platform tool unavoidably generates external temporary files, do not leave project work there; follow owner cleanup restrictions and **never delete other projects' or pre-existing user files**.
- Do NOT work on MATCH3_ENGINE, any games or Visual-UI-Factory. Do NOT use ADB, Android Emulator, Windows Player build, GitHub Actions, R2 publication, production credentials, billable providers or disk cleanup.
- Preserve existing Unity `ProjectSettings` changes and preview `.meta` files as owner-local dirty state unless explicitly reviewed/authorized; avoid resetting, staging or deleting them.
- Read Git status before and after. Fast-forward only; do not rewrite history or force push. After successful push to `main`, synchronize the **main local project folder** with `origin/main` and verify matching HEAD and working-tree contents, preserving unrelated local changes.
- **Only root `TASKS.md` controls milestones and tasks.** Update existing LFX-M11-005/009 status with real results only. Never mark official M11/M14, ENG-M24, production or Factory v1.0 PASS without accepted authority.

## 8. Delivery, no task-by-task interruptions

Implement the full coherent campaign-generation capability, fix errors, run permitted tests and review one final evidence package before reporting. Do not stop to report each subtask or request repetitive approval. Ask only if absolutely blocked by a necessary owner-only action.

Publish safe code, tests and `TASKS.md` updates to GitHub `main`. Upload one redacted SHA-verified evidence bundle to the existing Level Factory `05_EVIDENCE` Drive folder, and one final consolidated Codex report to `02_CODEX_LOGS`. Include source/push SHA, tested Python/Unity versions, generated versus unique/approved/Engine-qualified **separate counts**, genuine run timings/costs, failures, unchanged owner-local paths and outstanding blockers.

**Definition of done for this handoff:** working candidate-generation flow and reproducible saved reference-review candidates with test evidence, or a precise `BLOCKED` report documenting the actual source limitation; never a fabricated 500/500 or another preflight-only milestone with no generator.
