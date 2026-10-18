using System;
using NUnit.Framework;

namespace Match3Factory.Tests
{
    public sealed class NeutralVfxPreviewTests
    {
        [Test]
        public void AllFiveProfilesAndSixEffectsAreBoundedDeterministic()
        {
            CollectionAssert.AreEquivalent(GameProfileCatalog.AllProfileIds, NeutralThemePreviewRenderer.Profiles);
            Assert.AreEqual(6, NeutralVfxPreviewGeometry.Effects.Length);
            foreach (string profile in NeutralThemePreviewRenderer.Profiles)
            foreach (string effect in NeutralVfxPreviewGeometry.Effects)
            {
                for (int frame = 0; frame < NeutralVfxPreviewGeometry.FullFrameCount; frame++)
                {
                    var a = NeutralVfxPreviewGeometry.Build(profile, effect, frame, false);
                    var b = NeutralVfxPreviewGeometry.Build(profile, effect, frame, false);
                    Assert.That(a.Length, Is.InRange(2, 4));
                    Assert.AreEqual(a.Length, b.Length);
                    for (int i = 0; i < a.Length; i++)
                    {
                        Assert.AreEqual(a[i].Kind, b[i].Kind);
                        Assert.AreEqual(a[i].X, b[i].X);
                        Assert.AreEqual(a[i].Y, b[i].Y);
                        Assert.AreEqual(a[i].Size, b[i].Size);
                        Assert.That(a[i].X, Is.InRange(0f, 1000f));
                        Assert.That(a[i].Y, Is.InRange(0f, 1000f));
                        Assert.That(a[i].Size, Is.InRange(0f, 1000f));
                        Assert.That(a[i].Opacity, Is.InRange(0f, 1f));
                    }
                }
            }
            Assert.AreEqual("SYMBOLIC_FX_PREVIEW_ONLY", NeutralVfxPreviewGeometry.ResultStatus);
            Assert.AreEqual("BLOCKED_ENG_M24", NeutralVfxPreviewGeometry.EngineStatus);
            Assert.AreEqual("NOT_RUN", NeutralVfxPreviewGeometry.ReplayComparison);
        }

        [Test]
        public void ReducedMotionIsStaticAndUnknownEffectsFailClosed()
        {
            foreach (string effect in NeutralVfxPreviewGeometry.Effects)
            {
                var a = NeutralVfxPreviewGeometry.Build("Wonder_Pop", effect, 0, true);
                var b = NeutralVfxPreviewGeometry.Build("Wonder_Pop", effect, 0, true);
                Assert.AreEqual(a.Length, b.Length);
                for (int i = 0; i < a.Length; i++)
                    Assert.AreEqual(a[i].X, b[i].X);
                Assert.Throws<ArgumentOutOfRangeException>(() =>
                    NeutralVfxPreviewGeometry.Build("Wonder_Pop", effect, 1, true));
            }
            Assert.Throws<ArgumentException>(() =>
                NeutralVfxPreviewGeometry.Build("Unknown_Title", "combo", 0, false));
            Assert.Throws<ArgumentException>(() =>
                NeutralVfxPreviewGeometry.Build("Coral_Rescue", "unknown", 0, false));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                NeutralVfxPreviewGeometry.Build("Coral_Rescue", "portal", 12, false));
        }
    }
}
