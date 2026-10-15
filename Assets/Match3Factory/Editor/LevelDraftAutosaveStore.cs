using System;
using System.IO;
using System.Text;

namespace Match3Factory
{
    public enum AutosaveRecoveryStatus { Missing, Current, Backup, Invalid }

    public static class LevelDraftAutosaveStore
    {
        public static void Save(string path, LevelDraft draft)
        {
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("Autosave path is required.", nameof(path));
            if (draft == null) throw new ArgumentNullException(nameof(draft));
            var errors = draft.Validate();
            if (errors.Count != 0) throw new InvalidOperationException("Invalid drafts are not autosaved: " + string.Join(" ", errors));
            string fullPath = Path.GetFullPath(path);
            Directory.CreateDirectory(Path.GetDirectoryName(fullPath));
            string temporary = fullPath + ".tmp-" + Guid.NewGuid().ToString("N");
            try
            {
                using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                {
                    writer.Write(LevelDraftJson.Serialize(draft));
                    writer.Flush();
                    stream.Flush(true);
                }
                if (File.Exists(fullPath)) File.Replace(temporary, fullPath, fullPath + ".bak", true);
                else File.Move(temporary, fullPath);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }

        public static bool TryLoad(string path, out LevelDraft draft, out AutosaveRecoveryStatus status, out string message)
        {
            draft = null; message = null;
            string fullPath = Path.GetFullPath(path);
            if (!File.Exists(fullPath)) { status = AutosaveRecoveryStatus.Missing; return false; }
            try
            {
                draft = LevelDraftJson.Parse(File.ReadAllText(fullPath, Encoding.UTF8));
                status = AutosaveRecoveryStatus.Current;
                return true;
            }
            catch (Exception currentError)
            {
                string backup = fullPath + ".bak";
                if (File.Exists(backup))
                {
                    try
                    {
                        draft = LevelDraftJson.Parse(File.ReadAllText(backup, Encoding.UTF8));
                        status = AutosaveRecoveryStatus.Backup;
                        message = "The latest autosave was invalid; recovered the previous valid version. " + currentError.Message;
                        return true;
                    }
                    catch (Exception backupError)
                    {
                        status = AutosaveRecoveryStatus.Invalid;
                        message = "Both autosave versions are invalid. " + currentError.Message + " " + backupError.Message;
                        return false;
                    }
                }
                status = AutosaveRecoveryStatus.Invalid;
                message = "Autosave is invalid and was left untouched. " + currentError.Message;
                return false;
            }
        }
    }
}
