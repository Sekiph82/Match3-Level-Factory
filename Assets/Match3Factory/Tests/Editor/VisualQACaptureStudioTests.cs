using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class VisualQACaptureStudioTests
    {
        [Test]
        public void CapturePlansContainAllFifteenThemeAndOneHundredTwentyVfxImages()
        {
            var themes = VisualQACaptureStudio.CreateThemePlan();
            Assert.AreEqual(15, themes.Length);
            CollectionAssert.AreEquivalent(NeutralThemePreviewRenderer.Profiles,
                DistinctProfiles(themes));
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            {
                var matching = Array.FindAll(themes, item => item.profile == profile);
                CollectionAssert.AreEquivalent(new[] { 320, 390, 720 }, Array.ConvertAll(matching, item => item.width));
                foreach (var frame in matching)
                {
                    Assert.AreEqual(Mathf.RoundToInt(frame.width * 16f / 9f), frame.height);
                    Assert.AreEqual("theme", frame.category);
                }
            }

            var vfx = VisualQACaptureStudio.CreateVfxPlan();
            Assert.AreEqual(120, vfx.Length);
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            foreach (string effect in NeutralVfxPreviewGeometry.Effects)
            {
                var states = Array.FindAll(vfx, item => item.profile == profile && item.effect == effect);
                Assert.AreEqual(4, states.Length, profile + "/" + effect);
                CollectionAssert.AreEquivalent(new[] { 0, 5, 11 },
                    Array.ConvertAll(Array.FindAll(states, item => !item.reducedMotion), item => item.frame));
                Assert.AreEqual(1, Array.FindAll(states, item => item.reducedMotion && item.frame == 0).Length);
            }
        }

        [Test]
        public void AllThemeAndVfxCapturesHaveDeterministicBoundedPngRenders()
        {
            var draft = SampleDraft();
            string draftSha = LevelDraftJson.Sha256(draft);
            var plans = new List<VisualQACaptureStudio.CaptureFrame>();
            plans.AddRange(VisualQACaptureStudio.CreateThemePlan());
            plans.AddRange(VisualQACaptureStudio.CreateVfxPlan());
            Assert.AreEqual(135, plans.Count);
            foreach (var plan in plans)
            {
                Texture2D first = null, repeat = null;
                try
                {
                    first = VisualQACaptureStudio.Render(plan);
                    repeat = VisualQACaptureStudio.Render(plan);
                    Assert.AreEqual(plan.width, first.width, plan.fileName);
                    Assert.AreEqual(plan.height, first.height, plan.fileName);
                    Assert.LessOrEqual((long)first.width * first.height, VisualQACaptureStudio.MaxImagePixels, plan.fileName);
                    string pixelHash = VisualQACaptureStudio.PixelSha256(first);
                    Assert.AreEqual(pixelHash, VisualQACaptureStudio.PixelSha256(repeat), plan.fileName);
                    byte[] png = first.EncodeToPNG();
                    byte[] repeatedPng = repeat.EncodeToPNG();
                    Assert.Greater(png.Length, 8, plan.fileName);
                    Assert.LessOrEqual(png.LongLength, VisualQACaptureStudio.MaxPngBytes, plan.fileName);
                    Assert.AreEqual(Digest(png), Digest(repeatedPng), plan.fileName);
                }
                finally
                {
                    if (first != null) UnityEngine.Object.DestroyImmediate(first);
                    if (repeat != null) UnityEngine.Object.DestroyImmediate(repeat);
                }
            }
            Assert.AreEqual(draftSha, LevelDraftJson.Sha256(draft),
                "Rendering neutral evidence must not mutate canonical gameplay draft data.");
        }

        [Test]
        public void ReducedMotionUsesOnlyOneStableFrameAndKeepsPreviewAuthorityDisabled()
        {
            foreach (var plan in VisualQACaptureStudio.CreateVfxPlan())
            {
                if (!plan.reducedMotion) continue;
                Assert.AreEqual(0, plan.frame);
                var shapes = NeutralVfxPreviewGeometry.Build(plan.profile, plan.effect, plan.frame, true);
                Assert.That(shapes.Length, Is.InRange(2, 4));
                Assert.Throws<ArgumentOutOfRangeException>(() =>
                    NeutralVfxPreviewGeometry.Build(plan.profile, plan.effect, 1, true));
            }
            Assert.AreEqual("BLOCKED_ENG_M24", NeutralVfxPreviewGeometry.EngineStatus);
            Assert.AreEqual("NOT_RUN", NeutralVfxPreviewGeometry.ReplayComparison);
            var manifest = new VisualQACaptureStudio.CaptureManifest();
            Assert.AreEqual("NOT_RUN", manifest.playPauseInteractionStatus);
            Assert.AreEqual("DETERMINISTIC_RENDERER_OUTPUT_NOT_EDITOR_WINDOW_SCREENSHOT", manifest.imageEvidenceType);
        }

        [Test]
        public void CheckpointCaptureRequiresValidV2ReceiptAndRejectsInvalidJsonOrSha()
        {
            string valid = JsonUtility.ToJson(ValidReceipt());
            var parsed = ReferenceCheckpointPreview.Parse(valid);
            Assert.AreEqual(2, parsed.referencePreviewVersion);
            Texture2D image = VisualQACaptureStudio.RenderCheckpointBoard(parsed);
            Texture2D repeat = null;
            try
            {
                Assert.AreEqual(VisualQACaptureStudio.CheckpointImageWidth, image.width);
                Assert.AreEqual(VisualQACaptureStudio.CheckpointImageHeight, image.height);
                Assert.Greater(image.EncodeToPNG().Length, 8);
                repeat = VisualQACaptureStudio.RenderCheckpointBoard(parsed);
                Assert.AreEqual(VisualQACaptureStudio.PixelSha256(image), VisualQACaptureStudio.PixelSha256(repeat));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(image);
                if (repeat != null) UnityEngine.Object.DestroyImmediate(repeat);
            }
            Assert.Throws<ArgumentException>(() => ReferenceCheckpointPreview.Parse("{invalid json"));
            var badBoardHash = ValidReceipt();
            badBoardHash.initialBoardSha256 = new string('0', 64);
            Assert.Throws<ArgumentException>(() => ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(badBoardHash)));
            var badMetricHash = ValidReceipt();
            badMetricHash.checkpointSha256 = new string('0', 64);
            Assert.Throws<ArgumentException>(() => ReferenceCheckpointPreview.Parse(JsonUtility.ToJson(badMetricHash)));
        }

        [Test]
        public void SourceSvgsRemainByteIdenticalAndCaptureCodeIsEditorOnly()
        {
            string root = Directory.GetParent(Application.dataPath).FullName;
            var hashes = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            {
                string path = Path.Combine(root, "Assets", "Match3Factory", "Editor", "Previews", "Neutral", profile + ".svg");
                Assert.IsTrue(File.Exists(path), profile);
                hashes.Add(path, Digest(File.ReadAllBytes(path)));
            }
            foreach (var plan in VisualQACaptureStudio.CreateVfxPlan())
            {
                Texture2D texture = null;
                try { texture = VisualQACaptureStudio.Render(plan); }
                finally { if (texture != null) UnityEngine.Object.DestroyImmediate(texture); }
            }
            foreach (var item in hashes)
                Assert.AreEqual(item.Value, Digest(File.ReadAllBytes(item.Key)), Path.GetFileName(item.Key));

            Assert.AreEqual("Match3Factory.Editor", typeof(VisualQACaptureStudio).Assembly.GetName().Name);
            string editorAsmdef = Path.Combine(Application.dataPath, "Match3Factory", "Editor", "Match3Factory.Editor.asmdef");
            string asmdef = File.ReadAllText(editorAsmdef);
            StringAssert.Contains("\"includePlatforms\"", asmdef);
            StringAssert.Contains("\"Editor\"", asmdef);
            Assert.NotNull(AssetDatabase.LoadAssetAtPath<MonoScript>(
                "Assets/Match3Factory/Editor/VisualQACaptureStudio.cs"));
            Assert.NotNull(AssetDatabase.LoadAssetAtPath<MonoScript>(
                "Assets/Match3Factory/Editor/NeutralVfxPreviewRenderer.cs"));
        }

        [Test]
        public void CaptureBoundsRejectOversizedTexturesAndNoEngineOrRuntimeAuthorityIsIntroduced()
        {
            Assert.AreEqual(2400000, NeutralVfxPreviewRenderer.MaxPixelCount);
            Assert.AreEqual(16L * 1024 * 1024, VisualQACaptureStudio.MaxPngBytes);
            Assert.AreEqual(128L * 1024 * 1024, VisualQACaptureStudio.MaxOutputBytes);
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                NeutralVfxPreviewRenderer.Render("Coral_Rescue", "combo", 0, false, 3000, 5000));
            Assert.AreEqual("BLOCKED_ENG_M24", ReferenceCheckpointPreview.EngineStatus);
            Assert.AreEqual("REFERENCE_CHECKPOINT_PREVIEW_ONLY", ReferenceCheckpointPreview.ResultStatus);
            Assert.AreEqual("GEOMETRIC_EDITOR_PREVIEW_ONLY", NeutralThemePreviewRenderer.ResultStatus);
            Assert.AreEqual("SYMBOLIC_FX_PREVIEW_ONLY", NeutralVfxPreviewGeometry.ResultStatus);
        }

        private static ReferenceCheckpointPreview.Receipt ValidReceipt()
        {
            var cells = new ReferenceCheckpointPreview.BoardCell[36];
            for (int row = 0; row < 6; row++)
            for (int column = 0; column < 6; column++)
                cells[row * 6 + column] = new ReferenceCheckpointPreview.BoardCell {
                    row = row, column = column, type = 1, color = 1, status = 0
                };
            return new ReferenceCheckpointPreview.Receipt {
                resultStatus = ReferenceCheckpointPreview.ResultStatus,
                engineStatus = ReferenceCheckpointPreview.EngineStatus,
                sourceRevision = ReferenceCheckpointPreview.PinnedDonor,
                candidateIndex = 0, runIndex = 0, runSeed = 777,
                referencePreviewVersion = 2, donorMovesUsed = 2, donorShuffles = 0,
                policy = "smart", donorOutcome = "MOVE_LIMIT",
                checkpointSha256 = "4c1cafdc5872feaeeeb0e38142068ea17bae929e6ee0625bff80daa26643f4ec",
                initialBoardIsSeededDonorSetup = true, boardAtCheckpointAvailable = false,
                initialBoardSha256 = "10561542d92b047dca613cac4abbb5a5e5e30b23013794995362e9d7c0da41e8",
                initialBoard = new ReferenceCheckpointPreview.InitialBoard { rows = 6, columns = 6, cells = cells },
                checkpointsAreBeforeMove = true, paddedFinalStatisticsPresent = false,
                lastMoveMayBeUnobserved = true, exactCascadeOrderOrBoardFramesAvailable = false,
                goalsOrWinProved = false, releaseAuthorized = false,
                checkpoints = new[] {
                    new ReferenceCheckpointPreview.Checkpoint {
                        beforeMove = 1, stepSlot = 1, observedBeforeMove = true,
                        paddedFinalStatistics = false, cumulative = new ReferenceCheckpointPreview.Metrics() },
                    new ReferenceCheckpointPreview.Checkpoint {
                        beforeMove = 2, stepSlot = 2, observedBeforeMove = true,
                        paddedFinalStatistics = false, cumulative = new ReferenceCheckpointPreview.Metrics { score = 4, ndestroyed = 4 } }
                }
            };
        }

        private static LevelDraft SampleDraft()
        {
            return new LevelDraft {
                gameProfileId = "Coral_Rescue", seed = 712, width = 2, height = 2, layers = 1,
                activeMask = new[] { true, true, true, true },
                cells = new[] {
                    new CellDraft { row = 0, column = 0, layer = 0, active = true, contentId = "Blue" },
                    new CellDraft { row = 0, column = 1, layer = 0, active = true, contentId = "Green" },
                    new CellDraft { row = 1, column = 0, layer = 0, active = true, contentId = "Orange" },
                    new CellDraft { row = 1, column = 1, layer = 0, active = true, contentId = "Purple" },
                },
                goals = new[] { new GoalDraft { goalId = "goal.primary", targetId = "sample.score", targetCount = 1 } }
            };
        }

        private static string[] DistinctProfiles(VisualQACaptureStudio.CaptureFrame[] frames)
        {
            var profiles = new HashSet<string>(StringComparer.Ordinal);
            foreach (var frame in frames) profiles.Add(frame.profile);
            var result = new string[profiles.Count];
            profiles.CopyTo(result);
            return result;
        }

        private static string Digest(byte[] value)
        {
            using (var sha = SHA256.Create())
            {
                byte[] hash = sha.ComputeHash(value);
                var text = new StringBuilder(hash.Length * 2);
                foreach (byte b in hash) text.Append(b.ToString("x2"));
                return text.ToString();
            }
        }
    }
}
