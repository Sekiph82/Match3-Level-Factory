using System;
using System.Collections.Generic;
using System.Linq;

namespace Match3Factory
{
    [Serializable]
    public sealed class LevelDraft
    {
        public int draftVersion = 1;
        public string validationStatus = "PROTOTYPE_ONLY";
        public string gameProfileId = "Coral_Rescue";
        public int profileVersion = 1;
        public string worldId = "world.prototype";
        public string chapterId = "chapter.prototype";
        public string levelId = "level.prototype";
        public string releaseChannel = "local";
        public string platform = "windows-editor";
        public string locale = "en";
        public string minEngineVersion;
        public string maxEngineVersion;
        public long seed;
        public int width = 8;
        public int height = 8;
        public int layers = 1;
        public bool[] activeMask = Array.Empty<bool>();
        public int moveBudget = 20;
        public bool timedMode;
        public int timeLimitSeconds;
        public int oneStarThreshold = 1;
        public int twoStarThreshold = 2;
        public int threeStarThreshold = 3;
        public string difficultyLabel = "difficulty.unrated";
        public string editorHintKey;
        public CellDraft[] cells = Array.Empty<CellDraft>();
        public GoalDraft[] goals = Array.Empty<GoalDraft>();
        public string engineSchemaVersion;
        public string sourceRepository;
        public string sourceRevision;
        public string sourceKind;

        public List<string> Validate()
        {
            var errors = new List<string>();
            if (draftVersion != 1) errors.Add("Unsupported draftVersion; expected 1.");
            if (validationStatus != "PROTOTYPE_ONLY") errors.Add("Draft status must remain PROTOTYPE_ONLY until ENG-M24 is independently accepted.");
            if (!ProfileIds.Contains(gameProfileId ?? string.Empty)) errors.Add("Unknown gameProfileId.");
            if (profileVersion != 1) errors.Add("Unsupported profileVersion; expected 1.");
            if (!IsStableId(worldId) || !IsStableId(chapterId) || !IsStableId(levelId)) errors.Add("worldId, chapterId and levelId must be stable non-empty identifiers (letters, digits, dot, underscore, hyphen).");
            if (releaseChannel != "local" && releaseChannel != "development" && releaseChannel != "staging") errors.Add("releaseChannel must be local, development or staging until ENG-M24 is accepted.");
            if (platform != "windows-editor" && platform != "windows" && platform != "android" && platform != "ios" && platform != "webgl") errors.Add("Unknown target platform.");
            if (!System.Text.RegularExpressions.Regex.IsMatch(locale ?? string.Empty, "^[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*$")) errors.Add("locale must be a BCP-47-style language tag.");
            if (!string.IsNullOrEmpty(minEngineVersion) || !string.IsNullOrEmpty(maxEngineVersion)) errors.Add("Engine version constraints are unavailable until ENG-M24 is accepted.");
            if (width < 1 || width > 32) errors.Add("width must be between 1 and 32.");
            if (height < 1 || height > 32) errors.Add("height must be between 1 and 32.");
            if (layers < 1 || layers > 4) errors.Add("layers must be between 1 and 4.");
            if (seed < 0) errors.Add("seed must be a non-negative signed 64-bit integer.");
            if (moveBudget < 1 || moveBudget > 999) errors.Add("moveBudget must be between 1 and 999.");
            if (timedMode ? timeLimitSeconds < 1 || timeLimitSeconds > 3600 : timeLimitSeconds != 0)
                errors.Add("timeLimitSeconds must be 1..3600 for timed levels and 0 otherwise.");
            if (oneStarThreshold < 0 || oneStarThreshold > 99999 || twoStarThreshold < oneStarThreshold || twoStarThreshold > 99999 || threeStarThreshold < twoStarThreshold || threeStarThreshold > 99999)
                errors.Add("Star thresholds must be ascending values in 0..99999.");
            if (!IsStableId(difficultyLabel) || (!string.IsNullOrEmpty(editorHintKey) && !IsStableId(editorHintKey)))
                errors.Add("difficultyLabel and editorHintKey must be stable localization keys.");
            if (cells == null) errors.Add("cells is required.");
            else
            {
                long expectedCellCount = (long)width * height * layers;
                if (expectedCellCount < 1 || expectedCellCount > 4096)
                {
                    errors.Add("Cell count must be between 1 and 4096.");
                    return errors;
                }
                int expectedCells = (int)expectedCellCount;
                if (activeMask == null || activeMask.Length != expectedCells)
                    errors.Add("activeMask length must equal width × height × layers.");
                if (cells.Length != expectedCells)
                    errors.Add($"cells must contain exactly {expectedCells} entries, including holes.");
                var seen = new HashSet<string>(StringComparer.Ordinal);
                foreach (var cell in cells)
                {
                    if (cell == null) { errors.Add("cells cannot contain null entries."); continue; }
                    if (cell.row < 0 || cell.row >= height || cell.column < 0 || cell.column >= width || cell.layer < 0 || cell.layer >= layers)
                        errors.Add($"Cell coordinate out of range: {cell.row},{cell.column},{cell.layer}.");
                    if (string.IsNullOrWhiteSpace(cell.contentId) && string.IsNullOrWhiteSpace(cell.obstacleId) && cell.active)
                        errors.Add($"Active cell {cell.row},{cell.column},{cell.layer} requires contentId or obstacleId.");
                    if (!cell.active && (!string.IsNullOrEmpty(cell.contentId) || !string.IsNullOrEmpty(cell.obstacleId) || !string.IsNullOrEmpty(cell.specialId) || cell.locked || cell.lockDurability != 0 || cell.obstacleDurability != 0))
                        errors.Add($"Hole {cell.row},{cell.column},{cell.layer} cannot carry content, obstacle, special, or durability.");
                    if (cell.lockDurability < 0 || cell.lockDurability > 99)
                        errors.Add($"Invalid lock durability at {cell.row},{cell.column},{cell.layer}.");
                    foreach (var identifier in new[] { cell.contentId, cell.obstacleId, cell.specialId })
                        if (identifier != null && identifier.Length > 128)
                            errors.Add($"Invalid cell identifier at {cell.row},{cell.column},{cell.layer}.");
                    if (cell.obstacleDurability < 0 || cell.obstacleDurability > 99)
                        errors.Add($"Invalid obstacle durability at {cell.row},{cell.column},{cell.layer}.");
                    string key = $"{cell.row}:{cell.column}:{cell.layer}";
                    if (!seen.Add(key)) errors.Add($"Duplicate cell coordinate {key}.");
                    if (activeMask != null && cell.row >= 0 && cell.row < height && cell.column >= 0 && cell.column < width && cell.layer >= 0 && cell.layer < layers)
                    {
                        int index = (cell.layer * height + cell.row) * width + cell.column;
                        if (index < activeMask.Length && activeMask[index] != cell.active)
                            errors.Add($"activeMask disagrees with cell {key}.");
                    }
                }
                if (seen.Count == expectedCells)
                {
                    for (int layer = 0; layer < layers; layer++)
                    for (int row = 0; row < height; row++)
                    for (int column = 0; column < width; column++)
                        if (!seen.Contains($"{row}:{column}:{layer}"))
                            errors.Add($"Missing cell coordinate {row},{column},{layer}.");
                }
            }
            if (goals == null || goals.Length < 1 || goals.Length > 32) errors.Add("goals must contain 1..32 entries.");
            else
            {
                var ids = new HashSet<string>(StringComparer.Ordinal);
                foreach (var goal in goals)
                {
                    if (goal == null) { errors.Add("goals cannot contain null entries."); continue; }
                    if (string.IsNullOrWhiteSpace(goal.goalId) || !ids.Add(goal.goalId)) errors.Add("Goal IDs must be present and unique.");
                    if (string.IsNullOrWhiteSpace(goal.targetId)) errors.Add("Goal targetId is required.");
                    if (goal.goalId != null && goal.goalId.Length > 128) errors.Add("Goal IDs cannot exceed 128 characters.");
                    if (goal.targetId != null && goal.targetId.Length > 128) errors.Add("Goal targetId cannot exceed 128 characters.");
                    if (goal.targetCount < 1 || goal.targetCount > 99999) errors.Add("Goal targetCount is out of range.");
                }
            }
            if (!string.IsNullOrEmpty(engineSchemaVersion)) errors.Add("Engine schema is unavailable; draft cannot claim Engine compatibility.");
            return errors;
        }

