using System;
using System.Collections.Generic;
using System.Linq;

namespace Match3Factory
{
    public static class LevelDraftRegistry
    {
        public static string Key(LevelDraft draft)
        {
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            return string.Join("/", new[] { draft.gameProfileId, draft.worldId, draft.chapterId, draft.levelId });
        }

        public static List<string> ValidateUnique(IEnumerable<LevelDraft> drafts)
        {
            var errors = new List<string>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var draft in drafts ?? Enumerable.Empty<LevelDraft>())
            {
                if (draft == null) { errors.Add("Registry cannot contain a null draft."); continue; }
                string key = Key(draft);
                if (!seen.Add(key)) errors.Add("Duplicate level identity in game profile: " + key);
            }
            return errors;
        }

        public static bool TryCopyBoard(LevelDraft source, LevelDraft destination, out string error)
        {
            error = null;
            if (source == null || destination == null) { error = "Source and destination drafts are required."; return false; }
            var sourceErrors = source.Validate();
            if (sourceErrors.Count != 0) { error = "Source draft is invalid: " + string.Join(" ", sourceErrors); return false; }
            if (source.layers != 1 || destination.layers != 1 || source.width != destination.width || source.height != destination.height)
            { error = "Cross-profile board copy requires matching one-layer dimensions."; return false; }
            var candidate = destination.Clone();
            candidate.activeMask = (bool[])source.activeMask.Clone();
            candidate.cells = source.cells.Select(cell => new CellDraft
            {
                row = cell.row, column = cell.column, layer = cell.layer, active = cell.active,
                locked = cell.locked, contentId = cell.contentId, obstacleId = cell.obstacleId,
                obstacleDurability = cell.obstacleDurability, lockDurability = cell.lockDurability, specialId = cell.specialId
            }).ToArray();
            var errors = candidate.Validate().Concat(GameProfileCatalog.ValidateDraft(candidate)).ToArray();
            if (errors.Length != 0) { error = "Destination profile rejects copied board: " + string.Join(" ", errors); return false; }
            destination.activeMask = candidate.activeMask;
            destination.cells = candidate.cells;
            return true;
        }
    }
}
