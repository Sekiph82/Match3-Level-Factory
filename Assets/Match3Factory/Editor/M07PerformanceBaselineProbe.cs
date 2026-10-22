using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Match3Factory;
using UnityEditor;
using UnityEngine;

namespace Match3Factory
{
    [Serializable]
    public sealed class M07OperationMeasurement
    {
        public string operation;
        public int iterations;
        public double[] samplesMs;
        public double medianMs;
        public double p95Ms;
        public double worstMs;
        public double allocatedBytesPerCall;
        public bool allocationMetricAvailable;
        public string status;
    }

    [Serializable]
    public sealed class M07UnityPerformanceReport
    {
        public string taskId;
        public string resultStatus;
        public string engineStatus;
        public bool runtimeGameplay;
        public bool releaseAuthorized;
        public string unityVersion;
        public string operatingSystem;
        public string processor;
        public int logicalProcessorCount;
        public string fixtureSha256;
        public string canonicalDraftSha256;
        public int iterations;
        public double observationBudgetMs;
        public long workingSetBytes;
        public long peakWorkingSetBytes;
        public bool processWorkingSetMetricAvailable;
        public long gcTotalBytes;
        public M07OperationMeasurement[] operations;
    }

    public static class M07PerformanceBaselineProbe
    {
        private const string FixturePath = "Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json";
        private const string ExpectedRawFixtureSha256 = "0badd48bbd433066b7fe7274dc80acb9054a154ed8ed95cf7934ca280ac09d68";
        private const string ExpectedCanonicalDraftSha256 = "fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d";
        private const int Iterations = 25;
        private const double ObservationBudgetMilliseconds = 100.0;

        public static void WriteResultFromCommandLine()
        {
            string outputPath = null;
            var arguments = Environment.GetCommandLineArgs();
            for (int index = 0; index + 1 < arguments.Length; index++)
                if (arguments[index] == "-m07Output") outputPath = arguments[index + 1];
            if (string.IsNullOrWhiteSpace(outputPath))
                throw new InvalidOperationException("Missing -m07Output path for the performance evidence JSON.");
            var report = Capture();
            string json = JsonUtility.ToJson(report, true) + Environment.NewLine;
            File.WriteAllText(outputPath, json, new UTF8Encoding(false));
            UnityEngine.Debug.Log("LFX_M07_006_UNITY_RESULT " + json);
        }

        public static M07UnityPerformanceReport Capture()
        {
            var fixture = AssetDatabase.LoadAssetAtPath<TextAsset>(FixturePath);
            if (fixture == null) throw new InvalidOperationException("Pinned seed-712 fixture is missing.");
            string rawFixtureHash;
            using (var sha = SHA256.Create())
                rawFixtureHash = string.Concat(sha.ComputeHash(fixture.bytes).Select(value => value.ToString("x2", CultureInfo.InvariantCulture)));
            if (!string.Equals(rawFixtureHash, ExpectedRawFixtureSha256, StringComparison.Ordinal))
                throw new InvalidOperationException("Pinned seed-712 fixture SHA-256 did not match.");

            string json = fixture.text;
            var draft = LevelDraftJson.Parse(json);
            if (draft.seed != 712 || draft.validationStatus != "PROTOTYPE_ONLY" || draft.Validate().Count != 0)
                throw new InvalidOperationException("Pinned draft did not pass prototype-only validation.");
            string canonicalDraftHash = LevelDraftJson.Sha256(draft);
            if (!string.Equals(canonicalDraftHash, ExpectedCanonicalDraftSha256, StringComparison.Ordinal))
                throw new InvalidOperationException("Pinned seed-712 canonical draft SHA-256 did not match.");

            var operations = new[]
            {
                Measure("strict_parse_validate", () =>
                {
                    var parsed = LevelDraftJson.Parse(json);
                    if (parsed.Validate().Count != 0) throw new InvalidOperationException("Parsed fixture failed validation.");
                }),
                Measure("canonical_serialize_sha256", () =>
                {
                    string hash = LevelDraftJson.Sha256(draft);
                    if (hash.Length != 64) throw new InvalidOperationException("Unexpected SHA-256 output.");
                }),
                Measure("unity_json_clone", () =>
                {
                    var clone = draft.Clone();
                    if (clone == null || clone.seed != draft.seed || clone.cells.Length != draft.cells.Length)
                        throw new InvalidOperationException("Unity JSON clone did not preserve the draft shape.");
                }),
                Measure("draft_validation", () =>
                {
                    var errors = draft.Validate();
                    if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
                }),
            };
            using (var process = Process.GetCurrentProcess())
            {
                long workingSet = process.WorkingSet64;
                long peakWorkingSet = process.PeakWorkingSet64;
                return new M07UnityPerformanceReport
                {
                    taskId = "LFX-M07-006",
                    resultStatus = "REFERENCE_UNITY_EDITOR_BASELINE_ONLY",
                    engineStatus = "BLOCKED_ENG_M24",
                    runtimeGameplay = false,
                    releaseAuthorized = false,
                    unityVersion = Application.unityVersion,
                    operatingSystem = SystemInfo.operatingSystem,
                    processor = SystemInfo.processorType,
                    logicalProcessorCount = SystemInfo.processorCount,
                    fixtureSha256 = rawFixtureHash,
                    canonicalDraftSha256 = canonicalDraftHash,
                    iterations = Iterations,
                    observationBudgetMs = ObservationBudgetMilliseconds,
                    workingSetBytes = workingSet,
                    peakWorkingSetBytes = peakWorkingSet,
                    processWorkingSetMetricAvailable = workingSet > 0 && peakWorkingSet > 0,
                    gcTotalBytes = GC.GetTotalMemory(false),
                    operations = operations,
                };
            }
        }

        private static M07OperationMeasurement Measure(string name, Action action)
        {
            for (int warmup = 0; warmup < 3; warmup++) action();
            var elapsed = new double[Iterations];
            long allocatedBefore = GC.GetAllocatedBytesForCurrentThread();
            for (int index = 0; index < Iterations; index++)
            {
                long started = Stopwatch.GetTimestamp();
                action();
                elapsed[index] = (Stopwatch.GetTimestamp() - started) * 1000.0 / Stopwatch.Frequency;
            }
            long allocated = GC.GetAllocatedBytesForCurrentThread() - allocatedBefore;
            var ordered = (double[])elapsed.Clone();
            Array.Sort(ordered);
            double median = (ordered[(Iterations - 1) / 2] + ordered[Iterations / 2]) / 2.0;
            double p95 = ordered[(int)Math.Ceiling(Iterations * 0.95) - 1];
            double worst = ordered[Iterations - 1];
            return new M07OperationMeasurement
            {
                operation = name,
                iterations = Iterations,
                samplesMs = elapsed,
                medianMs = median,
                p95Ms = p95,
                worstMs = worst,
                allocatedBytesPerCall = (double)allocated / Iterations,
                allocationMetricAvailable = allocated > 0,
                status = p95 <= ObservationBudgetMilliseconds ? "OBSERVED_WITHIN_BUDGET" : "OBSERVED_OVER_BUDGET",
            };
        }
    }
}
