using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Match3Factory.Editor;
using NUnit.Framework;

namespace Match3Factory.Tests
{
    public sealed class CampaignArtifactIntegrityTests
    {
        [Test]
        public void UnchangedVersionOneLocalRunPassesIntegrityCheck()
        {
            var run = CreateRun();
            Assert.DoesNotThrow(() => CampaignArtifactIntegrity.VerifyLocalRun(run));
        }

        [Test]
        public void ModifiedDraftBytesAreRejected()
        {
            var run = CreateRun();
            File.AppendAllText(Path.Combine(run, "drafts", "Coral_Rescue", "attempt-01.json"), " ", Encoding.UTF8);
            Assert.Throws<InvalidDataException>(() => CampaignArtifactIntegrity.VerifyLocalRun(run));
        }

        [Test]
        public void ModifiedManifestEntryIsRejectedAgainstSummary()
        {
            var run = CreateRun();
            string path = Path.Combine(run, "manifest.json");
            string json = File.ReadAllText(path, Encoding.UTF8).Replace(Hash(Encoding.UTF8.GetBytes("{}")), new string('a', 64));
            File.WriteAllText(path, json, new UTF8Encoding(false));
            Assert.Throws<InvalidDataException>(() => CampaignArtifactIntegrity.VerifyLocalRun(run));
        }

        [Test]
        public void InconsistentSummaryIsRejectedAgainstManifest()
        {
            var run = CreateRun();
            string path = Path.Combine(run, "summary.json");
            File.WriteAllText(path, File.ReadAllText(path, Encoding.UTF8).Replace("Coral_Rescue", "Wonder_Pop"), new UTF8Encoding(false));
            Assert.Throws<InvalidDataException>(() => CampaignArtifactIntegrity.VerifyLocalRun(run));
        }

        [Test]
        public void MissingRecordFileIsRejected()
        {
            var run = CreateRun(writeRecord: false);
            Assert.Throws<InvalidDataException>(() => CampaignArtifactIntegrity.VerifyLocalRun(run));
        }

        [Test]
        public void FakeSummaryShaIsRejected()
        {
            var run = CreateRun();
            string path = Path.Combine(run, "summary.json");
            File.WriteAllText(path, File.ReadAllText(path, Encoding.UTF8).Replace(Hash(Encoding.UTF8.GetBytes("{}")), new string('f', 64)), new UTF8Encoding(false));
            Assert.Throws<InvalidDataException>(() => CampaignArtifactIntegrity.VerifyLocalRun(run));
        }

        private static string CreateRun(bool writeRecord = true)
        {
            string artifacts = Path.Combine(Directory.GetCurrentDirectory(), "Artifacts");
            string run = Path.Combine(artifacts, "LFX-M11-R07-V03-integrity-" + Guid.NewGuid().ToString("N"));
            string draftPath = Path.Combine(run, "drafts", "Coral_Rescue", "attempt-01.json");
            Directory.CreateDirectory(Path.GetDirectoryName(draftPath));
            byte[] record = Encoding.UTF8.GetBytes("{}");
            string recordSha = Hash(record);
            string draftSha = new string('b', 64);
            if (writeRecord) File.WriteAllBytes(draftPath, record);

            File.WriteAllText(Path.Combine(run, "summary.json"),
                "{\"sourceKind\":\"FactoryOriginalLocalSampleBoard\",\"localDraftCount\":1,\"engineQualifiedCampaignLevels\":0,\"engineStatus\":\"BLOCKED_ENG_M24\",\"records\":[{" +
                "\"profileId\":\"Coral_Rescue\",\"seed\":7,\"draftSha256\":\"" + draftSha + "\",\"status\":\"LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY\",\"recordPath\":\"drafts/Coral_Rescue/attempt-01.json\",\"recordSha256\":\"" + recordSha + "\"}]}",
                new UTF8Encoding(false));
            File.WriteAllText(Path.Combine(run, "manifest.json"),
                "{\"manifestVersion\":1,\"sourceKind\":\"FactoryOriginalLocalSampleBoard\",\"entries\":[{" +
                "\"path\":\"drafts/Coral_Rescue/attempt-01.json\",\"sizeBytes\":" + record.Length + ",\"sha256\":\"" + recordSha + "\",\"draftSha256\":\"" + draftSha + "\",\"status\":\"LOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY\",\"profileId\":\"Coral_Rescue\",\"seed\":7}]}",
                new UTF8Encoding(false));
            return run;
        }

        private static string Hash(byte[] bytes)
        {
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", string.Empty).ToLowerInvariant();
        }
    }
}
