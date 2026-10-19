// LFX -> VUF review-only schema LFXV1. Uses the ACTUAL strict LevelDraftJson
// parser and independently validated draft cells/goals. No sample-bot
// outcome, invented WIN, Engine-M24 resolver or game rights. Editor only.
using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace Match3Factory
{
    public static class LevelDraftVisualHandoff
    {
        public const string Stage = "LFXV1_VALIDATED_DRAFT_NOT_ENGINE_REPLAY";
        [Serializable] public sealed class Cell
        {
            public int row, column, layer, obstacleDurability, lockDurability;
            public bool active, locked;
            public string contentId, obstacleId, specialId;
        }
        [Serializable] public sealed class Goal
        {
            public string goalId, targetId;
            public int targetCount;
        }
        [Serializable] public sealed class Envelope
        {
            public int schemaVersion = 1, width, height, layers, moveBudget;
            public string stage = Stage, gameProfileId, levelId;
            public string sourceDraftSha256, sourceLevelFactoryGitSha = "UNPINNED";
            public long seed;
            public Cell[] cells;
            public Goal[] goals;
            public bool actualSdkWinVerified, engineM24ReleaseAccepted;
            public bool realPlayableLevel, assetRightsApproved, releaseAllowed;
        }

        public static Envelope FromCanonicalLevelDraft(string json)
        {
            // Actual real LFX strict reader checks schema, bounded arrays,
            // cell topology, activeMask, goals and PROTOTYPE_ONLY status.
            var draft = LevelDraftJson.Parse(json);
            string canonical = LevelDraftJson.Serialize(draft);
            string sha;
            using (var hasher = SHA256.Create())
                sha = BitConverter.ToString(hasher.ComputeHash(
                    Encoding.UTF8.GetBytes(canonical))).Replace("-", "")
                    .ToLowerInvariant();
            var envelope = new Envelope {
                gameProfileId = draft.gameProfileId,
                levelId = draft.levelId,
                width = draft.width, height = draft.height,
                layers = draft.layers, moveBudget = draft.moveBudget,
                seed = draft.seed, sourceDraftSha256 = sha,
                cells = draft.cells.OrderBy(c => c.layer).ThenBy(c => c.row)
                    .ThenBy(c => c.column).Select(c => new Cell {
                        row = c.row, column = c.column, layer = c.layer,
                        active = c.active, locked = c.locked,
                        contentId = c.contentId,
                        obstacleId = c.obstacleId,
                        specialId = c.specialId,
                        obstacleDurability = c.obstacleDurability,
                        lockDurability = c.lockDurability
                    }).ToArray(),
                goals = draft.goals.OrderBy(g => g.goalId, StringComparer.Ordinal)
                    .Select(g => new Goal {
                        goalId = g.goalId, targetId = g.targetId,
                        targetCount = g.targetCount
                    }).ToArray()
            };
            return envelope;
        }

        public static string ToJson(string canonicalDraftJson)
        {
            return JsonUtility.ToJson(FromCanonicalLevelDraft(canonicalDraftJson));
        }
    }
}
