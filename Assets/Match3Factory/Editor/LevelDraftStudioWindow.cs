using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.UIElements;
using UnityEngine;
using UnityEngine.UIElements;

namespace Match3Factory
{
    public sealed class LevelDraftStudioWindow : EditorWindow
    {
        private static readonly string[] Profiles = GameProfileCatalog.AllProfileIds.ToArray();
        private static readonly string[] GemIds = { "Blue", "Green", "Orange", "Purple", "White", "Yellow" };
        private static Func<string> autosavePathOverrideForTesting;
        private LevelDraft draft;
        private VisualElement board;
        private ScrollView boardScroll;
        private Label status;
        private VisualElement goalEditor;
        private VisualElement levelBrowser;
        private TextField levelSearch;
        private ObjectField sampleLevel;
        private int selectedGem;
        private int selectedRow;
        private int selectedColumn;
        private int selectedLayer;
        private string recoveryNotice;
        private bool autosaveQueued;
        private float zoom = 1f;
        private readonly System.Collections.Generic.Stack<LevelDraft> undo = new System.Collections.Generic.Stack<LevelDraft>();
        private readonly System.Collections.Generic.Stack<LevelDraft> redo = new System.Collections.Generic.Stack<LevelDraft>();

        [MenuItem("Tools/Match3 Factory/Level Draft Studio")]
        public static void Open()
        {
            var window = GetWindow<LevelDraftStudioWindow>();
            window.titleContent = new GUIContent("Level Draft Studio");
            window.minSize = new Vector2(760, 560);
        }

