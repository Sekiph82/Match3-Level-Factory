using System;
using System.Collections.Generic;
using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace Match3Factory
{
    public static class LevelDraftJson
    {
        private static readonly string[] DraftKeys = { "draftVersion", "validationStatus", "gameProfileId", "profileVersion", "worldId", "chapterId", "levelId", "releaseChannel", "platform", "locale", "minEngineVersion", "maxEngineVersion", "seed", "width", "height", "layers", "activeMask", "moveBudget", "timedMode", "timeLimitSeconds", "oneStarThreshold", "twoStarThreshold", "threeStarThreshold", "difficultyLabel", "editorHintKey", "cells", "goals", "engineSchemaVersion", "sourceRepository", "sourceRevision", "sourceKind" };
        private static readonly string[] CellKeys = { "row", "column", "layer", "active", "locked", "contentId", "obstacleId", "obstacleDurability", "lockDurability", "specialId" };
        private static readonly string[] GoalKeys = { "goalId", "targetId", "targetCount" };

        public static string Serialize(LevelDraft draft)
        {
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            var errors = draft.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            return SerializeCanonical(draft.Canonicalized());
        }

        public static string Sha256(LevelDraft draft)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(Serialize(draft));
            using (var hash = SHA256.Create())
            {
                var digest = hash.ComputeHash(bytes);
                var text = new StringBuilder(digest.Length * 2);
                foreach (byte value in digest) text.Append(value.ToString("x2", CultureInfo.InvariantCulture));
                return text.ToString();
            }
        }

        // INTERNAL_REUSE of the existing bounded UTF-8 JSON parser for other
        // editor-only receipts. Rejects duplicate keys, trailing content,
        // unknown/missing root keys, excessive nesting and oversized arrays.
        internal static void AssertStrictObjectKeys(string json, string[] requiredKeys, string context)
        {
            if (string.IsNullOrWhiteSpace(json) || Encoding.UTF8.GetByteCount(json) > 256000)
                throw new ArgumentException("Editor receipt is empty or exceeds 256 KB.");
            var value = StrictJsonReader.Parse(json) as Dictionary<string, object>;
            if (value == null) throw new ArgumentException("Editor receipt root must be an object.");
            RequireKeys(value, requiredKeys, context);
        }

        public static LevelDraft Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json) || Encoding.UTF8.GetByteCount(json) > 2_000_000)
                throw new ArgumentException("Draft JSON is empty or exceeds the 2 MB limit.", nameof(json));
            var root = StrictJsonReader.Parse(json) as Dictionary<string, object>;
            if (root == null) throw new ArgumentException("Draft JSON root must be an object.", nameof(json));
            RequireKeys(root, DraftKeys, "draft");
            RequireInteger(root, "draftVersion"); RequireInteger(root, "seed");
            RequireInteger(root, "profileVersion");
            RequireInteger(root, "width"); RequireInteger(root, "height"); RequireInteger(root, "layers"); RequireInteger(root, "moveBudget");
            RequireBoolean(root, "timedMode"); RequireInteger(root, "timeLimitSeconds");
            RequireInteger(root, "oneStarThreshold"); RequireInteger(root, "twoStarThreshold"); RequireInteger(root, "threeStarThreshold");
            RequireString(root, "validationStatus"); RequireString(root, "gameProfileId");
            RequireString(root, "worldId"); RequireString(root, "chapterId"); RequireString(root, "levelId");
            RequireString(root, "releaseChannel"); RequireString(root, "platform"); RequireString(root, "locale");
            RequireString(root, "difficultyLabel"); RequireNullableString(root, "editorHintKey");
            RequireNullableString(root, "minEngineVersion"); RequireNullableString(root, "maxEngineVersion");
            RequireNullableString(root, "engineSchemaVersion"); RequireNullableString(root, "sourceRepository"); RequireNullableString(root, "sourceRevision"); RequireNullableString(root, "sourceKind");
            var mask = root["activeMask"] as List<object>;
            if (mask == null) throw new ArgumentException("activeMask must be an array.", nameof(json));
            foreach (var item in mask) if (!(item is bool)) throw new ArgumentException("activeMask entries must be booleans.", nameof(json));
            var cells = root["cells"] as List<object>;
            if (cells == null) throw new ArgumentException("cells must be an array.", nameof(json));
            foreach (var item in cells)
            {
                var cell = item as Dictionary<string, object>;
                if (cell == null) throw new ArgumentException("Each cell must be an object.", nameof(json));
                RequireKeys(cell, CellKeys, "cell");
                RequireInteger(cell, "row"); RequireInteger(cell, "column"); RequireInteger(cell, "layer");
                RequireInteger(cell, "obstacleDurability"); RequireInteger(cell, "lockDurability");
                RequireBoolean(cell, "active"); RequireBoolean(cell, "locked");
                RequireCellIdentifier(cell, "contentId"); RequireCellIdentifier(cell, "obstacleId"); RequireCellIdentifier(cell, "specialId");
            }
            var goals = root["goals"] as List<object>;
            if (goals == null) throw new ArgumentException("goals must be an array.", nameof(json));
            foreach (var item in goals)
            {
                var goal = item as Dictionary<string, object>;
                if (goal == null) throw new ArgumentException("Each goal must be an object.", nameof(json));
                RequireKeys(goal, GoalKeys, "goal");
                RequireString(goal, "goalId"); RequireString(goal, "targetId"); RequireInteger(goal, "targetCount");
            }
            var draft = UnityEngine.JsonUtility.FromJson<LevelDraft>(json);
            if (draft == null) throw new ArgumentException("Draft JSON does not contain a LevelDraft.", nameof(json));
            foreach (var cell in draft.cells)
            {
                if (string.IsNullOrEmpty(cell.contentId)) cell.contentId = null;
                if (string.IsNullOrEmpty(cell.obstacleId)) cell.obstacleId = null;
                if (string.IsNullOrEmpty(cell.specialId)) cell.specialId = null;
            }
            if (string.IsNullOrEmpty(draft.editorHintKey)) draft.editorHintKey = null;
            var errors = draft.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            return draft.Canonicalized();
        }

        private static string SerializeCanonical(LevelDraft draft)
        {
            var b = new StringBuilder(1024);
            b.Append('{');
            Property(b, "draftVersion"); b.Append(draft.draftVersion.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "validationStatus"); StringValue(b, draft.validationStatus); b.Append(',');
            Property(b, "gameProfileId"); StringValue(b, draft.gameProfileId); b.Append(',');
            Property(b, "profileVersion"); b.Append(draft.profileVersion.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "worldId"); StringValue(b, draft.worldId); b.Append(',');
            Property(b, "chapterId"); StringValue(b, draft.chapterId); b.Append(',');
            Property(b, "levelId"); StringValue(b, draft.levelId); b.Append(',');
            Property(b, "releaseChannel"); StringValue(b, draft.releaseChannel); b.Append(',');
            Property(b, "platform"); StringValue(b, draft.platform); b.Append(',');
            Property(b, "locale"); StringValue(b, draft.locale); b.Append(',');
            Property(b, "minEngineVersion"); NullableString(b, draft.minEngineVersion); b.Append(',');
            Property(b, "maxEngineVersion"); NullableString(b, draft.maxEngineVersion); b.Append(',');
            Property(b, "seed"); b.Append(draft.seed.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "width"); b.Append(draft.width.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "height"); b.Append(draft.height.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "layers"); b.Append(draft.layers.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "activeMask"); b.Append('[');
            for (int i = 0; i < draft.activeMask.Length; i++) { if (i > 0) b.Append(','); b.Append(draft.activeMask[i] ? "true" : "false"); }
            b.Append("],"); Property(b, "moveBudget"); b.Append(draft.moveBudget.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "timedMode"); b.Append(draft.timedMode ? "true" : "false"); b.Append(',');
            Property(b, "timeLimitSeconds"); b.Append(draft.timeLimitSeconds.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "oneStarThreshold"); b.Append(draft.oneStarThreshold.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "twoStarThreshold"); b.Append(draft.twoStarThreshold.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "threeStarThreshold"); b.Append(draft.threeStarThreshold.ToString(CultureInfo.InvariantCulture)); b.Append(',');
            Property(b, "difficultyLabel"); StringValue(b, draft.difficultyLabel); b.Append(',');
            Property(b, "editorHintKey"); NullableString(b, draft.editorHintKey); b.Append(',');
            Property(b, "cells"); b.Append('[');
            for (int i = 0; i < draft.cells.Length; i++)
            {
                if (i > 0) b.Append(',');
                var cell = draft.cells[i]; b.Append('{');
                Property(b, "row"); b.Append(cell.row.ToString(CultureInfo.InvariantCulture)); b.Append(',');
                Property(b, "column"); b.Append(cell.column.ToString(CultureInfo.InvariantCulture)); b.Append(',');
                Property(b, "layer"); b.Append(cell.layer.ToString(CultureInfo.InvariantCulture)); b.Append(',');
                Property(b, "active"); b.Append(cell.active ? "true" : "false"); b.Append(',');
                Property(b, "locked"); b.Append(cell.locked ? "true" : "false"); b.Append(',');
                Property(b, "contentId"); NullableString(b, cell.contentId); b.Append(',');
                Property(b, "obstacleId"); NullableString(b, cell.obstacleId); b.Append(',');
                Property(b, "obstacleDurability"); b.Append(cell.obstacleDurability.ToString(CultureInfo.InvariantCulture)); b.Append(',');
                Property(b, "lockDurability"); b.Append(cell.lockDurability.ToString(CultureInfo.InvariantCulture)); b.Append(',');
                Property(b, "specialId"); NullableString(b, cell.specialId); b.Append('}');
            }
            b.Append("],"); Property(b, "goals"); b.Append('[');
            for (int i = 0; i < draft.goals.Length; i++)
            {
                if (i > 0) b.Append(','); var goal = draft.goals[i]; b.Append('{');
                Property(b, "goalId"); StringValue(b, goal.goalId); b.Append(',');
                Property(b, "targetId"); StringValue(b, goal.targetId); b.Append(',');
                Property(b, "targetCount"); b.Append(goal.targetCount.ToString(CultureInfo.InvariantCulture)); b.Append('}');
            }
            b.Append("],"); Property(b, "engineSchemaVersion"); NullableString(b, draft.engineSchemaVersion); b.Append(',');
            Property(b, "sourceRepository"); NullableString(b, draft.sourceRepository); b.Append(',');
            Property(b, "sourceRevision"); NullableString(b, draft.sourceRevision); b.Append(',');
            Property(b, "sourceKind"); NullableString(b, draft.sourceKind); b.Append('}');
            return b.ToString();
        }

        private static void Property(StringBuilder b, string name) { StringValue(b, name); b.Append(':'); }
        private static void NullableString(StringBuilder b, string value) { if (value == null) b.Append("null"); else StringValue(b, value); }
        private static void StringValue(StringBuilder b, string value)
        {
            b.Append('"');
            foreach (char c in value ?? string.Empty)
            {
                switch (c)
                {
                    case '"': b.Append("\\\""); break; case '\\': b.Append("\\\\"); break;
                    case '\b': b.Append("\\b"); break; case '\f': b.Append("\\f"); break;
                    case '\n': b.Append("\\n"); break; case '\r': b.Append("\\r"); break; case '\t': b.Append("\\t"); break;
                    default: if (c < 0x20) b.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture)); else b.Append(c); break;
                }
            }
            b.Append('"');
        }

        private static void RequireKeys(Dictionary<string, object> value, string[] required, string context)
        {
            var allowed = new HashSet<string>(required, StringComparer.Ordinal);
            foreach (var key in value.Keys) if (!allowed.Contains(key)) throw new ArgumentException("Unknown " + context + " field: " + key + ".");
            foreach (var key in required) if (!value.ContainsKey(key)) throw new ArgumentException("Missing " + context + " field: " + key + ".");
        }
        private static void RequireInteger(Dictionary<string, object> value, string key)
        {
            if (!(value[key] is JsonInteger)) throw new ArgumentException(key + " must be an integer.");
        }
        private static void RequireBoolean(Dictionary<string, object> value, string key)
        {
            if (!(value[key] is bool)) throw new ArgumentException(key + " must be a boolean.");
        }
        private static void RequireString(Dictionary<string, object> value, string key)
        {
            if (!(value[key] is string)) throw new ArgumentException(key + " must be a string.");
        }
        private static void RequireNullableString(Dictionary<string, object> value, string key)
        {
            if (value[key] != null && !(value[key] is string)) throw new ArgumentException(key + " must be a string or null.");
        }
        private static void RequireCellIdentifier(Dictionary<string, object> value, string key)
        {
            RequireNullableString(value, key);
            if (value[key] is string text && (text.Length == 0 || text.Length > 128))
                throw new ArgumentException(key + " must be null or a non-empty string of at most 128 characters.");
        }

        private sealed class JsonInteger { public readonly long Value; public JsonInteger(long value) { Value = value; } }
        private sealed class StrictJsonReader
        {
            private const int MaxDepth = 64;
            private const int MaxElements = 65536;
            private readonly string text; private int index;
            private int depth;
            private int elements;
            private StrictJsonReader(string text) { this.text = text; }
            public static object Parse(string text)
            {
                var reader = new StrictJsonReader(text); var value = reader.Value(); reader.Space();
                if (reader.index != text.Length) throw new ArgumentException("Unexpected content after JSON value.");
                return value;
            }
            private object Value()
            {
                if (++elements > MaxElements) throw Error("JSON element budget exceeded (maximum 65536 values).");
                Space(); if (index >= text.Length) throw Error("Expected a JSON value.");
                char c = text[index];
                if (c == '{') return Object(); if (c == '[') return Array(); if (c == '"') return String();
                if (c == 't') { Literal("true"); return true; } if (c == 'f') { Literal("false"); return false; } if (c == 'n') { Literal("null"); return null; }
                if (c == '-' || (c >= '0' && c <= '9')) return Number();
                throw Error("Invalid JSON value.");
            }
            private Dictionary<string, object> Object()
            {
                EnterContainer();
                try
                {
                    index++; Space(); var result = new Dictionary<string, object>(StringComparer.Ordinal);
                    if (Take('}')) return result;
                    while (true)
                    {
                        Space(); if (index >= text.Length || text[index] != '"') throw Error("Object key must be a string.");
                        string key = String(); Space(); Need(':'); object value = Value();
                        if (result.ContainsKey(key)) throw Error("Duplicate JSON key: " + key);
                        result.Add(key, value); Space(); if (Take('}')) return result; Need(',');
                    }
                }
                finally { depth--; }
            }
            private List<object> Array()
            {
                EnterContainer();
                try
                {
                    index++; Space(); var result = new List<object>(); if (Take(']')) return result;
                    while (true) { result.Add(Value()); Space(); if (Take(']')) return result; Need(','); }
                }
                finally { depth--; }
            }
            private void EnterContainer()
            {
                if (depth >= MaxDepth) throw Error("JSON nesting depth exceeds the maximum of 64.");
                depth++;
            }
            private string String()
            {
                Need('"'); var result = new StringBuilder();
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
                        case 'b': result.Append('\b'); break; case 'f': result.Append('\f'); break; case 'n': result.Append('\n'); break; case 'r': result.Append('\r'); break; case 't': result.Append('\t'); break;
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
                int start = index; if (Take('-')) { }
                if (Take('0')) { if (index < text.Length && char.IsDigit(text[index])) throw Error("Leading zero in number."); }
                else { if (index >= text.Length || text[index] < '1' || text[index] > '9') throw Error("Invalid number."); while (index < text.Length && char.IsDigit(text[index])) index++; }
                bool integer = true;
                if (Take('.')) { integer = false; Digits(); }
                if (Take('e') || Take('E')) { integer = false; if (!Take('+')) Take('-'); Digits(); }
                string raw = text.Substring(start, index - start); long parsed;
                if (integer && long.TryParse(raw, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out parsed)) return new JsonInteger(parsed);
                if (double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out _)) return raw;
                throw Error("Number is invalid or outside the supported range.");
            }
            private void Digits() { int start = index; while (index < text.Length && char.IsDigit(text[index])) index++; if (start == index) throw Error("Expected digits."); }
            private void Literal(string value) { if (index + value.Length > text.Length || string.CompareOrdinal(text, index, value, 0, value.Length) != 0) throw Error("Invalid JSON literal."); index += value.Length; }
            private void Space() { while (index < text.Length && (text[index] == ' ' || text[index] == '\t' || text[index] == '\r' || text[index] == '\n')) index++; }
            private bool Take(char c) { if (index < text.Length && text[index] == c) { index++; return true; } return false; }
            private void Need(char c) { if (!Take(c)) throw Error("Expected '" + c + "'."); }
            private ArgumentException Error(string message) { return new ArgumentException(message + " At character " + index.ToString(CultureInfo.InvariantCulture) + "."); }
        }
    }

    public enum EngineValidationStatus { BlockedEnginePackageUnavailable, Ready }
    public interface IEngineSimulationHost { EngineValidationStatus Status { get; } string BlockingReason { get; } }
    public sealed class EngineSimulationHostUnavailable : IEngineSimulationHost
    {
        public EngineValidationStatus Status => EngineValidationStatus.BlockedEnginePackageUnavailable;
        public string BlockingReason => "MATCH3_ENGINE ENG-M24 has no independently accepted final SDK package pin; authoritative simulation is blocked.";
    }
}
