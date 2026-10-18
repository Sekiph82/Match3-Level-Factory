using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>Manual read-only pre-move statistics viewer, no Engine or board state.</summary>
    public sealed class ReferenceCheckpointPreviewWindow : EditorWindow
    {
        private ReferenceCheckpointPreview.Receipt receipt;
        private int selected;
        private string notice = "Open a reference-checkpoint JSON created by the local stdout-only Python CLI.";
        private Vector2 scroll;

        [MenuItem("Tools/Match3 Factory/UltraGem Checkpoint Inspector")]
        public static void Open()
        {
            var window = GetWindow<ReferenceCheckpointPreviewWindow>();
            window.titleContent = new GUIContent("Donor Checkpoints");
            window.minSize = new Vector2(560, 550);
            window.Show();
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("UltraGem · Reference-only checkpoint inspector", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Cumulative diagnostic observations BEFORE donor moves. NOT a grid replay, " +
                "not cascade ordering, not goal completion and not a WIN or difficulty test. " +
                "MATCH3_ENGINE validation: BLOCKED_ENG_M24. Production release forbidden.",
                MessageType.Warning);
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("Open checkpoint JSON (read-only)")) OpenJson();
            if (GUILayout.Button("Clear")) { receipt = null; selected = 0; notice = "Cleared."; }
            EditorGUILayout.EndHorizontal();
            EditorGUILayout.HelpBox(notice, receipt == null ? MessageType.Info : MessageType.None);
            if (receipt == null) return;

            EditorGUILayout.LabelField("Pinned source revision", receipt.sourceRevision);
            EditorGUILayout.LabelField("Policy / run",
                receipt.policy + " / " + receipt.runIndex + " / candidate " + receipt.candidateIndex);
            EditorGUILayout.LabelField("Donor seed", receipt.runSeed.ToString());
            EditorGUILayout.LabelField("Donor stop reason", receipt.donorOutcome);
            EditorGUILayout.LabelField("Before-move checkpoint SHA256", receipt.checkpointSha256);
            EditorGUILayout.LabelField("Actual replay and goal proof", "NOT_RUN / UNAVAILABLE");
            DrawInitialBoard(receipt.initialBoard);
            selected = EditorGUILayout.IntSlider("Checkpoint (before move)",
                selected, 0, receipt.checkpoints.Length - 1);

            var point = receipt.checkpoints[selected];
            long[] values = point.cumulative.Values();
            long[] prev = selected == 0 ? new long[values.Length]
                : receipt.checkpoints[selected - 1].cumulative.Values();
            scroll = EditorGUILayout.BeginScrollView(scroll);
            EditorGUILayout.Space(5);
            EditorGUILayout.LabelField("Move " + point.beforeMove +
                " · cumulative observed events (no inferred frame)", EditorStyles.boldLabel);
            for (int i = 0; i < ReferenceCheckpointPreview.MetricNames.Length; i++)
                EditorGUILayout.LabelField(
                    ReferenceCheckpointPreview.MetricNames[i],
                    values[i] + "  (delta since previous checkpoint: +" + (values[i] - prev[i]) + ")");
            EditorGUILayout.EndScrollView();
        }

        private static void DrawInitialBoard(ReferenceCheckpointPreview.InitialBoard board)
        {
            EditorGUILayout.Space(6);
            EditorGUILayout.LabelField("Seeded original donor SETUP (never post-move)", EditorStyles.boldLabel);
            EditorGUILayout.LabelField(
                "Each cell shows type/color/lock status raw donor integers; no canonical Engine piece mapping.",
                EditorStyles.wordWrappedMiniLabel);
            const int size = 30;
            Rect canvas = GUILayoutUtility.GetRect(board.columns * size, board.rows * size,
                GUILayout.Width(board.columns * size), GUILayout.Height(board.rows * size));
            for (int i = 0; i < board.cells.Length; i++)
            {
                var cell = board.cells[i];
                Rect box = new Rect(canvas.x + cell.column * size, canvas.y + cell.row * size,
                    size - 1, size - 1);
                string label = cell.type < 0 ? "X" : cell.type.ToString() + "/" + cell.color;
                if (cell.status > 0) label += "*";
                GUI.Box(box, new GUIContent(label,
                    "row=" + cell.row + ", col=" + cell.column +
                    ", donor type=" + cell.type + ", donor color=" + cell.color +
                    ", donor lock status=" + cell.status));
            }
            EditorGUILayout.LabelField("Board SHA256 validated at import, not a replay checksum.",
                EditorStyles.wordWrappedMiniLabel);
        }

        private void OpenJson()
        {
            string path = EditorUtility.OpenFilePanel("Select a reference-checkpoint JSON", "", "json");
            if (string.IsNullOrEmpty(path)) return;
            // Invalidate prior receipt before reading so a failed import cannot retain stale evidence.
            receipt = null;
            selected = 0;
            try
            {
                var info = new FileInfo(path);
                if (!info.Exists || info.Length < 1 || info.Length > 256000)
                    throw new InvalidOperationException("Invalid or oversized checkpoint file.");
                string json = File.ReadAllText(path);
                receipt = ReferenceCheckpointPreview.Parse(json);
                notice = "Checksum verified; diagnostic only, not authenticated Engine evidence.";
            }
            catch (Exception error)
            {
                notice = "Rejected reference import: " + error.Message;
            }
            Repaint();
        }
    }
}
