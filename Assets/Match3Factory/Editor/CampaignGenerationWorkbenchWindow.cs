using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.UIElements;

namespace Match3Factory
{
    /// <summary>
    /// Editor-only client for Tools/UltraGem/campaign_generation_workbench.py.
    /// Generated content remains reference-only and outside Assets by default.
    /// </summary>
    public sealed class CampaignGenerationWorkbenchWindow : EditorWindow
    {
        private static readonly string[] Profiles =
        {
            "Coral_Rescue", "Garage_Legends", "Dino_Islands",
            "The_Fractured_Realms", "Wonder_Pop"
        };

        [Serializable]
        private sealed class SummaryEnvelope
        {
            public string resultStatus;
            public int generationAttempts;
            public int sourceBackedCandidateOutputs;
            public int generatedReferenceCandidates;
            public int uniqueOwnerReviewCandidates;
            public int ownerApprovedCandidates;
            public int engineQualifiedCampaignLevels;
            public string engineStatus;
            public CandidateSummary[] records;
        }

        [Serializable]
        private sealed class CandidateSummary
        {
            public string candidateId;
            public string profileId;
            public int attempt;
            public int donorSeed;
            public string recordPath;
            public string recordSha256;
            public string draftSha256;
            public string localPrefilterStatus;
            public string triageStatus;
            public string triageReason;
            public string duplicateOf;
        }

        [Serializable]
        private sealed class CandidateEnvelope
        {
            public string candidateId;
            public string triageStatus;
            public string triageReason;
            public string draftSha256;
            public LevelDraft draft;
        }

        [Serializable]
        private sealed class CampaignProgress
        {
            public string status;
            public int completed;
            public int total;
            public string profileId;
            public int attempt;
            public int uniqueOwnerReviewCandidates;
        }

        private readonly object outputLock = new object();
        private readonly StringBuilder stdout = new StringBuilder();
        private readonly StringBuilder stderr = new StringBuilder();
        private string pythonExecutable = "python";
        private string selectedProfile = Profiles[0];
        private bool allProfiles = true;
        private int attemptsPerProfile = 5;
        private int seedStart = 1000;
        private int rows = 8;
        private int columns = 8;
        private int colors = 3;
        private int runs = 2;
        private int maxMoves = 8;
        private int timeoutSeconds = 30;
        private float nearDuplicateThreshold = .95f;
        private string outputRelative;
        private CandidateEnvelope selectedCandidate;
        private LevelDraft selectedDraft;
        private Process process;
        private bool cancelRequested;
        private bool cancelMarkerWritten;
        private string processStatus = "Idle · reference-only · ENG-M24 blocked";
        private Label statusLabel;
        private Label summaryLabel;
        private VisualElement candidateQueue;
        private VisualElement boardPreview;
        private TextField outputField;
        private bool windowEnabled;
        private bool updateSubscribed;

        [MenuItem("Tools/Match3 Factory/Campaign Generation Workbench")]
        public static void Open()
        {
            var window = GetWindow<CampaignGenerationWorkbenchWindow>();
            window.titleContent = new GUIContent("Campaign QA Workbench");
            window.minSize = new Vector2(760, 620);
        }

        private void OnEnable()
        {
            windowEnabled = true;
            SubscribeToUpdates();
        }

        private void OnDisable()
        {
            windowEnabled = false;
            if (process != null && !process.HasExited)
            {
                RequestCancel();
                return;
            }
            UnsubscribeFromUpdates();
        }

