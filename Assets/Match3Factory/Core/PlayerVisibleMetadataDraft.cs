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
        private static readonly string[] RootKeys = { "schemaVersion", "gameProfileId", "nextLevelTeaserKey", "chapterProgressLabelKey", "journeyLevelCount", "chestMilestones", "collectionItems", "expiryUtc", "expirySourceReference", "expiryDisclosureKey" };
        private static readonly string[] MilestoneKeys = { "milestoneId", "atLevel", "starThreshold", "displayLabelKey" };
        private static readonly string[] CollectionItemKeys = { "itemId", "packId", "displayLabelKey" };
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
            var root = StrictMetadataJsonReader.Parse(json) as Dictionary<string, object>;
            if (root == null) throw new ArgumentException("Player metadata JSON root must be an object.", nameof(json));
            RequireKeys(root, RootKeys, "player metadata");
            RequireInteger(root, "schemaVersion"); RequireInteger(root, "journeyLevelCount");
            RequireString(root, "gameProfileId"); RequireString(root, "nextLevelTeaserKey"); RequireString(root, "chapterProgressLabelKey");
            RequireString(root, "expiryUtc"); RequireString(root, "expirySourceReference"); RequireString(root, "expiryDisclosureKey");
            RequireArray(root, "chestMilestones", MilestoneKeys);
            RequireArray(root, "collectionItems", CollectionItemKeys);
            var result = JsonUtility.FromJson<PlayerVisibleMetadataDraft>(json);
            if (result == null) throw new ArgumentException("Player metadata JSON is invalid.", nameof(json));
            var errors = result.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            return result;
        }

        private static void RequireKeys(Dictionary<string, object> value, string[] required, string context)
        {
            var allowed = new HashSet<string>(required, StringComparer.Ordinal);
            foreach (var key in value.Keys) if (!allowed.Contains(key)) throw new ArgumentException("Unknown " + context + " field: " + key + ".");
            foreach (var key in required) if (!value.ContainsKey(key)) throw new ArgumentException("Missing " + context + " field: " + key + ".");
        }

        private static void RequireArray(Dictionary<string, object> root, string key, string[] itemKeys)
        {
            var values = root[key] as List<object>;
            if (values == null) throw new ArgumentException(key + " must be an array.");
            foreach (var item in values)
            {
                var fields = item as Dictionary<string, object>;
                if (fields == null) throw new ArgumentException(key + " entries must be objects.");
                RequireKeys(fields, itemKeys, key + " entry");
                foreach (var field in itemKeys)
                {
                    if (key == "chestMilestones" && (field == "atLevel" || field == "starThreshold"))
                    {
                        if (!(fields[field] is long)) throw new ArgumentException(key + "." + field + " must be an integer.");
                    }
                    else if (!(fields[field] is string)) throw new ArgumentException(key + "." + field + " must be a string.");
                }
            }
        }

        private static void RequireInteger(Dictionary<string, object> value, string key)
        {
            if (!(value[key] is long)) throw new ArgumentException(key + " must be an integer.");
        }

        private static void RequireString(Dictionary<string, object> value, string key)
        {
            if (!(value[key] is string)) throw new ArgumentException(key + " must be a string.");
        }

        private static bool IsKey(string value) => !string.IsNullOrEmpty(value) && value.Length <= 128 && Regex.IsMatch(value, "^[A-Za-z0-9._-]+$");

        private sealed class StrictMetadataJsonReader
        {
            private const int MaxDepth = 32;
            private const int MaxElements = 4096;
            private readonly string text;
            private int index, depth, elements;
            private StrictMetadataJsonReader(string text) { this.text = text; }

            public static object Parse(string text)
            {
                var reader = new StrictMetadataJsonReader(text);
                var result = reader.Value(); reader.Space();
                if (reader.index != text.Length) throw reader.Error("Unexpected content after JSON value.");
                return result;
            }

            private object Value()
            {
                if (++elements > MaxElements) throw Error("Player metadata JSON element budget exceeded.");
                Space(); if (index >= text.Length) throw Error("Expected a JSON value.");
                char c = text[index];
                if (c == '{') return Object(); if (c == '[') return Array(); if (c == '"') return String();
                if (c == 't') { Literal("true"); return true; } if (c == 'f') { Literal("false"); return false; } if (c == 'n') { Literal("null"); return null; }
                if (c == '-' || (c >= '0' && c <= '9')) return Number();
                throw Error("Invalid JSON value.");
            }

            private Dictionary<string, object> Object()
            {
                Enter();
                try
                {
                    index++; Space(); var result = new Dictionary<string, object>(StringComparer.Ordinal);
                    if (Take('}')) return result;
                    while (true)
                    {
                        Space(); if (index >= text.Length || text[index] != '"') throw Error("Object key must be a string.");
                        string key = String(); Space(); Need(':'); object value = Value();
                        if (result.ContainsKey(key)) throw Error("Duplicate JSON key: " + key + ".");
                        result.Add(key, value); Space(); if (Take('}')) return result; Need(',');
                    }
                }
                finally { depth--; }
            }

            private List<object> Array()
            {
                Enter();
                try
                {
                    index++; Space(); var result = new List<object>(); if (Take(']')) return result;
                    while (true) { result.Add(Value()); Space(); if (Take(']')) return result; Need(','); }
                }
                finally { depth--; }
            }

            private string String()
            {
                Need('"'); var result = new System.Text.StringBuilder();
                while (index < text.Length)
                {
                    char c = text[index++]; if (c == '"') return result.ToString();
                    if (c < 0x20) throw Error("Unescaped control character in string.");
                    if (c != '\\') { result.Append(c); continue; }
                    if (index >= text.Length) throw Error("Incomplete string escape.");
                    char e = text[index++];
                    switch (e)
                    {
                        case '"': result.Append('"'); break; case '\\': result.Append('\\'); break; case '/': result.Append('/'); break;
                        case 'b': result.Append('\b'); break; case 'f': result.Append('\f'); break; case 'n': result.Append('\n'); break;
                        case 'r': result.Append('\r'); break; case 't': result.Append('\t'); break;
                        case 'u':
                            if (index + 4 > text.Length) throw Error("Incomplete Unicode escape.");
                            int code; if (!int.TryParse(text.Substring(index, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out code)) throw Error("Invalid Unicode escape.");
                            result.Append((char)code); index += 4; break;
                        default: throw Error("Invalid string escape.");
                    }
                }
                throw Error("Unterminated string.");
            }

            private object Number()
            {
                int start = index; Take('-');
                if (Take('0')) { if (index < text.Length && text[index] >= '0' && text[index] <= '9') throw Error("Leading zero in number."); }
                else { if (index >= text.Length || text[index] < '1' || text[index] > '9') throw Error("Invalid number."); while (index < text.Length && text[index] >= '0' && text[index] <= '9') index++; }
                bool integer = true;
                if (Take('.')) { integer = false; Digits(); }
                if (Take('e') || Take('E')) { integer = false; if (!Take('+')) Take('-'); Digits(); }
                string raw = text.Substring(start, index - start); long whole;
                if (integer && long.TryParse(raw, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out whole)) return whole;
                double number; if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out number)) return number;
                throw Error("Number is invalid or outside the supported range.");
            }

            private void Enter() { if (depth >= MaxDepth) throw Error("JSON nesting depth exceeds the maximum of 32."); depth++; }
            private void Digits() { int start = index; while (index < text.Length && text[index] >= '0' && text[index] <= '9') index++; if (start == index) throw Error("Expected digits."); }
            private void Literal(string value) { if (index + value.Length > text.Length || string.CompareOrdinal(text, index, value, 0, value.Length) != 0) throw Error("Invalid JSON literal."); index += value.Length; }
            private void Space() { while (index < text.Length && (text[index] == ' ' || text[index] == '\t' || text[index] == '\r' || text[index] == '\n')) index++; }
            private bool Take(char c) { if (index < text.Length && text[index] == c) { index++; return true; } return false; }
            private void Need(char c) { if (!Take(c)) throw Error("Expected '" + c + "'."); }
            private ArgumentException Error(string message) => new ArgumentException(message + " At character " + index.ToString(CultureInfo.InvariantCulture) + ".");
        }
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
