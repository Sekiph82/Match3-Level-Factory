# LFX-M11-005 / LFX-M11-009 R03 | Independent Source and Evidence Audit V01

**Audit date:** 2026-10-21. **Audited source commit:** `667e8b9f7f55eb3812ca502d8c44fe2ac54139f4`. **Result: R03 FULL INDEPENDENT ACCEPTANCE = NOT MET.** This is an independent assessment against the **previously frozen** `coordination/audits/LFX-M11-005_009_R03_FROZEN_AUDIT_CRITERIA_V01.md` (A00–A14); its requirements have **not** been retroactively changed. Source and artifact gains are separately accepted below. Root `TASKS.md` remains the sole task tracker and was NOT revised by this auditor. No new program tests were run on the owner's Windows host by the auditor.

**Original R03 Codex report:** https://drive.google.com/file/d/1KSUZvIxss5IqaSJkJAuTGwC7-3og59Ft/view

**Original R03 proof ZIP:** https://drive.google.com/file/d/17_Z4nA5r4t_ZcTgelyn8EPkExTTLNSf0/view

**R02 original prior ZIP:** https://drive.google.com/file/d/1K5bPITvrzPb3jZSFc9eo2gw3xNhOx6C_/view

**Implementation:** https://github.com/Sekiph82/Match3-Level-Factory/commit/667e8b9f7f55eb3812ca502d8c44fe2ac54139f4

## Independently performed checks and limitations

The auditor fetched the R03 report, source commit / changed-file list, frozen 15-gate rubric and the **actual binary R03 ZIP**. Used independent Python file-byte/JSON/hash checks on that acquired archive and also compared it with the separately acquired original R02 ZIP; inspected the actual new `factory_local_authoring.py`, TypeError sort fix, Unity Workbench C# changes and raw Python test runner logs. These are independent **artifact and source** checks, NOT execution of the owner's Windows test process or real Unity Editor.

- R03 archive **ZIP SHA256:** `fc2efb4548575ef1a0594c890b47a0a56a26c023abfa3d1f32bdf9caeadad309`.
- **110 ZIP entries**, `testzip()` CRC result **no errors**.
- Top-level `SHA256SUMS.json`: **109/109** recorded file sizes and SHA256 hashes match; no unmanifested payload files.
- Nested donor-before-fix manifest: **17/17**; donor-after-fix manifest: **23/23** files with matching hashes/sizes.
- Factory-local manifest: **25/25** saved draft JSON file SHA/sizes match; additionally all **25/25 canonical unformatted LevelDraft SHA256** values match the manifest's `draftSha256` field.
- Inspected every local draft: five per profile, all 8×8 / one layer / active cells, four sample palette colors, no locks/specials/obstacles, `sample.score=500`, `moveBudget=20`, prototype-only.
- Independent color-label-renaming-invariant **structural uniqueness: 25 different signatures among 25 local previews** (no obvious cross-profile clones). Their geometry and objectives are identical, so this is board-color-pattern variation, **not** evidence of 25 distinct objectives/mechanics or 25 solvable campaigns.
- The independent auditor's small **non-authoritative color-swap observation** found no initial straight 3-color matches and 15–36 potential color swaps per board in those 25 files; this does **not** implement/certify MATCH3_ENGINE rules, legal moves, difficulty or WIN.
- Six original R02 failed seeds `510001`, `610000`, `710000`, `810000`, `810001`, `910000` have recorded authentic call-chain tracebacks in R03 evidence: local `campaign_goal_contract.py` former line 182 `sorted(set(contentId))` mixes `None` and strings **after** donor candidate creation. The new source fix sorts with explicit None-aware ordering, retains diagnostics and does not modify the donor algorithms.
- Four historically successful donor draft hashes `510000`, `610001`, `710001`, `910001` match old and new; the 10/10 rerun and 0 fail appear in real donor-after-fix saved outputs/manifest.
- The **original R02 ZIP** has independent SHA `79faff7921c4ef2d1edb63dddccdf40d1fb55499ab76e9fcca9b5c35ed349053` and remains a separately acquired, preserved artifact. **Important provenance distinction:** R03's `donor-before-fix/` folder is a **reproduction with new traceback metadata**, not a byte-identical mirror of that R02 pilot. Original four draft SHA payloads match, but many complete R03 before-fix records are not byte-identical to the original ZIP. Do not describe reproduced logs as the original historical byte-for-byte evidence.
- Original Windows raw runner logs are **actually present** in R03 ZIP: focused postfinal **43 individual '... ok' records**, `Ran 43 tests in 19.652s`; full regression **258 individual '... ok' records**, `Ran 258 tests in 163.170s`, no skipped/failed reported. Wrappers identify CPython 3.12.10, commands, `exitCode=0`; full captured wall **167.536 seconds**. The full suite **includes** the focused tests. This is substantially stronger than the R02 summary-only evidence, but it remains **Codex-executed and auditor-reviewed**, not an independent Windows rerun.
- Real 10-donor-candidate R03 pilot wall time reported `25.482 s` with full per-seed records. Original independent local 25-preview pilot wall time reported `0.444 s`. These are **not** 500-level Engine validation throughput measures.

## Frozen 15-gate verdicts