        public LevelDraft Canonicalized()
        {
            var copy = Clone();
            copy.cells = (copy.cells ?? Array.Empty<CellDraft>())
                .OrderBy(x => x.row).ThenBy(x => x.column).ThenBy(x => x.layer).ToArray();
            copy.goals = (copy.goals ?? Array.Empty<GoalDraft>())
                .OrderBy(x => x.goalId, StringComparer.Ordinal).ToArray();
            return copy;
        }

        public LevelDraft Clone()
        {
            var clone = UnityEngine.JsonUtility.FromJson<LevelDraft>(UnityEngine.JsonUtility.ToJson(this));
            foreach (var cell in clone.cells)
            {
                if (string.IsNullOrEmpty(cell.contentId)) cell.contentId = null;
                if (string.IsNullOrEmpty(cell.obstacleId)) cell.obstacleId = null;
                if (string.IsNullOrEmpty(cell.specialId)) cell.specialId = null;
            }
            if (string.IsNullOrEmpty(clone.engineSchemaVersion)) clone.engineSchemaVersion = null;
            if (string.IsNullOrEmpty(clone.minEngineVersion)) clone.minEngineVersion = null;
            if (string.IsNullOrEmpty(clone.maxEngineVersion)) clone.maxEngineVersion = null;
            if (string.IsNullOrEmpty(clone.sourceRepository)) clone.sourceRepository = null;
            if (string.IsNullOrEmpty(clone.sourceRevision)) clone.sourceRevision = null;
            if (string.IsNullOrEmpty(clone.sourceKind)) clone.sourceKind = null;
            if (string.IsNullOrEmpty(clone.editorHintKey)) clone.editorHintKey = null;
            return clone;
        }

        private static readonly HashSet<string> ProfileIds = new HashSet<string>(StringComparer.Ordinal)
        {
            "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop"
        };

        private static bool IsStableId(string value) => !string.IsNullOrEmpty(value) && value.Length <= 128 && System.Text.RegularExpressions.Regex.IsMatch(value, "^[A-Za-z0-9._-]+$");
    }

    [Serializable]
    public sealed class CellDraft
    {
        public int row;
        public int column;
        public int layer;
        public bool active = true;
        public bool locked;
        public string contentId;
        public string obstacleId;
        public int obstacleDurability;
        public int lockDurability;
        public string specialId;
    }

    [Serializable]
    public sealed class GoalDraft
    {
        public string goalId;
        public string targetId;
        public int targetCount;
    }

}
