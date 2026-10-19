using System;
using UnityEngine;

namespace Match3Factory
{
    /// <summary>
    /// Rasterizes the same symbolic geometry used by the neutral VFX rehearsal window.
    /// This is an editor preview only; it does not simulate gameplay or Engine events.
    /// </summary>
    public static class NeutralVfxPreviewRenderer
    {
        public const int DefaultWidth = 320;
        public const int DefaultHeight = 568;
        public const int MaxPixelCount = 2400000;

        public static Texture2D Render(string profile, string effect, int frame, bool reduced,
            int width = DefaultWidth, int height = DefaultHeight)
        {
            if (width < 160 || height < 240 || width > 1600 || height > 3200 ||
                (long)width * height > MaxPixelCount)
                throw new ArgumentOutOfRangeException(nameof(width), "Use a bounded editor preview image.");

            Texture2D background = NeutralThemePreviewRenderer.Render(profile, width, height);
            try
            {
                Color32[] pixels = background.GetPixels32();
                var area = new Rect(width * 0.1f, height * (184f / 568f),
                    width * 0.8f, height * (255f / 568f));
                NeutralVfxPreviewGeometry.Shape[] shapes =
                    NeutralVfxPreviewGeometry.Build(profile, effect, frame, reduced);
                foreach (var shape in shapes) DrawShape(pixels, width, height, area, shape);

                var result = new Texture2D(width, height, TextureFormat.RGBA32, false)
                {
                    name = "Match3 Neutral VFX " + profile + " " + effect,
                    filterMode = FilterMode.Bilinear,
                    wrapMode = TextureWrapMode.Clamp,
                    hideFlags = HideFlags.HideAndDontSave
                };
                result.SetPixels32(pixels);
                result.Apply(false, false);
                return result;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(background);
            }
        }

        private static void DrawShape(Color32[] pixels, int width, int height, Rect area,
            NeutralVfxPreviewGeometry.Shape shape)
        {
            Color color;
            if (!ColorUtility.TryParseHtmlString(shape.Color, out color))
                throw new InvalidOperationException("Invalid built-in preview color.");
            Color32 source = color;
            source.a = (byte)Mathf.RoundToInt(Mathf.Clamp01(shape.Opacity) * 255f);
            float x = area.x + shape.X * area.width / 1000f;
            float y = area.y + shape.Y * area.height / 1000f;
            float radius = shape.Size * area.width / 1000f;
            switch (shape.Kind)
            {
                case "line": RasterRect(pixels, width, height, x - 4f, y - radius, 8f, 2f * radius, source); break;
                case "square": RasterRect(pixels, width, height, x - radius, y - radius,
                    2f * radius, 2f * radius, source); break;
                case "circle":
                case "oval": RasterDisc(pixels, width, height, x, y, radius, source); break;
                case "diamond": RasterDiamond(pixels, width, height, x, y, radius, source); break;
                default: throw new ArgumentException("Invalid original preview primitive.", nameof(shape));
            }
        }

        private static void RasterRect(Color32[] pixels, int width, int height,
            float x, float y, float rectWidth, float rectHeight, Color32 color)
        {
            int left = Mathf.Max(0, Mathf.CeilToInt(x));
            int right = Mathf.Min(width, Mathf.CeilToInt(x + rectWidth));
            int top = Mathf.Max(0, Mathf.CeilToInt(y));
            int bottom = Mathf.Min(height, Mathf.CeilToInt(y + rectHeight));
            for (int py = top; py < bottom; py++)
            for (int px = left; px < right; px++) Blend(pixels, width, height, px, py, color);
        }

        private static void RasterDisc(Color32[] pixels, int width, int height,
            float centerX, float centerY, float radius, Color32 color)
        {
            int left = Mathf.Max(0, Mathf.FloorToInt(centerX - radius));
            int right = Mathf.Min(width - 1, Mathf.CeilToInt(centerX + radius));
            int top = Mathf.Max(0, Mathf.FloorToInt(centerY - radius));
            int bottom = Mathf.Min(height - 1, Mathf.CeilToInt(centerY + radius));
            float squared = radius * radius;
            for (int py = top; py <= bottom; py++)
            for (int px = left; px <= right; px++)
            {
                float dx = px + 0.5f - centerX;
                float dy = py + 0.5f - centerY;
                if (dx * dx + dy * dy <= squared) Blend(pixels, width, height, px, py, color);
            }
        }

        private static void RasterDiamond(Color32[] pixels, int width, int height,
            float centerX, float centerY, float radius, Color32 color)
        {
            int left = Mathf.Max(0, Mathf.FloorToInt(centerX - radius));
            int right = Mathf.Min(width - 1, Mathf.CeilToInt(centerX + radius));
            int top = Mathf.Max(0, Mathf.FloorToInt(centerY - radius));
            int bottom = Mathf.Min(height - 1, Mathf.CeilToInt(centerY + radius));
            for (int py = top; py <= bottom; py++)
            for (int px = left; px <= right; px++)
            {
                float dx = Mathf.Abs(px + 0.5f - centerX);
                float dy = Mathf.Abs(py + 0.5f - centerY);
                if (dx + dy <= radius) Blend(pixels, width, height, px, py, color);
            }
        }

        private static void Blend(Color32[] pixels, int width, int height, int x, int y, Color32 source)
        {
            int index = (height - 1 - y) * width + x;
            Color32 destination = pixels[index];
            float alpha = source.a / 255f;
            float inverse = 1f - alpha;
            pixels[index] = new Color32(
                (byte)Mathf.Clamp(Mathf.RoundToInt(source.r * alpha + destination.r * inverse), 0, 255),
                (byte)Mathf.Clamp(Mathf.RoundToInt(source.g * alpha + destination.g * inverse), 0, 255),
                (byte)Mathf.Clamp(Mathf.RoundToInt(source.b * alpha + destination.b * inverse), 0, 255),
                255);
        }
    }
}
