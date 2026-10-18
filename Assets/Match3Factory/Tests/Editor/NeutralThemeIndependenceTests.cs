using System;
using NUnit.Framework;
using UnityEngine;

namespace Match3Factory.Tests
{
    /// <summary>LFX-M08-009 isolated editor-only draft hash parity, NOT Engine replay.</summary>
    public sealed class NeutralThemeIndependenceTests
    {
        private static LevelDraft Sample()
        {
            return new LevelDraft {
                gameProfileId = "Coral_Rescue",
                seed = 712, width = 2, height = 2, layers = 1,
                activeMask = new[] { true, true, true, true },
                cells = new[] {
                    new CellDraft { row = 0, column = 0, layer = 0, active = true, contentId = "Blue" },
                    new CellDraft { row = 0, column = 1, layer = 0, active = true, contentId = "Green" },
                    new CellDraft { row = 1, column = 0, layer = 0, active = true, contentId = "Orange" },
                    new CellDraft { row = 1, column = 1, layer = 0, active = true, contentId = "Purple" },
                },
                goals = new[] {
                    new GoalDraft { goalId = "goal.primary", targetId = "sample.score", targetCount = 1 }
                }
            };
        }

        [Test]
        public void AllFiveThemesAndSixFxPreviewFramesLeaveDraftBytesUnchanged()
        {
            var draft = Sample();
            string before = LevelDraftJson.Sha256(draft);
            Assert.AreEqual(5, NeutralThemePreviewRenderer.Profiles.Length);
            foreach (var profile in NeutralThemePreviewRenderer.Profiles)
            {
                Assert.AreEqual(3, NeutralThemePreviewRenderer.Palette(profile).Length);
                Assert.AreEqual(3, NeutralThemePreviewRenderer.Silhouettes(profile).Length);
                foreach (var effect in NeutralVfxPreviewGeometry.Effects)
                {
                    foreach (bool reduced in new[] { true, false })
                    {
                        int lastFrame = reduced ? 0 : NeutralVfxPreviewGeometry.FullFrameCount - 1;
                        var primitives = NeutralVfxPreviewGeometry.Build(profile, effect, lastFrame, reduced);
                        Assert.That(primitives.Length, Is.InRange(2, 4));
                        Assert.AreEqual(before, LevelDraftJson.Sha256(draft),
                            profile + " / " + effect + " mutated the core LevelDraft.");
                    }
                }
            }
            Assert.AreEqual("PROTOTYPE_ONLY", draft.validationStatus);
            Assert.AreEqual(before, LevelDraftJson.Sha256(draft));
        }

        [Test]
        public void NeutralPreviewComponentsAreEditorOnlyAndCannotChangeCoreAuthority()
        {
            Assert.AreEqual("Match3Factory.Editor", typeof(NeutralThemePreviewRenderer).Assembly.GetName().Name);
            Assert.AreEqual("Match3Factory.Editor", typeof(NeutralVfxPreviewGeometry).Assembly.GetName().Name);
            Assert.AreEqual("Match3Factory.Editor", typeof(ReferenceCheckpointPreview).Assembly.GetName().Name);
            Assert.AreEqual("Match3Factory.Core", typeof(LevelDraft).Assembly.GetName().Name);
            Assert.AreNotEqual(typeof(LevelDraft).Assembly, typeof(NeutralVfxPreviewGeometry).Assembly);
            Assert.AreEqual("BLOCKED_ENG_M24", NeutralThemePreviewRenderer.EngineStatus);
            Assert.AreEqual("BLOCKED_ENG_M24", NeutralVfxPreviewGeometry.EngineStatus);
        }
    }
}
