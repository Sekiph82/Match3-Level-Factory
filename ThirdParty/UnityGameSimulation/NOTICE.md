# Unity Game Simulation Match-3 sample intake

Source: `Unity-Technologies/Game-Simulation-Match-3-Sample`
Pinned source commit: `7a77506428e699f5bce8ab5e2c1bc3d1f3a966a7`
License: Unity Companion License for Unity-dependent projects; see `LICENSE.md`.

This project imports the Level Editor scene, its referenced LevelSO, gem and grid
scripts, bot, visual/runtime dependencies, prefabs, levels, textures, and required
scene assets from `Assets/Match3`. The exact upstream `Match3Bot.cs`, `LevelSO.cs`,
and `GameScene_Match3_LevelEditor.unity` are retained. `LevelEditor.cs` and
`Match3Visual.cs` were narrowly adapted to remove CodeMonkey utility calls while
preserving Unity-native camera, coroutine, and legacy animation behavior.

The upstream `Grid.cs` was not copied: it contains CodeMonkey utility code whose
file-level license was not established. `Assets/Match3/Scripts/Grid.cs` is a
small original Unity-native replacement. The upstream CodeMonkey subtree and
unneeded sample game scene/UI/analytics code were excluded. No sample art was
changed. Source blob IDs for each imported file are recorded in
`source-manifest.json`; local changes are identified there as adaptations.

This is an editor/runtime prototype. Unity sample mechanics and Match3Bot are
reference-only and do not establish MATCH3_ENGINE rule authority or parity.
