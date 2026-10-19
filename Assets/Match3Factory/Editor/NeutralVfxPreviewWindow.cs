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
        private Texture2D preview;
        private string cachedProfile;
        private string cachedEffect;
        private int cachedFrame = -1;
        private bool cachedReduced;
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
            ReleasePreview();
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
            string effect = NeutralVfxPreviewGeometry.Effects[effectIndex];
            if (preview == null || !string.Equals(profile, cachedProfile, StringComparison.Ordinal) ||
                !string.Equals(effect, cachedEffect, StringComparison.Ordinal) ||
                frame != cachedFrame || reduced != cachedReduced)
            {
                ReleasePreview();
                preview = NeutralVfxPreviewRenderer.Render(profile, effect, frame, reduced);
                cachedProfile = profile;
                cachedEffect = effect;
                cachedFrame = frame;
                cachedReduced = reduced;
            }
            scroll = EditorGUILayout.BeginScrollView(scroll, GUILayout.ExpandHeight(true));
            Rect canvas = GUILayoutUtility.GetRect(320, 568, GUILayout.Width(320), GUILayout.Height(568));
            if (Event.current.type == EventType.Repaint)
                GUI.DrawTexture(canvas, preview, ScaleMode.StretchToFill, false);
            EditorGUILayout.EndScrollView();
        }

        private void ReleasePreview()
        {
            if (preview != null) DestroyImmediate(preview);
            preview = null;
        }
    }
}
