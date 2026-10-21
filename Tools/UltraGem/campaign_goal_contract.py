"""Source-grounded donor goal diagnosis and separate local preview proposals.

This module identifies what the pinned UltraGem reference heuristics measure;
it never maps those measures to Factory or Engine goals. Its optional Track B
artifact authors an independent sample.score preview using the existing Studio
defaults. The donor draft and its original goal remain unchanged.
"""
from __future__ import annotations

import copy
import hashlib
import re
from pathlib import Path
from typing import Any

import leveldraft
from genlevels import SCORES_PREFERENCES
from profile_compatibility import diagnose_profile_compatibility
from scoregames import STAT_NAMES

ULTRAGEM_PREFIX = "ultragem.goal."
LOCAL_SCORE_TARGET = "sample.score"
LOCAL_SCORE_TARGET_COUNT = 500
LOCAL_MOVE_BUDGET = 20
LOCAL_DIFFICULTY_LABEL = "difficulty.unrated"
LOCAL_SOURCE_REPOSITORY = "Match3-Level-Factory"
LOCAL_SOURCE_REVISION = "LFX-M11-R02-local-preview-contract-v1"
LOCAL_SOURCE_KIND = "FactoryAuthoredLocalPreviewGoalAlternative"

_STAT_MEANINGS = {
    "score": "Per-step score: destroyed count plus 10 times each activated special type, as accumulated by scoregames.scoring_function.",
    "ndestroyed": "Per-step count of destroyed pieces accumulated from destroyed events.",
    "nunlocked": "Per-step sum of values carried by unlocked events.",
    "nstripe": "Per-step activation count for donor special types 2 and 3.",
    "nbomb": "Per-step activation count for donor special type 4.",
    "nzapper": "Per-step activation count for donor special type 5.",
    "combo_22": "Per-step count of donor combined events with value 22.",
    "combo_42": "Per-step count of donor combined events with value 42.",
    "combo_44": "Per-step count of donor combined events with value 44.",
    "combo_51": "Per-step count of donor combined events with value 51.",
    "combo_52": "Per-step count of donor combined events with value 52.",
    "combo_54": "Per-step count of donor combined events with value 54.",
    "combo_55": "Per-step count of donor combined events with value 55.",
}
_RANKED_IDS = tuple(name for group in SCORES_PREFERENCES for name in group)
if set(_RANKED_IDS) - set(STAT_NAMES) or set(STAT_NAMES) - set(_STAT_MEANINGS):
    raise RuntimeError("UltraGem goal vocabulary and scoring source are inconsistent")

_LOCAL_SOURCE_FILES = (
    "Tools/UltraGem/campaign_generation_workbench.py",
    "Tools/UltraGem/campaign_goal_contract.py",
    "Tools/UltraGem/factory_pipeline.py",
    "Tools/UltraGem/genlevels.py",
    "Tools/UltraGem/scoregames.py",
    "Tools/UltraGem/profile_compatibility.py",
    "Assets/Match3Factory/Editor/LevelDraftStudioWindow.cs",
    "Assets/Match3Factory/Editor/LevelDraftUnitySampleAdapter.cs",
    "Assets/Match3Factory/Core/GameProfileCatalog.cs",
    "Assets/Match3/Scripts/Match3.cs",
    "Assets/Match3/Scripts/Match3Bot.cs",
    "Assets/Match3/Scripts/LevelSO.cs",
)
_STUDIO_GEMS = frozenset({"Blue", "Green", "Orange", "Purple", "White", "Yellow"})
_GEM_IDS_PATTERN = re.compile(r'GemIds\s*=\s*\{([^}]*)\}', re.S)


def source_evidence(project_root: Path | str) -> list[dict[str, str]]:
    """Hash exact source files that ground donor and local sample meanings."""
    root = Path(project_root).resolve()
    result = []
    for relative in _LOCAL_SOURCE_FILES:
        path = root / relative
        if not path.is_file():
            raise ValueError(f"goal-contract evidence source is missing: {relative}")
        result.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return result


def _ranking_group(goal_id: str) -> int | None:
    for index, names in enumerate(SCORES_PREFERENCES, start=1):
        if goal_id in names:
            return index
    return None


