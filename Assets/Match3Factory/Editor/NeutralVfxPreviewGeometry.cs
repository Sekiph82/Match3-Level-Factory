using System;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>Editor-only original geometry. Never a gameplay/cascade simulation.</summary>
    public static class NeutralVfxPreviewGeometry
    {
        public const string ResultStatus = "SYMBOLIC_FX_PREVIEW_ONLY";
        public const string EngineStatus = "BLOCKED_ENG_M24";
        public const string ReplayComparison = "NOT_RUN";
        public const int FullFrameCount = 12;
        public static readonly string[] Effects = { "combo", "line", "fish", "egg", "conveyor", "portal" };

        public readonly struct Shape
        {
            public readonly string Kind;
            public readonly float X, Y, Size, Opacity;
            public readonly string Color;
            public Shape(string kind, float x, float y, float size, float opacity, string color)
            {
                Kind = kind; X = x; Y = y; Size = size; Opacity = opacity; Color = color;
            }
        }

        public static Shape[] Build(string profile, string effect, int frame, bool reduced)
        {
            string[] palette = NeutralThemePreviewRenderer.Palette(profile);
            if (Array.IndexOf(Effects, effect) < 0) throw new ArgumentException("Unsupported symbolic effect", nameof(effect));
            if (frame < 0 || frame >= (reduced ? 1 : FullFrameCount))
                throw new ArgumentOutOfRangeException(nameof(frame));
            float t = reduced ? 0.5f : frame / 11f;
            float alpha = reduced ? 0.9f : Mathf.Max(0.25f, 1f - 0.65f * t);
            string a = palette[2], b = palette[1];
            switch (effect)
            {
                case "combo": return new[] {
                    new Shape("circle", 500, 500, 80 + 230 * t, alpha, a),
                    new Shape("diamond", 500, 500, 70, 0.95f, b) };
                case "line": return new[] {
                    new Shape("line", 140 + 720 * t, 500, 100, alpha, a),
                    new Shape("square", 500, 500, 60, 0.9f, b) };
                case "fish": return new[] {
                    new Shape("oval", 160 + 680 * t, 500 - 100 * Mathf.Sin(t * Mathf.PI), 75, 0.95f, a),
                    new Shape("diamond", 850, 500, 65, 0.9f, b) };
                case "egg": return new[] {
                    new Shape("oval", 500, 500, 140 - 35 * t, 0.95f, a),
                    new Shape("line", 500, 470 + 110 * t, 80, alpha, b) };
                case "conveyor":
                    var tiles = new Shape[4];
                    for (int i = 0; i < tiles.Length; i++)
                        tiles[i] = new Shape("square", 180 + 160 * Mathf.Repeat(t + i / 4f, 1f),
                            500 + i * 45, 45, 0.95f, i % 2 == 0 ? a : b);
                    return tiles;
                case "portal": return new[] {
                    new Shape("circle", 250, 500, 95 + 20 * t, 0.92f, a),
                    new Shape("circle", 750, 500, 95 + 20 * (1 - t), 0.92f, a),
                    new Shape("diamond", 250 + 500 * t, 500 - 100 * Mathf.Sin(t * Mathf.PI), 44, alpha, b) };
                default: throw new ArgumentException("Unknown effect");
            }
        }
    }
}
