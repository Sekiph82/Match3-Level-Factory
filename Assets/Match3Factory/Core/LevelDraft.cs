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
        public long seed;
        public int width = 8;
        public int height = 8;
        public int layers = 1;
        public bool[] activeMask = Array.Empty<bool>();
        public int moveBudget = 20;
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
            if (width < 1 || width > 32) errors.Add("width must be between 1 and 32.");
            if (height < 1 || height > 32) errors.Add("height must be between 1 and 32.");
            if (layers < 1 || layers > 4) errors.Add("layers must be between 1 and 4.");
            if (moveBudget < 1 || moveBudget > 999) errors.Add("moveBudget must be between 1 and 999.");
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
                var seen = new HashSet<string>(StringComparer.Ordinal);
                foreach (var cell in cells)
                {
                    if (cell == null) { errors.Add("cells cannot contain null entries."); continue; }
                    if (cell.row < 0 || cell.row >= height || cell.column < 0 || cell.column >= width || cell.layer < 0 || cell.layer >= layers)
                        errors.Add($"Cell coordinate out of range: {cell.row},{cell.column},{cell.layer}.");
                    if (string.IsNullOrWhiteSpace(cell.contentId) && string.IsNullOrWhiteSpace(cell.obstacleId) && cell.active)
                        errors.Add($"Active cell {cell.row},{cell.column},{cell.layer} requires contentId or obstacleId.");
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
                if (cells.Length > width * height * layers) errors.Add("cells exceeds board capacity.");
            }
            if (goals == null) errors.Add("goals is required.");
            else
            {
                var ids = new HashSet<string>(StringComparer.Ordinal);
                foreach (var goal in goals)
                {
                    if (goal == null) { errors.Add("goals cannot contain null entries."); continue; }
                    if (string.IsNullOrWhiteSpace(goal.goalId) || !ids.Add(goal.goalId)) errors.Add("Goal IDs must be present and unique.");
                    if (string.IsNullOrWhiteSpace(goal.targetId)) errors.Add("Goal targetId is required.");
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
            return UnityEngine.JsonUtility.FromJson<LevelDraft>(UnityEngine.JsonUtility.ToJson(this));
        }

        private static readonly HashSet<string> ProfileIds = new HashSet<string>(StringComparer.Ordinal)
        {
            "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop"
        };
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
