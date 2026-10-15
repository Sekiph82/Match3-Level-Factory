using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.RegularExpressions;
using UnityEngine;

namespace Match3Factory
{
    [Serializable]
    public sealed class PlayerVisibleMetadataDraft
    {
        public int schemaVersion = 1;
        public string gameProfileId = "Coral_Rescue";
        public string nextLevelTeaserKey = "";
        public string chapterProgressLabelKey = "";
        public int journeyLevelCount = 10;
        public ChestMilestoneMetadata[] chestMilestones = Array.Empty<ChestMilestoneMetadata>();
        public CollectionItemMetadata[] collectionItems = Array.Empty<CollectionItemMetadata>();
        public string expiryUtc = "";
        public string expirySourceReference = "";
        public string expiryDisclosureKey = "";

        public List<string> Validate()
        {
            var errors = new List<string>();
            if (schemaVersion != 1) errors.Add("Unsupported player metadata schemaVersion; expected 1.");
            if (!GameProfileCatalog.AllProfileIds.Contains(gameProfileId)) errors.Add("Unknown gameProfileId.");
            if (!string.IsNullOrEmpty(nextLevelTeaserKey) && !IsKey(nextLevelTeaserKey)) errors.Add("nextLevelTeaserKey must be a stable localization key.");
            if (!string.IsNullOrEmpty(chapterProgressLabelKey) && !IsKey(chapterProgressLabelKey)) errors.Add("chapterProgressLabelKey must be a stable localization key.");
            if (journeyLevelCount != 10) errors.Add("journeyLevelCount must remain exactly 10 in schema v1.");

            var milestoneIds = new HashSet<string>(StringComparer.Ordinal);
            if (chestMilestones == null || chestMilestones.Length > 10) errors.Add("chestMilestones must contain 0..10 entries.");
            else foreach (var item in chestMilestones)
            {
                if (item == null) { errors.Add("chestMilestones cannot contain null entries."); continue; }
                if (!IsKey(item.milestoneId) || !milestoneIds.Add(item.milestoneId)) errors.Add("Chest milestone IDs must be unique stable keys.");
                if (item.atLevel < 1 || item.atLevel > 10) errors.Add("Chest milestone atLevel must be 1..10.");
                if (item.starThreshold < 1 || item.starThreshold > 3) errors.Add("Chest milestone starThreshold must be 1..3.");
                if (!IsKey(item.displayLabelKey)) errors.Add("Chest milestone displayLabelKey must be a stable localization key.");
            }

            var itemIds = new HashSet<string>(StringComparer.Ordinal);
            if (collectionItems == null || collectionItems.Length > 100) errors.Add("collectionItems must contain 0..100 entries.");
            else foreach (var item in collectionItems)
            {
                if (item == null) { errors.Add("collectionItems cannot contain null entries."); continue; }
                if (!IsKey(item.itemId) || !itemIds.Add(item.itemId)) errors.Add("Collection item IDs must be unique stable keys.");
                if (!IsKey(item.packId)) errors.Add("Collection packId must be a stable key.");
                if (!IsKey(item.displayLabelKey)) errors.Add("Collection displayLabelKey must be a stable localization key.");
            }

            bool hasExpiry = !string.IsNullOrEmpty(expiryUtc);
            bool hasSource = !string.IsNullOrEmpty(expirySourceReference);
            bool hasDisclosure = !string.IsNullOrEmpty(expiryDisclosureKey);
            if (hasExpiry != hasSource || hasExpiry != hasDisclosure)
                errors.Add("Expiry UTC, explicit source reference and disclosure key must be supplied together; no expiry is inferred.");
            if (hasExpiry && (!Regex.IsMatch(expiryUtc, @"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$") ||
                !DateTime.TryParseExact(expiryUtc, "yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out _)))
                errors.Add("expiryUtc must be a valid UTC timestamp in yyyy-MM-ddTHH:mm:ssZ format.");
            if (hasSource && (expirySourceReference.Length > 256 || string.IsNullOrWhiteSpace(expirySourceReference))) errors.Add("expirySourceReference must be explicit and at most 256 characters.");
            if (hasDisclosure && !IsKey(expiryDisclosureKey)) errors.Add("expiryDisclosureKey must be a stable localization key.");
            return errors;
        }

        public PlayerVisibleMetadataDraft Clone() => JsonUtility.FromJson<PlayerVisibleMetadataDraft>(JsonUtility.ToJson(this));
        public string ToJson() => JsonUtility.ToJson(this, true);
        public static PlayerVisibleMetadataDraft FromJson(string json)
        {
            if (string.IsNullOrWhiteSpace(json) || System.Text.Encoding.UTF8.GetByteCount(json) > 256_000)
                throw new ArgumentException("Player metadata JSON is empty or exceeds 256 KB.", nameof(json));
            var result = JsonUtility.FromJson<PlayerVisibleMetadataDraft>(json);
            if (result == null) throw new ArgumentException("Player metadata JSON is invalid.", nameof(json));
            var errors = result.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            return result;
        }

        private static bool IsKey(string value) => !string.IsNullOrEmpty(value) && value.Length <= 128 && Regex.IsMatch(value, "^[A-Za-z0-9._-]+$");
    }

    [Serializable]
    public sealed class ChestMilestoneMetadata
    {
        public string milestoneId;
        public int atLevel = 10;
        public int starThreshold = 1;
        public string displayLabelKey;
    }

    [Serializable]
    public sealed class CollectionItemMetadata
    {
        public string itemId;
        public string packId;
        public string displayLabelKey;
    }
}
