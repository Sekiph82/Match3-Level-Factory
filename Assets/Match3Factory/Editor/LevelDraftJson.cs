using System;
using System.Security.Cryptography;
using System.Text;

namespace Match3Factory
{
    public static class LevelDraftJson
    {
        public static string Serialize(LevelDraft draft)
        {
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            var errors = draft.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            return UnityEngine.JsonUtility.ToJson(draft.Canonicalized(), true);
        }

        public static string Sha256(LevelDraft draft)
        {
            byte[] bytes = Encoding.UTF8.GetBytes(Serialize(draft));
            using (var hash = SHA256.Create())
            {
                var digest = hash.ComputeHash(bytes);
                var text = new StringBuilder(digest.Length * 2);
                foreach (byte value in digest) text.Append(value.ToString("x2"));
                return text.ToString();
            }
        }

        public static LevelDraft Parse(string json)
        {
            if (string.IsNullOrWhiteSpace(json) || json.Length > 2_000_000)
                throw new ArgumentException("Draft JSON is empty or exceeds the 2 MB limit.", nameof(json));
            var draft = UnityEngine.JsonUtility.FromJson<LevelDraft>(json);
            if (draft == null) throw new ArgumentException("Draft JSON does not contain a LevelDraft.", nameof(json));
            var errors = draft.Validate();
            if (errors.Count != 0) throw new InvalidOperationException(string.Join(" ", errors));
            return draft.Canonicalized();
        }
    }

    public enum EngineValidationStatus
    {
        BlockedEnginePackageUnavailable,
        Ready
    }

    public interface IEngineSimulationHost
    {
        EngineValidationStatus Status { get; }
        string BlockingReason { get; }
    }

    public sealed class EngineSimulationHostUnavailable : IEngineSimulationHost
    {
        public EngineValidationStatus Status => EngineValidationStatus.BlockedEnginePackageUnavailable;
        public string BlockingReason => "MATCH3_ENGINE ENG-M24 has no independently accepted final SDK package pin; authoritative simulation is blocked.";
    }
}
