using System;
using System.Collections.Generic;

namespace Match3Factory
{
    public static class LevelDraftGridOperations
    {
        public static void Resize(LevelDraft draft, int width, int height, int layers)
        {
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            if (width < 1 || width > 32 || height < 1 || height > 32 || layers < 1 || layers > 4 || (long)width * height * layers > 4096)
                throw new ArgumentOutOfRangeException(nameof(width), "Grid dimensions must be width/height 1..32, layers 1..4, and at most 4096 cells.");

            var existing = new Dictionary<string, CellDraft>(StringComparer.Ordinal);
            if (draft.cells != null)
                foreach (var cell in draft.cells)
                    if (cell != null) existing[Key(cell.row, cell.column, cell.layer)] = cell;

            var cells = new CellDraft[width * height * layers];
            var mask = new bool[cells.Length];
            for (int layer = 0; layer < layers; layer++)
            for (int row = 0; row < height; row++)
            for (int column = 0; column < width; column++)
            {
                int index = Index(width, height, row, column, layer);
                CellDraft old;
                if (existing.TryGetValue(Key(row, column, layer), out old))
                {
                    cells[index] = new CellDraft
                    {
                        row = row, column = column, layer = layer, active = old.active,
                        locked = old.locked, contentId = old.contentId, obstacleId = old.obstacleId,
                        obstacleDurability = old.obstacleDurability, lockDurability = old.lockDurability,
                        specialId = old.specialId
                    };
                }
                else cells[index] = new CellDraft { row = row, column = column, layer = layer, active = true, contentId = "Blue" };
                mask[index] = cells[index].active;
            }

            draft.width = width; draft.height = height; draft.layers = layers;
            draft.cells = cells; draft.activeMask = mask;
        }

        public static int Index(int width, int height, int row, int column, int layer)
        {
            if (row < 0 || row >= height || column < 0 || column >= width || layer < 0)
                throw new ArgumentOutOfRangeException(nameof(row), "Grid cell coordinate is out of bounds.");
            return (layer * height + row) * width + column;
        }

        private static string Key(int row, int column, int layer) => layer + ":" + row + ":" + column;
    }
}