def diagnose_donor_goals(goals: Any) -> dict[str, Any]:
    """Return exact donor meanings without asserting local/Engine equivalence."""
    if not isinstance(goals, list) or not goals:
        return {"status": "REJECTED_INVALID_OR_EMPTY_GOALS", "goals": [], "sourceGoals": [],
                "proposalEligible": False, "reasonCode": "INVALID_OR_EMPTY_GOALS"}

    findings = []
    for index, goal in enumerate(goals):
        if not isinstance(goal, dict):
            findings.append({"index": index, "status": "REJECTED_INVALID_GOAL_OBJECT",
                             "reasonCode": "INVALID_GOAL_OBJECT"})
            continue
        target_id = goal.get("targetId")
        target_count = goal.get("targetCount")
        base = {"index": index, "goalId": goal.get("goalId"),
                "sourceTargetId": target_id, "sourceTargetCount": target_count,
                "localTargetId": None, "localEquivalence": "NOT_ESTABLISHED",
                "engineSemantics": "BLOCKED_ENG_M24"}
        if type(target_count) is not int or target_count < 1:
            findings.append({**base, "status": "REJECTED_INVALID_TARGET_COUNT",
                             "reasonCode": "TARGET_COUNT_MUST_BE_POSITIVE_INTEGER"})
            continue
        if not isinstance(target_id, str):
            findings.append({**base, "status": "REJECTED_UNKNOWN_GOAL_IDENTIFIER",
                             "reasonCode": "GOAL_TARGET_ID_NOT_A_STRING"})
            continue
        if target_id == "ultragem.score":
            findings.append({**base, "status": "IDENTIFIER_ONLY",
                             "donorMeaning": "Unranked mapper placeholder; this exact identifier is not emitted by genlevels.rank_levels.",
                             "rankingGroup": None,
                             "targetCountMeaning": "No donor-ranked observation is attached to this placeholder.",
                             "reasonCode": "UNRANKED_MAPPER_PLACEHOLDER"})
            continue
        if target_id.startswith(ULTRAGEM_PREFIX):
            goal_id = target_id[len(ULTRAGEM_PREFIX):]
            group = _ranking_group(goal_id)
            if group is None:
                findings.append({**base, "status": "REJECTED_UNKNOWN_DONOR_GOAL",
                                 "reasonCode": "GOAL_ID_NOT_IN_PINNED_RANKING_VOCABULARY",
                                 "donorGoalId": goal_id})
                continue
            findings.append({**base, "status": "SEMANTICS_VERIFIED_DONOR_ONLY",
                             "donorGoalId": goal_id, "donorMeaning": _STAT_MEANINGS[goal_id],
                             "rankingGroup": group,
                             "targetCountMeaning": "Pinned heuristic's integer observation at its selected smart-policy step; it is not a Factory or Engine goal mapping.",
                             "difficultyHypothesisMeaning": "Reference-only ratio of random-policy upper quantile to smart-policy median, rounded to 0.05; not certified difficulty.",
                             "reasonCode": "DONOR_METRIC_IDENTIFIED_NO_LOCAL_RULE_EQUIVALENCE"})
            continue
        findings.append({**base, "status": "REJECTED_UNKNOWN_GOAL_IDENTIFIER",
                         "reasonCode": "GOAL_TARGET_NOT_IN_PINNED_DONOR_CONTRACT"})

    if len(goals) != 1:
        status, reason = "REJECTED_MULTIPLE_SOURCE_GOALS", "MULTIPLE_OR_CONFLICTING_SOURCE_GOALS_UNSUPPORTED"
    elif findings[0].get("status") not in {"SEMANTICS_VERIFIED_DONOR_ONLY", "IDENTIFIER_ONLY"}:
        status, reason = "REJECTED_UNRESOLVED_SOURCE_GOAL", findings[0].get("reasonCode")
    else:
        status, reason = "DONOR_GOAL_DIAGNOSED_LOCAL_EQUIVALENCE_UNRESOLVED", findings[0].get("reasonCode")
    return {"status": status, "reasonCode": reason, "goals": findings,
            "sourceGoals": copy.deepcopy(goals),
            "proposalEligible": len(goals) == 1 and findings[0].get("status") in {
                "SEMANTICS_VERIFIED_DONOR_ONLY", "IDENTIFIER_ONLY"}}


def _studio_gems_from_source(project_root: Path | str) -> set[str]:
    path = Path(project_root).resolve() / "Assets/Match3Factory/Editor/LevelDraftStudioWindow.cs"
    if not path.is_file():
        raise ValueError("Level Draft Studio source is required to verify its local palette")
    match = _GEM_IDS_PATTERN.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("could not read the Level Draft Studio palette declaration")
    values = set(re.findall(r'"([^"\\]+)"', match.group(1)))
    if values != set(_STUDIO_GEMS):
        raise ValueError("Level Draft Studio palette changed; local proposal contract needs review")
    return values


