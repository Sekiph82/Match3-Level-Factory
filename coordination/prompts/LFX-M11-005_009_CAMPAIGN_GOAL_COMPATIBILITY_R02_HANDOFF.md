# LFX-M11-005 + LFX-M11-009 | R02 Goal-contract diagnosis, independent authoring and bounded five-game pilot

> **One execution handoff, not a new task or milestone.** Root `TASKS.md` remains the **only** canonical task tracker. This is the follow-up to `LFX-M11-005_009_CAMPAIGN_GENERATION_HANDOFF_V01.md`, which has already been implemented. **Do not repeat R01.**
>
> **Repo exclusively:** `Sekiph82/Match3-Level-Factory` at `C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory`. **Do not operate on MATCH3_ENGINE, Visual-UI-Factory or any game repo.** ENG-M24 is external and still BLOCKED.

## 1. Verified R01 handoff and the actual failure to solve

- Verified `main` R01 commit: `25ddbe7b255340780452c70eafd352418e0e978e`; re-read live HEAD and `TASKS.md` before starting, never roll back.
- R01 authored genuine `Tools/UltraGem/campaign_generation_workbench.py`, `campaign_generation_worker.py`, Unity Editor-only `CampaignGenerationWorkbenchWindow.cs`, tests and reproducible SHA evidence. R01 Python 18/18 focused and 233/233 full PASS on CPython 3.12.10.
- One real pinned-donor attempt per five profiles yielded **five source-backed outputs; five local compatibility rejections; zero local-review candidates and 0/500 Engine-qualified campaign levels**. Exact cause: `factory_pipeline.py` puts ranked goal `ultragem.goal.{recommendation.goalId}` in the LevelDraft, while `profile_compatibility.py` currently accepts only `sample.score` and `sample.glass`. It explicitly marks `ultragem.goal.score` as `GOAL_SEMANTICS_UNVERIFIED`.
- The source tests used 6×6, 3 colors, `runs=1`, `maxMoves=2`, and seeds 21000/121000/221000/321000/421000. Cross-profile structural duplicates existed (two structural signatures across five). **This was a pilot only, not a product campaign.**
- Unity Editor/GUI/compilation was NOT_RUN; no public screenshots or real UI proof.
- R01 report: https://drive.google.com/file/d/1Lw7GruP9d7hPIcYy9Uip16n4dUBBdAHQ/view ; evidence: https://drive.google.com/file/d/1s1nfmzEnsPibDxW7F-SVwJ83Fb9TFbES/view .
- Preserve real original donor records, original goal semantics, all old checkpoints/hashes, preexisting Unity settings and `.meta` changes. ENG-M24 production gameplay validation remains BLOCKED, no M11/M14 official PASS.

## 2. Goal: remove ambiguity, NOT the fail-closed safety barrier

**Do not change `SUPPORTED_GOALS` to accept `ultragem.goal.*` blindly. Do not silently rename an UltraGem score/goal into `sample.score`/`sample.glass` or fabricate a goal equivalence, score-to-WIN mapping, difficulty label, solvability or move path.** A matching string is not evidence of matching gameplay rules.

Inspect the **real** pinned donor ranking goal vocabulary and source behavior, alongside:
- `Tools/UltraGem/factory_pipeline.py`, `leveldraft.py`, `profile_compatibility.py`, `genlevels.py`, `scoregames.py`;
- `campaign_generation_workbench.py`, `campaign_generation_worker.py`, `candidate_diversity.py`, `reference_features.py`, `tutorial_templates.py`, `m11_milestone_qualification.py`;
- Unity `CampaignGenerationWorkbenchWindow.cs`, `LevelDraftStudioWindow.cs`, existing Editor assembly and tests.

Produce a **source-grounded exact goal-vocabulary diagnosis** for actual donor outputs: each `ultragem.goal.<id>` source value, its verified donor meaning (if provable), builder local `SUPPORTED_GOALS`, any independent authored sample goal schemas, clear `IDENTIFIER_ONLY` vs `SEMANTICS_VERIFIED` states, and which capabilities are blocked. Provide per-goal reason and evidence SHA/provenance, not a made-up universal mapping.

## 3. Two separate honest candidate tracks

**Track A: original source-backed donor drafts** must remain byte-for-byte/meaning-preserving and flagged `REFERENCE_ONLY_UNVERIFIED` / `REJECTED_PROFILE_COMPATIBILITY` whenever goals or special/lock/obstacle semantics are unresolved. Preserve `sourceGenerated=true`, original source SHA, ranking and goal IDs as raw evidence. Do not edit accepted old evidence or rewrite existing checkpoints.

