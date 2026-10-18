using System;
using UnityEditor;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>Visual rehearsal only. Never observes or changes actual game logic.</summary>
    public sealed class NeutralVfxPreviewWindow : EditorWindow
    {
        private int profileIndex, effectIndex, frame;
        private bool reduced = true, playing;
        private double nextFrameTime;
        private Texture2D background;
        private string cachedProfile;
        private Vector2 scroll;

        [MenuItem("Tools/Match3 Factory/Neutral VFX Rehearsal")]
        public static void Open()
        {
            var window = GetWindow<NeutralVfxPreviewWindow>();
            window.titleContent = new GUIContent("Neutral FX Rehearsal");
            window.minSize = new Vector2(440f, 590f);
            window.Show();
        }

        private void OnEnable() { EditorApplication.update += Tick; }
        private void OnDisable()
        {
            EditorApplication.update -= Tick;
            if (background != null) DestroyImmediate(background);
            background = null;
        }

        private void Tick()
        {
            if (!playing || reduced || EditorApplication.timeSinceStartup < nextFrameTime) return;
            nextFrameTime = EditorApplication.timeSinceStartup + 0.075;
            frame = (frame + 1) % NeutralVfxPreviewGeometry.FullFrameCount;
            Repaint();
        }

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Match3 Factory | Neutral FX Rehearsal", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Original geometric animation, no gameplay events, board mutations or asset imports. " +
                "NOT a match/cascade simulator. Engine BLOCKED_ENG_M24; replay NOT_RUN; publish disabled.",
                MessageType.Warning);
            EditorGUI.BeginChangeCheck();
            profileIndex = EditorGUILayout.Popup("Concept",
                profileIndex, NeutralThemePreviewRenderer.Profiles);
            effectIndex = EditorGUILayout.Popup("Schematic effect",
                effectIndex, NeutralVfxPreviewGeometry.Effects);
            reduced = EditorGUILayout.Toggle("Reduced motion", reduced);
            if (EditorGUI.EndChangeCheck()) { frame = 0; playing = false; }
            profileIndex = Mathf.Clamp(profileIndex, 0, NeutralThemePreviewRenderer.Profiles.Length - 1);
            effectIndex = Mathf.Clamp(effectIndex, 0, NeutralVfxPreviewGeometry.Effects.Length - 1);
            int count = reduced ? 1 : NeutralVfxPreviewGeometry.FullFrameCount;
            using (new EditorGUI.DisabledScope(reduced))
            {
                frame = EditorGUILayout.IntSlider("Frame", frame, 0, count - 1);
                EditorGUILayout.BeginHorizontal();
                if (GUILayout.Button(playing ? "Pause" : "Play"))
                {
                    playing = !playing;
                    nextFrameTime = EditorApplication.timeSinceStartup;
                }
                if (GUILayout.Button("Step")) { playing = false; frame = (frame + 1) % count; }
                EditorGUILayout.EndHorizontal();
            }
            EditorGUILayout.LabelField(reduced
                ? "Static accessible frame: no flashing, no movement."
                : "12 manually seekable frames / 900 ms. Mobile performance NOT_RUN.",
                EditorStyles.wordWrappedMiniLabel);

            string profile = NeutralThemePreviewRenderer.Profiles[profileIndex];
            if (background == null || !string.Equals(profile, cachedProfile, StringComparison.Ordinal))
            {
                if (background != null) DestroyImmediate(background);
                background = NeutralThemePreviewRenderer.Render(profile, 320, 568);
                cachedProfile = profile;
            }
            scroll = EditorGUILayout.BeginScrollView(scroll, GUILayout.ExpandHeight(true));
            Rect canvas = GUILayoutUtility.GetRect(320, 568, GUILayout.Width(320), GUILayout.Height(568));
            if (Event.current.type == EventType.Repaint)
            {
                GUI.DrawTexture(canvas, background, ScaleMode.StretchToFill, false);
                var fx = NeutralVfxPreviewGeometry.Build(profile,
                    NeutralVfxPreviewGeometry.Effects[effectIndex], frame, reduced);
                var area = new Rect(canvas.x + 32, canvas.y + 184, 256, 255);
                foreach (var shape in fx) DrawShape(area, shape);
            }
            EditorGUILayout.EndScrollView();
        }

        private static void DrawShape(Rect area, NeutralVfxPreviewGeometry.Shape s)
        {
            Color color;
            if (!ColorUtility.TryParseHtmlString(s.Color, out color))
                throw new InvalidOperationException("Invalid built-in preview color.");
            color.a = Mathf.Clamp01(s.Opacity);
            float x = area.x + s.X * area.width / 1000f;
            float y = area.y + s.Y * area.height / 1000f;
            float r = s.Size * area.width / 1000f;
            if (s.Kind == "line")
                EditorGUI.DrawRect(new Rect(x - 4, y - r, 8, 2 * r), color);
            else if (s.Kind == "square")
                EditorGUI.DrawRect(new Rect(x - r, y - r, 2 * r, 2 * r), color);
            else
            {
                Handles.BeginGUI();
                Handles.color = color;
                if (s.Kind == "diamond")
                    Handles.DrawAAConvexPolygon(
                        new Vector3(x, y - r), new Vector3(x + r, y),
                        new Vector3(x, y + r), new Vector3(x - r, y));
                else if (s.Kind == "circle" || s.Kind == "oval")
                    Handles.DrawSolidDisc(new Vector3(x, y), Vector3.forward, r);
                else throw new ArgumentException("Invalid original preview primitive.");
                Handles.EndGUI();
            }
        }
    }
}