        public void CreateGUI()
        {
            rootVisualElement.Clear();
            rootVisualElement.style.paddingLeft = 12;
            rootVisualElement.style.paddingRight = 12;
            rootVisualElement.style.paddingTop = 10;
            rootVisualElement.style.paddingBottom = 10;

            var heading = new Label("Campaign Candidate Generation · REFERENCE ONLY");
            heading.style.unityFontStyleAndWeight = FontStyle.Bold;
            heading.style.fontSize = 17;
            rootVisualElement.Add(heading);
            rootVisualElement.Add(new HelpBox(
                "This runs the pinned UltraGem source generator through a bounded Python subprocess. Donor statistics are not MATCH3_ENGINE replay, playability, difficulty certification, or WIN. Every candidate remains PROTOTYPE_ONLY; ENG-M24 is BLOCKED.",
                HelpBoxMessageType.Warning));

            var config = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            var python = new TextField("Python executable") { value = pythonExecutable };
            python.style.minWidth = 300;
            python.RegisterValueChangedCallback(evt => pythonExecutable = evt.newValue.Trim());
            config.Add(python);
            var profile = new DropdownField("Profile", Profiles.ToList(), selectedProfile);
            profile.RegisterValueChangedCallback(evt => selectedProfile = evt.newValue);
            config.Add(profile);
            var all = new Toggle("All five profiles") { value = allProfiles };
            all.RegisterValueChangedCallback(evt => allProfiles = evt.newValue);
            config.Add(all);
            rootVisualElement.Add(config);

            var budget = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            AddIntegerField(budget, "Attempts / profile (1–100)", attemptsPerProfile, value => attemptsPerProfile = value);
            AddIntegerField(budget, "Seed start", seedStart, value => seedStart = value);
            AddIntegerField(budget, "Rows (6–12)", rows, value => rows = value);
            AddIntegerField(budget, "Columns (6–12)", columns, value => columns = value);
            AddIntegerField(budget, "Colors (3–6)", colors, value => colors = value);
            AddIntegerField(budget, "Policy runs (1–8)", runs, value => runs = value);
            AddIntegerField(budget, "Moves / run (1–40)", maxMoves, value => maxMoves = value);
            AddIntegerField(budget, "Candidate timeout seconds", timeoutSeconds, value => timeoutSeconds = value);
            var threshold = new FloatField("Near-duplicate threshold") { value = nearDuplicateThreshold };
            threshold.RegisterValueChangedCallback(evt => nearDuplicateThreshold = evt.newValue);
            budget.Add(threshold);
            rootVisualElement.Add(budget);

            outputField = new TextField("Run folder (project relative)") { value = outputRelative ?? string.Empty, isReadOnly = true };
            rootVisualElement.Add(outputField);
            var actions = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            actions.Add(MakeButton("Generate new batch", StartNewBatch));
            actions.Add(MakeButton("Resume batch…", ChooseAndResume));
            actions.Add(MakeButton("Cancel after current candidate", RequestCancel));
            actions.Add(MakeButton("Load run summary", LoadSummary));
            actions.Add(MakeButton("Show output folder", ShowOutputFolder));
            rootVisualElement.Add(actions);

            statusLabel = new Label(processStatus);
            statusLabel.style.whiteSpace = WhiteSpace.Normal;
            rootVisualElement.Add(statusLabel);
            summaryLabel = new Label("No batch summary loaded.") { name = "campaign-summary" };
            summaryLabel.style.whiteSpace = WhiteSpace.Normal;
            rootVisualElement.Add(summaryLabel);
            rootVisualElement.Add(new Label("Candidate queue · generated/rejected/near duplicate outcomes"));
            candidateQueue = new VisualElement { name = "campaign-candidate-queue" };
            rootVisualElement.Add(candidateQueue);
            rootVisualElement.Add(new Label("Selected board preview"));
            boardPreview = new VisualElement { name = "campaign-board-preview" };
            rootVisualElement.Add(boardPreview);
            rootVisualElement.Add(MakeButton("Export selected · reference only", ExportSelectedReference));
            rootVisualElement.Add(new HelpBox(
                "Unity EditorWindow DPI, clipping, and interactive appearance require a manual editor check. This workbench does not create Player builds or call ADB.",
                HelpBoxMessageType.Info));
        }

        private static void AddIntegerField(VisualElement parent, string title, int value, Action<int> changed)
        {
            var field = new IntegerField(title) { value = value };
            field.style.minWidth = 190;
            field.RegisterValueChangedCallback(evt => changed(evt.newValue));
            parent.Add(field);
        }

