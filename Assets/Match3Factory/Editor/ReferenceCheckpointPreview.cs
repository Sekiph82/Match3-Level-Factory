using System;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>
    /// Read-only LFX-M08-007 UltraGem cumulative checkpoint receipt.
    /// NEVER engine playback, move legality, WIN, goal completion or cascade replay.
    /// This is an import contract for Python preview_reference_checkpoints.py.
    /// </summary>
    public static class ReferenceCheckpointPreview
    {
        public const string EngineStatus = "BLOCKED_ENG_M24";
        public const string ResultStatus = "REFERENCE_CHECKPOINT_PREVIEW_ONLY";
        public const string PinnedDonor = "0e64a5bc66a5fce4b899bf0734c9cc7417b4ed12"; 
        private static readonly string[] RequiredRootKeys = {
            "resultStatus", "engineStatus", "sourceRevision", "candidateIndex",
            "policy", "runIndex", "runSeed", "donorOutcome", "checkpointSha256",
            "checkpointsAreBeforeMove", "exactCascadeOrderOrBoardFramesAvailable",
            "goalsOrWinProved", "lastMoveMayBeUnobserved", "releaseAuthorized", "checkpoints"
        };
        public static readonly string[] MetricNames = {
            "score", "ndestroyed", "nunlocked", "nstripe", "nbomb", "nzapper",
            "combo_22", "combo_42", "combo_44", "combo_51", "combo_52", "combo_54", "combo_55"
        };

        [Serializable]
        public sealed class Metrics
        {
            public long score, ndestroyed, nunlocked, nstripe, nbomb, nzapper;
            public long combo_22, combo_42, combo_44, combo_51, combo_52, combo_54, combo_55;
            public long[] Values() => new[] {
                score, ndestroyed, nunlocked, nstripe, nbomb, nzapper,
                combo_22, combo_42, combo_44, combo_51, combo_52, combo_54, combo_55
            };
        }

        [Serializable]
        public sealed class Checkpoint
        {
            public int beforeMove;
            public Metrics cumulative;
        }

        [Serializable]
        public sealed class Receipt
        {
            public string resultStatus, engineStatus, sourceRevision, policy;
            public string donorOutcome, checkpointSha256;
            public int candidateIndex, runIndex;
            public long runSeed;
            public bool checkpointsAreBeforeMove, exactCascadeOrderOrBoardFramesAvailable;
            public bool goalsOrWinProved, lastMoveMayBeUnobserved, releaseAuthorized;
            public Checkpoint[] checkpoints;
        }

        public static Receipt Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json) || Encoding.UTF8.GetByteCount(json) > 256000)
                throw new ArgumentException("Checkpoint receipt is empty or exceeds 256 KB.");
            LevelDraftJson.AssertStrictObjectKeys(json, RequiredRootKeys, "reference checkpoint");
            Receipt receipt;
            try { receipt = JsonUtility.FromJson<Receipt>(json); }
            catch (Exception exc) { throw new ArgumentException("Malformed checkpoint receipt.", exc); }
            if (receipt == null || receipt.resultStatus != ResultStatus
                || receipt.engineStatus != EngineStatus || receipt.sourceRevision != PinnedDonor
                || receipt.releaseAuthorized || receipt.goalsOrWinProved
                || receipt.exactCascadeOrderOrBoardFramesAvailable
                || !receipt.checkpointsAreBeforeMove || !receipt.lastMoveMayBeUnobserved)
                throw new ArgumentException("Not a safe, pinned, pre-move reference checkpoint.");
            if (Array.IndexOf(new[] { "worst", "random", "best", "smart" }, receipt.policy) < 0
                || Array.IndexOf(new[] { "MOVE_LIMIT", "STEP_BUDGET_EXCEEDED",
                    "CASCADE_BUDGET_EXCEEDED", "NO_MOVES_AFTER_SHUFFLE_BUDGET" }, receipt.donorOutcome) < 0)
                throw new ArgumentException("Unknown UltraGem policy or terminal reference outcome.");
            if (receipt.candidateIndex < 0 || receipt.candidateIndex > 15
                || receipt.runIndex < 0 || receipt.runIndex > 7
                || receipt.runSeed < 0 || receipt.runSeed > int.MaxValue
                || receipt.checkpoints == null || receipt.checkpoints.Length < 1
                || receipt.checkpoints.Length > 40)
                throw new ArgumentException("Checkpoint header or count is outside donor bounds.");

            var body = new StringBuilder("[");
            long[] previous = new long[MetricNames.Length];
            for (int step = 0; step < receipt.checkpoints.Length; step++)
            {
                Checkpoint point = receipt.checkpoints[step];
                if (point == null || point.beforeMove != step + 1 || point.cumulative == null)
                    throw new ArgumentException("Missing or unordered pre-move checkpoint.");
                long[] values = point.cumulative.Values();
                if (step > 0) body.Append(',');
                body.Append('[');
                for (int col = 0; col < values.Length; col++)
                {
                    if (values[col] < previous[col] || values[col] > 1000000000000L)
                        throw new ArgumentException("Metrics must be bounded cumulative observations.");
                    if (col > 0) body.Append(',');
                    body.Append(values[col].ToString(CultureInfo.InvariantCulture));
                    previous[col] = values[col];
                }
                body.Append(']');
            }
            body.Append(']');
            string digest;
            using (var hash = SHA256.Create())
            {
                byte[] bytes = hash.ComputeHash(Encoding.UTF8.GetBytes(body.ToString()));
                var b = new StringBuilder(bytes.Length * 2);
                foreach (byte value in bytes)
                    b.Append(value.ToString("x2", CultureInfo.InvariantCulture));
                digest = b.ToString();
            }
            if (!string.Equals(receipt.checkpointSha256, digest, StringComparison.Ordinal))
                throw new ArgumentException("Checkpoint SHA256 mismatch (possibly damaged/stale data).");
            return receipt;
        }
    }
}
