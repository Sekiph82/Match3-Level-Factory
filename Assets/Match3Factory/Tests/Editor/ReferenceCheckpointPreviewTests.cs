using System;
using NUnit.Framework;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class ReferenceCheckpointPreviewTests
    {
        private static ReferenceCheckpointPreview.Receipt TwoSteps()
        {
            return new ReferenceCheckpointPreview.Receipt {
                resultStatus = ReferenceCheckpointPreview.ResultStatus,
                engineStatus = ReferenceCheckpointPreview.EngineStatus,
                sourceRevision = ReferenceCheckpointPreview.PinnedDonor,
                candidateIndex = 0, runIndex = 0, runSeed = 777,
                policy = "smart", donorOutcome = "MOVE_LIMIT",
                checkpointSha256 = "4c1cafdc5872feaeeeb0e38142068ea17bae929e6ee0625bff80daa26643f4ec",
                checkpointsAreBeforeMove = true, lastMoveMayBeUnobserved = true,
                exactCascadeOrderOrBoardFramesAvailable = false,
                goalsOrWinProved = false, releaseAuthorized = false,
                checkpoints = new[] {
                    new ReferenceCheckpointPreview.Checkpoint {
                        beforeMove = 1, cumulative = new ReferenceCheckpointPreview.Metrics() },
                    new ReferenceCheckpointPreview.Checkpoint {
                        beforeMove = 2, cumulative = new ReferenceCheckpointPreview.Metrics {
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
