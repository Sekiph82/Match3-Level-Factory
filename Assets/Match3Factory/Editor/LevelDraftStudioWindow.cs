using System;
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
        private LevelDraft draft;
        private VisualElement board;
        private ScrollView boardScroll;
        private Label status;
        private VisualElement goalEditor;
        private ObjectField sampleLevel;
        private int selectedGem;
        private int selectedRow;
        private int selectedColumn;
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
            actions.Add(MakeButton("Zoom +", () => SetZoom(zoom + .1f)));
            actions.Add(MakeButton("Zoom −", () => SetZoom(zoom - .1f)));
            rootVisualElement.Add(actions);

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
                    var cell = draft.cells.FirstOrDefault(item => item.row == r && item.column == c && item.layer == 0);
                    var button = new Button(() => Paint(r, c)) { text = CellLabel(cell) };
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

        private void Paint(int row, int column)
        {
            PushUndo();
            selectedRow = row;
            selectedColumn = column;
            var cell = draft.cells.First(item => item.row == row && item.column == column && item.layer == 0);
            cell.active = true;
            draft.activeMask[row * draft.width + column] = true;
            cell.contentId = GemIds[selectedGem];
            Refresh();
        }

        private void ToggleGlass()
        {
            var cell = draft.cells.FirstOrDefault(item => item.row == selectedRow && item.column == selectedColumn && item.layer == 0);
            if (cell == null) return;
            PushUndo();
            cell.obstacleId = cell.obstacleId == "sample.glass" ? null : "sample.glass";
            cell.obstacleDurability = cell.obstacleId == null ? 0 : 1;
            Refresh();
        }

        private void ToggleHole()
        {
            var cell = draft.cells.FirstOrDefault(item => item.row == selectedRow && item.column == selectedColumn && item.layer == 0);
            if (cell == null) return;
            PushUndo();
            cell.active = !cell.active;
            draft.activeMask[cell.row * draft.width + cell.column] = cell.active;
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
            string path = EditorUtility.SaveFilePanel("Save LevelDraft JSON", Application.dataPath, "level-draft", "json");
            if (string.IsNullOrEmpty(path)) return;
            try { File.WriteAllText(path, LevelDraftJson.Serialize(draft)); RefreshStatus(); }
            catch (Exception ex) { EditorUtility.DisplayDialog("Draft was not saved", ex.Message, "OK"); }
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
            return $"Profile v{profile.Version} · {profile.AudiencePolicy} · enabled: {string.Join(", ", profile.EnabledCapabilities)} · advanced mechanics disabled until ENG-M24: {string.Join(", ", profile.DisabledCapabilities)}";
        }

        private static string AutosavePath => Path.Combine(Directory.GetParent(Application.dataPath).FullName, "Library", "Match3Factory", "autosave-v1.json");

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