        private static Button MakeButton(string title, Action action)
        {
            var button = new Button(action) { text = title };
            button.style.marginRight = 5;
            button.style.marginTop = 4;
            return button;
        }

        private static string ProjectRoot => Directory.GetParent(Application.dataPath).FullName;

        private void StartNewBatch()
        {
            if (process != null && !process.HasExited)
            {
                EditorUtility.DisplayDialog("Batch already running", "Wait for the active batch or cancel it before starting another.", "OK");
                return;
            }
            if (!ValidateParameters(out string error))
            {
                EditorUtility.DisplayDialog("Unsafe batch parameters", error, "OK");
                return;
            }
            string runName = "CampaignQA-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 8);
            outputRelative = Path.Combine("Artifacts", runName).Replace('\\', '/');
            Launch(resume: false);
        }

        private void ChooseAndResume()
        {
            if (process != null && !process.HasExited)
            {
                EditorUtility.DisplayDialog("Batch already running", "Wait for the active batch or cancel it before resuming another.", "OK");
                return;
            }
            string path = EditorUtility.OpenFolderPanel("Select a campaign QA run to resume", Path.Combine(ProjectRoot, "Artifacts"), string.Empty);
            if (string.IsNullOrEmpty(path)) return;
            string root = Path.GetFullPath(ProjectRoot).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(path);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase))
            {
                EditorUtility.DisplayDialog("Invalid run folder", "Resume folders must be inside this Unity project.", "OK");
                return;
            }
            outputRelative = full.Substring(root.Length).Replace('\\', '/');
            if (!ValidateParameters(out string error))
            {
                EditorUtility.DisplayDialog("Unsafe batch parameters", "Resume values must match the original run. " + error, "OK");
                return;
            }
            Launch(resume: true);
        }

        private bool ValidateParameters(out string error)
        {
            long total = (allProfiles ? 5L : 1L) * attemptsPerProfile;
            long perCandidate = runs * (long)maxMoves * 4;
            if (string.IsNullOrWhiteSpace(pythonExecutable)) { error = "Set a Python executable available on PATH."; return false; }
            if (attemptsPerProfile < 1 || attemptsPerProfile > 100) { error = "Attempts must be 1..100 per profile."; return false; }
            if (seedStart < 0 || seedStart > 2147083548) { error = "Seed start is out of the safe range."; return false; }
            if (rows < 6 || rows > 12 || columns < 6 || columns > 12 || colors < 3 || colors > 6) { error = "Board dimensions or color count are outside donor bounds."; return false; }
            if (runs < 1 || runs > 8 || maxMoves < 1 || maxMoves > 40 || timeoutSeconds < 1 || timeoutSeconds > 300) { error = "Runs, moves, or timeout are outside the bounded ranges."; return false; }
            if (perCandidate > 4096 || total * perCandidate > 512000) { error = "Requested total exceeds existing workbench budgets."; return false; }
            if (float.IsNaN(nearDuplicateThreshold) || float.IsInfinity(nearDuplicateThreshold) || nearDuplicateThreshold < .5f || nearDuplicateThreshold > 1f) { error = "Near-duplicate threshold must be within 0.5..1."; return false; }
            error = null;
            return true;
        }

        private void Launch(bool resume)
        {
            var script = Path.Combine(ProjectRoot, "Tools", "UltraGem", "campaign_generation_workbench.py");
            if (!File.Exists(script))
            {
                EditorUtility.DisplayDialog("Generator unavailable", "Missing Tools/UltraGem/campaign_generation_workbench.py.", "OK");
                return;
            }
            var profileIds = allProfiles ? Profiles : new[] { selectedProfile };
            var arguments = new List<string>
            {
                Quote(script), "--project-root", Quote(ProjectRoot), "--profiles", Quote(string.Join(",", profileIds)),
                "--attempts-per-profile", attemptsPerProfile.ToString(), "--seed-start", seedStart.ToString(),
                "--rows", rows.ToString(), "--columns", columns.ToString(), "--colors", colors.ToString(),
                "--runs", runs.ToString(), "--max-moves", maxMoves.ToString(),
                "--candidate-timeout-seconds", timeoutSeconds.ToString(),
                "--near-duplicate-threshold", nearDuplicateThreshold.ToString(System.Globalization.CultureInfo.InvariantCulture),
                "--output-relative", Quote(outputRelative)
            };
            if (resume) arguments.Add("--resume");
            try
            {
                string outputDirectory = Path.Combine(ProjectRoot, outputRelative);
                if (resume)
                {
                    if (!Directory.Exists(outputDirectory))
                        throw new DirectoryNotFoundException("The selected resume folder is missing.");
                }
                else
                {
                    if (Directory.Exists(outputDirectory))
                        throw new IOException("The generated run folder already exists; its contents were left untouched.");
                    Directory.CreateDirectory(outputDirectory);
                }
                lock (outputLock) { stdout.Clear(); stderr.Clear(); }
                cancelRequested = false;
                cancelMarkerWritten = false;
                var info = new ProcessStartInfo
                {
                    FileName = pythonExecutable,
                    Arguments = string.Join(" ", arguments),
                    WorkingDirectory = ProjectRoot,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                };
                process = new Process { StartInfo = info, EnableRaisingEvents = true };
                process.OutputDataReceived += (_, evt) => AppendBounded(stdout, evt.Data);
                process.ErrorDataReceived += (_, evt) => AppendBounded(stderr, evt.Data);
                process.Start();
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
                outputField.value = outputRelative;
                processStatus = resume ? "Resuming bounded donor batch…" : "Generating bounded donor batch…";
                SubscribeToUpdates();
                RefreshStatus();
            }
            catch (Exception ex)
            {
                processStatus = "NOT_RUN · could not start Python: " + ex.Message;
                RefreshStatus();
            }
        }

        private static string Quote(string value)
        {
            return "\"" + (value ?? string.Empty).Replace("\"", "\\\"") + "\"";
        }

        private static void AppendBounded(StringBuilder target, string line)
        {
            if (line == null) return;
            lock (target)
            {
                if (target.Length > 12000) target.Remove(0, target.Length - 8000);
                target.AppendLine(line);
            }
        }

        private void PollProcess()
        {
            if (cancelRequested) WriteCancelMarkerIfAvailable();
            if (process == null)
            {
                if (!windowEnabled) UnsubscribeFromUpdates();
                return;
            }
            if (process.HasExited)
            {
                int exitCode = process.ExitCode;
                process.Dispose();
                process = null;
                processStatus = exitCode == 0
                    ? "Batch process finished · inspect summary and candidate status below."
                    : "Batch process failed · see diagnostic output below.";
                if (!windowEnabled) { UnsubscribeFromUpdates(); return; }
                LoadSummary();
                RefreshStatus();
                return;
            }
            if (!windowEnabled) return;
            string progressPath = Path.Combine(ProjectRoot, outputRelative ?? string.Empty, "progress.json");
            if (File.Exists(progressPath))
            {
                try
                {
                    var progress = JsonUtility.FromJson<CampaignProgress>(File.ReadAllText(progressPath));
                    if (progress != null)
                        processStatus = $"{progress.status} · {progress.completed}/{progress.total} jobs · unique owner review {progress.uniqueOwnerReviewCandidates}";
                }
                catch (Exception ex) { processStatus = "Reading progress failed: " + ex.Message; }
            }
            RefreshStatus();
        }

        private void RequestCancel()
        {
            if (process == null || process.HasExited)
            {
                processStatus = "No batch is running.";
                RefreshStatus();
                return;
            }
            cancelRequested = true;
            processStatus = "Cancel requested · current donor candidate may finish up to its configured timeout.";
            WriteCancelMarkerIfAvailable();
            RefreshStatus();
        }

        private void WriteCancelMarkerIfAvailable()
        {
            if (cancelMarkerWritten || string.IsNullOrEmpty(outputRelative)) return;
            string marker = Path.Combine(ProjectRoot, outputRelative, "CANCEL.request");
            if (!Directory.Exists(Path.GetDirectoryName(marker))) return;
            try { using (new FileStream(marker, FileMode.CreateNew, FileAccess.Write, FileShare.Read)) { } }
            catch (IOException) { }
            cancelMarkerWritten = true;
        }

        private void SubscribeToUpdates()
        {
            if (updateSubscribed) return;
            EditorApplication.update += PollProcess;
            updateSubscribed = true;
        }

        private void UnsubscribeFromUpdates()
        {
            if (!updateSubscribed) return;
            EditorApplication.update -= PollProcess;
            updateSubscribed = false;
        }

        private void RefreshStatus()
        {
            if (statusLabel == null) return;
            statusLabel.text = processStatus;
            lock (outputLock)
            lock (stdout)
            lock (stderr)
            {
                string outText = stdout.ToString().Trim();
                string errText = stderr.ToString().Trim();
                if (!string.IsNullOrEmpty(errText)) statusLabel.text += "\n" + errText;
                if (!string.IsNullOrEmpty(outText)) statusLabel.text += "\n" + outText;
            }
        }

        private void LoadSummary()
        {
            if (string.IsNullOrEmpty(outputRelative)) return;
            string path = Path.Combine(ProjectRoot, outputRelative, "summary.json");
            if (!File.Exists(path))
            {
                if (summaryLabel != null) summaryLabel.text = "No summary file yet. The run may still be starting or did not complete.";
                return;
            }
            try
            {
                var summary = JsonUtility.FromJson<SummaryEnvelope>(File.ReadAllText(path));
                if (summaryLabel != null)
                    summaryLabel.text = $"{summary.resultStatus} · jobs {summary.generationAttempts} · source-backed outputs {summary.sourceBackedCandidateOutputs} · locally eligible {summary.generatedReferenceCandidates} · unique owner review {summary.uniqueOwnerReviewCandidates} · owner approved {summary.ownerApprovedCandidates} · Engine qualified {summary.engineQualifiedCampaignLevels} · {summary.engineStatus}";
                BuildQueue(summary.records ?? Array.Empty<CandidateSummary>());
            }
            catch (Exception ex)
            {
                if (summaryLabel != null) summaryLabel.text = "Summary invalid: " + ex.Message;
            }
        }

        private void BuildQueue(IEnumerable<CandidateSummary> records)
        {
            if (candidateQueue == null) return;
            candidateQueue.Clear();
            foreach (var record in records)
            {
                string path = record.recordPath;
                var button = MakeButton($"{record.profileId} · #{record.attempt} · {record.triageStatus} · seed {record.donorSeed}", () => SelectCandidate(path));
                button.tooltip = record.triageReason + " · SHA-256 " + record.draftSha256;
                candidateQueue.Add(button);
            }
            if (!records.Any()) candidateQueue.Add(new Label("No candidate records in this run."));
        }

        private void SelectCandidate(string relativeRecordPath)
        {
            string path = Path.GetFullPath(Path.Combine(ProjectRoot, outputRelative, relativeRecordPath));
            string root = Path.GetFullPath(Path.Combine(ProjectRoot, outputRelative)).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!path.StartsWith(root, StringComparison.OrdinalIgnoreCase) || !File.Exists(path))
            {
                EditorUtility.DisplayDialog("Candidate record unavailable", "The selected record is missing or outside this run.", "OK");
                return;
            }
            try
            {
                selectedCandidate = JsonUtility.FromJson<CandidateEnvelope>(File.ReadAllText(path));
                if (selectedCandidate == null || selectedCandidate.draft == null)
                {
                    selectedDraft = null;
                    RenderBoardPreview("This record is a failed attempt and has no LevelDraft.");
                    return;
                }
                var errors = selectedCandidate.draft.Validate();
                errors.AddRange(GameProfileCatalog.ValidateDraft(selectedCandidate.draft));
                if (errors.Count > 0) throw new InvalidOperationException(string.Join("\n", errors));
                string actualSha = LevelDraftJson.Sha256(selectedCandidate.draft);
                if (!string.Equals(actualSha, selectedCandidate.draftSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Draft SHA-256 does not match the candidate record.");
                selectedDraft = selectedCandidate.draft;
                RenderBoardPreview($"{selectedCandidate.candidateId}\n{selectedCandidate.triageStatus} · {selectedCandidate.triageReason}\nSHA-256 {actualSha}\nPROTOTYPE_ONLY · ENG-M24 BLOCKED");
            }
            catch (Exception ex)
            {
                selectedDraft = null;
                RenderBoardPreview("Candidate rejected by Unity's strict parser: " + ex.Message);
            }
        }

        private void RenderBoardPreview(string heading)
        {
            if (boardPreview == null) return;
            boardPreview.Clear();
            var label = new Label(heading) { style = { whiteSpace = WhiteSpace.Normal } };
            boardPreview.Add(label);
            if (selectedDraft == null) return;
            for (int row = 0; row < selectedDraft.height; row++)
            {
                var line = new VisualElement { style = { flexDirection = FlexDirection.Row } };
                for (int column = 0; column < selectedDraft.width; column++)
                {
                    var cell = selectedDraft.cells.FirstOrDefault(item => item.row == row && item.column == column && item.layer == 0);
                    string text = cell == null || !cell.active ? "·" : cell.obstacleId != null ? "X" : cell.specialId != null ? "*" : cell.contentId ?? "?";
                    var cellLabel = new Label(text);
                    cellLabel.style.width = 54;
                    cellLabel.style.height = 30;
                    cellLabel.style.marginRight = 2;
                    cellLabel.style.marginBottom = 2;
                    cellLabel.style.unityTextAlign = TextAnchor.MiddleCenter;
                    line.Add(cellLabel);
                }
                boardPreview.Add(line);
            }
        }

        private void ExportSelectedReference()
        {
            if (selectedDraft == null || selectedCandidate == null || selectedCandidate.triageStatus != "UNIQUE_OWNER_REVIEW_CANDIDATE")
            {
                EditorUtility.DisplayDialog("Export unavailable", "Only locally prefiltered, unique owner-review candidates can be exported. Rejected or unresolved candidates remain in their QA record for inspection.", "OK");
                return;
            }
            try
            {
                string exportFolder = Path.Combine(ProjectRoot, outputRelative, "selected-reference-only");
                Directory.CreateDirectory(exportFolder);
                string fileName = selectedDraft.gameProfileId + "-" + selectedDraft.levelId + ".json";
                foreach (char invalid in Path.GetInvalidFileNameChars()) fileName = fileName.Replace(invalid, '_');
                string destination = Path.Combine(exportFolder, fileName);
                byte[] bytes = Encoding.UTF8.GetBytes(LevelDraftJson.Serialize(selectedDraft));
                using (var stream = new FileStream(destination, FileMode.CreateNew, FileAccess.Write, FileShare.Read))
                {
                    stream.Write(bytes, 0, bytes.Length);
                    stream.Flush(true);
                }
                EditorUtility.DisplayDialog("Reference-only export saved", destination + "\nSHA-256 " + LevelDraftJson.Sha256(selectedDraft) + "\nOwner review required; Engine remains blocked.", "OK");
            }
            catch (IOException)
            {
                EditorUtility.DisplayDialog("Export preserved existing file", "An export with this name already exists. No overwrite occurred.", "OK");
            }
            catch (Exception ex)
            {
                EditorUtility.DisplayDialog("Reference export failed", ex.Message, "OK");
            }
        }

        private void ShowOutputFolder()
        {
            if (string.IsNullOrEmpty(outputRelative)) return;
            string path = Path.Combine(ProjectRoot, outputRelative);
            if (Directory.Exists(path)) EditorUtility.RevealInFinder(path);
        }
    }
}
