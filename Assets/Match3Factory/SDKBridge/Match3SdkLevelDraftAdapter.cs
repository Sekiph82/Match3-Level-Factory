using System;
using System.Collections.Generic;
using System.Linq;
using SdkAppInterfaces = global::Match3.App.Interfaces;
using SdkCoreInterfaces = global::Match3.Core.Interfaces;
using SdkGridPosition = global::Match3.Core.Structs.GridPosition;
using SdkInfrastructure = global::Match3.Infrastructure;
using SdkSequenceDetectors = global::Match3.Infrastructure.SequenceDetectors;

namespace Match3Factory
{
    public sealed class Match3SdkSwapCandidate
    {
        public int startRow;
        public int startColumn;
        public int endRow;
        public int endColumn;
        public int matchedSlotCount;
    }

    public sealed class Match3SdkDraftAnalysis
    {
        public string resultStatus = "SDK_REFERENCE_ONLY";
        public string engineStatus = "BLOCKED_ENG_M24";
        public string apiPackage = "com.chebanovdd.match3sdk@771e62908056c2c5fa69937a52ca52ab589f19ea";
        public List<Match3SdkSwapCandidate> legalSwapCandidates = new List<Match3SdkSwapCandidate>();
    }

    /// <summary>
    /// Calls LibraStack's public IGameBoardSolver and line detectors on a temporary
    /// LevelDraft board. This is an API bridge, not a final Engine simulation host.
    /// </summary>
    public sealed class Match3SdkLevelDraftAdapter
    {
        private readonly Func<string, int> resolveItemId;
        private readonly SdkAppInterfaces.IGameBoardSolver<DraftGridSlot> solver;

        public Match3SdkLevelDraftAdapter(Func<string, int> resolveItemId)
        {
            this.resolveItemId = resolveItemId ?? throw new ArgumentNullException(nameof(resolveItemId));
            solver = new SdkInfrastructure.GameBoardSolver<DraftGridSlot>(
                new SdkAppInterfaces.ISequenceDetector<DraftGridSlot>[]
                {
                    new SdkSequenceDetectors.HorizontalLineDetector<DraftGridSlot>(),
                    new SdkSequenceDetectors.VerticalLineDetector<DraftGridSlot>()
                },
                Array.Empty<SdkAppInterfaces.ISpecialItemDetector<DraftGridSlot>>());
        }

        public Match3SdkDraftAnalysis AnalyzeLegalSwaps(LevelDraft draft)
        {
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            var errors = draft.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            if (draft.layers != 1) throw new NotSupportedException("The pinned SDK API bridge currently accepts one layer.");
            if (draft.cells.Any(cell => cell.active &&
                (!string.IsNullOrEmpty(cell.obstacleId) || cell.locked || cell.lockDurability > 0 || !string.IsNullOrEmpty(cell.specialId))))
                throw new NotSupportedException("The pinned SDK adapter currently supports plain items and holes only; obstacles, locks, and specials require Engine-owned capability adapters.");

            var slots = new DraftGridSlot[draft.height, draft.width];
            foreach (var cell in draft.cells)
            {
                int? itemId = null;
                if (cell.active)
                {
                    if (string.IsNullOrWhiteSpace(cell.contentId))
                        throw new NotSupportedException($"The pinned SDK adapter requires a concrete item ID at {cell.row},{cell.column}.");
                    itemId = resolveItemId(cell.contentId);
                }
                slots[cell.row, cell.column] = new DraftGridSlot(new SdkGridPosition(cell.row, cell.column), itemId, cell.active);
            }

            var board = new DraftGameBoard(slots);
            var result = new Match3SdkDraftAnalysis();
            for (int row = 0; row < draft.height; row++)
            for (int column = 0; column < draft.width; column++)
            {
                var start = new SdkGridPosition(row, column);
                TryCandidate(board, start, new SdkGridPosition(row, column + 1), result);
                TryCandidate(board, start, new SdkGridPosition(row + 1, column), result);
            }
            return result;
        }

        private void TryCandidate(DraftGameBoard board, SdkGridPosition start, SdkGridPosition end, Match3SdkDraftAnalysis result)
        {
            if (!board.IsPositionOnBoard(end)) return;
            var first = board[start];
            var second = board[end];
            if (!first.CanContainItem || !second.CanContainItem || !first.HasItem || !second.HasItem) return;

            first.SwapItemWith(second);
            var solved = solver.Solve(board, start, end);
            first.SwapItemWith(second);
            if (solved.SolvedSequences.Count == 0) return;

            result.legalSwapCandidates.Add(new Match3SdkSwapCandidate
            {
                startRow = start.RowIndex,
                startColumn = start.ColumnIndex,
                endRow = end.RowIndex,
                endColumn = end.ColumnIndex,
                matchedSlotCount = solved.SolvedSequences.Sum(sequence => sequence.SolvedGridSlots.Count)
            });
        }

        private sealed class DraftGameBoard : SdkAppInterfaces.IGameBoard<DraftGridSlot>
        {
            private readonly DraftGridSlot[,] slots;
            public DraftGameBoard(DraftGridSlot[,] slots) { this.slots = slots; }
            public int RowCount => slots.GetLength(0);
            public int ColumnCount => slots.GetLength(1);
            public DraftGridSlot this[SdkGridPosition position] => slots[position.RowIndex, position.ColumnIndex];
            public DraftGridSlot this[int rowIndex, int columnIndex] => slots[rowIndex, columnIndex];
            public bool IsPositionOnGrid(SdkGridPosition position) => IsPositionOnBoard(position);
            public bool IsPositionOnBoard(SdkGridPosition position) =>
                position.RowIndex >= 0 && position.RowIndex < RowCount &&
                position.ColumnIndex >= 0 && position.ColumnIndex < ColumnCount;
        }

        private sealed class DraftGridSlot : SdkCoreInterfaces.IGridSlot, SdkCoreInterfaces.IGridSlotState
        {
            private int? itemId;
            private readonly bool canContainItem;
            public DraftGridSlot(SdkGridPosition position, int? itemId, bool canContainItem)
            {
                GridPosition = position;
                this.itemId = itemId;
                this.canContainItem = canContainItem;
            }
            public int ItemId => itemId ?? 0;
            public bool HasItem => itemId.HasValue;
            public bool IsMovable => canContainItem;
            public bool CanContainItem => canContainItem;
            public SdkCoreInterfaces.IGridSlotState State => this;
            public SdkGridPosition GridPosition { get; }
            public int GroupId => ItemId;
            public bool IsLocked => false;
            public void SwapItemWith(DraftGridSlot other)
            {
                int? previous = itemId;
                itemId = other.itemId;
                other.itemId = previous;
            }
        }
    }
}
