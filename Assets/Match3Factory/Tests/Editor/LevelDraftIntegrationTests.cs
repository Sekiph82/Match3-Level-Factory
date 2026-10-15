using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Match3Factory;
using NUnit.Framework;
using UnityEditor;
using UnityEditor.Compilation;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UIElements;

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
        public void ReferenceAndFactoryAssembliesAreExcludedFromPlayerCompilation()
        {
            var playerAssemblies = CompilationPipeline.GetAssemblies(AssembliesType.Player);
            var playerNames = new HashSet<string>(playerAssemblies.Select(assembly => assembly.name));
            Assert.That(playerNames, Does.Not.Contain("Match3.Reference"));
            Assert.That(playerNames, Does.Not.Contain("Match3Factory.Editor"));
            Assert.That(playerNames, Does.Not.Contain("Match3Factory.SDKBridge"));
            Assert.That(playerNames, Does.Not.Contain("Match3Factory.Editor.Tests"));
            Assert.That(EditorBuildSettings.scenes.Any(scene => scene.enabled && scene.path.StartsWith("Assets/Match3/", System.StringComparison.Ordinal)), Is.False,
                "Sample scene must not be listed as a consumer-game player scene.");
        }

        [Test]
        [Explicit("Run as a separate local Windows Player build; Unity's build pipeline cannot reliably run inside the full EditMode suite.")]
        public void WindowsPlayerBuildExcludesReferenceFactoryAndTestAssemblies()
        {
            const string scenePath = "Assets/Match3Factory/Tests/Fixtures/PlayerFirewallProof.unity";
            const string outputDirectory = "Logs/PlayerFirewallProof";
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            try
            {
                Assert.That(EditorSceneManager.SaveScene(scene, scenePath), Is.True);
                Directory.CreateDirectory(outputDirectory);
                var options = new BuildPlayerOptions
                {
                    scenes = new[] { scenePath },
                    locationPathName = Path.Combine(outputDirectory, "FactoryFirewallProof.exe"),
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.StrictMode
                };
                BuildReport report = BuildPipeline.BuildPlayer(options);
                string buildMessages = string.Join("\n", report.steps.SelectMany(step => step.messages)
                    .Select(message => message.type + ": " + message.content));
                Assert.That(report.summary.result, Is.EqualTo(BuildResult.Succeeded), report.summary + "\n" + buildMessages);
                var outputAssemblies = Directory.GetFiles(outputDirectory, "*.dll", SearchOption.AllDirectories)
                    .Select(Path.GetFileNameWithoutExtension).ToArray();
                foreach (string forbidden in new[] { "Match3.Reference", "Match3Factory.Editor", "Match3Factory.SDKBridge", "Match3Factory.Editor.Tests", "Match3Factory.PlayMode.Tests" })
                    Assert.That(outputAssemblies, Does.Not.Contain(forbidden), "Player output must exclude " + forbidden + ".");
            }
            finally { EditorSceneManager.CloseScene(scene, true); }
        }

        [Test]
        public void FiveProfileRegistryIsExplicitAndFailsClosedForAdvancedMechanics()
        {
            Assert.That(GameProfileCatalog.AllProfileIds, Is.EquivalentTo(new[] { "Coral_Rescue", "Garage_Legends", "Dino_Islands", "The_Fractured_Realms", "Wonder_Pop" }));
            foreach (string id in GameProfileCatalog.AllProfileIds)
            {
                var profile = GameProfileCatalog.Get(id);
                Assert.That(profile.Version, Is.EqualTo(1));
                Assert.That(profile.EnabledCapabilities, Does.Contain("piece.color.basic"));
                Assert.That(profile.DisabledCapabilities, Does.Contain("transport.portal"));
            }
            Assert.That(GameProfileCatalog.Get("unknown"), Is.Null);
            var wonder = GameProfileCatalog.Get("Wonder_Pop");
            Assert.That(wonder.AudiencePolicy, Is.EqualTo("CHILD_SAFE_RESTRICTED"));
            Assert.That(wonder.EnabledCapabilities.Any(capability => capability.StartsWith("liveops.")), Is.False);
            var draft = NewDraft(); draft.cells[0].specialId = "ultragem.bomb";
            Assert.That(GameProfileCatalog.ValidateDraft(draft), Is.Not.Empty);
        }

        [Test]
        public void DraftMetadataRejectsProductionChannelUnknownPlatformAndEngineRangeClaims()
        {
            var draft = NewDraft();
            draft.releaseChannel = "production";
            Assert.That(draft.Validate().Any(error => error.Contains("releaseChannel")), Is.True);
            draft.releaseChannel = "local";
            draft.platform = "spaceship";
            Assert.That(draft.Validate().Any(error => error.Contains("platform")), Is.True);
            draft.platform = "windows-editor";
            draft.minEngineVersion = "1.0.0";
            Assert.That(draft.Validate().Any(error => error.Contains("Engine version constraints")), Is.True);
        }

        [Test]
        public void AutosaveKeepsPreviousValidDraftAndRecoversWithoutMutatingCorruptCurrentFile()
        {
            string folder = Path.Combine(Path.GetTempPath(), "Match3FactoryAutosaveTests", System.Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(folder);
            string path = Path.Combine(folder, "draft-v1.json");
            try
            {
                var first = NewDraft(); first.seed = 11;
                var second = NewDraft(); second.seed = 22;
                LevelDraftAutosaveStore.Save(path, first);
                LevelDraftAutosaveStore.Save(path, second);
                Assert.That(File.Exists(path + ".bak"), Is.True);
                string corrupt = "{broken";
                File.WriteAllText(path, corrupt);
                LevelDraft recovered;
                AutosaveRecoveryStatus status;
                string message;
                Assert.That(LevelDraftAutosaveStore.TryLoad(path, out recovered, out status, out message), Is.True);
                Assert.That(status, Is.EqualTo(AutosaveRecoveryStatus.Backup));
                Assert.That(recovered.seed, Is.EqualTo(11));
                Assert.That(File.ReadAllText(path), Is.EqualTo(corrupt), "Recovery reads must not overwrite the corrupt current artifact.");
                Assert.That(message, Does.Contain("previous valid version"));
            }
            finally { Directory.Delete(folder, true); }
        }

        [Test]
        public void DraftStudioShowsEveryCompositeGoalForEditing()
        {
            var window = ScriptableObject.CreateInstance<LevelDraftStudioWindow>();
            try
            {
                var draft = NewDraft();
                draft.goals = new[]
                {
                    new GoalDraft { goalId = "goal.score", targetId = "sample.score", targetCount = 500 },
                    new GoalDraft { goalId = "goal.glass", targetId = "sample.glass", targetCount = 1 }
                };
                typeof(LevelDraftStudioWindow).GetField("draft", BindingFlags.Instance | BindingFlags.NonPublic).SetValue(window, draft);
                window.CreateGUI();
                Assert.That(window.rootVisualElement.Q<IntegerField>("goal-target-0"), Is.Not.Null);
                Assert.That(window.rootVisualElement.Q<IntegerField>("goal-target-1"), Is.Not.Null);
                Assert.That(window.rootVisualElement.Q<TextField>("goal-target-id-1").value, Is.EqualTo("sample.glass"));
            }
            finally { UnityEngine.Object.DestroyImmediate(window); }
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
        public void CSharpCanonicalJsonMatchesTheSharedPythonGoldenFixture()
        {
            string fixturePath = Path.Combine(Application.dataPath, "Match3Factory/Tests/Fixtures/leveldraft_v1_unicode.json");
            string expected = File.ReadAllText(fixturePath, System.Text.Encoding.UTF8).TrimStart('\uFEFF', '\r', '\n');
            var parsed = LevelDraftJson.Parse(expected);
            Assert.That(LevelDraftJson.Serialize(parsed), Is.EqualTo(expected));
            Assert.That(LevelDraftJson.Sha256(parsed), Is.EqualTo("60943fb8cc6a9941803f66e9785b12ccaa70af12648042e05ed594868af209a4"));
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

        [Test]
        public void LevelDraftRejectsMissingDuplicateOffboardAndMaskMismatchCells()
        {
            var draft = NewDraft();
            draft.cells = draft.cells.Take(3).ToArray();
            Assert.That(draft.Validate().Any(error => error.Contains("exactly 4 entries")), Is.True);
            draft = NewDraft();
            draft.cells[3] = CloneCell(draft.cells[2]);
            Assert.That(draft.Validate().Any(error => error.Contains("Duplicate cell coordinate")), Is.True);
            draft = NewDraft();
            draft.cells[3].column = 9;
            Assert.That(draft.Validate().Any(error => error.Contains("coordinate out of range")), Is.True);
            draft = NewDraft();
            draft.activeMask[3] = false;
            Assert.That(draft.Validate().Any(error => error.Contains("activeMask disagrees")), Is.True);
        }

        [TestCase("unknown-field")]
        [TestCase("duplicate-key")]
        [TestCase("wrong-type")]
        [TestCase("missing-field")]
        public void StrictUnityParserRejectsAdversarialDrafts(string mutation)
        {
            string json = LevelDraftJson.Serialize(NewDraft());
            switch (mutation)
            {
                case "unknown-field": json = json.Substring(0, json.Length - 1) + ",\"unexpected\":true}"; break;
                case "duplicate-key": json = json.Substring(0, json.Length - 1) + ",\"seed\":1}"; break;
                case "wrong-type": json = json.Replace("\"width\":2", "\"width\":2.5"); break;
                case "missing-field": json = json.Replace("\"seed\":0,", string.Empty); break;
            }
            Assert.Throws<System.ArgumentException>(() => LevelDraftJson.Parse(json));
        }

        [Test]
        public void LevelSoAdapterRejectsCompositeOrContradictoryGoalsWithoutMutation()
        {
            var source = AssetDatabase.LoadAssetAtPath<LevelSO>("Assets/Match3/Levels/Level_D.asset");
            var draft = LevelDraftUnitySampleAdapter.FromLevelSO(source, "Coral_Rescue", 17);
            var target = ScriptableObject.CreateInstance<LevelSO>();
            try
            {
                target.width = 77; target.height = 66; target.moveAmount = 55; target.targetScore = 44;
                target.goalType = LevelSO.GoalType.Score;
                target.levelGridPositionList = new List<LevelSO.LevelGridPosition>();
                target.gemList = new List<GemSO>(source.gemList);
                var originalCells = target.levelGridPositionList;
                draft.goals = draft.goals.Concat(new[] { new GoalDraft { goalId = "goal.secondary", targetId = "sample.score", targetCount = 9 } }).ToArray();
                Assert.Throws<System.NotSupportedException>(() => LevelDraftUnitySampleAdapter.ApplyToLevelSO(draft, target));
                Assert.That(target.width, Is.EqualTo(77)); Assert.That(target.height, Is.EqualTo(66));
                Assert.That(target.moveAmount, Is.EqualTo(55)); Assert.That(target.targetScore, Is.EqualTo(44));
                Assert.That(target.levelGridPositionList, Is.SameAs(originalCells));

                draft = LevelDraftUnitySampleAdapter.FromLevelSO(source, "Coral_Rescue", 17);
                draft.goals[0].targetId = "sample.glass";
                draft.goals[0].targetCount = 999;
                Assert.Throws<System.NotSupportedException>(() => LevelDraftUnitySampleAdapter.ApplyToLevelSO(draft, target));
                Assert.That(target.width, Is.EqualTo(77)); Assert.That(target.levelGridPositionList, Is.SameAs(originalCells));
            }
            finally { Object.DestroyImmediate(target); }
        }

        [Test]
        public void PinnedSdkAdapterUsesTheEngineSolverForAPlainBoard()
        {
            var draft = new LevelDraft
            {
                width = 3,
                height = 3,
                activeMask = Enumerable.Repeat(true, 9).ToArray(),
                cells = new[]
                {
                    SdkCell(0, 0, "A"), SdkCell(0, 1, "A"), SdkCell(0, 2, "B"),
                    SdkCell(1, 0, "B"), SdkCell(1, 1, "A"), SdkCell(1, 2, "A"),
                    SdkCell(2, 0, "B"), SdkCell(2, 1, "A"), SdkCell(2, 2, "B")
                },
                goals = new[] { new GoalDraft { goalId = "goal.primary", targetId = "sample.score", targetCount = 1 } }
            };
            var adapter = new Match3SdkLevelDraftAdapter(id => id == "A" ? 1 : 2);
            var result = adapter.AnalyzeLegalSwaps(draft);
            Assert.That(result.resultStatus, Is.EqualTo("SDK_REFERENCE_ONLY"));
            Assert.That(result.engineStatus, Is.EqualTo("BLOCKED_ENG_M24"));
            Assert.That(result.legalSwapCandidates.Any(move =>
                move.startRow == 0 && move.startColumn == 2 && move.endRow == 1 && move.endColumn == 2), Is.True);
            Assert.That(result.legalSwapCandidates.Any(move => move.matchedSlotCount >= 3), Is.True);
        }

        [Test]
        public void PinnedSdkAdapterRejectsSemanticsOutsideItsCurrentContract()
        {
            var draft = NewDraft();
            draft.cells[0].obstacleId = "sample.glass";
            draft.cells[0].obstacleDurability = 1;
            var adapter = new Match3SdkLevelDraftAdapter(_ => 1);
            Assert.Throws<System.NotSupportedException>(() => adapter.AnalyzeLegalSwaps(draft));
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

        private static CellDraft SdkCell(int row, int column, string itemId)
        {
            return new CellDraft { row = row, column = column, layer = 0, active = true, contentId = itemId };
        }

        private static CellDraft CloneCell(CellDraft cell)
        {
            return new CellDraft
            {
                row = cell.row, column = cell.column, layer = cell.layer, active = cell.active,
                locked = cell.locked, contentId = cell.contentId, obstacleId = cell.obstacleId,
                obstacleDurability = cell.obstacleDurability, lockDurability = cell.lockDurability,
                specialId = cell.specialId
            };
        }

        private static void SetPrivateField(object instance, string fieldName, object value)
        {
            typeof(Match3Bot).Assembly.GetType(instance.GetType().FullName)
                .GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic).SetValue(instance, value);
        }
    }
}
