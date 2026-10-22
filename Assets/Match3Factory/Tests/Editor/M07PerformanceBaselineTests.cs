using Match3Factory;
using NUnit.Framework;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class M07PerformanceBaselineTests
    {
        [Test]
        public void CapturesUnityEditorLevelDraftPerformanceBaseline()
        {
            var report = M07PerformanceBaselineProbe.Capture();
            Assert.That(report.taskId, Is.EqualTo("LFX-M07-006"));
            Assert.That(report.iterations, Is.EqualTo(25));
            Assert.That(report.fixtureSha256, Is.EqualTo("0badd48bbd433066b7fe7274dc80acb9054a154ed8ed95cf7934ca280ac09d68"));
            Assert.That(report.canonicalDraftSha256, Is.EqualTo("fffe76265e590a787b3e1284a2960b378c88df3f0f5260f3d10faf639d5c794d"));
            Assert.That(report.operations, Has.Length.EqualTo(4));
            Assert.That(report.runtimeGameplay, Is.False);
            Assert.That(report.releaseAuthorized, Is.False);
            Assert.That(report.engineStatus, Is.EqualTo("BLOCKED_ENG_M24"));
            TestContext.WriteLine(JsonUtility.ToJson(report, true));
        }
    }
}
