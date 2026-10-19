// Existing LFX real LevelDraft -> VUF review pair: explicit, user-selected,
// NEW external directory, no scene or project modifications. Non-shipping.
using System;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Match3Factory
{
    public sealed class LevelDraftVisualHandoffWindow : EditorWindow
    {
        private string draftFile = "";
        private string status =
            "Export strictly validated PROTOTYPE_ONLY LevelDraft, not Engine WIN/replay.";

        [MenuItem("Tools/MATCH3 Factory/Export Real LFXV1 Visual Review Pair")]
        public static void Open()
        {
            var window = GetWindow<LevelDraftVisualHandoffWindow>("LFXV1 Export");
            window.minSize = new Vector2(560f, 220f);
            window.Show();
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Real LFX LevelDraft -> VUF source handoff",
                EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Select an existing LevelDraftJson v1 document created by this " +
                "Factory. Export creates only a NEW external folder containing " +
                "canonical LevelDraft JSON and SHA-bound LFXV1 review JSON. " +
                "Engine M24, live match rules, score and art rights remain OPEN.",
                MessageType.Warning);
            if (GUILayout.Button("Select existing LevelDraft v1 JSON"))
            {
                draftFile = EditorUtility.OpenFilePanel(
                    "Existing Level Factory PROTOTYPE_ONLY draft",
                    Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                    "json");
            }
            EditorGUILayout.SelectableLabel(draftFile);
            if (GUILayout.Button("Validate and export to NEW external folder"))
            {
                try
                {
                    if (String.IsNullOrEmpty(draftFile) || !File.Exists(draftFile))
                        throw new IOException("select existing LevelDraft");
                    string parent = EditorUtility.OpenFolderPanel(
                        "Existing external parent for new LFXV1 review folder",
                        Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                        "");
                    if (String.IsNullOrEmpty(parent)) return;
                    string newFolder = Path.Combine(parent,
                        "LFXV1_Review_" + DateTime.UtcNow.ToString("yyyyMMddTHHmmssfff"));
                    LevelDraftVisualHandoff.ExportNewExternalPair(
                        File.ReadAllText(draftFile), newFolder);
                    status = "Generated two genuine SHA-bound draft sources: " +
                        newFolder + " . NOT an Engine-authoritative release.";
                }
                catch (Exception ex) { status = "BLOCKED: " + ex.Message; }
            }
            EditorGUILayout.HelpBox(status, MessageType.Info);
        }
    }
}
