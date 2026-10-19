// LFX -> VUF review-only schema LFXV1. Uses the ACTUAL strict LevelDraftJson
// parser and independently validated draft cells/goals. No sample-bot
// outcome, invented WIN, Engine-M24 resolver or game rights. Editor only.
using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
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

        // Delivers two exact source bytes to a NONEXISTENT external folder,
        // so a VUF consumer can independently pin SHA(canonical LevelDraft)
        // against the real derived board and never trust an unverified path.
        public static void ExportNewExternalPair(string validatedDraftJson,
            string externalNewFolder)
        {
            if (String.IsNullOrEmpty(externalNewFolder) ||
                !Path.IsPathRooted(externalNewFolder))
                throw new ArgumentException("absolute external new folder required");
            string folder = Path.GetFullPath(externalNewFolder);
            string checkout = Path.GetFullPath(Directory.GetCurrentDirectory())
                .TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (folder.StartsWith(checkout, StringComparison.OrdinalIgnoreCase) ||
                Directory.Exists(folder) || File.Exists(folder))
                throw new IOException("cannot overwrite repo or existing owner files");
            var parent = Directory.GetParent(folder);
            if (parent == null || !parent.Exists)
                throw new IOException("parent must already exist");
            for (var d = parent; d != null; d = d.Parent)
                if ((d.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("linked export folder rejected");
            var draft = LevelDraftJson.Parse(validatedDraftJson);
            string canonical = LevelDraftJson.Serialize(draft);
            string envelope = ToJson(canonical);
            Directory.CreateDirectory(folder);
            // FileMode.CreateNew ensures zero original/source overwrites.
            using (var file = new FileStream(Path.Combine(folder,
                "leveldraft_v1_canonical.json"), FileMode.CreateNew))
            {
                var bytes = new UTF8Encoding(false).GetBytes(canonical);
                file.Write(bytes, 0, bytes.Length);
            }
            using (var file = new FileStream(Path.Combine(folder,
                "LFXV1_visual_handoff.json"), FileMode.CreateNew))
            {
                var bytes = new UTF8Encoding(false).GetBytes(envelope);
                file.Write(bytes, 0, bytes.Length);
            }
        }
    }
}
