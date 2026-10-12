# Match3-Level-Factory | MASTER TASKS.md

> Created 2026-10-12. Empty repository bootstrap. All tasks `PLANNED`, zero audited. Single root source of truth.

## Mission and non-negotiable architecture
- Standalone 5-game level **editor + generator + solver + difficulty QA + publisher**. Depends on the **MATCH3_ENGINE exact runtime rules**, never forks or approximates them.
- Five titles: Coral_Rescue, Garage_Legends, Dino_Islands, The_Fractured_Realms, Wonder_Pop; same serialized level schema, progression contract and runtime patch protocol, separate levels/art/content namespaces.
- Unity installed Editor `6000.6.5f1`. Engine and Factory v1.0 must PASS before themed game implementation. Factory planning/CLI schema tasks may overlap engine only after source contract stabilized.
- OTA = levels/data/licensed asset bundles, not C# or executable hot-code. Downloads before gameplay with verified manifest, offline cache and rollback.
- Never use unlicensed `daltonbr/Match3` code/images: three early level mechanics are references, independently recreated with source attribution/rights review.

## Coordination contract
- GitHub holds implementation source, tests and **only root TASKS.md** for lifecycle. All prompts, Codex logs, audit criteria/results, release evidence and screenshots are exclusively Google Drive.
- Project Drive: https://drive.google.com/drive/folders/1CTXf6G7PU1p_MVLMBD016jSPkZ0EuOqQ
- Paths: `01_PROMPTS` / `02_CODEX_LOGS` / `03_AUDIT_CRITERIA` / `04_AUDIT_RESULTS` / `05_EVIDENCE` / `06_RELEASES`.
- ChatGPT authors implementation prompts and performs independent audits/status edits. Codex implements/reports; Codex does not mutate TASKS.md or claim PASS.
- Codex fetches and safely synchronizes main before each task, preserves owner-local/untracked files, avoids hard reset, deletions and force push.
- States: PLANNED, IN_PROGRESS, READY_FOR_AUDIT, FAIL/BLOCKED, PASS/CLOSED. Log must include actual SHA, commands/results, elapsed time, seed/engine version, Drive evidence paths; do not invent tests.

## Gates
- Exact Engine parity, deterministic replay and graded uncertainty: 'failed search' is not proof UNSOLVED. Every auto-generated level must be engine-compatible and verified before publication.
- Owner approval required for production remote release and destructive operations. R2 secrets must never go into Git/Unity builds.
- Publish not permitted without accepted audit results and tests; each 5-game profile must pass import/export/runtime.
- **RELEASE BUILD FIREWALL:** Unit/solver/load tests and regression fixtures are GitHub test sources in dedicated test assemblies; full test run outputs, screenshots, benchmarks and evidence go to Drive. Factory CLI/editor, test DLLs, regression datasets and editor-only tools MUST NOT enter any consumer game APK/AAB/IPA or published Addressables. Only audited level JSON/manifests/allowed themed bundles ship to players. CI inspects actual game build outputs/assembly list and refuses forbidden developer/test artifacts.

## Detailed milestones