| Gate | Verdict | Strict criterion, evidence and remaining deficiency |
|---|---|---|
| **A00** | **BLOCKED** | GitHub implementation SHA and after-push Windows git-status evidence verified; commit touches only this repo. The R03 archive supplies after-push status but not a complete independently comparable pre-run snapshot, and no authority exists to independently inspect other local repos. Owner-local preservation is credible but not proven at full frozen standard. |
| **A01** | **PASS** | Six precise historic failing seeds, bounded configuration and genuine traceback file/line provenance in `execution-logs/six-historical-donor-seed-reproduction.json` and six reproduced `donor-before-fix/failures/*.json`. |
| **A02** | **PASS** | Source diff shows explicit `None`-aware local diagnostic sort; no changes to pinned donor scoring, ranking or gameplay files. Errors not silently suppressed. |
| **A03** | **PASS** | Four matching original donor draft SHA256 values independently checked; reproduced formerly failing seed outputs evidenced. R02 original ZIP remains available separately; R03's reproduced before-fix metadata is **not** claimed byte-identical. |
| **A04** | **PASS** | Original donor draft/goal untouched; 10 separate source-hash-linked local goal proposal records remain rejected, not Engine-qualified or owner-approved. |
| **A05** | **PASS (LOCAL ONLY)** | Real independent Factory-authored original batch implemented and 25 files present; no donor board input and no invented Engine semantics. 25 locally compatible previews are **not** campaign or WIN content. |
| **A06** | **PASS (SOURCE/JSON ONLY)** | Exact local sample palette, fully active cells and bounded goal/board constraints verified from code and artifacts. Real C# sample-adapter invocation belongs to A10 and has NOT_RUN. |
| **A07** | **PASS (PILOT SCOPE)** | Donor 10 outputs / 0 errors; 10 rejected derived proposals; Factory-local 25/25 structurally unique; separate owner/Engine zero counters and local status. Broad mechanic/goal diversity is NOT established. |
| **A08** | **FAIL** | Existing donor workbench has separate cancel/resume/checkpoint tests, but **new Factory-original local authoring batch has no cancel, resume or checkpoint recovery lifecycle** (explicitly admitted in Codex's report and confirmed in `factory_local_authoring.py`). Frozen gate requires integrated pause/resume/tamper/safe partial run. Source/JSON deterministic tests are insufficient for the unimplemented local lifecycle. |
| **A09** | **PASS** | Bounded 10-attempt real donor and 25-preview locally authored pilots with separate run metadata, SHA files and reported wall-clock times. No blind 500 generation. |
| **A10** | **NOT_RUN** | No actual Unity 6000.6.5f1 Editor C# compile/EditMode or manual Campaign Workbench GUI start/progress/cancel/preview evidence. Newly changed Unity window cannot be accepted as working UI. |
| **A11** | **PASS (RAW LOG EVIDENCE)** | ZIP contains complete per-test Python 3.12.10 logs, command wrappers, 43 focused and 258 full passing case lines, 0 FAIL/ERROR/SKIP reported, elapsed times. Auditor **did not run** the owner's Windows tests independently. |
| **A12** | **PASS** | ZIP CRC; 109/109 outer, 17/17 and 23/23 donor, 25/25 local file integrity, 25/25 canonical draft hashes and source/derived references verified. Cryptographic integrity does not prove gameplay. |
| **A13** | **PASS (HONEST GATE)** | `engineStatus=BLOCKED_ENG_M24`, owner-approved and Engine-qualified counts zero, no tag/release. All 25 new items are sample-preview drafts, campaign `0/500`. |
| **A14** | **BLOCKED** | One final report and one ZIP in Drive, root TASKS actual status updates and project-only GitHub changed paths confirmed. No independent pre/post Windows-wide proof for prohibited external actions, so do not independently certify all owner-machine/no-other-repo assertions. |

**Totals:** 11 PASS (some scoped to source/artifact evidence), **1 FAIL**, **2 BLOCKED**, **1 NOT_RUN**. **Frozen full R03 result = NOT MET.**

## Defects and next acceptance requirements

- **P1-01: R03 local-authoring recovery gap (A08 FAIL).** Existing authoring batches are capped at 50/10 per profile, and write all draft files create-only, but contain no local cancel/resume/recovery checkpoint. Add deterministic, SHA-revalidated resumable sessions and negative crash/tamper/cancel tests; do not overwrite old evidence or silently increase budgets.
- **P1-02: Unity Workbench not executed (A10 NOT_RUN).** Compile actual edited `CampaignGenerationWorkbenchWindow.cs` using permitted Unity 6000.6.5f1 project and execute focused EditMode plus manual interaction with retained artifacts. If this invokes prohibited ADB/Android or conflicts with another active Unity instance, document precise reason and require owner-approved safe validation; **no fake GUI PASS**.
- **P1-03: No campaign qualification (external).** Current local authoring goal/board is a 20-move `sample.score=500` prototype, not independently verified five-bot Engine WIN, profile-specific difficulty or 100 unique campaign levels per title. Remain 0/500; no premature release.
- **P2-01: Missing verifiable before-state proof (A00/A14).** Include bounded pre/post git status, paths under owner root, original file hashes of protected uncommitted content where safe, tested source SHA and no-change evidence. External repo write absence must remain reported rather than declared independently proven where unobservable.
- **P2-02: Diversity limits (A07 scoped).** The 25 independently distinct preview boards use identical 8×8 geometry, score goal 500 and 20 moves. Different color arrangements are genuine structural variation but do **not** establish level mechanics, objective variety, difficulty, 100/profile throughput or Engine playability. Future small multi-configuration pilot and owner visual inspection required.

**Final ruling:** R03 fixes a real defect: the six failures arose in Factory diagnostic sorting, not UltraGem donor generation. It also adds an actually evidenced local board generator, improves raw test evidence and achieves 25 schema-compatible previews. This is **material progress**, not R03 full audit PASS and not M11 PASS. Maintain `LFX-M11-005=IN_PROGRESS`, `LFX-M11-009=BLOCKED`, `ENG-M24=BLOCKED`, **0/500** accepted campaign. Do not rewrite the frozen criteria or re-run already completed R01/R02 work.
