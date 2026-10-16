using System.Linq;
using System.IO;
using System.Text;
using NUnit.Framework;

namespace Match3Factory.Tests
{
    public sealed class PlayerVisibleMetadataTests
    {
        [Test]
        public void VersionedPlayerMetadataRoundTripsWithoutGrantingGameLogic()
        {
            var value = new PlayerVisibleMetadataDraft
            {
                gameProfileId = "Wonder_Pop",
                nextLevelTeaserKey = "teaser.chapter2.level1",
                chapterProgressLabelKey = "progress.chapter2",
                chestMilestones = new[] { new ChestMilestoneMetadata { milestoneId = "chest.level10", atLevel = 10, starThreshold = 3, displayLabelKey = "chest.level10.label" } },
                collectionItems = new[] { new CollectionItemMetadata { itemId = "shell.blue", packId = "shells.coastal", displayLabelKey = "collection.shell.blue" } },
                expiryUtc = "2027-01-01T00:00:00Z",
                expirySourceReference = "owner-content-record-42",
                expiryDisclosureKey = "event.expires.utc"
            };
            Assert.That(value.Validate(), Is.Empty);
            var parsed = PlayerVisibleMetadataDraft.FromJson(value.ToJson());
            Assert.That(parsed.schemaVersion, Is.EqualTo(1));
            Assert.That(parsed.journeyLevelCount, Is.EqualTo(10));
            Assert.That(parsed.chestMilestones.Single().starThreshold, Is.EqualTo(3));
            Assert.That(parsed.collectionItems.Single().packId, Is.EqualTo("shells.coastal"));
            Assert.That(parsed.expirySourceReference, Is.EqualTo("owner-content-record-42"));
            Assert.That(parsed.Validate(), Is.Empty);
        }

        [Test]
        public void InvalidMilestonesDuplicateCollectionsAndUnsubstantiatedExpiryAreRejected()
        {
            var value = new PlayerVisibleMetadataDraft
            {
                nextLevelTeaserKey = "../unsafe",
                journeyLevelCount = 9,
                chestMilestones = new[]
                {
                    new ChestMilestoneMetadata { milestoneId = "same", atLevel = 11, starThreshold = 4, displayLabelKey = "label" },
                    new ChestMilestoneMetadata { milestoneId = "same", atLevel = 10, starThreshold = 1, displayLabelKey = "label" }
                },
                collectionItems = new[]
                {
                    new CollectionItemMetadata { itemId = "same", packId = "pack", displayLabelKey = "label" },
                    new CollectionItemMetadata { itemId = "same", packId = "pack", displayLabelKey = "label" }
                },
                expiryUtc = "2027-02-31T00:00:00Z",
                expiryDisclosureKey = "expires.label"
            };
            var errors = value.Validate();
            Assert.That(errors.Any(error => error.Contains("localization key")), Is.True);
            Assert.That(errors.Any(error => error.Contains("exactly 10")), Is.True);
            Assert.That(errors.Any(error => error.Contains("unique stable keys")), Is.True);
            Assert.That(errors.Any(error => error.Contains("valid UTC timestamp")), Is.True);
            Assert.That(errors.Any(error => error.Contains("supplied together")), Is.True);
        }

        [Test]
        public void UnsupportedMetadataVersionIsRejectedWithoutChangingCallerJson()
        {
            string json = new PlayerVisibleMetadataDraft { schemaVersion = 2 }.ToJson();
            var original = json;
            Assert.Throws<System.InvalidOperationException>(() => PlayerVisibleMetadataDraft.FromJson(json));
            Assert.That(json, Is.EqualTo(original));
        }

        [TestCase("unknown-root-field")]
        [TestCase("duplicate-root-key")]
        [TestCase("unknown-nested-field")]
        [TestCase("duplicate-nested-key")]
        [TestCase("null-nested-entry")]
        [TestCase("wrong-array-type")]
        [TestCase("wrong-nested-type")]
        [TestCase("missing-root-field")]
        [TestCase("oversized-json")]
        public void StrictMetadataParserRejectsMalformedOrForeignFieldsWithoutMutatingInput(string failure)
        {
            var value = new PlayerVisibleMetadataDraft { chestMilestones = new[] { new ChestMilestoneMetadata { milestoneId = "chest.one", atLevel = 1, starThreshold = 2, displayLabelKey = "chest.one.label" } } };
            string json = value.ToJson();
            switch (failure)
            {
                case "unknown-root-field": json = json.TrimEnd('}') + ",\"foreign\":true}"; break;
                case "duplicate-root-key": json = json.TrimEnd('}') + ",\"schemaVersion\":1}"; break;
                case "unknown-nested-field": json = json.Replace("\"displayLabelKey\": \"chest.one.label\"", "\"displayLabelKey\": \"chest.one.label\", \"unexpected\": 1"); break;
                case "duplicate-nested-key": json = json.Replace("\"milestoneId\": \"chest.one\"", "\"milestoneId\": \"chest.one\", \"milestoneId\": \"chest.other\""); break;
                case "null-nested-entry": json = json.Replace("\"chestMilestones\": [", "\"chestMilestones\": [null,"); break;
                case "wrong-array-type": json = System.Text.RegularExpressions.Regex.Replace(json, "\"chestMilestones\"\\s*:\\s*\\[.*?\\]", "\"chestMilestones\":null", System.Text.RegularExpressions.RegexOptions.Singleline); break;
                case "wrong-nested-type": json = json.Replace("\"atLevel\": 1", "\"atLevel\": 1.0"); break;
                case "missing-root-field": json = System.Text.RegularExpressions.Regex.Replace(json, ",\\s*\"expiryDisclosureKey\"\\s*:\\s*\"\"", ""); break;
                case "oversized-json": json = new string(' ', 256_001); break;
            }
            string original = json;
            Assert.Catch<System.Exception>(() => PlayerVisibleMetadataDraft.FromJson(json));
            Assert.That(json, Is.EqualTo(original));
        }

        [Test]
        public void MetadataAtomicSavePreservesOriginalBytesWhenStagingFails()
        {
            string directory = Path.Combine(Path.GetTempPath(), "metadata-atomic-" + System.Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(directory);
            string path = Path.Combine(directory, "campaign.json");
            byte[] original = Encoding.UTF8.GetBytes("owner-authored bytes\r\n");
            File.WriteAllBytes(path, original);
            Assert.Throws<IOException>(() => PlayerVisibleMetadataStore.Save(path, new PlayerVisibleMetadataDraft(), _ => throw new IOException("injected stage failure")));
            Assert.That(File.ReadAllBytes(path), Is.EqualTo(original));
            Assert.That(Directory.GetFiles(directory, "*.tmp-*").Length, Is.Zero);
            PlayerVisibleMetadataStore.Save(path, new PlayerVisibleMetadataDraft());
            Assert.That(PlayerVisibleMetadataDraft.FromJson(File.ReadAllText(path)).schemaVersion, Is.EqualTo(1));
            Assert.That(Directory.GetFiles(directory, "campaign.json.bak-*").Length, Is.EqualTo(1));
        }
    }
}