**Track B: clearly labelled independent *Factory-authored* LOCAL PREVIEW goal alternatives**, only if the exact local contract can be grounded in already present owner-original `LevelDraft` schema/template logic, and only via **new, separate derived artifact(s)** with provenance chain `sourceDraftSha256 → authoredLocalGoalProposalSha256`, explicit goal authoring rationale, and strict compatibility+roundtrip checks. The donor never authored the alternative goal and its difficulty ranking must not be inherited for it. Must be clearly displayed as `LOCALLY_AUTHORED_PREVIEW_ONLY`, `ORIGINAL_DONOR_GOAL_UNRESOLVED`, `ENGINE_NOT_RUN`; never claim it is an official target or canonical goal.

If the local goal interpretation is also not verifiable, **do not generate Track B**, return `BLOCKED_NO_PROVABLE_GOAL_CONTRACT` with a precise source explanation. Failing closed is required. Do not bypass screening merely to raise counters.

Maintain **distinct counters**: donor attempt, donor original output, unresolved goal rejection, derived local authoring proposal (if any), locally authorable unique drafts, owner-reviewed/approved, and Engine-qualified campaign (still 0). No mutation/rename-only samples counted as new gameplay. No silent widening of mechanic/color/obstacle support. Near-duplicates remain screened across seeds and game profiles.

## 4. Make the existing workbench usable and verify it

- Add the smallest needed **integrated R02** source/Editor UI improvements, not another preflight/status-only module. Show original goals alongside any separately authored local preview proposal, exact rejection codes, filters for source/derived, unique/near-duplicate groups, provenance SHA and explicit clickable review path where existing Studio APIs permit.
- Exercise actual R01 stop/resume + hash check with any new fields. Guard older R01 checkpoints and version migration (never overwrite or reinterpret them silently). Maintain unique project-local output folders, strict deterministic SHA manifests and complete real source evidence.
- Identify missing compile or API integration risks in new C# workbench window, avoid guessing Unity internal Editor API. Run safe Unity EditMode compilation/tests **only if compatible with owner's strict no-ADB/no-Android policy**. If this cannot be done without implicit prohibited tooling, keep `Unity/GUI: NOT_RUN` and provide a reproducible owner-only check; do not claim GUI PASS from source scans.
- Preserve existing Python R01 tests and increase real negative coverage: unmapped donor goal, malicious/unknown goal, conflicting targetCount, source-to-derived provenance, no inherited donor difficulty/Win, wrong profile, duplicate/near-duplicate across batches, cancellation/resume/tampered checkpoint, and empty/underfilled result. No result field may claim Engine WIN, certified difficulty, five bots or official acceptance.

## 5. A measured real donor pilot before any scale-up

First run small **bounded** real UltraGem experiments: compare several *documented* distinct configuration/seed variants per profile, check original goal vocabulary, actual structural diversity and cost. Do not launch 500 full candidate attempts blindly. Use measured timeouts and global budgets. If and only if the source semantics and local authoring path are supported, scale to a limited reviewed batch (e.g. 5–10/profile) before proposing 100/profile. Honest `0` counts are acceptable.

For all candidates, record original and derived statuses separately and persist generated draft bytes/hashes, exact donor revision, seed, board shape/goal family, per-profile duplicate/near-duplicate reason, benchmark runtime and stop reasons. **0/500 Engine-qualified campaign levels stays unchanged** unless a separate actually accepted Engine execution occurs, which is OUT OF SCOPE here.

## 6. Testing and delivery

- Python CPython 3.12.10 focused R02 and full regression; real donor smoke with exact seeds/config, SHA manifest verified and no harmful side effects. Unity source/Editor tests only under the restrictions above.
- No clone/worktree outside the named existing project, no Github Actions, no ADB, Android Emulator, Windows Player builds, real R2/online writes, store/IAP/ad actions, disk cleanup, appdata/TEMP sweeps or secret material.
- Preserve uncommitted `ProjectSettings/ProjectSettings.asset`, `ProjectSettings/PackageManagerSettings.asset`, all user preview `.meta`, previous Artifacts and other owner files. No force push. Fast-forward `main` only; after normal push synchronize and verify the main local checkout against `origin/main`, retaining unrelated local modifications.
- Only root `TASKS.md` is the task authority; update existing **LFX-M11-005 and LFX-M11-009** with the R02 outcomes. Other milestone states unchanged absent independently verified acceptance.
- Put one redacted complete evidence bundle under the existing project `05_EVIDENCE` Drive folder, and one final Codex report in `02_CODEX_LOGS`. Include original vs separately-authored counts, exact SHA evidence, real tests, changes, blocker IDs and remaining 100/profile shortfall.
- Do not report task-by-task. Treat R02 as **one cohesive work package**, fixing source/Editor/test integration together where safe. Only stop on a genuine unsolvable authority, safety or compatibility block.

**R02 closure:** trustworthy diagnosis of all donor goal rejections + materially more usable integrated Factory review workbench; if possible, **explicitly separated** local-authoring proposals with real tests, never fabricated goal mappings or 500 campaign successes. M11 and Engine remain BLOCKED until independently accepted.
