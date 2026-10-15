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
        private static readonly string[] Profiles =
        {
            "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop"
        };
        private static readonly string[] GemIds = { "Blue", "Green", "Orange", "Purple", "White", "Yellow" };
        private LevelDraft draft;
        private VisualElement board;
        private Label status;
        private ObjectField sampleLevel;
        private int selectedGem;
        private int selectedRow;
        private int selectedColumn;
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
            draft ??= NewDraft(8, 8);
            rootVisualElement.Clear();
            rootVisualElement.style.paddingLeft = 12;
            rootVisualElement.style.paddingRight = 12;
            rootVisualElement.style.paddingTop = 10;
            rootVisualElement.style.paddingBottom = 10;

            var heading = new Label("Match3 Level Draft Studio · PROTOTYPE_ONLY");
            heading.style.unityFontStyleAndWeight = FontStyle.Bold;
            heading.style.fontSize = 17;
            rootVisualElement.Add(heading);

            var actions = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            actions.Add(MakeButton("New 8×8", () => { PushUndo(); draft = NewDraft(8, 8); Refresh(); }));
            actions.Add(MakeButton("Open JSON", OpenDraft));
            actions.Add(MakeButton("Save JSON", SaveDraft));
            actions.Add(MakeButton("Undo", Undo));
            actions.Add(MakeButton("Redo", Redo));
            actions.Add(MakeButton("Validate", ValidateDraft));
            rootVisualElement.Add(actions);

            var fields = new VisualElement { style = { flexDirection = FlexDirection.Row, flexWrap = Wrap.Wrap } };
            var profile = new DropdownField("Game profile", Profiles.ToList(), Mathf.Max(0, Array.IndexOf(Profiles, draft.gameProfileId)));
            profile.RegisterValueChangedCallback(evt => { PushUndo(); draft.gameProfileId = evt.newValue; RefreshStatus(); });
            profile.style.minWidth = 260;
            fields.Add(profile);
            var seed = new LongField("Seed") { value = draft.seed };
            seed.RegisterValueChangedCallback(evt => { PushUndo(); draft.seed = evt.newValue; });
            fields.Add(seed);
            var moves = new IntegerField("Moves") { value = draft.moveBudget };
            moves.RegisterValueChangedCallback(evt => { PushUndo(); draft.moveBudget = evt.newValue; RefreshStatus(); });
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

            board = new VisualElement();
            board.style.flexDirection = FlexDirection.Column;
            board.style.marginTop = 10;
            board.style.alignItems = Align.FlexStart;
            rootVisualElement.Add(board);

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
            board.Clear();
            for (int row = 0; row < draft.height; row++)
            {
                var line = new VisualElement { style = { flexDirection = FlexDirection.Row } };
                for (int column = 0; column < draft.width; column++)
                {
                    int r = row, c = column;
                    var cell = draft.cells.FirstOrDefault(item => item.row == r && item.column == c && item.layer == 0);
                    var button = new Button(() => Paint(r, c)) { text = CellLabel(cell) };
                    button.style.width = 54;
                    button.style.height = 44;
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
            status.text = errors.Count == 0
                ? "Valid draft · local editor only · PROTOTYPE_ONLY · Engine ENG-M24 gate pending."
                : string.Join("\n", errors);
        }
    }
}
