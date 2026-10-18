using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using NUnit.Framework;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class NeutralThemePreviewTests
    {
        [Test]
        public void FiveProfilesMatchOriginalPaletteAndSilhouetteContract()
        {
            CollectionAssert.AreEquivalent(GameProfileCatalog.AllProfileIds, NeutralThemePreviewRenderer.Profiles);
            Assert.AreEqual(5, NeutralThemePreviewRenderer.Profiles.Length);
            CollectionAssert.AreEqual(new[] { "#103F62", "#1B819A", "#A8DFE8" },
                NeutralThemePreviewRenderer.Palette("Coral_Rescue"));
            CollectionAssert.AreEqual(new[] { "octagon", "square", "triangle" },
                NeutralThemePreviewRenderer.Silhouettes("Garage_Legends"));
            CollectionAssert.AreEqual(new[] { "circle", "rounded_square", "star" },
                NeutralThemePreviewRenderer.Silhouettes("Wonder_Pop"));
            var external = NeutralThemePreviewRenderer.Palette("Wonder_Pop");
            external[0] = "#000000";
            Assert.AreEqual("#355777", NeutralThemePreviewRenderer.Palette("Wonder_Pop")[0]);
            Assert.AreEqual("GEOMETRIC_EDITOR_PREVIEW_ONLY", NeutralThemePreviewRenderer.ResultStatus);
            Assert.AreEqual("BLOCKED_ENG_M24", NeutralThemePreviewRenderer.EngineStatus);
        }

        [Test]
        public void EachTitleRendersDistinctDeterministicPortraitGeometry()
        {
            var digests = new HashSet<string>(StringComparer.Ordinal);
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            {
                Texture2D first = null;
                Texture2D repeat = null;
                try
                {
                    first = NeutralThemePreviewRenderer.Render(profile, 320, 568);
                    repeat = NeutralThemePreviewRenderer.Render(profile, 320, 568);
                    Assert.AreEqual(320, first.width);
                    Assert.AreEqual(568, first.height);
                    string fingerprint = Digest(first);
                    Assert.AreEqual(fingerprint, Digest(repeat), profile + " must render deterministically");
                    Assert.IsTrue(digests.Add(fingerprint), "Themes must be visually distinct");
                    Assert.AreNotEqual(first.GetPixel(20, 20), first.GetPixel(160, 284),
                        "Preview must contain a visible geometric board");
                }
                finally
                {
                    if (first != null) UnityEngine.Object.DestroyImmediate(first);
                    if (repeat != null) UnityEngine.Object.DestroyImmediate(repeat);
                }
            }
            Assert.AreEqual(5, digests.Count);
        }

        [Test]
        public void RetinaAndPortraitSizesStayBounded()
        {
            foreach (var dimension in new[] { new[] { 390, 693 }, new[] { 720, 1280 } })
            {
                Texture2D image = null;
                try
                {
                    image = NeutralThemePreviewRenderer.Render("Coral_Rescue", dimension[0], dimension[1]);
                    Assert.AreEqual(dimension[0], image.width);
                    Assert.AreEqual(dimension[1], image.height);
                }
                finally
                {
                    if (image != null) UnityEngine.Object.DestroyImmediate(image);
                }
            }
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                NeutralThemePreviewRenderer.Render("Coral_Rescue", 3000, 5000));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                NeutralThemePreviewRenderer.Render("Coral_Rescue", 100, 100));
            Assert.Throws<ArgumentException>(() =>
                NeutralThemePreviewRenderer.Render("Unknown_Title", 390, 693));
        }

        private static string Digest(Texture2D texture)
        {
            Color32[] colors = texture.GetPixels32();
            byte[] bytes = new byte[colors.Length * 4];
            for (int i = 0; i < colors.Length; i++)
            {
                int offset = i * 4;
                bytes[offset] = colors[i].r;
                bytes[offset + 1] = colors[i].g;
                bytes[offset + 2] = colors[i].b;
                bytes[offset + 3] = colors[i].a;
            }
            using (var sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "");
        }
    }
}
