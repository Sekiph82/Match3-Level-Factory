using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace Match3Factory.Editor
{
    /// <summary>
    /// Verifies the cross-references written by the local authoring pipeline before
    /// a saved board is accepted for a read-only preview. This is integrity checking,
    /// not a signature or an Engine authority claim.
    /// </summary>
    public static class CampaignArtifactIntegrity
    {
        private const string ExpectedSourceKind = "FactoryOriginalLocalSampleBoard";

        [Serializable]
        private sealed class LocalSummary
        {
            public string sourceKind;
            public int localDraftCount;
            public int engineQualifiedCampaignLevels;
            public string engineStatus;
            public LocalRecord[] records;
        }

        [Serializable]
        private sealed class LocalRecord
        {
            public string profileId;
            public int seed;
            public string draftSha256;
            public string status;
            public string recordPath;
            public string recordSha256;
        }

        [Serializable]
        private sealed class LocalManifest
        {
            public int manifestVersion;
            public string sourceKind;
            public LocalManifestEntry[] entries;
        }

        [Serializable]
        private sealed class LocalManifestEntry
        {
            public string path;
            public long sizeBytes;
            public string sha256;
            public string draftSha256;
            public string status;
            public string profileId;
            public int seed;
        }

        public static void VerifyLocalRun(string runDirectory)
        {
            if (string.IsNullOrWhiteSpace(runDirectory) || !Directory.Exists(runDirectory))
                throw new InvalidDataException("Local authoring run directory is missing.");

            string summaryPath = Path.Combine(runDirectory, "summary.json");
            string manifestPath = Path.Combine(runDirectory, "manifest.json");
            if (!File.Exists(summaryPath) || !File.Exists(manifestPath))
                throw new InvalidDataException("Local authoring summary or manifest is missing.");

            LocalSummary summary = JsonUtility.FromJson<LocalSummary>(File.ReadAllText(summaryPath, Encoding.UTF8));
            LocalManifest manifest = JsonUtility.FromJson<LocalManifest>(File.ReadAllText(manifestPath, Encoding.UTF8));
            if (summary == null || manifest == null || summary.records == null || manifest.entries == null)
                throw new InvalidDataException("Local authoring summary or manifest schema is invalid.");
            if (manifest.manifestVersion != 1 || summary.sourceKind != ExpectedSourceKind || manifest.sourceKind != ExpectedSourceKind)
                throw new InvalidDataException("Local authoring summary or manifest version/source is unverifiable.");
            if (summary.localDraftCount != summary.records.Length || manifest.entries.Length != summary.records.Length)
                throw new InvalidDataException("Local authoring summary and manifest record counts disagree.");
            if (summary.engineQualifiedCampaignLevels != 0 || summary.engineStatus != "BLOCKED_ENG_M24")
                throw new InvalidDataException("Local preview artifact carries an invalid Engine authority status.");

            var entries = new Dictionary<string, LocalManifestEntry>(StringComparer.Ordinal);
            foreach (LocalManifestEntry entry in manifest.entries)
            {
                if (entry == null || string.IsNullOrWhiteSpace(entry.path) || !IsSha256(entry.sha256) || !IsSha256(entry.draftSha256))
                    throw new InvalidDataException("Local manifest contains an invalid entry.");
                ValidateRelativePath(entry.path);
                if (entries.ContainsKey(entry.path))
                    throw new InvalidDataException("Local manifest contains a duplicate path.");
                entries.Add(entry.path, entry);
            }

            var summaryPaths = new HashSet<string>(StringComparer.Ordinal);
            foreach (LocalRecord record in summary.records)
            {
                if (record == null || string.IsNullOrWhiteSpace(record.recordPath) || !IsSha256(record.recordSha256) || !IsSha256(record.draftSha256))
                    throw new InvalidDataException("Local summary contains an invalid record.");
                ValidateRelativePath(record.recordPath);
                if (!summaryPaths.Add(record.recordPath) || !entries.TryGetValue(record.recordPath, out LocalManifestEntry entry))
                    throw new InvalidDataException("Local summary paths are duplicated or absent from the manifest.");
                if (entry.profileId != record.profileId || entry.seed != record.seed || entry.status != record.status ||
                    !FixedEquals(entry.draftSha256, record.draftSha256) || !FixedEquals(entry.sha256, record.recordSha256))
                    throw new InvalidDataException("Local summary and manifest entry disagree.");

                string fullPath = Path.GetFullPath(Path.Combine(runDirectory, record.recordPath.Replace('/', Path.DirectorySeparatorChar)));
                string root = Path.GetFullPath(runDirectory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
                if (!fullPath.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(fullPath))
                    throw new InvalidDataException("A local preview record is missing or resolves outside its run.");
                byte[] bytes = File.ReadAllBytes(fullPath);
                if (bytes.LongLength != entry.sizeBytes || !FixedEquals(Sha256(bytes), entry.sha256) || !FixedEquals(Sha256(bytes), record.recordSha256))
                    throw new InvalidDataException("Local preview record bytes do not match the summary and manifest SHA-256 values.");
            }
        }

        private static void ValidateRelativePath(string path)
        {
            if (Path.IsPathRooted(path) || path.IndexOf('\\') >= 0 || path.Split('/').Any(part => string.IsNullOrWhiteSpace(part) || part == "." || part == ".."))
                throw new InvalidDataException("Local manifest path is unsafe.");
        }

        private static bool IsSha256(string value)
        {
            return value != null && value.Length == 64 && value.All(c => (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'));
        }

        private static string Sha256(byte[] bytes)
        {
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", string.Empty).ToLowerInvariant();
        }

        private static bool FixedEquals(string left, string right)
        {
            return string.Equals(left, right, StringComparison.OrdinalIgnoreCase);
        }
    }
}
