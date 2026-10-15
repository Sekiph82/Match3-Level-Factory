# LibraStack Match3 SDK API dependency

The Factory references, without copying, the Unity package
`com.chebanovdd.match3sdk` from `LibraStack/Match3-SDK` at commit
`771e62908056c2c5fa69937a52ca52ab589f19ea`, plus UniTask at
`2e993ff18f28c931602a07292df0b0804eebef99`. The pinned SDK package metadata
declares MIT; the package dependency is kept as a Git URL in
`Packages/manifest.json` so the source pin is explicit.

`Match3SdkLevelDraftAdapter` uses the SDK's public `IGameBoard<T>`,
`IGameBoardSolver<T>`, `HorizontalLineDetector<T>`, and
`VerticalLineDetector<T>` APIs. It handles a bounded one-layer board of plain
items and holes and rejects locks, obstacles and specials. This adapter is a
prototype bridge to the current SDK package and does not certify final
MATCH3_ENGINE parity. The local `com.match3.engine` runtime package currently
contains only an assembly marker, while ENG-M24 remains PLANNED.
