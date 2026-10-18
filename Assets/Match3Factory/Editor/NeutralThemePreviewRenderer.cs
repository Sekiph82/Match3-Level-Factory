using System;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>
    /// Editor-only original geometric game previews. No textures, sprites, rules or
    /// game runtime are imported. Does not depend on SVG importer or ENG-M24.
    /// </summary>
    public static class NeutralThemePreviewRenderer
    {
        public const string ResultStatus = "GEOMETRIC_EDITOR_PREVIEW_ONLY";
        public const string EngineStatus = "BLOCKED_ENG_M24";
        public static readonly string[] Profiles =
        {
            "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop"
        };

        private static readonly string[][] Colors =
        {
            new[] { "#103F62", "#1B819A", "#A8DFE8" },
            new[] { "#202D3C", "#E58D37", "#F1DCC4" },
            new[] { "#244E42", "#84AB63", "#F7D38B" },
            new[] { "#2C2350", "#8866B9", "#D7C6EF" },
            new[] { "#355777", "#E9AAAD", "#F7E9CB" }
        };
        // Same original symbolic shapes as Tools/UltraGem/neutral_preview_recipes.py.
        private static readonly string[][] Shapes =
        {
            new[] { "circle", "diamond", "hexagon" },
            new[] { "octagon", "square", "triangle" },
            new[] { "oval", "hexagon", "diamond" },
            new[] { "diamond", "triangle", "star" },
            new[] { "circle", "rounded_square", "star" }
        };

        public static string[] Palette(string profile)
        {
            int i = ProfileIndex(profile);
            return (string[])Colors[i].Clone();
        }

        public static string[] Silhouettes(string profile)
        {
            int i = ProfileIndex(profile);
            return (string[])Shapes[i].Clone();
        }

        public static Texture2D Render(string profile, int width, int height)
        {
            int index = ProfileIndex(profile);
            if (width < 160 || height < 240 || width > 1600 || height > 3200 ||
                (long)width * height > 2400000L)
                throw new ArgumentOutOfRangeException(nameof(width), "Use a bounded editor preview, not an asset pack.");

            var palette = new Color[3];
            for (int i = 0; i < 3; i++)
            {
                if (!ColorUtility.TryParseHtmlString(Colors[index][i], out palette[i]))
                    throw new InvalidOperationException("Invalid built-in preview color.");
            }
            var pixels = new Color32[width * height];
            var top = Color.Lerp(palette[0], Color.black, 0.12f);
            var bottom = Color.Lerp(palette[0], palette[1], 0.35f);

            for (int y = 0; y < height; y++)
            {
                float v = (y + 0.5f) / height;
                for (int x = 0; x < width; x++)
                {
                    float u = (x + 0.5f) / width;
                    Color col = Color.Lerp(bottom, top, v);
                    // Fixed original neutral board geometry, not a playable Match3 scene.
                    bool board = u > 0.10f && u < 0.90f && v > 0.26f && v < 0.78f;
                    if (board)
                    {
                        col = Color.Lerp(col, Color.white, 0.095f);
                        float gridX = Mathf.Repeat((u - 0.1f) * 5f / 0.8f, 1f);
                        float gridY = Mathf.Repeat((v - 0.26f) * 7f / 0.52f, 1f);
                        if (gridX < 0.017f || gridY < 0.014f)
                            col = Color.Lerp(col, palette[2], 0.25f);
                    }
                    if (u > 0.18f && u < 0.82f && v > 0.87f && v < 0.915f)
                        col = Color.Lerp(palette[1], Color.white, 0.30f);

                    float itemY = 0.51f;
                    for (int shapeIndex = 0; shapeIndex < 3; shapeIndex++)
                    {
                        float centerX = (shapeIndex + 1) * 0.25f;
                        float dx = (u - centerX) / 0.112f;
                        float dy = (v - itemY) / (0.112f * width / (float)height);
                        // Normalize in pixel space to avoid stretching at modern phone aspect ratios.
                        dy = (v - itemY) * height / (0.112f * width);
                        if (Inside(Shapes[index][shapeIndex], dx, dy))
                            col = Color.Lerp(palette[(shapeIndex + 1) % 3], Color.white,
                                0.13f + 0.16f * Mathf.Clamp01(1f - Mathf.Abs(dx + dy) / 2f));
                    }
                    pixels[y * width + x] = (Color32)col;
                }
            }
            var texture = new Texture2D(width, height, TextureFormat.RGBA32, false)
            {
                name = "Match3 Neutral Preview " + profile,
                filterMode = FilterMode.Bilinear,
                wrapMode = TextureWrapMode.Clamp,
                hideFlags = HideFlags.HideAndDontSave
            };
            texture.SetPixels32(pixels);
            texture.Apply(false, false);
            return texture;
        }

        private static int ProfileIndex(string profile)
        {
            if (profile == null) throw new ArgumentNullException(nameof(profile));
            for (int i = 0; i < Profiles.Length; i++)
                if (string.Equals(Profiles[i], profile, StringComparison.Ordinal)) return i;
            throw new ArgumentException("Unknown game profile. No fallback may change game semantics.", nameof(profile));
        }

        private static bool Inside(string shape, float x, float y)
        {
            float ax = Mathf.Abs(x), ay = Mathf.Abs(y);
            switch (shape)
            {
                case "circle": return x * x + y * y <= 0.80f;
                case "diamond": return ax + ay <= 1.13f;
                case "hexagon": return ax <= 0.87f && ay <= 1f && ax + ay * 0.50f <= 1.13f;
                case "octagon": return Mathf.Max(ax, ay) <= 0.90f && ax + ay <= 1.43f;
                case "square": return ax <= 0.84f && ay <= 0.84f;
                case "triangle": return y >= -0.88f && y <= 0.88f && ax <= (0.88f - y) * 0.60f;
                case "oval": return x * x / 0.60f + y * y <= 0.90f;
                case "star":
                    float radius = Mathf.Sqrt(x * x + y * y);
                    return radius <= 0.64f + 0.26f * Mathf.Cos(5f * Mathf.Atan2(y, x));
                case "rounded_square":
                    float cornerX = Mathf.Max(ax - 0.65f, 0f), cornerY = Mathf.Max(ay - 0.65f, 0f);
                    return ax <= 0.92f && ay <= 0.92f && cornerX * cornerX + cornerY * cornerY <= 0.27f * 0.27f;
                default: throw new ArgumentException("Unknown symbolic shape", nameof(shape));
            }
        }
    }
}
