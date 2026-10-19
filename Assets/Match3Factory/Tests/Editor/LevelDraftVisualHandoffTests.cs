using System;
using System.IO;
using System.Linq;
using Match3Factory;
using NUnit.Framework;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class LevelDraftVisualHandoffTests
    {
        private const string Fixture =
            "Assets/Match3Factory/Tests/Fixtures/leveldraft_v1_unicode.json";

        [Test]
        public void ActualLfxV1FixtureProjectsUnicodeAndHoleWithoutInventedWin()
        {
            var json = File.ReadAllText(Fixture);
            var handoff = LevelDraftVisualHandoff.FromCanonicalLevelDraft(json);
            Assert.That(handoff.stage, Is.EqualTo(LevelDraftVisualHandoff.Stage));
            Assert.That(handoff.gameProfileId, Is.EqualTo("Coral_Rescue"));
            Assert.That(handoff.levelId, Is.EqualTo("level.fixture-r01"));
            Assert.That(handoff.width, Is.EqualTo(2));
            Assert.That(handoff.height, Is.EqualTo(2));
            Assert.That(handoff.seed, Is.EqualTo(731));
            Assert.That(handoff.cells.Length, Is.EqualTo(4));
            Assert.That(handoff.cells[0].contentId, Is.EqualTo("gem.猫"));
            Assert.That(handoff.cells[1].contentId, Is.EqualTo("gem.\"quoted\""));
            Assert.That(handoff.cells[2].active, Is.False);
            Assert.That(handoff.cells[2].contentId, Is.Null);
            Assert.That(handoff.goals[0].targetCount, Is.EqualTo(321));
            Assert.That(handoff.sourceDraftSha256.Length, Is.EqualTo(64));
            Assert.That(handoff.actualSdkWinVerified, Is.False);
            Assert.That(handoff.engineM24ReleaseAccepted, Is.False);
            Assert.That(handoff.releaseAllowed, Is.False);
        }

        [Test]
        public void LfxV1ExportIsDeterministicAndOnlyProvidesDraftGeometry()
        {
            var source = File.ReadAllText(Fixture);
            string first = LevelDraftVisualHandoff.ToJson(source);
            string second = LevelDraftVisualHandoff.ToJson(source);
            Assert.That(first, Is.EqualTo(second));
            var result = JsonUtility.FromJson<LevelDraftVisualHandoff.Envelope>(first);
            Assert.That(result.sourceDraftSha256,
                Is.EqualTo(LevelDraftJson.Sha256(LevelDraftJson.Parse(source))));
            Assert.That(result.realPlayableLevel, Is.False);
            Assert.That(result.assetRightsApproved, Is.False);
            Assert.That(result.cells.Select(c => c.layer).Distinct(), Is.EquivalentTo(new[]{0}));
        }

        [Test]
        public void InvalidLfxDraftMustFailBeforeCreatingAnyVisualHandoff()
        {
            var valid = File.ReadAllText(Fixture);
            Assert.Throws<ArgumentException>(() =>
                LevelDraftVisualHandoff.ToJson(
                    valid.Replace("\"draftVersion\":1", "\"draftVersion\":9")));
        }
    }
}