### LFX-M00 | Bootstrap, upstream parity and scope
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M00-001 Unity 6.6 editor project** `PLANNED`. **Deliverable:** Build a factory that runs on Windows without game installs and uses engine UPM dependency. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-002 Engine dependency lock** `PLANNED`. **Deliverable:** Pin exact ENGINE package SHA/version and compatibility contract. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-003 Read-only SDK evaluation** `PLANNED`. **Deliverable:** Review LibraStack core and ensure Factory calls same rules not duplicate solver. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-004 Shared schemas** `PLANNED`. **Deliverable:** Import versioned level/game profile/obstacle/special/goal definitions from engine. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-005 CLI baseline** `PLANNED`. **Deliverable:** Validate and compile level pack with deterministic exit codes. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-006 Desktop tool strategy** `PLANNED`. **Deliverable:** Compare Unity EditorWindow vs standalone UI options, choose lowest-maintenance supported workflow. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-007 Drive workflow** `PLANNED`. **Deliverable:** Prompt, Codex log, audit criteria, evidence and release structure; no coordination data committed to GitHub. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M00-008 Preflight audit** `PLANNED`. **Deliverable:** Prove factory project compiles, engine dependency exists, limits documented. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M00 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M01 | Five-game profile system
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M01-001 Game registry** `PLANNED`. **Deliverable:** Exact IDs Coral_Rescue Garage_Legends Dino_Islands The_Fractured_Realms Wonder_Pop. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-002 Profile capabilities** `PLANNED`. **Deliverable:** Each title declares piece kinds, allowed blockers, boosts, gravity and themes. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-003 Per-game content channels** `PLANNED`. **Deliverable:** Dev staging production, platform channel, locale, schema constraints. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-004 World/chapter/level identifiers** `PLANNED`. **Deliverable:** Shared naming but per-game unique namespace and stable ID. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-005 Profile versioning** `PLANNED`. **Deliverable:** Invalidate incompatible packs rather than silent fallback. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-006 Missing asset behavior** `PLANNED`. **Deliverable:** Neutral placeholder preview with unavailable themed image warning. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-007 Cross-profile import/export** `PLANNED`. **Deliverable:** Copy geometry between games only when capability check succeeds. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M01-008 Five config smoke** `PLANNED`. **Deliverable:** All game modes load without final licensed asset packs. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M01 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M02 | Visual level editor
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M02-001 Grid painting** `PLANNED`. **Deliverable:** Width height rows columns active holes layer selection drag paint undo redo. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-002 Piece placement** `PLANNED`. **Deliverable:** Static types weighted random spawn, scripted initial layout and anchors. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-003 Obstacles** `PLANNED`. **Deliverable:** Damage layers, immobilizers, spreaders, generators, collectors property sheets. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-004 Level goals** `PLANNED`. **Deliverable:** Composite goals, color counts, rescue, blockers and score threshold panel. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-005 Moves/star tuning** `PLANNED`. **Deliverable:** Moves, optional time mode, 1/2/3 star, difficulty labels, localization keys. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-006 World organization** `PLANNED`. **Deliverable:** Tree of worlds chapters levels and milestones with search/filter. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-007 Validation feedback** `PLANNED`. **Deliverable:** Inline errors, warnings and capability badges for each game. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-008 Keyboard and accessibility** `PLANNED`. **Deliverable:** Tooltips undo/redo save shortcut zoom pan high-DPI. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M02-009 Autosave and recovery** `PLANNED`. **Deliverable:** Versioned drafts, crashes restore safely with no lost edits. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M02 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M03 | Canonical serialization
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M03-001 JSON schema version 1** `PLANNED`. **Deliverable:** Explicit board mask layers targets seed random weights stars capabilities and triggers. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-002 Schema parser** `PLANNED`. **Deliverable:** Strict types ranges, field validation and informative errors. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-003 Canonical encoding** `PLANNED`. **Deliverable:** Stable key ordering SHA-256 digest and deterministic exports. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-004 Engine roundtrip** `PLANNED`. **Deliverable:** Engine can load exported fixture without data loss. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-005 Backward migrations** `PLANNED`. **Deliverable:** Migrate known old schemas with rollback and warnings. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-006 Missing capability errors** `PLANNED`. **Deliverable:** Unknown special obstacle or goal rejected before publish. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-007 Pack metadata** `PLANNED`. **Deliverable:** Game ID, release, engine min/max platform, locale and source provenance. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M03-008 Negative fixtures** `PLANNED`. **Deliverable:** Malformed JSON oversized board, duplicate IDs, invalid references, unsupported types. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M03 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M04 | Solver/replay verification
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M04-001 Authoritative gameplay simulation** `PLANNED`. **Deliverable:** Use actual engine assembly to simulate, no alternative match algorithm. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-002 Deterministic replay** `PLANNED`. **Deliverable:** Given seed actions repeated simulation produces identical hash. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-003 Legal move enumeration** `PLANNED`. **Deliverable:** Match-special-aware solver and no-move/dry-run logic. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-004 Budget control** `PLANNED`. **Deliverable:** Configurable time/iteration/memory caps and explicit UNKNOWN on timeout. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-005 Exact solvability claims** `PLANNED`. **Deliverable:** Distinguish SOLVED, PROVEN_UNSOLVABLE, UNKNOWN and INVALID. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-006 Retry protocol** `PLANNED`. **Deliverable:** Configurable attempts up to documented limit, seeded outcomes and provenance. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-007 Cascade coverage** `PLANNED`. **Deliverable:** Verify all special combos, obstacles and refill via engine fixtures. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-008 Replay acceptance** `PLANNED`. **Deliverable:** Play-level imported back into Unity and WIN checksum consistency. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M04-009 Solver evidence** `PLANNED`. **Deliverable:** Persist move trace, seed, timing, hash and engine version in report. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M04 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M05 | Difficulty analyzer
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M05-001 Feature extraction** `PLANNED`. **Deliverable:** Board cells, piece variety, blockers HP, targets, goal pressure, move count. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-002 Multi-seed estimate** `PLANNED`. **Deliverable:** Simulate different seeded runs and uncertainty interval. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-003 Success rate metrics** `PLANNED`. **Deliverable:** Distribution of completion per seed and allowed move budget. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-004 Game profile calibration** `PLANNED`. **Deliverable:** Same difficulty schema but age-aware weighting and goals. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-005 Very easy/expert tiers** `PLANNED`. **Deliverable:** Configurable distribution thresholds and named tuning inputs. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-006 Bias tests** `PLANNED`. **Deliverable:** Avoid scoring from just raw size or blocker count. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-007 Evidence dashboards** `PLANNED`. **Deliverable:** Histograms/CSV and compact explanation per level. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M05-008 Owner controls** `PLANNED`. **Deliverable:** Manual override with explicit rationale and trace, not hidden mutation. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M05 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M06 | Automatic level generation
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M06-001 Parametric generator** `PLANNED`. **Deliverable:** Variable dimensions, holes, blockers, goals, seeded pieces, legal move presence. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-002 First 3 tutorial templates** `PLANNED`. **Deliverable:** Recreate Daltonbr intentions lawfully; very easy stepping and no copy assets. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-003 Mutation system** `PLANNED`. **Deliverable:** Controlled variants from approved source level and provenance. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-004 Hard constraints** `PLANNED`. **Deliverable:** Respect exact game capabilities, piece count and board schema. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-005 Goal feasibility filter** `PLANNED`. **Deliverable:** Reject impossible targets and guaranteed dead ends. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-006 Simulated anneal/search** `PLANNED`. **Deliverable:** Optimize target difficulty using bounded compute. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-007 Diversity checking** `PLANNED`. **Deliverable:** Deduplicate board signatures and avoid near-identical releases. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-008 Factory candidate ranking** `PLANNED`. **Deliverable:** Composite fun/difficulty/risk score with reasons. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M06-009 Human approval gate** `PLANNED`. **Deliverable:** Generated != published; owner review before release. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M06 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M07 | QA and regression
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M07-001 Unit schema suite** `PLANNED`. **Deliverable:** Valid and invalid pack behaviors with golden hashes. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-002 Cross-game parity** `PLANNED`. **Deliverable:** All five profiles share same board engine and update contract. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-003 Repeated stochastic tests** `PLANNED`. **Deliverable:** Distribution across seeds and fail/unknown classification. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-004 Engine upgrade regression** `PLANNED`. **Deliverable:** Revalidate all packs on new engine releases. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-005 Build pipeline** `PLANNED`. **Deliverable:** CI lint, compile, run, export preview, verify provenance and guarantee consumer builds exclude Factory editor/test binaries, fixtures, diagnostics and evidence. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-006 Performance baseline** `PLANNED`. **Deliverable:** Time and memory under fixed CPU budget, report outliers. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-007 Negative-path QA** `PLANNED`. **Deliverable:** Corrupt configs, conflicting goals, unsupported mechanics, batch cancellation. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M07-008 Evidenced audit** `PLANNED`. **Deliverable:** Reproducible commands and results available in Drive. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M07 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M08 | Theme preview and asset workflow
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M08-001 Theme pack contract** `PLANNED`. **Deliverable:** Preview-only sprite/background/effect bindings, separate rights metadata. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-002 Coral preview** `PLANNED`. **Deliverable:** Underwater palette and placeholders before owner-approved original art. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-003 Garage preview** `PLANNED`. **Deliverable:** Tools and car parts as replaceable art bindings. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-004 Dino preview** `PLANNED`. **Deliverable:** Eggs/dinosaur/habitat palette without changing rule engine. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-005 Fantasy preview** `PLANNED`. **Deliverable:** Distinct energy/realm pieces and creatures via skins. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-006 Wonder preview** `PLANNED`. **Deliverable:** Age appropriate accessible shapes and soft animation. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-007 Preview simulator** `PLANNED`. **Deliverable:** Observe cascades special combos, obstacles, goals before publishing. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-008 Asset provenance** `PLANNED`. **Deliverable:** Do not import unlicensed Daltonbr assets, fonts or sounds. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M08-009 No art in core** `PLANNED`. **Deliverable:** Changing theme doesn't alter physics, RNG or difficulty outcome. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M08 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M09 | Pack release builder
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M09-001 Immutable level packs** `PLANNED`. **Deliverable:** Group world/chapter/level JSON and optional assets by game and channel. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-002 Version & manifest** `PLANNED`. **Deliverable:** Signed SHA-256 release, per-file hashes, schema min/max, engine capability bounds. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-003 Incremental diff** `PLANNED`. **Deliverable:** Changed files only and cache-safe immutable object names. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-004 Atomic release pointer** `PLANNED`. **Deliverable:** Publish staged payload, verify, switch channel manifest after all checks. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-005 Rollback metadata** `PLANNED`. **Deliverable:** Explicit previous accepted release, no mutable in-place corruption. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-006 Platform separation** `PLANNED`. **Deliverable:** Android/iOS/desktop asset bundle requirements and localization. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-007 Conflicts and locks** `PLANNED`. **Deliverable:** Concurrent publisher cannot overwrite approved release. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M09-008 Provenance and audit** `PLANNED`. **Deliverable:** Export approver, commit hash, engine version, level IDs and signed release record. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M09 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M10 | Cloudflare R2 publishing
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M10-001 Bucket/path topology** `PLANNED`. **Deliverable:** Five game roots, dev/staging/prod, platform, level/media separation. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-002 Read-only client access** `PLANNED`. **Deliverable:** Signed manifests and controlled public/cdn read; no R2 writer in APK/IPA. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-003 Writer auth** `PLANNED`. **Deliverable:** CI secrets/short-lived credentials outside Git and client build. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-004 Upload staging** `PLANNED`. **Deliverable:** Hash-check R2 objects and metadata before promotion. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-005 Canary release** `PLANNED`. **Deliverable:** Small staged audience path with rollback switch. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-006 Download smoke** `PLANNED`. **Deliverable:** Engine prelaunch client reads released level packs and offline fallback. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-007 Operations checklist** `PLANNED`. **Deliverable:** Emergency rollback, expired key rotation, owner approval. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M10-008 No silent prod write** `PLANNED`. **Deliverable:** Factory publish needs authorized channel, trace and preview. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M10 exit:** all subtasks PASS, no blocker, owner approval where needed.

