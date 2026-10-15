using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Match3Factory;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Match3Factory.Tests
{
    public sealed class LevelDraftIntegrationTests
    {
        [Test]
        public void SampleLevelEditorSceneOpensWithoutMissingScripts()
        {
            const string scenePath = "Assets/Match3/GameScene_Match3_LevelEditor.unity";
            var scene = EditorSceneManager.OpenScene(scenePath, OpenSceneMode.Additive);
            try
            {
                Assert.That(scene.IsValid(), Is.True);
                var missing = scene.GetRootGameObjects()
                    .SelectMany(root => root.GetComponentsInChildren<MonoBehaviour>(true))
                    .Where(component => component == null)
                    .ToArray();
                Assert.That(missing, Is.Empty, "The imported sample scene must resolve all MonoBehaviour scripts.");
                Assert.That(scene.GetRootGameObjects().SelectMany(root => root.GetComponentsInChildren<LevelEditor>(true)), Is.Not.Empty);
            }
            finally
            {
                EditorSceneManager.CloseScene(scene, true);
            }
        }

        [Test]
        public void SampleLevelSoImportsAndExportsThroughLevelDraft()
        {
            var source = AssetDatabase.LoadAssetAtPath<LevelSO>("Assets/Match3/Levels/Level_D.asset");
            Assert.That(source, Is.Not.Null);
            var draft = LevelDraftUnitySampleAdapter.FromLevelSO(source, "Coral_Rescue", 17);
            var target = ScriptableObject.CreateInstance<LevelSO>();
            try
            {
                target.gemList = new List<GemSO>(source.gemList);
                LevelDraftUnitySampleAdapter.ApplyToLevelSO(draft, target);
                Assert.That(target.width, Is.EqualTo(source.width));
                Assert.That(target.height, Is.EqualTo(source.height));
                Assert.That(target.levelGridPositionList.Count, Is.EqualTo(source.levelGridPositionList.Count));
                Assert.That(target.levelGridPositionList.Select(cell => $"{cell.y}:{cell.x}:{cell.gemSO.name}:{cell.hasGlass}"),
                    Is.EquivalentTo(source.levelGridPositionList.Select(cell => $"{cell.y}:{cell.x}:{cell.gemSO.name}:{cell.hasGlass}")));
            }
            finally
            {
                Object.DestroyImmediate(target);
            }
        }

        [Test]
        public void SampleBotChoosesTheHigherScoringCandidate()
        {
            var level = ScriptableObject.CreateInstance<LevelSO>();
            level.goalType = LevelSO.GoalType.Score;
            var gameObject = new GameObject("Match3Bot test") { hideFlags = HideFlags.HideAndDontSave };
            gameObject.SetActive(false);
            try
            {
                var bot = gameObject.AddComponent<Match3Bot>();
                typeof(Match3Bot).GetField("levelSO", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(bot, level);
                var weaker = new Match3.PossibleMove(0, 0, 0, 1)
                {
                    allLinkedGemGridPositionList = new List<List<Match3.GemGridPosition>>
                    {
                        new List<Match3.GemGridPosition> { null, null }
                    }
                };
                var stronger = new Match3.PossibleMove(1, 1, 1, 2)
                {
                    allLinkedGemGridPositionList = new List<List<Match3.GemGridPosition>>
                    {
                        new List<Match3.GemGridPosition> { null, null, null, null }
                    }
                };
                var choose = typeof(Match3Bot).GetMethod("GetBestPossibleMove", BindingFlags.Instance | BindingFlags.NonPublic);
                var selected = (Match3.PossibleMove)choose.Invoke(bot, new object[] { new List<Match3.PossibleMove> { weaker, stronger } });
                Assert.That(selected, Is.SameAs(stronger));
            }
            finally
            {
                Object.DestroyImmediate(gameObject);
                Object.DestroyImmediate(level);
            }
        }

        [Test]
        public void SampleBotAutomaticallyUsesAMoveWhenTheVisualStateIsReady()
        {
            var level = AssetDatabase.LoadAssetAtPath<LevelSO>("Assets/Match3/Levels/Level_D.asset");
            Assert.That(level, Is.Not.Null);
            var gameObject = new GameObject("Match3Bot autoplay test") { hideFlags = HideFlags.HideAndDontSave };
            gameObject.SetActive(false);
            try
            {
                var match3 = gameObject.AddComponent<Match3>();
                var visual = gameObject.AddComponent<Match3Visual>();
                var bot = gameObject.AddComponent<Match3Bot>();
                match3.SetLevelSO(level);
                Assert.That(match3.GetAllPossibleMoves(), Is.Not.Empty, "The sample LevelSO must present a legal bot move.");
                SetPrivateField(visual, "match3", match3);
                SetPrivateField(bot, "match3", match3);
                SetPrivateField(bot, "match3Visual", visual);
                SetPrivateField(bot, "levelSO", level);
                // EditMode does not call Awake for this inactive fixture object.
                typeof(Match3Bot).GetMethod("Awake", BindingFlags.Instance | BindingFlags.NonPublic)
                    .Invoke(bot, null);

                typeof(Match3Visual).GetMethod("SetState", BindingFlags.Instance | BindingFlags.NonPublic)
                    .Invoke(visual, new object[] { Match3Visual.State.WaitingForUser });

                Assert.That(match3.GetUsedMoveCount(), Is.EqualTo(1), "The WaitingForUser bot callback should execute one swap.");
            }
            finally
            {
                Object.DestroyImmediate(gameObject);
            }
        }

        [Test]
        public void LevelDraftJsonRoundTripsAndHashesCanonicalContent()
        {
            var draft = NewDraft();
            draft.cells = draft.cells.Reverse().ToArray();
            var json = LevelDraftJson.Serialize(draft);
            var parsed = LevelDraftJson.Parse(json);
            Assert.That(LevelDraftJson.Serialize(parsed), Is.EqualTo(json));
            Assert.That(LevelDraftJson.Sha256(parsed), Is.EqualTo(LevelDraftJson.Sha256(draft)));
            Assert.That(parsed.validationStatus, Is.EqualTo("PROTOTYPE_ONLY"));
        }

        [Test]
        public void LevelDraftRejectsUnknownProfileAndEngineSchemaClaims()
        {
            var draft = NewDraft();
            draft.gameProfileId = "Unknown_Game";
            Assert.That(draft.Validate().Any(error => error.Contains("Unknown gameProfileId")), Is.True);
            draft.gameProfileId = "Coral_Rescue";
            draft.engineSchemaVersion = "anything";
            Assert.That(draft.Validate().Any(error => error.Contains("Engine schema is unavailable")), Is.True);
        }

        private static LevelDraft NewDraft()
        {
            return new LevelDraft
            {
                width = 2,
                height = 2,
                activeMask = new[] { true, true, true, true },
                cells = new[]
                {
                    new CellDraft { row = 0, column = 0, layer = 0, active = true, contentId = "Blue" },
                    new CellDraft { row = 0, column = 1, layer = 0, active = true, contentId = "Green" },
                    new CellDraft { row = 1, column = 0, layer = 0, active = true, contentId = "Orange" },
                    new CellDraft { row = 1, column = 1, layer = 0, active = true, contentId = "Purple" }
                },
                goals = new[] { new GoalDraft { goalId = "goal.primary", targetId = "sample.score", targetCount = 500 } }
            };
        }

        private static void SetPrivateField(object instance, string fieldName, object value)
        {
            typeof(Match3Bot).Assembly.GetType(instance.GetType().FullName)
                .GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic).SetValue(instance, value);
        }
    }
}
