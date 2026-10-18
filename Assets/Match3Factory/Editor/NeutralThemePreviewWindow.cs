using System;
using UnityEditor;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>
    /// Genuine native Editor preview. Uses ONLY Unity Texture2D geometric drawing.
    /// No SVG package, premium artwork, gameplay state, third-party downloads,
    /// production runtime or Engine resolver is required.
    /// </summary>
    public sealed class NeutralThemePreviewWindow : EditorWindow
    {
        private static readonly int[] Widths = { 320, 390, 720 };
        private int selectedProfile;
        private int selectedWidth = 1;
        private Texture2D preview;
        private string cachedProfile;
        private int cachedWidth;
        private int cachedHeight;
        private Vector2 scroll;

        [MenuItem("Tools/Match3 Factory/Neutral Theme Previews")]
        public static void Open()
        {
            var window = GetWindow<NeutralThemePreviewWindow>();
            window.titleContent = new GUIContent("Neutral Theme Previews");
            window.minSize = new Vector2(410f, 500f);
            window.Show();
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Match3 Factory · Five Neutral Themes", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Editor-only original geometric concepts. No official game sprites, " +
                "gameplay simulation, title-specific obstacles, store artwork or " +
                "ENG-M24 validation. Engine: BLOCKED_ENG_M24.",
                MessageType.Info);
            selectedProfile = EditorGUILayout.Popup("Profile", selectedProfile, NeutralThemePreviewRenderer.Profiles);
            selectedWidth = EditorGUILayout.Popup("Portrait width", selectedWidth,
                new[] { "320 px", "390 px", "720 px" });
            selectedProfile = Mathf.Clamp(selectedProfile, 0, NeutralThemePreviewRenderer.Profiles.Length - 1);
            selectedWidth = Mathf.Clamp(selectedWidth, 0, Widths.Length - 1);

            string profile = NeutralThemePreviewRenderer.Profiles[selectedProfile];
            int logicalWidth = Widths[selectedWidth];
            int logicalHeight = Mathf.RoundToInt(logicalWidth * 16f / 9f);
            float pixelsPerPoint = Mathf.Clamp(EditorGUIUtility.pixelsPerPoint, 1f, 3f);
            float boundedScale = Mathf.Min(pixelsPerPoint,
                Mathf.Sqrt(2400000f / (logicalWidth * (float)logicalHeight)));
            int renderWidth = Mathf.Max(160, Mathf.FloorToInt(logicalWidth * boundedScale));
            int renderHeight = Mathf.Max(240, Mathf.FloorToInt(logicalHeight * boundedScale));
            if (preview == null || cachedProfile != profile ||
                cachedWidth != renderWidth || cachedHeight != renderHeight)
            {
                if (preview != null) DestroyImmediate(preview);
                preview = NeutralThemePreviewRenderer.Render(profile, renderWidth, renderHeight);
                cachedProfile = profile;
                cachedWidth = renderWidth;
                cachedHeight = renderHeight;
            }
            EditorGUILayout.LabelField(
                "Preview " + logicalWidth + " × " + logicalHeight +
                " editor px · raster " + renderWidth + " × " + renderHeight +
                " · no Unity SVG importer needed",
                EditorStyles.miniLabel);

            scroll = EditorGUILayout.BeginScrollView(scroll, GUILayout.ExpandWidth(true),
                GUILayout.ExpandHeight(true));
            Rect rect = GUILayoutUtility.GetRect(logicalWidth, logicalHeight,
                GUILayout.Width(logicalWidth), GUILayout.Height(logicalHeight));
            if (Event.current.type == EventType.Repaint)
                GUI.DrawTexture(rect, preview, ScaleMode.ScaleToFit, false);
            EditorGUILayout.EndScrollView();
        }

        private void OnDisable()
        {
            if (preview != null) DestroyImmediate(preview);
            preview = null;
        }
    }
}