def diagnose_local_sample_proposal(draft: dict[str, Any], project_root: Path | str) -> dict[str, Any]:
    """Check the separate preview against present Factory sample constraints."""
    findings = []
    try:
        leveldraft.validate(draft)
    except (TypeError, ValueError) as exc:
        return {"status": "REJECTED_INVALID_LOCAL_DRAFT", "findings": [str(exc)],
                "profileCompatibility": {"localPolicyStatus": "NOT_RUN"},
                "sampleAdapterStatus": "NOT_RUN"}
    profile = diagnose_profile_compatibility(draft)
    if profile["findings"]:
        findings.extend({"code": item.get("code", "PROFILE_POLICY"),
                         "reason": item.get("capabilityId", item.get("path")),
                         "sourceValue": item.get("sourceValue")}
                        for item in profile["findings"])
    try:
        studio_gems = _studio_gems_from_source(project_root)
    except ValueError as exc:
        studio_gems = set()
        findings.append({"code": "STUDIO_PALETTE_UNVERIFIED", "reason": str(exc)})
    # A valid active sample obstacle may have no gem content. Keep that None
    # finding visible, but never compare it directly with string identifiers.
    unsupported_content = sorted(
        {cell.get("contentId") for cell in draft["cells"]
         if cell.get("active") and cell.get("contentId") not in studio_gems},
        key=lambda value: (value is not None, "" if value is None else str(value)),
    )
    if unsupported_content:
        findings.append({"code": "SAMPLE_GEM_BINDING_REQUIRED",
                         "reason": "Donor identifiers are not Level Draft Studio sample GemIds; no remapping was performed.",
                         "sourceValues": unsupported_content})
    unsupported_cells = [cell for cell in draft["cells"] if (
        not cell.get("active") or (cell.get("active") and (cell.get("locked") or cell.get("lockDurability", 0) > 0 or
        cell.get("specialId") or (cell.get("obstacleId") not in (None, "sample.glass")) or
        cell.get("obstacleDurability", 0) > (1 if cell.get("obstacleId") == "sample.glass" else 0))))]
    if unsupported_cells:
        findings.append({"code": "SAMPLE_CELL_MECHANIC_UNSUPPORTED",
                         "reason": "LevelDraftUnitySampleAdapter rejects inactive cells, locks, specials, unsupported obstacles, and unsupported durability.",
                         "cellCount": len(unsupported_cells)})
    goals = draft["goals"]
    if len(goals) != 1 or goals[0]["targetId"] != LOCAL_SCORE_TARGET:
        findings.append({"code": "LOCAL_SCORE_GOAL_REQUIRED",
                         "reason": "The preview proposal must use exactly one independently authored sample.score goal."})
    status = "LOCALLY_AUTHORABLE_PREVIEW_ONLY" if not findings else "REJECTED_LOCAL_SAMPLE_COMPATIBILITY"
    return {"status": status, "findings": findings,
            "profileCompatibility": profile,
            "sampleAdapterStatus": "COMPATIBLE_PREVIEW_SCHEMA_ONLY" if not findings else "REJECTED_OR_NOT_BOUND",
            "engineStatus": "BLOCKED_ENG_M24"}


def build_local_goal_proposal(*, source_draft: dict[str, Any], source_draft_sha256: str,
                              source_record_path: str,
                              source_repository: str, source_revision: str,
                              source_goal_diagnosis: dict[str, Any],
                              source_ranking_status: str,
                              project_root: Path | str) -> dict[str, Any] | None:
    """Author one separate default sample.score proposal, never altering source."""
    leveldraft.validate(source_draft)
    if leveldraft.sha256(source_draft) != source_draft_sha256:
        raise ValueError("source draft digest does not match canonical bytes")
    if not source_goal_diagnosis.get("proposalEligible"):
        return None

    proposal_draft = copy.deepcopy(source_draft)
    original_goals = copy.deepcopy(source_draft["goals"])
    proposal_draft.update({
        "goals": [{"goalId": "goal.primary", "targetId": LOCAL_SCORE_TARGET,
                   "targetCount": LOCAL_SCORE_TARGET_COUNT}],
        "moveBudget": LOCAL_MOVE_BUDGET,
        "difficultyLabel": LOCAL_DIFFICULTY_LABEL,
        "editorHintKey": "authoring.localPreviewOnly",
        "sourceRepository": LOCAL_SOURCE_REPOSITORY,
        "sourceRevision": LOCAL_SOURCE_REVISION,
        "sourceKind": LOCAL_SOURCE_KIND,
    })
    leveldraft.validate(proposal_draft)
    canonical = leveldraft.loads_strict(leveldraft.dumps_canonical(proposal_draft))
    proposal_sha = leveldraft.sha256(canonical)
    local_diagnostics = diagnose_local_sample_proposal(canonical, project_root)
    return {
        "proposalVersion": 1,
        "artifactKind": "FACTORY_AUTHORED_LOCAL_PREVIEW_GOAL_ALTERNATIVE",
        "artifactStatus": "LOCALLY_AUTHORED_PREVIEW_ONLY",
        "sourceGenerated": False,
        "sourceRecordPath": source_record_path,
        "sourceRepository": source_repository,
        "sourceRevision": source_revision,
        "sourceDraftSha256": source_draft_sha256,
        "authoredLocalGoalProposalSha256": proposal_sha,
        "originalDonorGoals": original_goals,
        "goalContractDiagnosis": source_goal_diagnosis,
        "authoring": {
            "goalId": "goal.primary", "targetId": LOCAL_SCORE_TARGET,
            "targetCount": LOCAL_SCORE_TARGET_COUNT,
            "moveBudget": LOCAL_MOVE_BUDGET,
            "difficultyLabel": LOCAL_DIFFICULTY_LABEL,
            "goalContractStatus": "LOCAL_SAMPLE_SCORE_RULE_VERIFIED; NO_DONOR_OR_ENGINE_EQUIVALENCE",
            "rationale": "LevelDraftStudioWindow.NewDraft uses sample.score targetCount 500, moveBudget 20, and difficulty.unrated. LevelDraftUnitySampleAdapter stores sample.score targetCount as LevelSO.targetScore; Match3.TryIsGameOver checks score >= targetScore. These are independent local sample defaults/rules; no donor targetCount, moveBudget, ranking, difficulty, or WIN result is inherited.",
            "sourceRankingStatusObservedButNotInherited": source_ranking_status,
            "donorDifficultyHypothesisInherited": False,
            "donorTargetCountInherited": False,
            "donorMoveBudgetInherited": False,
            "winClaim": False,
        },
        "localAuthoringDiagnostics": local_diagnostics,
        "engineStatus": "BLOCKED_ENG_M24",
        "engineQualified": False,
        "ownerApproved": False,
        "releaseAuthorized": False,
        "draft": canonical,
    }