### LFX-M11 | Release v1.0 and five titles qualification
**State: PLANNED; closure only after independent PASS and reproducible Drive evidence.**

- [ ] **LFX-M11-001 Factory clean install** `PLANNED`. **Deliverable:** Fresh Windows Unity 6.6 project and CLI setup instructions. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-002 Cross-title smoke** `PLANNED`. **Deliverable:** Each of five profiles editor→simulator→pack→runtime→WIN. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-003 Roundtrip versioning** `PLANNED`. **Deliverable:** Export+import preserves canonical hash and accepted outcomes. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-004 Remote patch E2E** `PLANNED`. **Deliverable:** New/changed level downloaded before play, bad update falls back. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-005 Bulk test** `PLANNED`. **Deliverable:** Representative 100-level packs and seed budget profile. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-006 Legal review** `PLANNED`. **Deliverable:** SDK MIT, third-party art and Unity build rights verification. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-007 Independent audit** `PLANNED`. **Deliverable:** No hard blocker; consumer build exclusion tests for Factory/test components passed; owner greenlight, timestamped evidence and rollback plan. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
- [ ] **LFX-M11-008 Factory v1 release** `PLANNED`. **Deliverable:** Immutable tag, docs, package and changelog before game coding. **Acceptance evidence:** linked implementation commit, exact positive/negative tests, run seed and version where applicable, Drive-based Codex log and independently reviewed audit.
**LFX-M11 exit:** all subtasks PASS, no blocker, owner approval where needed.

## Final release requirements
- Five game profiles: profile→editor→validated pack→engine runtime→deterministic replay→remote patch all pass.
- All deployment credentials remain outside repos, proofs in Drive and runtime packages signed + hashed.
- v1.0 is *not* implicitly approved by completing source code. Owner and independent audit approval are mandatory.

_Total 12 milestones, 100 numbered tasks. None yet implemented._