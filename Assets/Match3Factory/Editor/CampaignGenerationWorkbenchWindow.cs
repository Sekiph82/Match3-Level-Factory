using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Match3Factory.Editor;
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
            public int workbenchVersion;
            public int generationAttempts;
            public int sourceBackedCandidateOutputs;
            public int donorOriginalOutputCount;
            public int unresolvedGoalRejectionCount;
            public int derivedLocalAuthoringProposalCount;
            public int locallyAuthorableUniqueDraftCount;
            public int generatedReferenceCandidates;
            public int uniqueOwnerReviewCandidates;
            public int ownerApprovedCandidates;
            public int engineQualifiedCampaignLevels;
            public string engineStatus;
            public CandidateSummary[] records;
            public ProposalSummary[] localGoalProposals;
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
            public string goalContractStatus;
            public string sourceGoalSummary;
            public string localAuthoringStatus;
            public ProposalReference localGoalProposal;
            public string donorRevision;
            public string donorSourceRepository;
            public GoalContractDiagnosis goalContractDiagnosis;
        }

        [Serializable]
        private sealed class GoalContractDiagnosis
        {
            public string status;
            public string reasonCode;
            public DonorGoalFinding[] goals;
        }

        [Serializable]
        private sealed class DonorGoalFinding
        {
            public string sourceTargetId;
            public string status;
            public string donorMeaning;
            public string targetCountMeaning;
            public string difficultyHypothesisMeaning;
            public string localEquivalence;
            public string reasonCode;
        }

        [Serializable]
        private sealed class LocalSampleDiagnostics
        {
            public string status;
            public LocalSampleFinding[] findings;
        }

        [Serializable]
        private sealed class LocalSampleFinding
        {
            public string code;
            public string reason;
        }

        [Serializable]
        private sealed class ProposalUniqueness
        {
            public string status;
            public string duplicateOf;
        }

        [Serializable]
        private sealed class ProposalReference
        {
            public string status;
            public string recordPath;
            public string recordSha256;
            public string draftSha256;
            public string sourceRecordPath;
            public string sourceDraftSha256;
            public string localAuthoringStatus;
            public string uniquenessStatus;
        }

        [Serializable]
        private sealed class ProposalSummary
        {
            public string profileId;
            public string candidateId;
            public int attempt;
            public int donorSeed;
            public string sourceDraftSha256;
            public string sourceRecordPath;
            public string sourceRecordSha256;
            public string status;
            public string recordPath;
            public string recordSha256;
            public string draftSha256;
            public string localAuthoringStatus;
            public string uniquenessStatus;
        }

        [Serializable]
        private sealed class CandidateEnvelope
        {
            public string candidateId;
            public string triageStatus;
            public string triageReason;
            public string draftSha256;
            public string profileId;
            public int donorSeed;
            public ProposalReference localGoalProposal;
            public string goalContractStatus;
            public GoalContractDiagnosis goalContractDiagnosis;
            public string donorSourceRepository;
            public string donorRevision;
            public LevelDraft draft;
        }

        [Serializable]
        private sealed class LocalGoalProposalEnvelope
        {
            public string artifactKind;
            public string artifactStatus;
            public bool sourceGenerated;
            public string sourceRecordPath;
            public string sourceDraftSha256;
            public string authoredLocalGoalProposalSha256;
            public string localAuthoringStatus;
            public string engineStatus;
            public bool engineQualified;
            public bool ownerApproved;
            public bool releaseAuthorized;
            public ProposalAuthoring authoring;
            public GoalDraft[] originalDonorGoals;
            public GoalContractDiagnosis goalContractDiagnosis;
            public LocalSampleDiagnostics localAuthoringDiagnostics;
            public ProposalUniqueness uniqueness;
            public LevelDraft draft;
        }

        [Serializable]
        private sealed class ProposalAuthoring
        {
            public bool donorDifficultyHypothesisInherited;
            public bool donorTargetCountInherited;
            public bool donorMoveBudgetInherited;
            public bool winClaim;
            public string targetId;
            public int targetCount;
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

        [Serializable]
        private sealed class RunConfigurationEnvelope
        {
            public int workbenchVersion;
            public string sourceRevision;
            public string configurationSha256;
        }

        [Serializable]
        private sealed class LocalAuthoringSummary
        {
            public string resultStatus;
            public string sourceKind;
            public int generationAttempts;
            public int localDraftCount;
            public int locallyCompatibleUniqueCount;
            public int engineQualifiedCampaignLevels;
            public string engineStatus;
            public LocalAuthoringRecord[] records;
        }

        [Serializable]
        private sealed class LocalAuthoringRecord
        {
            public string candidateId;
            public string profileId;
            public int attempt;
            public int seed;
            public string draftSha256;
            public string status;
            public string recordPath;
            public string recordSha256;
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
        private string localOutputRelative;
        private SummaryEnvelope loadedSummary;
        private LocalAuthoringSummary loadedLocalSummary;
        private CandidateEnvelope selectedCandidate;
        private LocalGoalProposalEnvelope selectedProposal;
        private LevelDraft selectedDraft;
        private string selectedArtifactPath;
        private bool showSourceCandidates = true;
        private bool showLocalProposals = true;
        private string statusFilter = "All statuses";
        private Process process;
        private bool cancelRequested;
        private bool localRun;
        private bool cancelMarkerWritten;
        private string processStatus = "Idle · reference-only · ENG-M24 blocked";
        private Label statusLabel;
        private Label summaryLabel;
        private ScrollView candidateQueue;
        private ScrollView localCandidateQueue;
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
            actions.Add(MakeButton("Start original local preview batch (max 10/profile)", StartLocalAuthoringBatch));
            actions.Add(MakeButton("Resume batch…", ChooseAndResume));
            actions.Add(MakeButton("Cancel after current candidate", RequestCancel));
            actions.Add(MakeButton("Load run summary", LoadSummary));
            actions.Add(MakeButton("Load local preview set…", LoadLocalSummary));
            actions.Add(MakeButton("Show output folder", ShowOutputFolder));
            rootVisualElement.Add(actions);

            statusLabel = new Label(processStatus);
            statusLabel.style.whiteSpace = WhiteSpace.Normal;
            rootVisualElement.Add(statusLabel);
            summaryLabel = new Label("No batch summary loaded.") { name = "campaign-summary" };
            summaryLabel.style.whiteSpace = WhiteSpace.Normal;
            rootVisualElement.Add(summaryLabel);
            rootVisualElement.Add(new Label("Review queue · source drafts and separate local preview alternatives"));
            var filters = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            var sourceToggle = new Toggle("Original donor outputs") { value = showSourceCandidates };
            sourceToggle.RegisterValueChangedCallback(evt => { showSourceCandidates = evt.newValue; RefreshLoadedQueue(); });
            filters.Add(sourceToggle);
            var proposalToggle = new Toggle("Locally authored preview alternatives") { value = showLocalProposals };
            proposalToggle.RegisterValueChangedCallback(evt => { showLocalProposals = evt.newValue; RefreshLoadedQueue(); });
            filters.Add(proposalToggle);
            var statusChoices = new List<string> { "All statuses", "Unique", "Near duplicate", "Duplicate", "Rejected / failed" };
            var statusDropdown = new DropdownField("Structure/status group", statusChoices, statusFilter);
            statusDropdown.RegisterValueChangedCallback(evt => { statusFilter = evt.newValue; RefreshLoadedQueue(); });
            filters.Add(statusDropdown);
            rootVisualElement.Add(filters);
            var reviewColumns = new VisualElement { style = { flexDirection = FlexDirection.Row } };
            var donorColumn = new VisualElement { style = { flexGrow = 1, minWidth = 300 } };
            donorColumn.Add(new Label("DONOR SOURCE + DERIVED GOAL PROPOSALS"));
            candidateQueue = new ScrollView { name = "campaign-candidate-queue" };
            candidateQueue.style.maxHeight = 260;
            donorColumn.Add(candidateQueue);
            var localColumn = new VisualElement { style = { flexGrow = 1, minWidth = 300 } };
            localColumn.Add(new Label("FACTORY-ORIGINAL LOCAL BOARDS"));
            localCandidateQueue = new ScrollView { name = "campaign-local-candidate-queue" };
            localCandidateQueue.style.maxHeight = 260;
            localColumn.Add(localCandidateQueue);
            reviewColumns.Add(donorColumn);
            reviewColumns.Add(localColumn);
            rootVisualElement.Add(reviewColumns);
            rootVisualElement.Add(new Label("Selected board and goal provenance"));
            boardPreview = new VisualElement { name = "campaign-board-preview" };
            rootVisualElement.Add(boardPreview);
            rootVisualElement.Add(MakeButton("Export selected · reference only", ExportSelectedReference));
            rootVisualElement.Add(MakeButton("Reveal selected review artifact", RevealSelectedArtifact));
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

        private void StartLocalAuthoringBatch()
        {
            if (process != null && !process.HasExited)
            {
                EditorUtility.DisplayDialog("Batch already running", "Wait for or cancel the active batch first.", "OK");
                return;
            }
            string script = Path.Combine(ProjectRoot, "Tools", "UltraGem", "factory_local_authoring.py");
            if (!File.Exists(script))
            {
                EditorUtility.DisplayDialog("Local authoring unavailable", "Missing Tools/UltraGem/factory_local_authoring.py.", "OK");
                return;
            }
            string runName = "FactoryLocalQA-" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N").Substring(0, 8);
            outputRelative = Path.Combine("Artifacts", runName).Replace('\\', '/');
            var profileIds = allProfiles ? Profiles : new[] { selectedProfile };
            var args = new List<string> { Quote(script), "--project-root", Quote(ProjectRoot),
                "--profiles", Quote(string.Join(",", profileIds)), "--attempts-per-profile", Math.Max(1, Math.Min(10, attemptsPerProfile)).ToString(),
                "--seed-start", seedStart.ToString(), "--width", columns.ToString(),
                "--height", rows.ToString(), "--colors", colors.ToString(), "--output-relative", Quote(outputRelative), "--session-start" };
            try
            {
                string directory = Path.Combine(ProjectRoot, outputRelative);
                if (Directory.Exists(directory)) throw new IOException("Unique local run folder already exists; left unchanged.");
                localRun = true;
                lock (outputLock) { stdout.Clear(); stderr.Clear(); }
                cancelRequested = false;
                cancelMarkerWritten = false;
                var info = new ProcessStartInfo { FileName = pythonExecutable, Arguments = string.Join(" ", args),
                    WorkingDirectory = ProjectRoot, UseShellExecute = false, CreateNoWindow = true,
                    RedirectStandardOutput = true, RedirectStandardError = true };
                process = new Process { StartInfo = info };
                process.OutputDataReceived += (_, evt) => AppendBounded(stdout, evt.Data);
                process.ErrorDataReceived += (_, evt) => AppendBounded(stderr, evt.Data);
                process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
                outputField.value = outputRelative;
                processStatus = "Starting checkpointed Factory-local preview run · cancellable and resumable · Engine blocked…";
                SubscribeToUpdates(); RefreshStatus();
            }
            catch (Exception ex) { processStatus = "NOT_RUN · local authoring process could not start: " + ex.Message; RefreshStatus(); }
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
            string configPath = Path.Combine(full, "run-config.json");
            if (!File.Exists(configPath))
            {
                EditorUtility.DisplayDialog("Resume unavailable", "This folder has no authenticated workbench run configuration. It remains untouched.", "OK");
                return;
            }
            try
            {
                var run = JsonUtility.FromJson<RunConfigurationEnvelope>(File.ReadAllText(configPath));
                if (File.Exists(Path.Combine(full, "checkpoint.json")) &&
                    run != null && run.sourceRevision == "LFX-M11-R04-local-authoring-v2")
                {
                    localRun = true;
                    LaunchLocalSession(resume: true);
                    return;
                }
                if (run == null || run.workbenchVersion != 2)
                {
                    EditorUtility.DisplayDialog("R01 run is read-only", "Older campaign workbench runs can be loaded from their summary for review, but R02 does not resume, migrate, or rewrite their checkpoints. Start a new R02 run.", "OK");
                    return;
                }
            }
            catch (Exception ex)
            {
                EditorUtility.DisplayDialog("Resume unavailable", "Run configuration is invalid: " + ex.Message, "OK");
                return;
            }
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
            localRun = false;
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

        private void LaunchLocalSession(bool resume)
        {
            if (process != null && !process.HasExited)
            {
                EditorUtility.DisplayDialog("Batch already running", "Wait for the active batch or cancel it before starting another.", "OK");
                return;
            }
            string script = Path.Combine(ProjectRoot, "Tools", "UltraGem", "factory_local_authoring.py");
            if (!File.Exists(script))
            {
                EditorUtility.DisplayDialog("Local authoring unavailable", "Missing Tools/UltraGem/factory_local_authoring.py.", "OK");
                return;
            }
            var args = new List<string> { Quote(script), "--project-root", Quote(ProjectRoot),
                "--output-relative", Quote(outputRelative), resume ? "--session-resume" : "--session-start" };
            if (!resume)
            {
                var profileIds = allProfiles ? Profiles : new[] { selectedProfile };
                args.Add("--profiles"); args.Add(Quote(string.Join(",", profileIds)));
                args.Add("--attempts-per-profile"); args.Add(Math.Max(1, Math.Min(10, attemptsPerProfile)).ToString());
                args.Add("--seed-start"); args.Add(seedStart.ToString());
                args.Add("--width"); args.Add(columns.ToString()); args.Add("--height"); args.Add(rows.ToString());
                args.Add("--colors"); args.Add(colors.ToString());
            }
            try
            {
                string runDirectory = Path.Combine(ProjectRoot, outputRelative);
                if (resume ? !Directory.Exists(runDirectory) : Directory.Exists(runDirectory))
                    throw new IOException(resume ? "Selected local run folder is missing." : "Unique local run folder already exists; left unchanged.");
                localRun = true;
                lock (outputLock) { stdout.Clear(); stderr.Clear(); }
                cancelRequested = false;
                cancelMarkerWritten = false;
                var info = new ProcessStartInfo { FileName = pythonExecutable, Arguments = string.Join(" ", args),
                    WorkingDirectory = ProjectRoot, UseShellExecute = false, CreateNoWindow = true,
                    RedirectStandardOutput = true, RedirectStandardError = true };
                process = new Process { StartInfo = info, EnableRaisingEvents = true };
                process.OutputDataReceived += (_, evt) => AppendBounded(stdout, evt.Data);
                process.ErrorDataReceived += (_, evt) => AppendBounded(stderr, evt.Data);
                process.Start(); process.BeginOutputReadLine(); process.BeginErrorReadLine();
                outputField.value = outputRelative;
                localOutputRelative = outputRelative;
                processStatus = resume ? "Resuming Factory-local run after checkpoint validation…" :
                    "Running checkpointed Factory-local sample previews · donor input unused · ENG-M24 blocked…";
                SubscribeToUpdates(); RefreshStatus();
            }
            catch (Exception ex) { processStatus = "NOT_RUN · local session could not start: " + ex.Message; RefreshStatus(); }
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
            string marker = Path.Combine(ProjectRoot, outputRelative, localRun ? "cancel.request" : "CANCEL.request");
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
            if (string.IsNullOrEmpty(outputRelative))
            {
                string selected = EditorUtility.OpenFilePanel("Load a campaign run summary for read-only review", Path.Combine(ProjectRoot, "Artifacts"), "json");
                if (string.IsNullOrEmpty(selected)) return;
                string full = Path.GetFullPath(selected);
                string artifactRoot = Path.GetFullPath(Path.Combine(ProjectRoot, "Artifacts")).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                if (!full.StartsWith(artifactRoot, StringComparison.OrdinalIgnoreCase) ||
                    !string.Equals(Path.GetFileName(full), "summary.json", StringComparison.OrdinalIgnoreCase))
                {
                    EditorUtility.DisplayDialog("Invalid run summary", "Choose a summary.json inside this project's Artifacts folder. The selected file was not changed.", "OK");
                    return;
                }
                outputRelative = Path.GetDirectoryName(full).Substring(Path.GetFullPath(ProjectRoot).TrimEnd(Path.DirectorySeparatorChar).Length + 1).Replace('\\', '/');
                if (outputField != null) outputField.value = outputRelative;
            }
            string path = Path.Combine(ProjectRoot, outputRelative, "summary.json");
            if (!File.Exists(path))
            {
                if (summaryLabel != null) summaryLabel.text = "No summary file yet. The run may still be starting or did not complete.";
                return;
            }
            try
            {
                string raw = File.ReadAllText(path);
                if (raw.Contains("\"sourceKind\": \"FactoryOriginalLocalSampleBoard\""))
                {
                    loadedLocalSummary = JsonUtility.FromJson<LocalAuthoringSummary>(raw);
                    localOutputRelative = outputRelative;
                    if (summaryLabel != null)
                        summaryLabel.text = $"FACTORY ORIGINAL LOCAL · {loadedLocalSummary.generationAttempts} attempts · {loadedLocalSummary.localDraftCount} drafts · locally compatible unique {loadedLocalSummary.locallyCompatibleUniqueCount} · owner approved 0 · Engine qualified {loadedLocalSummary.engineQualifiedCampaignLevels} · {loadedLocalSummary.engineStatus}";
                    RefreshLoadedQueue();
                    return;
                }
                var summary = JsonUtility.FromJson<SummaryEnvelope>(raw);
                loadedSummary = summary;
                if (summaryLabel != null)
                    summaryLabel.text = $"{summary.resultStatus} v{summary.workbenchVersion} · donor attempts {summary.generationAttempts} · original donor outputs {summary.donorOriginalOutputCount} · unresolved donor goals {summary.unresolvedGoalRejectionCount} · derived local proposals {summary.derivedLocalAuthoringProposalCount} · locally authorable unique {summary.locallyAuthorableUniqueDraftCount} · owner approved {summary.ownerApprovedCandidates} · Engine qualified {summary.engineQualifiedCampaignLevels} · {summary.engineStatus}";
                RefreshLoadedQueue();
            }
            catch (Exception ex)
            {
                if (summaryLabel != null) summaryLabel.text = "Summary invalid: " + ex.Message;
            }
        }

        private void RefreshLoadedQueue()
        {
            if (candidateQueue == null || localCandidateQueue == null) return;
            candidateQueue.Clear();
            localCandidateQueue.Clear();
            if (loadedSummary != null && showSourceCandidates)
            {
                foreach (var record in loadedSummary.records ?? Array.Empty<CandidateSummary>())
                {
                    if (!MatchesStatusFilter(record.triageStatus)) continue;
                    string path = record.recordPath;
                    var button = MakeButton($"SOURCE · {record.profileId} · #{record.attempt} · {record.triageStatus} · {record.sourceGoalSummary}", () => SelectCandidate(path, record.recordSha256));
                    button.tooltip = record.triageReason + " · original LevelDraft SHA-256 " + record.draftSha256;
                    candidateQueue.Add(button);
                }
            }
            if (loadedSummary != null && showLocalProposals)
            {
                foreach (var proposal in loadedSummary.localGoalProposals ?? Array.Empty<ProposalSummary>())
                {
                    if (!MatchesStatusFilter(proposal.uniquenessStatus)) continue;
                    var button = MakeButton($"DERIVED PREVIEW · {proposal.profileId} · #{proposal.attempt} · {proposal.localAuthoringStatus} · {proposal.uniquenessStatus}", () => SelectLocalProposal(proposal));
                    button.tooltip = $"Original goal retained in source record · source {proposal.sourceDraftSha256} → local proposal {proposal.draftSha256}";
                    candidateQueue.Add(button);
                }
            }
            if (loadedLocalSummary != null)
            {
                foreach (var record in loadedLocalSummary.records ?? Array.Empty<LocalAuthoringRecord>())
                {
                    var button = MakeButton($"FACTORY LOCAL · {record.profileId} · #{record.attempt} · {record.status} · seed {record.seed}", () => SelectLocalBoard(record));
                    button.tooltip = "Factory-authored sample board · no donor input · " + record.draftSha256;
                    localCandidateQueue.Add(button);
                }
            }
            if (candidateQueue.childCount == 0) candidateQueue.Add(new Label("No donor/proposal records loaded or matching filters."));
            if (localCandidateQueue.childCount == 0) localCandidateQueue.Add(new Label("No independent Factory-local set loaded."));
        }

        private void LoadLocalSummary()
        {
            string selected = EditorUtility.OpenFilePanel("Load a Factory-local preview summary", Path.Combine(ProjectRoot, "Artifacts"), "json");
            if (string.IsNullOrEmpty(selected)) return;
            string full = Path.GetFullPath(selected);
            string artifactRoot = Path.GetFullPath(Path.Combine(ProjectRoot, "Artifacts")).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!full.StartsWith(artifactRoot, StringComparison.OrdinalIgnoreCase) ||
                !string.Equals(Path.GetFileName(full), "summary.json", StringComparison.OrdinalIgnoreCase))
            {
                EditorUtility.DisplayDialog("Invalid local run summary", "Choose summary.json inside this project's Artifacts folder.", "OK");
                return;
            }
            try
            {
                string raw = File.ReadAllText(full);
                if (!raw.Contains("\"sourceKind\": \"FactoryOriginalLocalSampleBoard\""))
                    throw new InvalidOperationException("Selected summary is not a Factory-original local authoring run.");
                string selectedRun = Path.GetDirectoryName(full);
                CampaignArtifactIntegrity.VerifyLocalRun(selectedRun);
                localOutputRelative = selectedRun.Substring(Path.GetFullPath(ProjectRoot).TrimEnd(Path.DirectorySeparatorChar).Length + 1).Replace('\\', '/');
                loadedLocalSummary = JsonUtility.FromJson<LocalAuthoringSummary>(raw);
                if (summaryLabel != null)
                    summaryLabel.text = $"DONOR + FACTORY LOCAL REVIEW · donor outputs {loadedSummary?.donorOriginalOutputCount ?? 0} · independent local drafts {loadedLocalSummary.localDraftCount} · Engine qualified 0 · BLOCKED_ENG_M24";
                RefreshLoadedQueue();
            }
            catch (Exception ex) { EditorUtility.DisplayDialog("Local summary unavailable", ex.Message, "OK"); }
        }

        private void SelectLocalBoard(LocalAuthoringRecord record)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(localOutputRelative) || string.IsNullOrWhiteSpace(record.recordPath) ||
                    Path.IsPathRooted(record.recordPath) || record.recordPath.Split('/', '\\').Any(part => part == ".."))
                    throw new InvalidOperationException("Local review artifact path is unsafe.");
                string localRoot = Path.GetFullPath(Path.Combine(ProjectRoot, localOutputRelative)).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                string path = Path.GetFullPath(Path.Combine(localRoot, record.recordPath));
                if (!path.StartsWith(localRoot, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException("Local review artifact resolves outside its run.");
                CampaignArtifactIntegrity.VerifyLocalRun(localRoot.TrimEnd(Path.DirectorySeparatorChar));
                byte[] bytes = File.ReadAllBytes(path);
                if (!string.Equals(Sha256(bytes), record.recordSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Local draft file SHA-256 does not match its summary.");
                var draft = JsonUtility.FromJson<LevelDraft>(Encoding.UTF8.GetString(bytes));
                if (draft == null || draft.sourceKind != "FactoryOriginalLocalSampleBoard" ||
                    draft.sourceRevision != "LFX-M11-R04-local-authoring-v2" ||
                    !string.Equals(LevelDraftJson.Sha256(draft), record.draftSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Local draft provenance or canonical SHA-256 is invalid.");
                var errors = draft.Validate();
                if (errors.Count > 0) throw new InvalidOperationException(string.Join(" ", errors));
                var capabilityErrors = GameProfileCatalog.ValidateDraft(draft);
                if (capabilityErrors.Count > 0) throw new NotSupportedException(string.Join(" ", capabilityErrors));
                selectedDraft = draft; selectedCandidate = null; selectedProposal = null; selectedArtifactPath = path;
                RenderBoardPreview($"FACTORY ORIGINAL LOCAL · {record.candidateId}\nLOCAL_SAMPLE_COMPATIBLE_PREVIEW_ONLY · sample.score 500 / 20 moves\nSource: {draft.sourceRepository}@{draft.sourceRevision} · {draft.sourceKind}\nSHA-256 {record.draftSha256}\nPROTOTYPE_ONLY · ENGINE_NOT_RUN · ENG-M24 BLOCKED · not a WIN");
            }
            catch (Exception ex) { RenderBoardPreview("Local board rejected: " + ex.Message); }
        }

        private static string Sha256(byte[] bytes)
        {
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", string.Empty).ToLowerInvariant();
        }

        private bool MatchesStatusFilter(string status)
        {
            if (statusFilter == "All statuses") return true;
            status = status ?? string.Empty;
            if (statusFilter == "Unique") return status.StartsWith("UNIQUE", StringComparison.Ordinal) || status == "LOCALLY_AUTHORABLE_UNIQUE_PREVIEW_ONLY";
            if (statusFilter == "Near duplicate") return status.Contains("NEAR_DUPLICATE");
            if (statusFilter == "Duplicate") return status.Contains("DUPLICATE") && !status.Contains("NEAR_DUPLICATE");
            return !(status.StartsWith("UNIQUE", StringComparison.Ordinal) ||
                     status == "LOCALLY_AUTHORABLE_UNIQUE_PREVIEW_ONLY" || status.Contains("DUPLICATE"));
        }

        private string ResolveRunArtifact(string relativePath)
        {
            if (string.IsNullOrWhiteSpace(outputRelative) || string.IsNullOrWhiteSpace(relativePath) ||
                Path.IsPathRooted(relativePath) || relativePath.Split('/', '\\').Any(part => part == ".."))
                throw new InvalidOperationException("The review artifact path is unsafe.");
            string root = Path.GetFullPath(Path.Combine(ProjectRoot, outputRelative)).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(Path.Combine(root, relativePath));
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("The review artifact resolves outside its unique run folder.");
            return full;
        }

        private static string Sha256Bytes(byte[] bytes)
        {
            using (var hash = SHA256.Create())
                return string.Concat(hash.ComputeHash(bytes).Select(value => value.ToString("x2", System.Globalization.CultureInfo.InvariantCulture)));
        }

        private static string FormatGoals(IEnumerable<GoalDraft> goals)
        {
            return string.Join(", ", (goals ?? Enumerable.Empty<GoalDraft>())
                .Select(goal => goal == null ? "<invalid>" : $"{goal.goalId}:{goal.targetId}={goal.targetCount}"));
        }

        private static string FormatDonorGoalDiagnosis(GoalContractDiagnosis diagnosis)
        {
            if (diagnosis == null || diagnosis.goals == null || diagnosis.goals.Length == 0)
                return "R01 record has no R02 goal diagnosis; source bytes retained unchanged.";
            return string.Join("\n", diagnosis.goals.Select(goal =>
                $"{goal.sourceTargetId} · {goal.status} · {goal.reasonCode}\n{goal.donorMeaning}\n{goal.targetCountMeaning}"));
        }

        private static string FormatLocalFindings(LocalSampleDiagnostics diagnostics)
        {
            if (diagnostics == null) return "Local preview diagnostics unavailable.";
            if (diagnostics.findings == null || diagnostics.findings.Length == 0) return diagnostics.status;
            return diagnostics.status + " · " + string.Join("; ", diagnostics.findings.Select(item => item.code + ": " + item.reason));
        }

        private void SelectCandidate(string relativeRecordPath, string expectedRecordSha)
        {
            string path;
            try { path = ResolveRunArtifact(relativeRecordPath); }
            catch (Exception ex) { EditorUtility.DisplayDialog("Candidate record unavailable", ex.Message, "OK"); return; }
            if (!File.Exists(path))
            {
                EditorUtility.DisplayDialog("Candidate record unavailable", "The selected record is missing or outside this run.", "OK");
                return;
            }
            try
            {
                byte[] raw = File.ReadAllBytes(path);
                if (!string.Equals(Sha256Bytes(raw), expectedRecordSha, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Candidate record SHA-256 does not match summary.json.");
                selectedCandidate = JsonUtility.FromJson<CandidateEnvelope>(Encoding.UTF8.GetString(raw));
                selectedProposal = null;
                selectedArtifactPath = path;
                if (selectedCandidate == null || selectedCandidate.draft == null)
                {
                    selectedDraft = null;
                    RenderBoardPreview("This record is a failed attempt and has no LevelDraft.");
                    return;
                }
                var errors = selectedCandidate.draft.Validate();
                if (errors.Count > 0) throw new InvalidOperationException(string.Join("\n", errors));
                string actualSha = LevelDraftJson.Sha256(selectedCandidate.draft);
                if (!string.Equals(actualSha, selectedCandidate.draftSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Draft SHA-256 does not match the candidate record.");
                selectedDraft = selectedCandidate.draft;
                var capabilityErrors = GameProfileCatalog.ValidateDraft(selectedCandidate.draft);
                string capabilityStatus = capabilityErrors.Count == 0 ? "local profile check passed" : "local profile check rejected: " + string.Join("; ", capabilityErrors);
                RenderBoardPreview($"ORIGINAL DONOR · {selectedCandidate.candidateId}\n{selectedCandidate.triageStatus} · {selectedCandidate.triageReason}\nOriginal goal(s): {FormatGoals(selectedDraft.goals)}\nGoal contract: {selectedCandidate.goalContractStatus ?? "R01 record · diagnosis not stored"}\n{FormatDonorGoalDiagnosis(selectedCandidate.goalContractDiagnosis)}\nDonor provenance: {selectedCandidate.donorSourceRepository}@{selectedCandidate.donorRevision}\nSHA-256 {actualSha}\n{capabilityStatus}\nPROTOTYPE_ONLY · ENGINE_NOT_RUN · ENG-M24 BLOCKED");
            }
            catch (Exception ex)
            {
                selectedDraft = null;
                RenderBoardPreview("Candidate rejected by Unity's strict parser: " + ex.Message);
            }
        }

        private void SelectLocalProposal(ProposalSummary summary)
        {
            try
            {
                string proposalPath = ResolveRunArtifact(summary.recordPath);
                byte[] proposalBytes = File.ReadAllBytes(proposalPath);
                if (!string.Equals(Sha256Bytes(proposalBytes), summary.recordSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Derived proposal record SHA-256 does not match summary.json.");
                selectedProposal = JsonUtility.FromJson<LocalGoalProposalEnvelope>(Encoding.UTF8.GetString(proposalBytes));
                if (selectedProposal == null || selectedProposal.draft == null ||
                    selectedProposal.artifactKind != "FACTORY_AUTHORED_LOCAL_PREVIEW_GOAL_ALTERNATIVE" ||
                    selectedProposal.artifactStatus != "LOCALLY_AUTHORED_PREVIEW_ONLY" ||
                    selectedProposal.sourceGenerated || selectedProposal.engineStatus != "BLOCKED_ENG_M24" ||
                    selectedProposal.engineQualified || selectedProposal.ownerApproved || selectedProposal.releaseAuthorized)
                    throw new InvalidOperationException("Derived proposal authority labels are invalid.");
                if (selectedProposal.localAuthoringStatus != summary.localAuthoringStatus ||
                    selectedProposal.uniqueness == null || selectedProposal.uniqueness.status != summary.uniquenessStatus)
                    throw new InvalidOperationException("Proposal review status disagrees with summary.json.");
                string sourcePath = ResolveRunArtifact(selectedProposal.sourceRecordPath);
                byte[] sourceBytes = File.ReadAllBytes(sourcePath);
                if (!string.Equals(Sha256Bytes(sourceBytes), summary.sourceRecordSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Original source record SHA-256 does not match summary.json.");
                selectedCandidate = JsonUtility.FromJson<CandidateEnvelope>(Encoding.UTF8.GetString(sourceBytes));
                if (selectedCandidate == null || selectedCandidate.draft == null ||
                    !string.Equals(LevelDraftJson.Sha256(selectedCandidate.draft), selectedProposal.sourceDraftSha256, StringComparison.OrdinalIgnoreCase) ||
                    !string.Equals(selectedProposal.sourceDraftSha256, summary.sourceDraftSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Source-to-derived LevelDraft hash chain is invalid.");
                if (selectedProposal.originalDonorGoals == null ||
                    FormatGoals(selectedProposal.originalDonorGoals) != FormatGoals(selectedCandidate.draft.goals))
                    throw new InvalidOperationException("The derived proposal does not retain the original donor goals.");
                if (selectedProposal.authoring == null || selectedProposal.authoring.donorDifficultyHypothesisInherited ||
                    selectedProposal.authoring.donorTargetCountInherited || selectedProposal.authoring.donorMoveBudgetInherited ||
                    selectedProposal.authoring.winClaim || selectedProposal.authoring.targetId != "sample.score" ||
                    selectedProposal.authoring.targetCount != 500)
                    throw new InvalidOperationException("Local proposal contains inherited donor difficulty, target, move-budget, or WIN claims.");
                var errors = selectedProposal.draft.Validate();
                if (errors.Count > 0) throw new InvalidOperationException(string.Join("\n", errors));
                string actualSha = LevelDraftJson.Sha256(selectedProposal.draft);
                if (!string.Equals(actualSha, selectedProposal.authoredLocalGoalProposalSha256, StringComparison.OrdinalIgnoreCase) ||
                    !string.Equals(actualSha, summary.draftSha256, StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("Derived LevelDraft SHA-256 does not match the proposal chain.");
                selectedDraft = selectedProposal.draft;
                selectedArtifactPath = proposalPath;
                var capabilityErrors = GameProfileCatalog.ValidateDraft(selectedDraft);
                string capabilityStatus = capabilityErrors.Count == 0 ? "local profile check passed" : "local profile check rejected: " + string.Join("; ", capabilityErrors);
                RenderBoardPreview($"LOCALLY AUTHORED PREVIEW ONLY · {summary.candidateId}\nOriginal donor goal(s): {FormatGoals(selectedCandidate.draft.goals)}\n{FormatDonorGoalDiagnosis(selectedProposal.goalContractDiagnosis)}\nSeparate local proposal: {FormatGoals(selectedDraft.goals)}\n{FormatLocalFindings(selectedProposal.localAuthoringDiagnostics)}\nSource SHA-256 {selectedProposal.sourceDraftSha256}\nDerived SHA-256 {actualSha}\n{summary.localAuthoringStatus} · {capabilityStatus}\nDonor ranking, targetCount, move budget, difficulty, and WIN were not inherited.\nPROTOTYPE_ONLY · ENGINE_NOT_RUN · ENG-M24 BLOCKED");
            }
            catch (Exception ex)
            {
                selectedDraft = null;
                EditorUtility.DisplayDialog("Proposal integrity check failed", ex.Message, "OK");
                RenderBoardPreview("Derived proposal failed provenance or schema verification: " + ex.Message);
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
            if (selectedDraft == null || selectedCandidate == null || selectedProposal != null || selectedCandidate.triageStatus != "UNIQUE_OWNER_REVIEW_CANDIDATE")
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

        private void RevealSelectedArtifact()
        {
            if (string.IsNullOrEmpty(selectedArtifactPath) || !File.Exists(selectedArtifactPath))
            {
                EditorUtility.DisplayDialog("Review artifact unavailable", "Select a verified source or derived record first.", "OK");
                return;
            }
            EditorUtility.RevealInFinder(selectedArtifactPath);
        }

        private void ShowOutputFolder()
        {
            if (string.IsNullOrEmpty(outputRelative)) return;
            string path = Path.Combine(ProjectRoot, outputRelative);
            if (Directory.Exists(path)) EditorUtility.RevealInFinder(path);
        }
    }
}
