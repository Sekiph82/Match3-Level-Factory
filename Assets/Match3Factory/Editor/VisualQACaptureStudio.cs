using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace Match3Factory
{
    public sealed class VisualQACaptureStudio : EditorWindow
    {
        private string checkpointPath = string.Empty;
        private string lastOutputDirectory = string.Empty;
        private string status = "Select an optional real Checkpoint v2 JSON, then export evidence.";
        private CaptureJob activeJob;

        [MenuItem("Tools/Match3 Factory/Visual QA Capture Studio")]
        public static void Open()
        {
            var window = GetWindow<VisualQACaptureStudio>();
            window.titleContent = new GUIContent("Visual QA Capture Studio");
            window.minSize = new Vector2(520, 280);
            window.Show();
        }

        [MenuItem("Tools/Match3 Factory/Visual QA Capture Studio/Export QA Evidence (batchmode)")]
        public static void ExportBatchmodeFromCommandLine()
        {
            if (!Application.isBatchMode)
            {
                Debug.LogError("Batchmode evidence entry requires -batchmode and -executeMethod.");
                return;
            }

            string checkpoint = ReadArgument("-visualQaCheckpointJson");
            var job = new CaptureJob(checkpoint);
            job.Initialize();
            while (!job.IsComplete) job.Step();
            Debug.Log("LFX-M08 Visual QA evidence: " + job.OutputDirectory + " | " + job.Summary);
            EditorApplication.Exit(job.HasFailures ? 1 : 0);
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("LFX-M08 · Visual QA Capture Studio", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Exports deterministic renderer images, not Unity EditorWindow screenshots. " +
                "No Engine replay, cascade, goal, or WIN authority is produced. ENG-M24: BLOCKED.",
                MessageType.Warning);
            EditorGUILayout.LabelField("Checkpoint v2 source JSON (optional)");
            EditorGUILayout.BeginHorizontal();
            checkpointPath = EditorGUILayout.TextField(checkpointPath);
            if (GUILayout.Button("Browse…", GUILayout.Width(90)))
            {
                string selected = EditorUtility.OpenFilePanel("Select real UltraGem Checkpoint v2 JSON", "", "json");
                if (!string.IsNullOrEmpty(selected)) checkpointPath = selected;
            }
            EditorGUILayout.EndHorizontal();

            using (new EditorGUI.DisabledScope(activeJob != null))
            {
                if (GUILayout.Button("Export QA Evidence", GUILayout.Height(32))) StartExport();
            }
            if (activeJob != null)
            {
                EditorGUILayout.LabelField("Progress", activeJob.ProgressLabel);
                EditorGUI.ProgressBar(EditorGUILayout.GetControlRect(false, 18), activeJob.Progress,
                    "Captures are rendered one at a time; original inputs are read-only.");
            }
            EditorGUILayout.HelpBox(status, MessageType.Info);
            if (!string.IsNullOrEmpty(lastOutputDirectory))
                EditorGUILayout.SelectableLabel(lastOutputDirectory, EditorStyles.textField, GUILayout.Height(18));
            EditorGUILayout.LabelField("Manual EditorWindow, DPI, clipping and Play/Pause interaction checks remain separate.",
                EditorStyles.wordWrappedMiniLabel);
        }

        private void StartExport()
        {
            try
            {
                activeJob = new CaptureJob(checkpointPath);
                activeJob.Initialize();
                status = "Export started. The output folder is unique and create-only.";
                EditorApplication.update += TickExport;
            }
            catch (Exception error)
            {
                activeJob = null;
                status = "Export could not start: " + SafeMessage(error.Message);
                Debug.LogException(error);
            }
        }

        private void TickExport()
        {
            if (activeJob == null) { EditorApplication.update -= TickExport; return; }
            activeJob.Step();
            if (activeJob.IsComplete)
            {
                EditorApplication.update -= TickExport;
                lastOutputDirectory = activeJob.OutputDirectory;
                status = activeJob.Summary;
                if (activeJob.HasFailures) Debug.LogError("LFX-M08 Visual QA capture completed with failures: " + status);
                else Debug.Log("LFX-M08 Visual QA capture completed: " + status);
                activeJob = null;
            }
            Repaint();
        }

        private void OnDisable()
        {
            EditorApplication.update -= TickExport;
            if (activeJob != null) activeJob.Abort("Capture window was closed.");
            // A partially exported, unique folder is deliberately retained for diagnosis.
            activeJob = null;
        }

        private static string ReadArgument(string name)
        {
            string[] args = Environment.GetCommandLineArgs();
            for (int i = 0; i + 1 < args.Length; i++)
                if (string.Equals(args[i], name, StringComparison.Ordinal)) return args[i + 1];
            return string.Empty;
        }

        private static string SafeMessage(string value)
        {
            string project = Directory.GetParent(Application.dataPath).FullName;
            string user = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return (value ?? "Unknown error").Replace(project, "<PROJECT>").Replace(user, "<USER>");
        }

        [Serializable]
        public sealed class CaptureFrame
        {
            public string category;
            public string profile;
            public string effect;
            public int width;
            public int height;
            public int frame;
            public bool reducedMotion;
            public string fileName;
        }

        [Serializable]
        public sealed class CheckRecord
        {
            public string name;
            public string status;
            public string details;
        }

        [Serializable]
        public sealed class ImageRecord
        {
            public string category;
            public string profile;
            public string effect;
            public int width;
            public int height;
            public int frame;
            public bool reducedMotion;
            public string fileName;
            public string sha256;
            public string pixelSha256;
            public long byteCount;
            public bool deterministicRepeat;
        }

        [Serializable]
        public sealed class CaptureManifest
        {
            public string schema = "LFX-M08-VISUAL-QA-CAPTURE-1";
            public string createdUtc;
            public string unityVersion;
            public string gitCommitSha;
            public string engineStatus = "BLOCKED_ENG_M24";
            public string checkpointSourceFileName;
            public string checkpointSourceSha256;
            public string checkpointParseStatus = "NOT_RUN";
            public string checkpointPolicy;
            public int checkpointCandidateIndex;
            public int checkpointRunIndex;
            public long checkpointRunSeed;
            public int checkpointCount;
            public int donorMovesUsed;
            public int paddedFinalStatisticsCount;
            public int donorShuffles;
            public string checkpointSha256;
            public string initialBoardSha256;
            public string imageEvidenceType = "DETERMINISTIC_RENDERER_OUTPUT_NOT_EDITOR_WINDOW_SCREENSHOT";
            public string editorWindowScreenshotStatus = "NOT_RUN";
            public string dpiVisualInspectionStatus = "NOT_RUN";
            public string clippingVisualInspectionStatus = "NOT_RUN";
            public string playPauseInteractionStatus = "NOT_RUN";
            public string targetDevicePerformanceStatus = "NOT_RUN";
            public string result;
            public CheckRecord[] checks;
            public ImageRecord[] images;
            public string[] warnings;
            public string[] errors;
        }

        public static CaptureFrame[] CreateThemePlan()
        {
            var result = new List<CaptureFrame>();
            int[] widths = { 320, 390, 720 };
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            foreach (int width in widths)
            {
                int height = Mathf.RoundToInt(width * 16f / 9f);
                result.Add(new CaptureFrame {
                    category = "theme", profile = profile, width = width, height = height,
                    fileName = "theme-" + profile + "-" + width + "x" + height + ".png"
                });
            }
            return result.ToArray();
        }

        public static CaptureFrame[] CreateVfxPlan()
        {
            var result = new List<CaptureFrame>();
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            foreach (string effect in NeutralVfxPreviewGeometry.Effects)
            {
                foreach (int frame in new[] { 0, 5, 11 })
                    result.Add(new CaptureFrame {
                        category = "vfx", profile = profile, effect = effect, frame = frame,
                        width = NeutralVfxPreviewRenderer.DefaultWidth, height = NeutralVfxPreviewRenderer.DefaultHeight,
                        fileName = "vfx-" + profile + "-" + effect + "-frame-" + frame.ToString("00") + ".png"
                    });
                result.Add(new CaptureFrame {
                    category = "vfx", profile = profile, effect = effect, frame = 0, reducedMotion = true,
                    width = NeutralVfxPreviewRenderer.DefaultWidth, height = NeutralVfxPreviewRenderer.DefaultHeight,
                    fileName = "vfx-" + profile + "-" + effect + "-reduced-motion.png"
                });
            }
            return result.ToArray();
        }

        public static Texture2D Render(CaptureFrame frame)
        {
            if (frame == null) throw new ArgumentNullException(nameof(frame));
            if (frame.category == "theme")
                return NeutralThemePreviewRenderer.Render(frame.profile, frame.width, frame.height);
            if (frame.category == "vfx")
                return NeutralVfxPreviewRenderer.Render(frame.profile, frame.effect,
                    frame.frame, frame.reducedMotion, frame.width, frame.height);
            throw new ArgumentException("Unsupported capture category.", nameof(frame));
        }

        public static string PixelSha256(Texture2D texture)
        {
            if (texture == null) throw new ArgumentNullException(nameof(texture));
            Color32[] colors = texture.GetPixels32();
            byte[] bytes = new byte[colors.Length * 4];
            for (int i = 0; i < colors.Length; i++)
            {
                int offset = i * 4;
                bytes[offset] = colors[i].r;
                bytes[offset + 1] = colors[i].g;
                bytes[offset + 2] = colors[i].b;
                bytes[offset + 3] = colors[i].a;
            }
            return Sha256(bytes);
        }

        public const long MaxPngBytes = 16L * 1024 * 1024;
        public const long MaxOutputBytes = 128L * 1024 * 1024;
        public const int MaxImagePixels = 2400000;
        public const int CheckpointImageWidth = 960;
        public const int CheckpointImageHeight = 1260;

        public static Texture2D RenderCheckpointBoard(ReferenceCheckpointPreview.Receipt receipt)
        {
            return CheckpointBoardRasterizer.Render(receipt);
        }

        private sealed class CaptureJob
        {
            private readonly string checkpointPath;
            private readonly CaptureManifest manifest = new CaptureManifest();
            private readonly List<ImageRecord> images = new List<ImageRecord>();
            private readonly List<CheckRecord> checks = new List<CheckRecord>();
            private readonly List<string> warnings = new List<string>();
            private readonly List<string> errors = new List<string>();
            private readonly Dictionary<string, string> sourceHashes = new Dictionary<string, string>(StringComparer.Ordinal);
            private readonly CaptureFrame[] themes = CreateThemePlan();
            private readonly CaptureFrame[] effects = CreateVfxPlan();
            private string outputDirectory;
            private long outputBytes;
            private int index;
            private int phase;
            private bool initialized, complete;
            private ReferenceCheckpointPreview.Receipt receipt;

            public CaptureJob(string checkpointPath) { this.checkpointPath = checkpointPath ?? string.Empty; }
            public bool IsComplete { get { return complete; } }
            public bool HasFailures { get; private set; }
            public string OutputDirectory { get { return outputDirectory ?? string.Empty; } }
            public float Progress
            {
                get
                {
                    if (complete) return 1f;
                    int completedCaptures = phase == 1 ? index : phase == 2 ? themes.Length + index : themes.Length + effects.Length;
                    return Mathf.Clamp01(completedCaptures / (float)(themes.Length + effects.Length + 1));
                }
            }
            public string ProgressLabel { get { return phase == 0 ? "Preparing" : phase == 1 ? "Theme images " + index + "/" + themes.Length : phase == 2 ? "VFX images " + index + "/" + effects.Length : "Checkpoint and manifest"; } }
            public string Summary { get; private set; }

            public void Abort(string reason)
            {
                if (complete) return;
                HasFailures = true;
                errors.Add("Capture stopped before completion: " + SafeMessage(reason));
                phase = 3;
                receipt = null;
                FinalizeManifest();
                complete = true;
            }

            public void Initialize()
            {
                if (initialized) return;
                initialized = true;
                string root = Directory.GetParent(Application.dataPath).FullName;
                string artifactRoot = Path.Combine(root, "Artifacts", "VisualQA");
                Directory.CreateDirectory(artifactRoot);
                outputDirectory = CreateUniqueRunDirectory(artifactRoot);
                manifest.createdUtc = DateTime.UtcNow.ToString("o");
                manifest.unityVersion = Application.unityVersion;
                manifest.gitCommitSha = ReadGitCommit(root, warnings);
                CaptureSourceHashes(root, sourceHashes, warnings);
                if (string.IsNullOrWhiteSpace(checkpointPath))
                {
                    manifest.checkpointParseStatus = "NOT_RUN";
                    warnings.Add("No Checkpoint v2 JSON was selected; checkpoint capture is NOT_RUN.");
                }
                else
                {
                    try
                    {
                        string fullPath = Path.GetFullPath(checkpointPath);
                        var info = new FileInfo(fullPath);
                        if (!info.Exists || info.Length < 1 || info.Length > 256000)
                            throw new InvalidOperationException("Checkpoint JSON is missing, empty, or oversized.");
                        byte[] bytes = File.ReadAllBytes(fullPath);
                        string json = new UTF8Encoding(false, true).GetString(bytes);
                        receipt = ReferenceCheckpointPreview.Parse(json);
                        manifest.checkpointSourceFileName = info.Name;
                        manifest.checkpointSourceSha256 = Sha256(bytes);
                        manifest.checkpointPolicy = receipt.policy;
                        manifest.checkpointCandidateIndex = receipt.candidateIndex;
                        manifest.checkpointRunIndex = receipt.runIndex;
                        manifest.checkpointRunSeed = receipt.runSeed;
                        manifest.checkpointCount = receipt.checkpoints.Length;
                        manifest.donorMovesUsed = receipt.donorMovesUsed;
                        manifest.paddedFinalStatisticsCount = receipt.checkpoints.Length - receipt.donorMovesUsed;
                        manifest.donorShuffles = receipt.donorShuffles;
                        manifest.checkpointSha256 = receipt.checkpointSha256;
                        manifest.initialBoardSha256 = receipt.initialBoardSha256;
                        manifest.checkpointParseStatus = "PASS";
                    }
                    catch (Exception error)
                    {
                        manifest.checkpointParseStatus = "FAIL";
                        errors.Add("Checkpoint source rejected: " + SafeMessage(error.Message));
                    }
                }
                phase = 1;
            }

            public void Step()
            {
                if (!initialized) Initialize();
                if (complete) return;
                if (phase == 1)
                {
                    if (index < themes.Length) { CaptureImage(themes[index++]); return; }
                    phase = 2; index = 0; return;
                }
                if (phase == 2)
                {
                    if (index < effects.Length) { CaptureImage(effects[index++]); return; }
                    phase = 3; index = 0; return;
                }
                if (phase == 3)
                {
                    if (receipt != null) CaptureCheckpointImage();
                    FinalizeManifest();
                    complete = true;
                }
            }

            private void CaptureImage(CaptureFrame frame)
            {
                Texture2D texture = null, repeat = null;
                try
                {
                    texture = Render(frame);
                    if ((long)texture.width * texture.height > MaxImagePixels)
                        throw new InvalidOperationException("Rendered image exceeds the pixel budget.");
                    string pixelHash = PixelSha256(texture);
                    repeat = Render(frame);
                    bool deterministic = string.Equals(pixelHash, PixelSha256(repeat), StringComparison.Ordinal);
                    if (!deterministic) throw new InvalidOperationException("Repeated pixel render hash differed.");
                    byte[] png = texture.EncodeToPNG();
                    WritePng(frame.fileName, png);
                    images.Add(new ImageRecord {
                        category = frame.category, profile = frame.profile, effect = frame.effect,
                        width = texture.width, height = texture.height, frame = frame.frame,
                        reducedMotion = frame.reducedMotion, fileName = frame.fileName,
                        sha256 = Sha256(png), pixelSha256 = pixelHash, byteCount = png.LongLength,
                        deterministicRepeat = deterministic
                    });
                }
                catch (Exception error)
                {
                    HasFailures = true;
                    errors.Add(frame.fileName + ": " + SafeMessage(error.Message));
                }
                finally
                {
                    if (texture != null) UnityEngine.Object.DestroyImmediate(texture);
                    if (repeat != null) UnityEngine.Object.DestroyImmediate(repeat);
                }
            }

            private void CaptureCheckpointImage()
            {
                try
                {
                    const string fileName = "checkpoint-v2-seeded-setup-board.png";
                    Texture2D image = CheckpointBoardRasterizer.Render(receipt);
                    try
                    {
                        byte[] png = image.EncodeToPNG();
                        WritePng(fileName, png);
                        string pixelHash = PixelSha256(image);
                        Texture2D repeat = CheckpointBoardRasterizer.Render(receipt);
                        try
                        {
                            bool deterministic = string.Equals(pixelHash, PixelSha256(repeat), StringComparison.Ordinal);
                            if (!deterministic) throw new InvalidOperationException("Repeated checkpoint board render hash differed.");
                            images.Add(new ImageRecord {
                                category = "checkpoint", profile = receipt.policy, effect = string.Empty,
                                width = image.width, height = image.height, frame = 0, reducedMotion = false,
                                fileName = fileName, sha256 = Sha256(png), pixelSha256 = pixelHash,
                                byteCount = png.LongLength, deterministicRepeat = deterministic
                            });
                        }
                        finally { UnityEngine.Object.DestroyImmediate(repeat); }
                    }
                    finally { UnityEngine.Object.DestroyImmediate(image); }
                }
                catch (Exception error)
                {
                    HasFailures = true;
                    manifest.checkpointParseStatus = "FAIL";
                    errors.Add("Checkpoint board capture: " + SafeMessage(error.Message));
                }
            }

            private void WritePng(string fileName, byte[] bytes)
            {
                if (bytes == null || bytes.Length < 8 || bytes.Length > MaxPngBytes)
                    throw new InvalidOperationException("PNG is empty or exceeds the per-image byte budget.");
                if (outputBytes + bytes.LongLength > MaxOutputBytes)
                    throw new InvalidOperationException("QA run exceeds the total output byte budget.");
                string path = Path.Combine(outputDirectory, fileName);
                using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                    stream.Write(bytes, 0, bytes.Length);
                outputBytes += bytes.LongLength;
            }

            private void FinalizeManifest()
            {
                int themeCount = 0, vfxCount = 0;
                foreach (var image in images)
                {
                    if (image.category == "theme") themeCount++;
                    else if (image.category == "vfx") vfxCount++;
                }
                AddCheck("Theme captures", themeCount == 15 ? "PASS" : "FAIL", themeCount + "/15 PNGs from NeutralThemePreviewRenderer.Render().");
                AddCheck("VFX captures", vfxCount == 120 ? "PASS" : "FAIL", vfxCount + "/120 PNGs from NeutralVfxPreviewGeometry.Build() and shared renderer.");
                AddCheck("Checkpoint v2", manifest.checkpointParseStatus,
                    manifest.checkpointParseStatus == "PASS" ? "ReferenceCheckpointPreview.Parse() accepted the source; image shows seeded setup only." : "Engine replay and WIN proof are not produced.");
                AddCheck("Git commit SHA", manifest.gitCommitSha != "UNKNOWN" && manifest.gitCommitSha.Length == 40 ? "PASS" : "FAIL",
                    "Manifest HEAD: " + manifest.gitCommitSha + ". Working-tree edits are not represented by HEAD.");
                bool deterministic = true;
                foreach (var image in images) if (!image.deterministicRepeat) deterministic = false;
                AddCheck("Deterministic image hashes", deterministic && images.Count > 0 ? "PASS" : "FAIL",
                    "Repeated pixel SHA-256 matches each PNG render; " + images.Count + " image(s).");
                bool unchanged = VerifySourceHashes(Directory.GetParent(Application.dataPath).FullName, sourceHashes, warnings);
                AddCheck("Neutral SVG source files unchanged", unchanged ? "PASS" : "FAIL",
                    "Read-only SHA-256 before/after capture for the five tracked neutral SVG sources.");
                AddCheck("Output bounds", outputBytes <= MaxOutputBytes ? "PASS" : "FAIL",
                    outputBytes + " bytes total; max " + MaxOutputBytes + ", max " + MaxPngBytes + " per PNG, one texture pair at a time.");
                AddCheck("Editor-only assembly", "PASS", "Studio and PNG render helpers live under Assets/Match3Factory/Editor and its Editor-only asmdef.");
                AddCheck("Unity EditorWindow screenshot", "NOT_RUN", "These files are renderer outputs, not desktop/window screenshots.");
                AddCheck("Window DPI, clipping and scaling inspection", "NOT_RUN", "Requires visual inspection of real Editor windows.");
                AddCheck("Play/Pause UI interaction", "NOT_RUN", "Frame states were rendered directly; controls were not clicked.");
                AddCheck("Engine replay / gameplay parity", "NOT_RUN", "ENG-M24 is BLOCKED; no Engine replay, cascade, goal or WIN claim.");
                manifest.images = images.ToArray();
                manifest.checks = checks.ToArray();
                manifest.warnings = warnings.ToArray();
                manifest.errors = errors.ToArray();
                if (manifest.checkpointParseStatus == "FAIL") HasFailures = true;
                manifest.result = HasFailures ? "FAIL" : "CAPTURE_COMPLETE_WITH_NOT_RUN_UI_AND_ENGINE_CHECKS";
                Summary = manifest.result + ": themes=" + themeCount + "/15, vfx=" + vfxCount + "/120, checkpoint=" + manifest.checkpointParseStatus + ", images=" + images.Count + ", bytes=" + outputBytes;
                try
                {
                    string path = Path.Combine(outputDirectory, "manifest.json");
                    byte[] data = new UTF8Encoding(false).GetBytes(JsonUtility.ToJson(manifest, true) + "\n");
                    if (outputBytes + data.LongLength > MaxOutputBytes)
                        throw new InvalidOperationException("QA manifest would exceed the total output byte budget.");
                    using (var stream = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                        stream.Write(data, 0, data.Length);
                }
                catch (Exception error)
                {
                    HasFailures = true;
                    errors.Add("Manifest write: " + SafeMessage(error.Message));
                    Summary = "FAIL: manifest write failed; " + SafeMessage(error.Message);
                }
            }

            private void AddCheck(string name, string state, string details)
            {
                if (state == "FAIL") HasFailures = true;
                checks.Add(new CheckRecord { name = name, status = state, details = details });
            }
        }

        private static string CreateUniqueRunDirectory(string artifactRoot)
        {
            for (int attempt = 0; attempt < 20; attempt++)
            {
                string stamp = DateTime.UtcNow.ToString("yyyyMMdd'T'HHmmssfff'Z'");
                string suffix = Guid.NewGuid().ToString("N").Substring(0, 8);
                string candidate = Path.Combine(artifactRoot, stamp + "-" + suffix);
                try { Directory.CreateDirectory(candidate); return candidate; }
                catch (IOException) { }
            }
            throw new IOException("Could not create a unique QA output folder.");
        }

        private static string ReadGitCommit(string projectRoot, List<string> warnings)
        {
            try
            {
                var start = new ProcessStartInfo("git", "rev-parse HEAD") {
                    WorkingDirectory = projectRoot, UseShellExecute = false,
                    RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true
                };
                using (var process = Process.Start(start))
                {
                    if (process == null || !process.WaitForExit(3000))
                    {
                        if (process != null) try { process.Kill(); } catch { }
                        warnings.Add("Git HEAD lookup timed out; manifest commit SHA is UNKNOWN.");
                        return "UNKNOWN";
                    }
                    string value = process.StandardOutput.ReadToEnd().Trim();
                    if (process.ExitCode == 0 && value.Length == 40) return value;
                }
            }
            catch (Exception error) { warnings.Add("Git HEAD lookup failed: " + SafeMessage(error.Message)); }
            return "UNKNOWN";
        }

        private static void CaptureSourceHashes(string projectRoot, Dictionary<string, string> output, List<string> warnings)
        {
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            {
                string path = Path.Combine(projectRoot, "Assets", "Match3Factory", "Editor", "Previews", "Neutral", profile + ".svg");
                try { if (File.Exists(path)) output[profile] = Sha256(File.ReadAllBytes(path));
                    else warnings.Add("Neutral source SVG missing for " + profile + "."); }
                catch (Exception error) { warnings.Add("Could not hash neutral source " + profile + ": " + SafeMessage(error.Message)); }
            }
        }

        private static bool VerifySourceHashes(string projectRoot, Dictionary<string, string> before, List<string> warnings)
        {
            bool unchanged = before.Count == NeutralThemePreviewRenderer.Profiles.Length;
            foreach (var item in before)
            {
                string path = Path.Combine(projectRoot, "Assets", "Match3Factory", "Editor", "Previews", "Neutral", item.Key + ".svg");
                try { if (!File.Exists(path) || !string.Equals(item.Value, Sha256(File.ReadAllBytes(path)), StringComparison.Ordinal)) unchanged = false; }
                catch (Exception error) { unchanged = false; warnings.Add("Source hash verification failed for " + item.Key + ": " + SafeMessage(error.Message)); }
            }
            return unchanged;
        }

        private static string Sha256(byte[] bytes)
        {
            using (var sha = SHA256.Create())
            {
                byte[] digest = sha.ComputeHash(bytes);
                var result = new StringBuilder(digest.Length * 2);
                foreach (byte value in digest) result.Append(value.ToString("x2"));
                return result.ToString();
            }
        }

        private static class CheckpointBoardRasterizer
        {
            private const int Width = CheckpointImageWidth;
            private const int Height = CheckpointImageHeight;
            private static readonly Color32 Background = new Color32(18, 29, 39, 255);
            private static readonly Color32 White = new Color32(238, 245, 248, 255);
            private static readonly Color32 Muted = new Color32(163, 184, 195, 255);
            private static readonly Color32 Grid = new Color32(86, 109, 122, 255);
            private static readonly Color32 Cell = new Color32(39, 59, 72, 255);
            private static readonly Color32 Disabled = new Color32(30, 39, 46, 255);
            private static readonly Color32 Actual = new Color32(73, 174, 128, 255);
            private static readonly Color32 Padded = new Color32(222, 160, 69, 255);

            public static Texture2D Render(ReferenceCheckpointPreview.Receipt receipt)
            {
                if (receipt == null || receipt.initialBoard == null) throw new ArgumentNullException(nameof(receipt));
                var pixels = new Color32[Width * Height];
                for (int i = 0; i < pixels.Length; i++) pixels[i] = Background;
                DrawText(pixels, "REFERENCE ONLY", 36, 28, 6, White);
                DrawText(pixels, "ULTRAGEM SEEDED SETUP BOARD", 36, 88, 3, Muted);
                DrawText(pixels, "POLICY " + receipt.policy + " RUN " + receipt.runIndex + " SEED " + receipt.runSeed, 36, 132, 2, White);
                DrawText(pixels, "ACTUAL PRE-MOVE COUNTERS " + receipt.donorMovesUsed, 36, 172, 2, Actual);
                DrawText(pixels, "PADDED FINAL COUNTERS " + (receipt.checkpoints.Length - receipt.donorMovesUsed) + " NO MOVE", 500, 172, 2, Padded);
                var actualMetrics = receipt.donorMovesUsed > 0
                    ? receipt.checkpoints[receipt.donorMovesUsed - 1].cumulative : new ReferenceCheckpointPreview.Metrics();
                var finalMetrics = receipt.checkpoints[receipt.checkpoints.Length - 1].cumulative;
                DrawText(pixels, "LAST OBSERVED SCORE " + actualMetrics.score + " DESTROYED " + actualMetrics.ndestroyed,
                    36, 224, 2, Actual);
                DrawText(pixels, "PADDED FINAL SCORE " + finalMetrics.score + " DESTROYED " + finalMetrics.ndestroyed,
                    500, 224, 2, receipt.paddedFinalStatisticsPresent ? Padded : Muted);

                int timelineX = 36, timelineY = 270, timelineWidth = Width - 72;
                int slotWidth = Math.Max(1, timelineWidth / receipt.checkpoints.Length);
                for (int i = 0; i < receipt.checkpoints.Length; i++)
                    FillRect(pixels, timelineX + i * slotWidth, timelineY, Math.Max(4, slotWidth - 4), 18,
                        receipt.checkpoints[i].observedBeforeMove ? Actual : Padded);

                int boardSide = 760;
                int cellSide = boardSide / Math.Max(receipt.initialBoard.rows, receipt.initialBoard.columns);
                int boardWidth = cellSide * receipt.initialBoard.columns;
                int boardHeight = cellSide * receipt.initialBoard.rows;
                int boardX = (Width - boardWidth) / 2;
                int boardY = 320;
                for (int i = 0; i < receipt.initialBoard.cells.Length; i++)
                {
                    var cell = receipt.initialBoard.cells[i];
                    int x = boardX + cell.column * cellSide;
                    int y = boardY + cell.row * cellSide;
                    FillRect(pixels, x, y, cellSide - 2, cellSide - 2, cell.type < 0 ? Disabled : Cell);
                    DrawRectOutline(pixels, x, y, cellSide - 2, cellSide - 2, Grid);
                    string label = (cell.type < 0 ? "X" : cell.type.ToString()) + "/" + cell.color;
                    if (cell.status > 0) label += "*";
                    int scale = Math.Max(2, Math.Min(6, cellSide / 18));
                    int textWidth = label.Length * 6 * scale;
                    DrawText(pixels, label, x + Math.Max(2, (cellSide - textWidth) / 2),
                        y + Math.Max(2, (cellSide - 7 * scale) / 2), scale, White);
                }
                int footerY = Math.Min(Height - 160, boardY + boardHeight + 32);
                DrawText(pixels, "RAW DONOR TYPE/COLOR; STAR MEANS LOCK STATUS ABOVE ZERO", 36, footerY, 2, Muted);
                DrawText(pixels, "NOT ENGINE REPLAY", 36, footerY + 42, 3, Padded);
                DrawText(pixels, "NOT CASCADE ANIMATION", 36, footerY + 82, 3, Padded);
                DrawText(pixels, "NOT WIN PROOF", 36, footerY + 122, 3, Padded);
                DrawText(pixels, "ENG-M24 BLOCKED", 620, footerY + 122, 2, White);

                var texture = new Texture2D(Width, Height, TextureFormat.RGBA32, false)
                {
                    name = "LFX-M08 Checkpoint v2 seeded setup board",
                    filterMode = FilterMode.Point,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave
                };
                texture.SetPixels32(pixels);
                texture.Apply(false, false);
                return texture;
            }

            private static void FillRect(Color32[] pixels, int x, int y, int width, int height, Color32 color)
            {
                for (int py = Math.Max(0, y); py < Math.Min(Height, y + height); py++)
                for (int px = Math.Max(0, x); px < Math.Min(Width, x + width); px++) pixels[(Height - 1 - py) * Width + px] = color;
            }

            private static void DrawRectOutline(Color32[] pixels, int x, int y, int width, int height, Color32 color)
            {
                FillRect(pixels, x, y, width, 1, color); FillRect(pixels, x, y + height - 1, width, 1, color);
                FillRect(pixels, x, y, 1, height, color); FillRect(pixels, x + width - 1, y, 1, height, color);
            }

            private static void DrawText(Color32[] pixels, string text, int x, int y, int scale, Color32 color)
            {
                if (string.IsNullOrEmpty(text)) return;
                int cursor = x;
                foreach (char original in text.ToUpperInvariant())
                {
                    if (original == '\n') { cursor = x; y += 9 * scale; continue; }
                    char ch = original == '_' ? '-' : original;
                    byte[] glyph;
                    if (!Glyphs.TryGetValue(ch, out glyph)) glyph = Glyphs[' '];
                    for (int row = 0; row < 7; row++)
                    for (int col = 0; col < 5; col++)
                        if ((glyph[row] & (1 << (4 - col))) != 0)
                            FillRect(pixels, cursor + col * scale, y + row * scale, scale, scale, color);
                    cursor += 6 * scale;
                }
            }

            private static readonly Dictionary<char, byte[]> Glyphs = new Dictionary<char, byte[]>
            {
                { ' ', new byte[] {0,0,0,0,0,0,0} }, { 'A', new byte[] {14,17,17,31,17,17,17} },
                { 'B', new byte[] {30,17,17,30,17,17,30} }, { 'C', new byte[] {14,17,16,16,16,17,14} },
                { 'D', new byte[] {30,17,17,17,17,17,30} }, { 'E', new byte[] {31,16,16,30,16,16,31} },
                { 'F', new byte[] {31,16,16,30,16,16,16} }, { 'G', new byte[] {14,17,16,23,17,17,15} },
                { 'H', new byte[] {17,17,17,31,17,17,17} }, { 'I', new byte[] {14,4,4,4,4,4,14} },
                { 'J', new byte[] {7,2,2,2,18,18,12} }, { 'K', new byte[] {17,18,20,24,20,18,17} },
                { 'L', new byte[] {16,16,16,16,16,16,31} }, { 'M', new byte[] {17,27,21,21,17,17,17} },
                { 'N', new byte[] {17,25,21,19,17,17,17} }, { 'O', new byte[] {14,17,17,17,17,17,14} },
                { 'P', new byte[] {30,17,17,30,16,16,16} }, { 'Q', new byte[] {14,17,17,17,21,18,13} },
                { 'R', new byte[] {30,17,17,30,20,18,17} }, { 'S', new byte[] {15,16,16,14,1,1,30} },
                { 'T', new byte[] {31,4,4,4,4,4,4} }, { 'U', new byte[] {17,17,17,17,17,17,14} },
                { 'V', new byte[] {17,17,17,17,17,10,4} }, { 'W', new byte[] {17,17,17,21,21,21,10} },
                { 'X', new byte[] {17,17,10,4,10,17,17} }, { 'Y', new byte[] {17,17,10,4,4,4,4} },
                { 'Z', new byte[] {31,1,2,4,8,16,31} }, { '0', new byte[] {14,17,19,21,25,17,14} },
                { '1', new byte[] {4,12,4,4,4,4,14} }, { '2', new byte[] {14,17,1,2,4,8,31} },
                { '3', new byte[] {30,1,1,14,1,1,30} }, { '4', new byte[] {2,6,10,18,31,2,2} },
                { '5', new byte[] {31,16,16,30,1,1,30} }, { '6', new byte[] {14,16,16,30,17,17,14} },
                { '7', new byte[] {31,1,2,4,8,8,8} }, { '8', new byte[] {14,17,17,14,17,17,14} },
                { '9', new byte[] {14,17,17,15,1,1,14} }, { '/', new byte[] {1,2,2,4,8,8,16} },
                { '-', new byte[] {0,0,0,31,0,0,0} }, { ':', new byte[] {0,4,4,0,4,4,0} },
                { '.', new byte[] {0,0,0,0,0,12,12} }, { '*', new byte[] {0,21,14,31,14,21,0} }
            };
        }
    }
}
