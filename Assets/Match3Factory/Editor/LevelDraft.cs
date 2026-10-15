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

    public static class LevelDraftUnitySampleAdapter
    {
        public static LevelDraft FromLevelSO(LevelSO source, string gameProfileId, long seed)
        {
            if (source == null) throw new ArgumentNullException(nameof(source));
            var draft = new LevelDraft
            {
                gameProfileId = gameProfileId,
                seed = seed,
                width = source.width,
                height = source.height,
                layers = 1,
                activeMask = Enumerable.Repeat(true, source.width * source.height).ToArray(),
                moveBudget = source.moveAmount,
                sourceRepository = "Unity-Technologies/Game-Simulation-Match-3-Sample",
                sourceRevision = "7a77506428e699f5bce8ab5e2c1bc3d1f3a966a7",
                sourceKind = "UnityLevelSO"
            };
            if (source.levelGridPositionList == null) throw new InvalidOperationException("LevelSO has no levelGridPositionList.");
            draft.cells = source.levelGridPositionList.Select(position =>
            {
                if (position == null || position.gemSO == null) throw new InvalidOperationException("LevelSO contains a cell without a GemSO.");
                return new CellDraft
                {
                    row = position.y,
                    column = position.x,
                    layer = 0,
                    active = true,
                    contentId = position.gemSO.name,
                    obstacleId = position.hasGlass ? "sample.glass" : null,
                    obstacleDurability = position.hasGlass ? 1 : 0
                };
            }).ToArray();
            string targetId = source.goalType == LevelSO.GoalType.Glass ? "sample.glass" : "sample.score";
            int targetCount = source.goalType == LevelSO.GoalType.Glass
                ? draft.cells.Count(cell => cell.obstacleId == "sample.glass")
                : source.targetScore;
            draft.goals = targetCount > 0
                ? new[] { new GoalDraft { goalId = "sample.primary", targetId = targetId, targetCount = targetCount } }
                : Array.Empty<GoalDraft>();
            var errors = draft.Validate();
            if (errors.Count > 0) throw new InvalidOperationException(string.Join(" ", errors));
            return draft.Canonicalized();
        }

        public static void ApplyToLevelSO(LevelDraft draft, LevelSO target)
        {
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            if (target == null) throw new ArgumentNullException(nameof(target));
            var errors = draft.Validate();
            if (errors.Count > 0) throw new InvalidOperationException(string.Join(" ", errors));
            if (draft.layers != 1) throw new NotSupportedException("The sample LevelSO supports one layer only.");
            var gems = target.gemList == null
                ? new Dictionary<string, GemSO>(StringComparer.Ordinal)
                : target.gemList.Where(gem => gem != null).GroupBy(gem => gem.name, StringComparer.Ordinal)
                    .ToDictionary(group => group.Key, group => group.First(), StringComparer.Ordinal);
            var unsupported = draft.cells.FirstOrDefault(cell => !cell.active ||
                !string.IsNullOrEmpty(cell.obstacleId) && cell.obstacleId != "sample.glass" || cell.obstacleDurability > 1 ||
                cell.locked || cell.lockDurability > 0 || !string.IsNullOrEmpty(cell.specialId));
            if (unsupported != null)
                throw new NotSupportedException($"The sample LevelSO cannot represent this cell ({unsupported.row},{unsupported.column}): active={unsupported.active}, obstacle={unsupported.obstacleId ?? "<none>"}, durability={unsupported.obstacleDurability}, locked={unsupported.locked}, lockDurability={unsupported.lockDurability}, special={unsupported.specialId ?? "<none>"}.");
            var mapped = new List<LevelSO.LevelGridPosition>(draft.cells.Length);
            foreach (var cell in draft.cells)
            {
                if (!gems.TryGetValue(cell.contentId, out var gem)) throw new NotSupportedException($"Unknown sample gem identifier '{cell.contentId}'.");
                mapped.Add(new LevelSO.LevelGridPosition
                {
                    x = cell.column,
                    y = cell.row,
                    gemSO = gem,
                    hasGlass = cell.obstacleId == "sample.glass"
                });
            }
            target.width = draft.width;
            target.height = draft.height;
            target.moveAmount = draft.moveBudget;
            target.levelGridPositionList = mapped;
            var goal = draft.goals.FirstOrDefault();
            if (goal != null && goal.targetId == "sample.glass") target.goalType = LevelSO.GoalType.Glass;
            else if (goal != null && goal.targetId == "sample.score")
            {
                target.goalType = LevelSO.GoalType.Score;
                target.targetScore = goal.targetCount;
            }
            else throw new NotSupportedException("The sample LevelSO supports only glass and score goals.");
        }
    }
}
