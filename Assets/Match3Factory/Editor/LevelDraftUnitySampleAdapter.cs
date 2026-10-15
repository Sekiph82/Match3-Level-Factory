using System;
using System.Collections.Generic;
using System.Linq;

namespace Match3Factory
{
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