        public void CreateGUI()
        {
            if (draft == null)
            {
                LevelDraft restored;
                AutosaveRecoveryStatus recovery;
                string message;
                if (LevelDraftAutosaveStore.TryLoad(AutosavePath, out restored, out recovery, out message))
                {
                    draft = restored;
                    if (recovery != AutosaveRecoveryStatus.Current) recoveryNotice = message ?? "Recovered the previous valid autosave.";
                }
                else
                {
                    draft = NewDraft(8, 8);
                    if (recovery == AutosaveRecoveryStatus.Invalid) recoveryNotice = message;
                }
            }
            rootVisualElement.Clear();
            rootVisualElement.style.paddingLeft = 12;
            rootVisualElement.style.paddingRight = 12;
            rootVisualElement.style.paddingTop = 10;
            rootVisualElement.style.paddingBottom = 10;
            rootVisualElement.focusable = true;
            rootVisualElement.RegisterCallback<KeyDownEvent>(OnKeyDown);

            var heading = new Label("Match3 Level Draft Studio · PROTOTYPE_ONLY");
            heading.style.unityFontStyleAndWeight = FontStyle.Bold;
            heading.style.fontSize = 17;
            rootVisualElement.Add(heading);
            if (!string.IsNullOrEmpty(recoveryNotice)) rootVisualElement.Add(new HelpBox(recoveryNotice, HelpBoxMessageType.Warning));

            var actions = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            actions.Add(MakeButton("New 8×8", () => { PushUndo(); draft = NewDraft(8, 8); Refresh(); }));
            actions.Add(MakeButton("Open JSON", OpenDraft));
            actions.Add(MakeButton("Save JSON", SaveDraft));
            actions.Add(MakeButton("Undo", Undo));
            actions.Add(MakeButton("Redo", Redo));
            actions.Add(MakeButton("Validate", ValidateDraft));
            actions.Add(MakeButton("Player metadata", PlayerVisibleMetadataStudioWindow.Open));
            actions.Add(MakeButton("Zoom +", () => SetZoom(zoom + .1f)));
            actions.Add(MakeButton("Zoom −", () => SetZoom(zoom - .1f)));
            rootVisualElement.Add(actions);

            var gridControls = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            var gridWidth = new IntegerField("Width") { value = draft.width };
            gridWidth.RegisterValueChangedCallback(evt => ResizeBoard(evt.newValue, draft.height, draft.layers));
            gridControls.Add(gridWidth);
            var gridHeight = new IntegerField("Height") { value = draft.height };
            gridHeight.RegisterValueChangedCallback(evt => ResizeBoard(draft.width, evt.newValue, draft.layers));
            gridControls.Add(gridHeight);
            var gridLayers = new IntegerField("Layers (1–4)") { value = draft.layers };
            gridLayers.RegisterValueChangedCallback(evt => ResizeBoard(draft.width, draft.height, evt.newValue));
            gridControls.Add(gridLayers);
            selectedLayer = Mathf.Clamp(selectedLayer, 0, draft.layers - 1);
            var layerChoices = Enumerable.Range(0, draft.layers).Select(index => index.ToString()).ToList();
            var layerPicker = new DropdownField("Active layer", layerChoices, Mathf.Clamp(selectedLayer, 0, layerChoices.Count - 1));
            layerPicker.RegisterValueChangedCallback(evt => { selectedLayer = int.Parse(evt.newValue); Refresh(); });
            gridControls.Add(layerPicker);
            rootVisualElement.Add(gridControls);

            var fields = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            var profile = new DropdownField("Game profile", Profiles.ToList(), Mathf.Max(0, Array.IndexOf(Profiles, draft.gameProfileId)));
            profile.RegisterValueChangedCallback(evt =>
            {
                PushUndo(); draft.gameProfileId = evt.newValue;
                var capabilityLabel = rootVisualElement.Q<Label>("profile-capabilities");
                if (capabilityLabel != null) capabilityLabel.text = ProfileCapabilitySummary(evt.newValue);
                RefreshStatus(); QueueAutosave();
            });
            profile.style.minWidth = 260;
            fields.Add(profile);
            var seed = new LongField("Seed") { value = draft.seed };
            seed.RegisterValueChangedCallback(evt => { PushUndo(); draft.seed = evt.newValue; QueueAutosave(); });
            fields.Add(seed);
            var moves = new IntegerField("Moves") { value = draft.moveBudget };
            moves.RegisterValueChangedCallback(evt => { PushUndo(); draft.moveBudget = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(moves);
            var world = new TextField("World ID") { value = draft.worldId };
            world.RegisterValueChangedCallback(evt => { PushUndo(); draft.worldId = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(world);
            var chapter = new TextField("Chapter ID") { value = draft.chapterId };
            chapter.RegisterValueChangedCallback(evt => { PushUndo(); draft.chapterId = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(chapter);
            var level = new TextField("Level ID") { value = draft.levelId };
            level.RegisterValueChangedCallback(evt => { PushUndo(); draft.levelId = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(level);
            var locale = new TextField("Locale") { value = draft.locale };
            locale.RegisterValueChangedCallback(evt => { PushUndo(); draft.locale = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(locale);
            var timed = new Toggle("Timed mode") { value = draft.timedMode };
            timed.RegisterValueChangedCallback(evt => { PushUndo(); draft.timedMode = evt.newValue; if (!evt.newValue) draft.timeLimitSeconds = 0; Refresh(); QueueAutosave(); });
            fields.Add(timed);
            var seconds = new IntegerField("Time limit (seconds)") { value = draft.timeLimitSeconds };
            seconds.SetEnabled(draft.timedMode);
            seconds.RegisterValueChangedCallback(evt => { PushUndo(); draft.timeLimitSeconds = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(seconds);
            foreach (var threshold in new[] {
                Tuple.Create("1-star threshold", 1), Tuple.Create("2-star threshold", 2), Tuple.Create("3-star threshold", 3) })
            {
                int star = threshold.Item2;
                var field = new IntegerField(threshold.Item1) { value = star == 1 ? draft.oneStarThreshold : star == 2 ? draft.twoStarThreshold : draft.threeStarThreshold };
                field.RegisterValueChangedCallback(evt => {
                    PushUndo();
                    if (star == 1) draft.oneStarThreshold = evt.newValue;
                    else if (star == 2) draft.twoStarThreshold = evt.newValue;
                    else draft.threeStarThreshold = evt.newValue;
                    RefreshStatus(); QueueAutosave();
                });
                fields.Add(field);
            }
            var difficulty = new TextField("Difficulty localization key") { value = draft.difficultyLabel };
            difficulty.RegisterValueChangedCallback(evt => { PushUndo(); draft.difficultyLabel = evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(difficulty);
            var hint = new TextField("Editor hint key") { value = draft.editorHintKey ?? string.Empty };
            hint.RegisterValueChangedCallback(evt => { PushUndo(); draft.editorHintKey = string.IsNullOrWhiteSpace(evt.newValue) ? null : evt.newValue; RefreshStatus(); QueueAutosave(); });
            fields.Add(hint);
            rootVisualElement.Add(fields);

            var gemTools = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            gemTools.Add(new Label("Paint gem:"));
            var gem = new DropdownField(GemIds.ToList(), selectedGem);
            gem.RegisterValueChangedCallback(evt => selectedGem = Array.IndexOf(GemIds, evt.newValue));
            gemTools.Add(gem);
            gemTools.Add(MakeButton("Toggle glass", ToggleGlass));
            gemTools.Add(MakeButton("Toggle hole", ToggleHole));
            rootVisualElement.Add(gemTools);
            var capabilities = new Label(ProfileCapabilitySummary(draft.gameProfileId)) { name = "profile-capabilities" };
            capabilities.style.whiteSpace = WhiteSpace.Normal;
            rootVisualElement.Add(capabilities);
            rootVisualElement.Add(new HelpBox("Neutral placeholder labels are used because title-specific art is not installed. This preview does not imply licensed asset availability.", HelpBoxMessageType.Info));

            var browserHeader = new VisualElement { style = { flexDirection = FlexDirection.Row } };
            browserHeader.Add(new Label("World / chapter / level browser"));
            browserHeader.Add(MakeButton("Refresh browser", BuildLevelBrowser));
            rootVisualElement.Add(browserHeader);
            levelSearch = new TextField("Filter profile/world/chapter/level");
            levelSearch.RegisterValueChangedCallback(_ => BuildLevelBrowser());
            rootVisualElement.Add(levelSearch);
            levelBrowser = new VisualElement { name = "level-browser" };
            rootVisualElement.Add(levelBrowser);
            BuildLevelBrowser();

            var goalsHeader = new VisualElement { style = { flexDirection = FlexDirection.Row } };
            goalsHeader.Add(new Label("Goals"));
            goalsHeader.Add(MakeButton("Add goal", AddGoal));
            rootVisualElement.Add(goalsHeader);
            goalEditor = new VisualElement { name = "goal-editor" };
            rootVisualElement.Add(goalEditor);
            BuildGoalEditor();

            boardScroll = new ScrollView(ScrollViewMode.VerticalAndHorizontal);
            boardScroll.style.maxHeight = 460;
            board = new VisualElement();
            board.style.flexDirection = FlexDirection.Column;
            board.style.marginTop = 10;
            board.style.alignItems = Align.FlexStart;
            boardScroll.Add(board);
            rootVisualElement.Add(boardScroll);

            sampleLevel = new ObjectField("Unity sample LevelSO") { objectType = typeof(LevelSO), allowSceneObjects = false };
            rootVisualElement.Add(sampleLevel);
            var sampleActions = new VisualElement { style = { flexDirection = FlexDirection.Row } };
            sampleActions.Add(MakeButton("Import LevelSO", ImportSampleLevel));
            sampleActions.Add(MakeButton("Save to LevelSO", ExportSampleLevel));
            sampleActions.Add(MakeButton("Copy board from JSON", CopyBoardFromJson));
            rootVisualElement.Add(sampleActions);

            status = new Label();
            status.style.whiteSpace = WhiteSpace.Normal;
            status.style.marginTop = 8;
            rootVisualElement.Add(status);
            Refresh();
        }

        private static Button MakeButton(string label, Action action)
        {
            var button = new Button(action) { text = label };
            button.tooltip = label;
            button.style.marginRight = 5;
            button.style.marginTop = 4;
            return button;
        }

        private static LevelDraft NewDraft(int width, int height)
        {
            var draft = new LevelDraft { width = width, height = height, seed = 1, moveBudget = 20 };
            draft.activeMask = Enumerable.Repeat(true, width * height).ToArray();
            draft.cells = Enumerable.Range(0, height)
                .SelectMany(row => Enumerable.Range(0, width).Select(column => new CellDraft
                {
                    row = row,
                    column = column,
                    layer = 0,
                    active = true,
                    contentId = GemIds[(row * width + column) % GemIds.Length]
                })).ToArray();
            draft.goals = new[] { new GoalDraft { goalId = "goal.primary", targetId = "sample.score", targetCount = 500 } };
            return draft;
        }

        private void Refresh()
        {
            BuildGoalEditor();
            board.Clear();
            for (int row = 0; row < draft.height; row++)
            {
                var line = new VisualElement { style = { flexDirection = FlexDirection.Row } };
                for (int column = 0; column < draft.width; column++)
                {
                    int r = row, c = column;
                    var cell = draft.cells.FirstOrDefault(item => item.row == r && item.column == c && item.layer == selectedLayer);
                    var button = new Button(() => Paint(r, c)) { text = CellLabel(cell) };
                    button.RegisterCallback<PointerEnterEvent>(evt => { if ((evt.pressedButtons & 1) != 0) Paint(r, c, false, button); });
                    button.style.width = 54 * zoom;
                    button.style.height = 44 * zoom;
                    button.style.marginRight = 2;
                    button.style.marginBottom = 2;
                    button.style.unityFontStyleAndWeight = cell != null && cell.active ? FontStyle.Bold : FontStyle.Normal;
                    if (cell == null || !cell.active) button.style.backgroundColor = new Color(.28f, .28f, .28f);
                    else if (cell.obstacleId == "sample.glass") button.style.backgroundColor = new Color(.35f, .72f, .88f);
                    line.Add(button);
                }
                board.Add(line);
            }
            RefreshStatus();
            QueueAutosave();
        }

        private void BuildGoalEditor()
        {
            if (goalEditor == null || draft == null) return;
            goalEditor.Clear();
            if (draft.goals == null) draft.goals = Array.Empty<GoalDraft>();
            for (int index = 0; index < draft.goals.Length; index++)
            {
                int goalIndex = index;
                var goal = draft.goals[index];
                var row = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
                var goalId = new TextField("ID") { name = "goal-id-" + index, value = goal.goalId ?? string.Empty };
                goalId.RegisterValueChangedCallback(evt =>
                {
                    PushUndo(); draft.goals[goalIndex].goalId = evt.newValue; RefreshStatus(); QueueAutosave();
                });
                var targetId = new TextField("Target") { name = "goal-target-id-" + index, value = goal.targetId ?? string.Empty };
                targetId.RegisterValueChangedCallback(evt =>
                {
                    PushUndo(); draft.goals[goalIndex].targetId = evt.newValue; RefreshStatus(); QueueAutosave();
                });
                var targetCount = new IntegerField("Count") { name = "goal-target-" + index, value = goal.targetCount };
                targetCount.RegisterValueChangedCallback(evt =>
                {
                    PushUndo(); draft.goals[goalIndex].targetCount = evt.newValue; RefreshStatus(); QueueAutosave();
                });
                row.Add(goalId); row.Add(targetId); row.Add(targetCount);
                if (draft.goals.Length > 1) row.Add(MakeButton("Remove", () => RemoveGoal(goalIndex)));
                goalEditor.Add(row);
            }
        }

        private void AddGoal()
        {
            PushUndo();
            var goals = draft.goals ?? Array.Empty<GoalDraft>();
            draft.goals = goals.Concat(new[] { new GoalDraft { goalId = "goal." + (goals.Length + 1), targetId = "sample.score", targetCount = 1 } }).ToArray();
            BuildGoalEditor(); RefreshStatus(); QueueAutosave();
        }

        private void RemoveGoal(int index)
        {
            if (draft.goals == null || draft.goals.Length <= 1 || index < 0 || index >= draft.goals.Length) return;
            PushUndo();
            draft.goals = draft.goals.Where((_, goalIndex) => goalIndex != index).ToArray();
            BuildGoalEditor(); RefreshStatus(); QueueAutosave();
        }

        private static string CellLabel(CellDraft cell)
        {
            if (cell == null || !cell.active) return "hole";
            return cell.obstacleId == "sample.glass" ? "glass" : cell.contentId ?? "?";
        }

        private void Paint(int row, int column, bool rebuild = true, Button paintedCell = null)
        {
            PushUndo();
            selectedRow = row;
            selectedColumn = column;
            selectedLayer = Mathf.Clamp(selectedLayer, 0, draft.layers - 1);
            var cell = draft.cells.First(item => item.row == row && item.column == column && item.layer == selectedLayer);
            cell.active = true;
            draft.activeMask[LevelDraftGridOperations.Index(draft.width, draft.height, row, column, selectedLayer)] = true;
            cell.contentId = GemIds[selectedGem];
            if (rebuild) Refresh();
            else
            {
                paintedCell.text = CellLabel(cell);
                paintedCell.style.unityFontStyleAndWeight = FontStyle.Bold;
                paintedCell.style.backgroundColor = cell.obstacleId == "sample.glass" ? new Color(.35f, .72f, .88f) : StyleKeyword.Null;
                RefreshStatus();
                QueueAutosave();
            }
        }

        private void ResizeBoard(int width, int height, int layers)
        {
            if (width < 1 || width > 32 || height < 1 || height > 32 || layers < 1 || layers > 4 || (long)width * height * layers > 4096)
            {
                CreateGUI();
                return;
            }
            PushUndo();
            LevelDraftGridOperations.Resize(draft, width, height, layers);
            selectedLayer = Mathf.Clamp(selectedLayer, 0, layers - 1);
            selectedRow = Mathf.Clamp(selectedRow, 0, height - 1);
            selectedColumn = Mathf.Clamp(selectedColumn, 0, width - 1);
            CreateGUI();
        }

        private void ToggleGlass()
        {
            var cell = draft.cells.FirstOrDefault(item => item.row == selectedRow && item.column == selectedColumn && item.layer == selectedLayer);
            if (cell == null) return;
            PushUndo();
            cell.obstacleId = cell.obstacleId == "sample.glass" ? null : "sample.glass";
            cell.obstacleDurability = cell.obstacleId == null ? 0 : 1;
            Refresh();
        }

        private void ToggleHole()
        {
            var cell = draft.cells.FirstOrDefault(item => item.row == selectedRow && item.column == selectedColumn && item.layer == selectedLayer);
            if (cell == null) return;
            PushUndo();
            cell.active = !cell.active;
            draft.activeMask[LevelDraftGridOperations.Index(draft.width, draft.height, cell.row, cell.column, cell.layer)] = cell.active;
            if (!cell.active) { cell.contentId = null; cell.obstacleId = null; cell.obstacleDurability = 0; }
            else cell.contentId = GemIds[selectedGem];
            Refresh();
        }

        private void PushUndo()
        {
            undo.Push(draft.Clone());
            redo.Clear();
        }

        private void Undo()
        {
            if (undo.Count == 0) return;
            redo.Push(draft.Clone());
            draft = undo.Pop();
            Refresh();
        }

        private void Redo()
        {
            if (redo.Count == 0) return;
            undo.Push(draft.Clone());
            draft = redo.Pop();
            Refresh();
        }

        private void OpenDraft()
        {
            string path = EditorUtility.OpenFilePanel("Open LevelDraft JSON", Application.dataPath, "json");
            if (string.IsNullOrEmpty(path)) return;
            try { draft = LevelDraftJson.Parse(File.ReadAllText(path)); Refresh(); }
            catch (Exception ex) { EditorUtility.DisplayDialog("Invalid draft", ex.Message, "OK"); }
        }

        private void SaveDraft()
        {
            string levelFolder = Path.Combine(Application.dataPath, "Match3Factory", "Levels");
            Directory.CreateDirectory(levelFolder);
            string path = EditorUtility.SaveFilePanel("Save LevelDraft JSON", levelFolder, draft.levelId, "json");
            if (string.IsNullOrEmpty(path)) return;
            if (File.Exists(path) && !EditorUtility.DisplayDialog("Replace existing draft?",
                    "The selected file already exists. Replace its contents with this validated LevelDraft?", "Replace", "Cancel")) return;
            var existing = new System.Collections.Generic.List<LevelDraft>();
            if (Directory.Exists(levelFolder))
            foreach (string existingPath in Directory.GetFiles(levelFolder, "*.json", SearchOption.AllDirectories))
            {
                try
                {
                    var existingDraft = LevelDraftJson.Parse(File.ReadAllText(existingPath));
                    if (!string.Equals(Path.GetFullPath(existingPath), Path.GetFullPath(path), StringComparison.OrdinalIgnoreCase)) existing.Add(existingDraft);
                }
                catch { /* Invalid artifacts are surfaced individually by the browser and cannot become registry authority. */ }
            }
            existing.Add(draft);
            var identityErrors = LevelDraftRegistry.ValidateUnique(existing);
            if (identityErrors.Count != 0)
            {
                EditorUtility.DisplayDialog("Duplicate level identity", string.Join("\n", identityErrors), "OK");
                return;
            }
            try { File.WriteAllText(path, LevelDraftJson.Serialize(draft)); RefreshStatus(); }
            catch (Exception ex) { EditorUtility.DisplayDialog("Draft was not saved", ex.Message, "OK"); }
        }

        private void BuildLevelBrowser()
        {
            if (levelBrowser == null) return;
            levelBrowser.Clear();
            string folder = Path.Combine(Application.dataPath, "Match3Factory", "Levels");
            if (!Directory.Exists(folder))
            {
                levelBrowser.Add(new Label("No saved LevelDrafts yet. Save a draft into Assets/Match3Factory/Levels."));
                return;
            }
            var entries = new System.Collections.Generic.List<Tuple<string, LevelDraft>>();
            foreach (string path in Directory.GetFiles(folder, "*.json", SearchOption.AllDirectories).Take(500))
            {
                try { entries.Add(Tuple.Create(path, LevelDraftJson.Parse(File.ReadAllText(path)))); }
                catch (Exception ex) { entries.Add(Tuple.Create(path, (LevelDraft)null)); Debug.LogWarning("Ignored invalid LevelDraft in browser: " + Path.GetFileName(path) + " · " + ex.Message); }
            }
            var valid = entries.Where(entry => entry.Item2 != null).Select(entry => entry.Item2).ToArray();
            var duplicates = new HashSet<string>(LevelDraftRegistry.ValidateUnique(valid).Select(error => error.Substring(error.IndexOf(": ", StringComparison.Ordinal) + 2)), StringComparer.Ordinal);
            string filter = levelSearch == null ? string.Empty : levelSearch.value ?? string.Empty;
            int shown = 0;
            foreach (var entry in entries)
            {
                string title = entry.Item2 == null ? Path.GetFileName(entry.Item1) + " · INVALID" :
                    $"{entry.Item2.gameProfileId} / {entry.Item2.worldId} / {entry.Item2.chapterId} / {entry.Item2.levelId}";
                if (title.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0) continue;
                var draftAtPath = entry.Item2;
                var button = new Button(() =>
                {
                    if (draftAtPath == null) { EditorUtility.DisplayDialog("Invalid LevelDraft", "This JSON did not pass the strict parser.", "OK"); return; }
                    PushUndo(); draft = draftAtPath.Clone(); Refresh();
                }) { text = title };
                button.tooltip = entry.Item2 != null && duplicates.Contains(LevelDraftRegistry.Key(entry.Item2))
                    ? "Duplicate profile/world/chapter/level identity; resolve before save."
                    : entry.Item1;
                levelBrowser.Add(button); shown++;
            }
            if (shown == 0) levelBrowser.Add(new Label("No levels match this filter."));
        }

        private void ValidateDraft()
        {
            var errors = draft.Validate();
            errors.AddRange(GameProfileCatalog.ValidateDraft(draft));
            status.text = errors.Count == 0 ? "Draft valid for local authoring. PROTOTYPE_ONLY; Engine simulation/export unavailable." : string.Join("\n", errors);
        }

        private void ImportSampleLevel()
        {
            var source = sampleLevel.value as LevelSO;
            if (source == null) { EditorUtility.DisplayDialog("Select a LevelSO", "Choose a Unity sample LevelSO asset first.", "OK"); return; }
            try { PushUndo(); draft = LevelDraftUnitySampleAdapter.FromLevelSO(source, draft.gameProfileId, draft.seed); Refresh(); }
            catch (Exception ex) { EditorUtility.DisplayDialog("LevelSO import failed", ex.Message, "OK"); }
        }

        private void CopyBoardFromJson()
        {
            string path = EditorUtility.OpenFilePanel("Copy board geometry from LevelDraft", "Assets/Match3Factory/Levels", "json");
            if (string.IsNullOrEmpty(path)) return;
            try
            {
                var source = LevelDraftJson.Parse(File.ReadAllText(path));
                string error;
                if (!LevelDraftRegistry.TryCopyBoard(source, draft, out error))
                    EditorUtility.DisplayDialog("Board copy rejected", error, "OK");
                else { PushUndo(); Refresh(); QueueAutosave(); }
            }
            catch (Exception ex) { EditorUtility.DisplayDialog("Board copy failed", ex.Message, "OK"); }
        }

        private void ExportSampleLevel()
        {
            var target = sampleLevel.value as LevelSO;
            if (target == null) { EditorUtility.DisplayDialog("Select a LevelSO", "Choose a Unity sample LevelSO asset first.", "OK"); return; }
            try
            {
                PushUndo();
                LevelDraftUnitySampleAdapter.ApplyToLevelSO(draft, target);
                EditorUtility.SetDirty(target);
                AssetDatabase.SaveAssets();
                Refresh();
            }
            catch (Exception ex) { EditorUtility.DisplayDialog("LevelSO export failed", ex.Message, "OK"); }
        }

        private void RefreshStatus()
        {
            if (status == null) return;
            var errors = draft.Validate();
            errors.AddRange(GameProfileCatalog.ValidateDraft(draft));
            status.text = errors.Count == 0
                ? "Valid draft · local editor only · PROTOTYPE_ONLY · Engine ENG-M24 gate pending."
                : string.Join("\n", errors);
        }

        private static string ProfileCapabilitySummary(string profileId)
        {
            var profile = GameProfileCatalog.Get(profileId);
            if (profile == null) return "Unknown profile: all capabilities disabled.";
            return $"{profile.DisplayName} · profile v{profile.Version} · {profile.AudiencePolicy} · {profile.NeutralFallbackLabel} · enabled: {string.Join(", ", profile.EnabledCapabilities)} · advanced mechanics disabled until ENG-M24: {string.Join(", ", profile.DisabledCapabilities)}";
        }

        private static string AutosavePath => autosavePathOverrideForTesting != null
            ? autosavePathOverrideForTesting()
            : Path.Combine(Directory.GetParent(Application.dataPath).FullName, "Library", "Match3Factory", "autosave-v1.json");

        private void QueueAutosave()
        {
            if (draft == null || autosaveQueued) return;
            autosaveQueued = true;
            EditorApplication.delayCall += () =>
            {
                autosaveQueued = false;
                if (this == null || draft == null) return;
                try { LevelDraftAutosaveStore.Save(AutosavePath, draft); }
                catch (Exception ex) { recoveryNotice = "Autosave failed; the draft remains in memory. " + ex.Message; RefreshStatus(); }
            };
        }

        private void OnDisable()
        {
            if (draft == null) return;
            try { LevelDraftAutosaveStore.Save(AutosavePath, draft); }
            catch (Exception ex) { Debug.LogWarning("Match3 Factory autosave failed: " + ex.Message); }
        }

        private void SetZoom(float value)
        {
            zoom = Mathf.Clamp(value, .5f, 2.5f);
            Refresh();
        }

        private void OnKeyDown(KeyDownEvent evt)
        {
            if (!evt.ctrlKey) return;
            if (evt.keyCode == KeyCode.Z && evt.shiftKey) Redo();
            else if (evt.keyCode == KeyCode.Z) Undo();
            else if (evt.keyCode == KeyCode.Y) Redo();
            else if (evt.keyCode == KeyCode.S) SaveDraft();
            else return;
            evt.StopPropagation();
        }
    }
}
