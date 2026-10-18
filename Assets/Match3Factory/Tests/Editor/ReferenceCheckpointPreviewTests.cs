using System;
using NUnit.Framework;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class ReferenceCheckpointPreviewTests
    {
        private static ReferenceCheckpointPreview.Receipt TwoSteps()
        {
            var cells = new ReferenceCheckpointPreview.BoardCell[36];
            for (int row = 0; row < 6; row++)
            for (int column = 0; column < 6; column++)
                cells[row * 6 + column] = new ReferenceCheckpointPreview.BoardCell
                { row = row, column = column, type = 1, color = 1, status = 0 };
            return new ReferenceCheckpointPreview.Receipt {
                resultStatus = ReferenceCheckpointPreview.ResultStatus,
                engineStatus = ReferenceCheckpointPreview.EngineStatus,
                sourceRevision = ReferenceCheckpointPreview.PinnedDonor,
                candidateIndex = 0, runIndex = 0, runSeed = 777,
                referencePreviewVersion = 2, donorMovesUsed = 2, donorShuffles = 0,
                policy = "smart", donorOutcome = "MOVE_LIMIT",
                checkpointSha256 = "4c1cafdc5872feaeeeb0e38142068ea17bae929e6ee0625bff80daa26643f4ec",
                initialBoardIsSeededDonorSetup = true, boardAtCheckpointAvailable = false,
                initialBoardSha256 = "10561542d92b047dca613cac4abbb5a5e5e30b23013794995362e9d7c0da41e8",
                initialBoard = new ReferenceCheckpointPreview.InitialBoard
                { rows = 6, columns = 6, cells = cells },
                checkpointsAreBeforeMove = true, paddedFinalStatisticsPresent = false, lastMoveMayBeUnobserved = true,
                exactCascadeOrderOrBoardFramesAvailable = false,
                goalsOrWinProved = false, releaseAuthorized = false,
                checkpoints = new[] {
                    new ReferenceCheckpointPreview.Checkpoint {
                        beforeMove = 1, stepSlot = 1, observedBeforeMove = true, paddedFinalStatistics = false, cumulative = new ReferenceCheckpointPreview.Metrics() },
                    new ReferenceCheckpointPreview.Checkpoint {
                        beforeMove = 2, stepSlot = 2, observedBeforeMove = true, paddedFinalStatistics = false, cumulative = new ReferenceCheckpointPreview.Metrics {
                            score = 4, ndestroyed = 4 } },
                }
            };
        }

        [Test]
        public void PythonCanonicalCheckpointDigestRoundTripsAsReadOnlyDiagnostic()
        {
            var a = TwoSteps();
            var json = JsonUtility.ToJson(a);
            var imported = ReferenceCheckpointPreview.Parse(json);
            Assert.AreEqual(2, imported.checkpoints.Length);
            Assert.AreEqual(4L, imported.checkpoints[1].cumulative.ndestroyed);
            Assert.AreEqual(0L, imported.checkpoints[0].cumulative.score);
            Assert.IsFalse(imported.releaseAuthorized);
            Assert.IsFalse(imported.goalsOrWinProved);
            Assert.AreEqual("BLOCKED_ENG_M24", imported.engineStatus);
            Assert.AreEqual(a.checkpointSha256, imported.checkpointSha256);
            Assert.AreEqual(36, imported.initialBoard.cells.Length);
            Assert.AreEqual(a.initialBoardSha256, imported.initialBoardSha256);
            Assert.IsFalse(imported.boardAtCheckpointAvailable);
        }

        [Test]
        public void TamperingOrEngineAuthorityClaimsAreRejected()
        {
            var altered = TwoSteps();
            altered.checkpoints[1].cumulative.score = 8;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(altered)));
            altered = TwoSteps();
            altered.releaseAuthorized = true;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(altered)));
            altered = TwoSteps();
            altered.sourceRevision = "unverified";
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(altered)));
            altered = TwoSteps();
            altered.checkpoints[0].beforeMove = 4;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(altered)));
            altered = TwoSteps();
            altered.goalsOrWinProved = true;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(altered)));
        }

        [Test]
        public void StrictJsonRejectsDuplicateUnknownAndMissingRootKeys()
        {
            string valid = JsonUtility.ToJson(TwoSteps());
            string duplicated = valid.Replace("\"runSeed\":777", "\"runSeed\":777,\"runSeed\":778");
            Assert.AreNotEqual(valid, duplicated, "Known Unity JSON fixture must include runSeed");
            Assert.Throws<ArgumentException>(() => ReferenceCheckpointPreview.Parse(duplicated));
            string extra = valid.Substring(0, valid.Length - 1) + ",\"win\":true}";
            Assert.Throws<ArgumentException>(() => ReferenceCheckpointPreview.Parse(extra));
            string omitted = valid.Replace("\"resultStatus\":\"REFERENCE_CHECKPOINT_PREVIEW_ONLY\",", "");
            Assert.AreNotEqual(valid, omitted);
            Assert.Throws<ArgumentException>(() => ReferenceCheckpointPreview.Parse(omitted));
        }

        [Test]
        public void InitialBoardMustBeCanonicalAndCannotClaimMoveFrames()
        {
            var disabledLocked = TwoSteps();
            disabledLocked.initialBoard.cells[0].type = -1;
            disabledLocked.initialBoard.cells[0].color = 0;
            disabledLocked.initialBoard.cells[0].status = 2;
            // The pinned InitialFillerDisable preserves a preexisting double
            // lock status on a newly disabled cell. This cross-language
            // SHA256 golden is independently computed for that legal board.
            disabledLocked.initialBoardSha256 = "836e99f35018ae2df8a3e4066fb5911d9ff77289f4a78b3203c76cc7fd00eb42";
            var allowed = ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(disabledLocked));
            Assert.AreEqual(-1, allowed.initialBoard.cells[0].type);
            Assert.AreEqual(2, allowed.initialBoard.cells[0].status);
            // Tampered versions with stale board hash remain rejected.
            var changed = TwoSteps();
            changed.initialBoard.cells[0].type = 2;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(changed)));
            changed = TwoSteps();
            changed.initialBoard.cells[1].column = 0;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(changed)));
            changed = TwoSteps();
            changed.boardAtCheckpointAvailable = true;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(changed)));
            changed = TwoSteps();
            changed.initialBoardIsSeededDonorSetup = false;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(changed)));
        }

        [Test]
        public void PaddedDonorFinalStatisticsCannotMasqueradeAsAnExtraMove()
        {
            var padded = TwoSteps();
            padded.donorOutcome = "NO_MOVES_AFTER_SHUFFLE_BUDGET";
            padded.donorMovesUsed = 1;
            padded.donorShuffles = 21;
            padded.checkpointsAreBeforeMove = false;
            padded.paddedFinalStatisticsPresent = true;
            padded.checkpoints[1].stepSlot = 2;
            padded.checkpoints[1].beforeMove = 0;
            padded.checkpoints[1].observedBeforeMove = false;
            padded.checkpoints[1].paddedFinalStatistics = true;
            var receipt = ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(padded));
            Assert.IsTrue(receipt.checkpoints[1].paddedFinalStatistics);
            Assert.IsFalse(receipt.checkpoints[1].observedBeforeMove);
            Assert.AreEqual(0, receipt.checkpoints[1].beforeMove);
            padded.checkpoints[1].beforeMove = 2; // fake real move frame
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(padded)));
            padded = TwoSteps();
            padded.donorMovesUsed = 1; // no corresponding padded flag
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(padded)));
        }

        [Test]
        public void BoundedNegativeInputsAndNoFalseWin()
        {
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(string.Empty));
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(new string('x', 256001)));
            var invalid = TwoSteps();
            invalid.donorOutcome = "WIN";
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(invalid)));
            invalid = TwoSteps();
            invalid.policy = "Expert";
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(invalid)));
            invalid = TwoSteps();
            invalid.checkpoints[1].cumulative.score = -1;
            Assert.Throws<ArgumentException>(() =>
                ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(invalid)));
        }
    }
}
