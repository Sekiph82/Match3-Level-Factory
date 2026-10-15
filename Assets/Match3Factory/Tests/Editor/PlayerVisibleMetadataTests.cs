using System.Linq;
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
            const string json = "{\"schemaVersion\":2,\"gameProfileId\":\"Coral_Rescue\",\"journeyLevelCount\":10}";
            var original = json;
            Assert.Throws<System.InvalidOperationException>(() => PlayerVisibleMetadataDraft.FromJson(json));
            Assert.That(json, Is.EqualTo(original));
        }
    }
}
