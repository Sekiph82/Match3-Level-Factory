using System;
using System.IO;
using System.Text;

namespace Match3Factory
{
    public static class PlayerVisibleMetadataStore
    {
        public static void Save(string path, PlayerVisibleMetadataDraft metadata) => Save(path, metadata, null);

        // The callback is an explicit fault-injection seam used by EditMode regression tests.
        public static void Save(string path, PlayerVisibleMetadataDraft metadata, Action<string> beforeCommit)
        {
            if (string.IsNullOrWhiteSpace(path)) throw new ArgumentException("Metadata path is required.", nameof(path));
            if (metadata == null) throw new ArgumentNullException(nameof(metadata));
            var errors = metadata.Validate();
            if (errors.Count != 0) throw new InvalidOperationException("Invalid metadata is not saved: " + string.Join(" ", errors));

            string fullPath = Path.GetFullPath(path);
            string directory = Path.GetDirectoryName(fullPath);
            Directory.CreateDirectory(directory);
            string temporary = Path.Combine(directory, Path.GetFileName(fullPath) + ".tmp-" + Guid.NewGuid().ToString("N"));
            try
            {
                using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                using (var writer = new StreamWriter(stream, new UTF8Encoding(false)))
                {
                    writer.Write(metadata.ToJson());
                    writer.Write('\n');
                    writer.Flush();
                    stream.Flush(true);
                }

                beforeCommit?.Invoke(temporary);
                if (File.Exists(fullPath))
                {
                    string backup = fullPath + ".bak-" + Guid.NewGuid().ToString("N");
                    File.Replace(temporary, fullPath, backup, true);
                }
                else File.Move(temporary, fullPath);
            }
            finally
            {
                if (File.Exists(temporary)) File.Delete(temporary);
            }
        }
    }
}
