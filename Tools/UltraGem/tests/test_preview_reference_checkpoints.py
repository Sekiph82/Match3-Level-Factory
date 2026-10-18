"""LFX-M08-007 isolated unit fixtures, NOT full donor or Engine replay tests."""
from __future__ import annotations
import copy
import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Isolated preview test fixture when this file is run outside the checkout.
# In the actual repository, always import the REAL pinned scoregames module.
if not (Path(__file__).resolve().parents[1] / "scoregames.py").is_file():
    stub = types.ModuleType("scoregames")
    stub.STAT_NAMES = (
        "score","ndestroyed","nunlocked","nstripe","nbomb","nzapper",
        "combo_22","combo_42","combo_44","combo_51","combo_52","combo_54","combo_55")
    sys.modules["scoregames"] = stub
from preview_reference_checkpoints import preview_reference_checkpoints, PINNED


class CheckpointPreviewTests(unittest.TestCase):
    def example(self):
        steps = [[0] * 13, [4,4] + [0] * 11, [18,14,2,1] + [0] * 9]
        run = {"completedRuns":1,"outcomes":["MOVE_LIMIT"],"runSeeds":[777],"steps":[steps]}
        return {
            "resultStatus":"REFERENCE_ONLY_UNVERIFIED",
            "engineStatus":"BLOCKED_ENG_M24",
            "sourceRepository":"JohannesBuchner/ultragem","sourceRevision":PINNED,
            "configuration":{"maxMoves":3},
            "referenceStatistics":[{
                "candidateIndex":0,
                "statistics":{p:copy.deepcopy(run) for p in ("worst","random","best","smart")}
            }]
        }

    def test_checkpoint_deltas_and_immutability(self):
        src = self.example()
        pristine = copy.deepcopy(src)
        output = preview_reference_checkpoints(src,candidate_index=0,policy="smart",run_index=0)
        self.assertEqual(src,pristine)
        self.assertEqual(output,preview_reference_checkpoints(src,candidate_index=0,policy="smart",run_index=0))
        self.assertEqual(output["checkpoints"][1]["deltaSincePriorCheckpoint"],
                         {"score":4,"ndestroyed":4})
        self.assertEqual(output["checkpoints"][2]["deltaSincePriorCheckpoint"],
                         {"score":14,"ndestroyed":10,"nunlocked":2,"nstripe":1})
        self.assertFalse(output["goalsOrWinProved"])
        self.assertFalse(output["releaseAuthorized"])
        self.assertTrue(output["lastMoveMayBeUnobserved"])
        self.assertEqual(output["engineStatus"],"BLOCKED_ENG_M24")

    def test_invalid_authority_never_claims_win(self):
        for change in ("fake_win","engine","revision"):
            source = self.example()
            if change == "fake_win":
                source["referenceStatistics"][0]["statistics"]["smart"]["outcomes"] = ["UNVERIFIED_WIN"]
            if change == "engine": source["engineStatus"] = "CERTIFIED"
            if change == "revision": source["sourceRevision"] = "unverified"
            with self.subTest(change=change), self.assertRaises(ValueError):
                preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)

    def test_boundaries_and_tamper_fails_closed(self):
        for change in ("backward","too_many","missing","duplicate","bad_metrics"):
            source = self.example()
            if change == "backward":
                source["referenceStatistics"][0]["statistics"]["smart"]["steps"][0][2][0] = 1
            if change == "too_many": source["configuration"]["maxMoves"] = 500
            if change == "missing": source["referenceStatistics"] = []
            if change == "duplicate":
                source["referenceStatistics"].append(copy.deepcopy(source["referenceStatistics"][0]))
            if change == "bad_metrics":
                source["referenceStatistics"][0]["statistics"]["smart"]["steps"][0][0].append(1)
            with self.subTest(change=change), self.assertRaises(ValueError):
                preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)
        for invalid in ("Expert", "../smart", None, 77):
            with self.assertRaises(ValueError):
                preview_reference_checkpoints(self.example(),candidate_index=0,policy=invalid,run_index=0)



class CheckpointCliTests(unittest.TestCase):
    def test_cli_reads_one_reference_run_and_rejects_duplicate_keys(self):
        import contextlib
        import io
        import json
        import tempfile
        from preview_reference_checkpoints import main
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "batch.json"
            source.write_text(json.dumps(CheckpointPreviewTests().example(), sort_keys=True), encoding="utf-8")
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                self.assertEqual(main(["--input", str(source), "--policy", "smart"]), 0)
            result = json.loads(capture.getvalue())
            self.assertEqual(result["donorOutcome"], "MOVE_LIMIT")
            self.assertFalse(result["releaseAuthorized"])
            source.write_text('{"resultStatus":"A","resultStatus":"B"}', encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--input", str(source)]), 2)

    def test_cli_limits_and_never_overwrites_source(self):
        import contextlib
        import io
        import json
        import tempfile
        from preview_reference_checkpoints import main
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "batch.json"
            original = json.dumps(CheckpointPreviewTests().example(), sort_keys=True)
            source.write_text(original, encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--input", str(source), "--candidate", "999"]), 2)
                self.assertEqual(main(["--input", str(source), "--run", "3"]), 2)
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            source.write_text("x" * 2_000_001, encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--input", str(source)]), 2)



if __name__ == "__main__":
    unittest.main()
