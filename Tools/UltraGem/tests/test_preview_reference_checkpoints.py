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
        run = {"completedRuns":1,"outcomes":["MOVE_LIMIT"],"runSeeds":[0],
               "movesUsed":[3],"shuffles":[0],"steps":[steps]}
        return {
            "resultStatus":"REFERENCE_ONLY_UNVERIFIED",
            "engineStatus":"BLOCKED_ENG_M24",
            "sourceRepository":"JohannesBuchner/ultragem","sourceRevision":PINNED,
            "seed":43,
            "configuration":{
                "rows":6,"columns":6,"colors":3,
                "candidateCount":1,"runsPerPolicy":1,"maxMoves":3
            },
            "referenceStatistics":[{
                "candidateIndex":0,"seed":43,
                "initialBoard":{
                    "rows":6,"columns":6,
                    "cells":[{"row":r,"column":c,"type":1,"color":1,"status":0}
                             for r in range(6) for c in range(6)]
                },
                "statistics":{
                    p:dict(copy.deepcopy(run),runSeeds=[(43+104729+1009*i)%(2**31-1)])
                    for i,p in enumerate(("worst","random","best","smart"))
                }
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
        self.assertEqual(output["referencePreviewVersion"], 2)
        self.assertEqual(output["donorMovesUsed"], 3)
        self.assertTrue(output["checkpointsAreBeforeMove"])
        self.assertFalse(output["paddedFinalStatisticsPresent"])
        self.assertTrue(all(x["observedBeforeMove"] for x in output["checkpoints"]))
        self.assertTrue(all(not x["paddedFinalStatistics"] for x in output["checkpoints"]))
        self.assertTrue(output["initialBoardIsSeededDonorSetup"])
        self.assertFalse(output["boardAtCheckpointAvailable"])
        self.assertEqual(len(output["initialBoard"]["cells"]),36)
        self.assertEqual(output["initialBoardSha256"],
                         "10561542d92b047dca613cac4abbb5a5e5e30b23013794995362e9d7c0da41e8")

    def test_padded_final_statistics_are_not_real_move_frames(self):
        source = self.example()
        row = source["referenceStatistics"][0]["statistics"]["smart"]
        row["outcomes"] = ["NO_MOVES_AFTER_SHUFFLE_BUDGET"]
        row["movesUsed"] = [1]
        row["shuffles"] = [21]
        row["steps"][0][1] = [4, 4] + [0] * 11
        row["steps"][0][2] = [4, 4] + [0] * 11
        output = preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)
        self.assertFalse(output["checkpointsAreBeforeMove"])
        self.assertTrue(output["paddedFinalStatisticsPresent"])
        self.assertEqual(output["donorMovesUsed"],1)
        self.assertEqual(output["donorShuffles"],21)
        self.assertEqual([x["observedBeforeMove"] for x in output["checkpoints"]],
                         [True,False,False])
        self.assertEqual([x["beforeMove"] for x in output["checkpoints"]],[1,0,0])
        self.assertEqual([x["paddedFinalStatistics"] for x in output["checkpoints"]],
                         [False,True,True])
        self.assertFalse(output["goalsOrWinProved"])
        # The actual UltraGem _simulate_one() pads with the same final
        # score repeatedly. A drifting later slot is fabricated data.
        row["steps"][0][2] = [5,5] + [0] * 11
        with self.assertRaisesRegex(ValueError, "repeat one final score"):
            preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)

    def test_pinned_donor_disabled_after_locked_area_is_legal(self):
        # gemengine.InitialFillerDisable.apply writes type=-1 and color=0,
        # but deliberately leaves status from DoubleLock (0/2) unchanged.
        source = self.example()
        cells = source["referenceStatistics"][0]["initialBoard"]["cells"]
        cells[0].update({"type":-1,"color":0,"status":2})
        result = preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)
        self.assertEqual(result["initialBoard"]["cells"][0]["type"], -1)
        self.assertEqual(result["initialBoard"]["cells"][0]["status"], 2)
        self.assertFalse(result["boardAtCheckpointAvailable"])

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
        for corruption in ("moves_used","shuffle_claim","zero_moves_limit"):
            source = self.example()
            row = source["referenceStatistics"][0]["statistics"]["smart"]
            if corruption == "moves_used": row["movesUsed"] = [4]
            if corruption == "shuffle_claim": row["outcomes"] = ["NO_MOVES_AFTER_SHUFFLE_BUDGET"]
            if corruption == "zero_moves_limit": row["movesUsed"] = [0]
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)
        for corruption in ("candidate_seed","run_seed","dimensions","color_range","run_count"):
            source=self.example()
            record=source["referenceStatistics"][0]
            if corruption=="candidate_seed": record["seed"]+=1
            if corruption=="run_seed": record["statistics"]["smart"]["runSeeds"][0]+=1
            if corruption=="dimensions": source["configuration"]["rows"]=7
            if corruption=="color_range": record["initialBoard"]["cells"][0]["color"]=5
            if corruption=="run_count": source["configuration"]["runsPerPolicy"]=2
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                preview_reference_checkpoints(source,candidate_index=0,policy="smart",run_index=0)
        for corruption in ("duplicate_coordinate","unknown_type","wrong_count","disabled_locked"):
            source=self.example()
            cells=source["referenceStatistics"][0]["initialBoard"]["cells"]
            if corruption=="duplicate_coordinate": cells[1]["row"]=cells[0]["row"]; cells[1]["column"]=cells[0]["column"]
            if corruption=="unknown_type": cells[4]["type"]=99
            if corruption=="wrong_count": cells.pop()
            if corruption=="disabled_locked": cells[8].update({"type":-1,"color":2,"status":2})
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
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



    def test_optional_output_creates_only_new_project_relative_file(self):
        import contextlib
        import io
        import json
        import os
        import tempfile
        from preview_reference_checkpoints import main
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            source.write_text(json.dumps(CheckpointPreviewTests().example()), encoding="utf-8")
            previous_cwd = os.getcwd()
            try:
                os.chdir(directory)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["--input", str(source), "--output", "preview.json"]), 0)
                target = Path(directory) / "preview.json"
                before = target.read_text(encoding="utf-8")
                self.assertEqual(json.loads(before)["engineStatus"], "BLOCKED_ENG_M24")
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["--input", str(source), "--output", "preview.json"]), 2)
                    self.assertEqual(main(["--input", str(source), "--output", "../escape.json"]), 2)
                    self.assertEqual(main(["--input", str(source), "--output", str(source)]), 2)
                self.assertEqual(target.read_text(encoding="utf-8"), before)
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
