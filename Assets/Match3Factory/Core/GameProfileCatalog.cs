using System;
using System.Collections.Generic;
using System.Linq;

namespace Match3Factory
{
    public sealed class GameProfileDefinition
    {
        public string Id { get; internal set; }
        public string DisplayName { get; internal set; }
        public int Version { get; internal set; }
        public string AudiencePolicy { get; internal set; }
        public string NeutralFallbackLabel { get; internal set; }
        public HashSet<string> EnabledCapabilities { get; internal set; }
        public HashSet<string> DisabledCapabilities { get; internal set; }
    }

    /// <summary>Conservative versioned profiles. Every profile stays reference-only until Engine parity is accepted.</summary>
    public static class GameProfileCatalog
    {
        private static readonly string[] AdvancedCapabilities =
        {
            "piece.weighted", "piece.scripted", "piece.anchored", "obstacle.immobilizer",
            "obstacle.spreader", "obstacle.generator", "obstacle.collector", "transport.conveyor",
            "transport.portal", "special.fish_2x2", "special.missile", "special.countdown",
            "special.egg", "special.swirl", "goal.ingredient", "goal.timer", "liveops.ads",
            "liveops.social", "liveops.loot", "analytics.behavioral"
        };
        private static readonly string[] BasicCapabilities = { "piece.color.basic", "goal.score", "goal.sample.glass" };
        private static readonly GameProfileDefinition[] Definitions = BuildDefinitions();
        private static readonly Dictionary<string, GameProfileDefinition> ById = BuildIndex(Definitions);

        public static IReadOnlyList<string> AllProfileIds => Definitions.Select(profile => profile.Id).ToArray();

        public static GameProfileDefinition Get(string id)
        {
            GameProfileDefinition value;
            if (id == null || !ById.TryGetValue(id, out value)) return null;
            return Copy(value);
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

        public static bool HasUniqueIds(IEnumerable<GameProfileDefinition> profiles)
        {
            var ids = new HashSet<string>(StringComparer.Ordinal);
            return profiles != null && profiles.All(profile => profile != null && !string.IsNullOrWhiteSpace(profile.Id) && ids.Add(profile.Id));
        }

        private static GameProfileDefinition[] BuildDefinitions()
        {
            var names = new[] { "Coral Rescue", "Garage Legends", "Dino Islands", "The Fractured Realms", "Wonder Pop" };
            var ids = new[] { "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop" };
            return ids.Select((id, index) => new GameProfileDefinition
            {
                Id = id,
                DisplayName = names[index],
                Version = 1,
                AudiencePolicy = id == "Wonder_Pop" ? "CHILD_SAFE_RESTRICTED" : "UNCLASSIFIED_NO_LIVEOPS",
                NeutralFallbackLabel = "Neutral placeholder · title art unavailable",
                EnabledCapabilities = new HashSet<string>(BasicCapabilities, StringComparer.Ordinal),
                DisabledCapabilities = new HashSet<string>(AdvancedCapabilities, StringComparer.Ordinal)
            }).ToArray();
        }

        private static Dictionary<string, GameProfileDefinition> BuildIndex(GameProfileDefinition[] profiles)
        {
            if (!HasUniqueIds(profiles)) throw new InvalidOperationException("Game profile IDs must be unique and non-empty.");
            return profiles.ToDictionary(profile => profile.Id, profile => profile, StringComparer.Ordinal);
        }

        private static GameProfileDefinition Copy(GameProfileDefinition profile) => new GameProfileDefinition
        {
            Id = profile.Id, DisplayName = profile.DisplayName, Version = profile.Version,
            AudiencePolicy = profile.AudiencePolicy, NeutralFallbackLabel = profile.NeutralFallbackLabel,
            EnabledCapabilities = new HashSet<string>(profile.EnabledCapabilities, StringComparer.Ordinal),
            DisabledCapabilities = new HashSet<string>(profile.DisabledCapabilities, StringComparer.Ordinal)
        };
    }
}