def validate_local_goal_proposal(proposal: dict[str, Any], *, project_root: Path | str) -> None:
    """Fail closed on altered provenance, target semantics, or authority claims."""
    if not isinstance(proposal, dict) or proposal.get("artifactKind") != "FACTORY_AUTHORED_LOCAL_PREVIEW_GOAL_ALTERNATIVE":
        raise ValueError("not a local preview goal proposal")
    draft = proposal.get("draft")
    leveldraft.validate(draft)
    digest = leveldraft.sha256(draft)
    if digest != proposal.get("authoredLocalGoalProposalSha256"):
        raise ValueError("local proposal draft SHA-256 mismatch")
    source_sha = proposal.get("sourceDraftSha256")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha):
        raise ValueError("source draft SHA-256 is invalid")
    if not isinstance(proposal.get("sourceRecordPath"), str) or not proposal["sourceRecordPath"].startswith("candidates/"):
        raise ValueError("source candidate record path is invalid")
    if draft["sourceKind"] != LOCAL_SOURCE_KIND or draft["sourceRepository"] != LOCAL_SOURCE_REPOSITORY:
        raise ValueError("proposal draft authoring provenance is invalid")
    if draft["goals"] != [{"goalId": "goal.primary", "targetId": LOCAL_SCORE_TARGET,
                           "targetCount": LOCAL_SCORE_TARGET_COUNT}]:
        raise ValueError("proposal must use the exact separate local sample.score default")
    if proposal.get("originalDonorGoals") != proposal.get("goalContractDiagnosis", {}).get("sourceGoals"):
        raise ValueError("proposal source goal provenance is inconsistent")
    if (draft["moveBudget"] != LOCAL_MOVE_BUDGET or
            draft["difficultyLabel"] != LOCAL_DIFFICULTY_LABEL):
        raise ValueError("proposal must not inherit donor move budget or difficulty")
    authoring = proposal.get("authoring", {})
    if any(authoring.get(key) is not False for key in (
            "donorDifficultyHypothesisInherited", "donorTargetCountInherited",
            "donorMoveBudgetInherited", "winClaim")):
        raise ValueError("proposal contains inherited donor difficulty/goal or WIN authority")
    if diagnose_donor_goals(proposal.get("originalDonorGoals")) != proposal.get("goalContractDiagnosis"):
        raise ValueError("proposal donor-goal diagnosis is forged or stale")
    if proposal.get("sourceGenerated") is not False or proposal.get("artifactStatus") != "LOCALLY_AUTHORED_PREVIEW_ONLY":
        raise ValueError("local proposal must remain distinct from donor-generated output")
    if proposal.get("engineStatus") != "BLOCKED_ENG_M24" or proposal.get("engineQualified") is not False:
        raise ValueError("Engine authority fields are invalid")
    if proposal.get("ownerApproved") is not False or proposal.get("releaseAuthorized") is not False:
        raise ValueError("owner/release authority fields are invalid")
    expected = diagnose_local_sample_proposal(draft, project_root)
    if proposal.get("localAuthoringDiagnostics") != expected:
        raise ValueError("local compatibility receipt is forged or stale")
