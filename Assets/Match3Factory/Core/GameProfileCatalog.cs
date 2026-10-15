using System;
using System.Collections.Generic;
using System.Linq;

namespace Match3Factory
{
    public sealed class GameProfileDefinition
    {
        public string Id { get; internal set; }
        public int Version { get; internal set; }
        public string AudiencePolicy { get; internal set; }
        public HashSet<string> EnabledCapabilities { get; internal set; }
        public HashSet<string> DisabledCapabilities { get; internal set; }
    }

    /// <summary>Conservative local profile registry. Advanced mechanics remain disabled until Engine parity is accepted.</summary>
    public static class GameProfileCatalog
    {
        private static readonly string[] ProfileIds =
        {
            "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop"
        };

        private static readonly string[] AdvancedCapabilities =
        {
            "piece.weighted", "piece.scripted", "piece.anchored", "obstacle.immobilizer",
            "obstacle.spreader", "obstacle.generator", "obstacle.collector", "transport.conveyor",
            "transport.portal", "special.fish_2x2", "special.missile", "special.countdown",
            "special.egg", "special.swirl", "goal.ingredient", "goal.timer", "liveops.ads",
            "liveops.social", "liveops.loot", "analytics.behavioral"
        };

        public static IReadOnlyList<string> AllProfileIds => ProfileIds;

        public static GameProfileDefinition Get(string id)
        {
            if (!ProfileIds.Contains(id, StringComparer.Ordinal)) return null;
            return new GameProfileDefinition
            {
                Id = id,
                Version = 1,
                AudiencePolicy = id == "Wonder_Pop" ? "CHILD_SAFE_RESTRICTED" : "UNCLASSIFIED_NO_LIVEOPS",
                EnabledCapabilities = new HashSet<string>(new[] { "piece.color.basic", "goal.score", "goal.sample.glass" }, StringComparer.Ordinal),
                DisabledCapabilities = new HashSet<string>(AdvancedCapabilities, StringComparer.Ordinal)
            };
        }

        public static List<string> ValidateDraft(LevelDraft draft)
        {
            var errors = new List<string>();
            var profile = draft == null ? null : Get(draft.gameProfileId);
            if (profile == null) { errors.Add("Unknown game profile; no capabilities are enabled."); return errors; }
            if (profile.AudiencePolicy == "CHILD_SAFE_RESTRICTED" && profile.EnabledCapabilities.Any(id => id.StartsWith("liveops.", StringComparison.Ordinal)))
                errors.Add("Wonder_Pop child policy cannot enable ads, social or loot capabilities.");
            if (draft.cells != null)
            foreach (var cell in draft.cells)
            {
                if (cell == null || !cell.active) continue;
                if (cell.locked || cell.lockDurability > 0) errors.Add($"Profile {profile.Id} does not enable cell locks at {cell.row},{cell.column}.");
                if (!string.IsNullOrEmpty(cell.specialId)) errors.Add($"Profile {profile.Id} does not enable special '{cell.specialId}'.");
                if (!string.IsNullOrEmpty(cell.obstacleId) && cell.obstacleId != "sample.glass")
                    errors.Add($"Profile {profile.Id} does not enable obstacle '{cell.obstacleId}'.");
            }
            if (draft.goals != null)
            foreach (var goal in draft.goals)
                if (goal != null && goal.targetId != "sample.score" && goal.targetId != "sample.glass")
                    errors.Add($"Profile {profile.Id} does not enable goal '{goal.targetId}'.");
            return errors;
        }
    }
}
