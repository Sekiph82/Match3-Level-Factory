# Match3 Level Factory prototype

This Unity 6000.6.5f1 project is the R06 M00–M03 prototype. It contains a
LevelDraft editor, a LevelSO import/export bridge for the Unity sample, and a
bounded Python 3 UltraGem reference pipeline. All generated drafts are marked
`PROTOTYPE_ONLY`; MATCH3_ENGINE is the sole authority for final rules and
validation.

Open the project root in Unity and choose **Tools → Match3 Factory → Level Draft
Studio**. The window can paint a single-layer board, holes and glass, validate,
undo/redo, save/open LevelDraft JSON, and import/export supported sample
LevelSO assets. The sample adapter rejects semantics LevelSO cannot represent.

The Python environment is pinned to Python 3.12.10 in `Tools/UltraGem/.python-version`.
Install it with `python -m pip install -r Tools/UltraGem/requirements-lock.txt`,
then run the test suite with `python -m unittest discover -s Tools/UltraGem/tests -v`.
Run a small reference generation with:

```powershell
python Tools/UltraGem/factory_pipeline.py --rows 8 --columns 8 --colors 3 --seed 31 --candidates 1 --runs 2 --max-moves 20 --time-budget-seconds 60 --profile Coral_Rescue --output Artifacts/Prototype/example.json
```

The Unity EditMode tests use the installed Unity 6000.6.5f1 editor and can be
run with `-runTests -testPlatform editmode`. Source revisions, notices, and
file-level import hashes are recorded under `Tools/UltraGem/upstream` and
`ThirdParty/UnityGameSimulation`.

`ENG-M24` remains planned in MATCH3_ENGINE. The prototype does not claim Engine
compatibility, authoritative simulation parity, final difficulty, publishable
packs, or milestone acceptance. See the root `TASKS.md` for current blockers.
