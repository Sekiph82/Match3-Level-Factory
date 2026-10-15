using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace Match3Factory.Tests.PlayMode
{
    public sealed class SampleBotPlayModeTests
    {
        [UnityTest]
        public IEnumerator ActiveSampleBotPlaysThreeRealMovesThroughVisualStateLoop()
        {
            float previousScale = Time.timeScale;
            Time.timeScale = 8f;
            var level = ScriptableObject.CreateInstance<LevelSO>();
            var gems = new List<GemSO>();
            var root = new GameObject("PlayMode sample board");
            var cameraObject = new GameObject("PlayMode sample camera");
            var gemPrefab = MakePrefab("Gem prefab", true);
            var glassPrefab = MakePrefab("Glass prefab", false);
            var backgroundPrefab = MakePrefab("Background prefab", false);
            try
            {
                for (int i = 0; i < 4; i++) { var gem = ScriptableObject.CreateInstance<GemSO>(); gem.name = "Gem" + i; gems.Add(gem); }
                level.gemList = gems;
                level.width = 8; level.height = 8; level.moveAmount = 80; level.targetScore = 999999;
                level.goalType = LevelSO.GoalType.Score;
                level.levelGridPositionList = MakeBoard(level, gems);

                root.SetActive(false);
                var match3 = root.AddComponent<Match3>();
                var visual = root.AddComponent<Match3Visual>();
                var bot = root.AddComponent<Match3Bot>();
                Set(visual, "pfGemGridVisual", gemPrefab.transform);
                Set(visual, "pfGlassGridVisual", glassPrefab.transform);
                Set(visual, "pfBackgroundGridVisual", backgroundPrefab.transform);
                Set(visual, "cameraTransform", cameraObject.transform);
                Set(visual, "match3", match3);
                Set(bot, "match3", match3);
                Set(bot, "match3Visual", visual);
                Set(bot, "levelSO", level);
                root.SetActive(true);
                match3.SetLevelSO(level);
                Assert.That(match3.GetAllPossibleMoves(), Is.Not.Empty, "The real sample board needs legal moves before autoplay starts.");

                float deadline = Time.realtimeSinceStartup + 12f;
                while (match3.GetUsedMoveCount() < 3 && Time.realtimeSinceStartup < deadline) yield return null;
                Assert.That(match3.GetUsedMoveCount(), Is.GreaterThanOrEqualTo(3), "The bot must complete three live Update/coroutine move cycles.");
            }
            finally
            {
                Time.timeScale = previousScale;
                UnityEngine.Object.Destroy(root);
                UnityEngine.Object.Destroy(cameraObject);
                UnityEngine.Object.Destroy(gemPrefab);
                UnityEngine.Object.Destroy(glassPrefab);
                UnityEngine.Object.Destroy(backgroundPrefab);
                UnityEngine.Object.Destroy(level);
                foreach (var gem in gems) UnityEngine.Object.Destroy(gem);
            }
        }

        private static List<LevelSO.LevelGridPosition> MakeBoard(LevelSO level, List<GemSO> gems)
        {
            var random = new System.Random(431);
            var result = new List<LevelSO.LevelGridPosition>(level.width * level.height);
            var grid = new int[level.width, level.height];
            for (int y = 0; y < level.height; y++)
            for (int x = 0; x < level.width; x++)
            {
                int value;
                int attempts = 0;
                do { value = random.Next(gems.Count); attempts++; }
                while (attempts < 100 && ((x >= 2 && grid[x - 1, y] == value && grid[x - 2, y] == value) ||
                                          (y >= 2 && grid[x, y - 1] == value && grid[x, y - 2] == value)));
                grid[x, y] = value;
                result.Add(new LevelSO.LevelGridPosition { x = x, y = y, gemSO = gems[value] });
            }
            return result;
        }

        private static GameObject MakePrefab(string name, bool withSprite)
        {
            var root = new GameObject(name);
            if (withSprite)
            {
                var child = new GameObject("sprite");
                child.transform.SetParent(root.transform, false);
                child.AddComponent<SpriteRenderer>();
            }
            return root;
        }

        private static void Set(object target, string field, object value)
        {
            typeof(Match3Visual).Assembly.GetType(target.GetType().FullName)
                .GetField(field, BindingFlags.Instance | BindingFlags.NonPublic).SetValue(target, value);
        }
    }
}
