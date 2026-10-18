"""Offline LFX-M08-011 source tests; NOT Unity Editor or Engine acceptance."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vfx_storyboard import EFFECTS, create_vfx_storyboard


class VfxStoryboardTests(unittest.TestCase):
    def test_all_profiles_and_six_fx_are_deterministic_and_bounded(self):
        from neutral_preview_recipes import PALETTES
        self.assertEqual(len(EFFECTS), 6)
        for profile in PALETTES:
            for effect in EFFECTS:
                a = create_vfx_storyboard(profile, effect, reduced_motion=False)
                b = create_vfx_storyboard(profile, effect, reduced_motion=False)
                self.assertEqual(a, b)
                self.assertEqual(a['frameCount'], 12)
                self.assertEqual(a['engineReplayComparison'], 'NOT_RUN')
                self.assertFalse(a['releaseAuthorized'])
                self.assertFalse(a['isGameplayRuleSource'])
                self.assertEqual(len(a['storyboardSha256']), 64)
                self.assertLess(len(json.dumps(a)), 10000)
                for frame in a['frames']:
                    self.assertLessEqual(frame['atMs'], 900)
                    self.assertLessEqual(len(frame['elements']), 4)
                    for element in frame['elements']:
                        for k in ('x', 'y', 'size', 'opacityPermille'):
                            self.assertGreaterEqual(element[k], 0)
                            self.assertLessEqual(element[k], 1000)

    def test_reduced_motion_freezes_geometry_without_claiming_engine_parity(self):
        animated = create_vfx_storyboard('Wonder_Pop', 'portal', reduced_motion=False)
        reduced = create_vfx_storyboard('Wonder_Pop', 'portal', reduced_motion=True)
        self.assertEqual(reduced['frameCount'], 1)
        self.assertEqual(reduced['frameDurationMs'], 0)
        self.assertNotEqual(animated['storyboardSha256'], reduced['storyboardSha256'])
        self.assertEqual(animated['engineStatus'], 'BLOCKED_ENG_M24')
        for output in (animated, reduced):
            for key in ('winning', 'moves', 'cascadeCount', 'replayHash', 'engineValidated'):
                self.assertNotIn(key, output)

    def test_negative_inputs_and_caller_data_isolation(self):
        for invalid in (None, 123, '../portal', 'unknown', ''):
            with self.assertRaises((ValueError, TypeError)):
                create_vfx_storyboard('Coral_Rescue', invalid)
        for invalid in (None, True, 0, '../Coral_Rescue'):
            with self.assertRaises((ValueError, TypeError)):
                create_vfx_storyboard(invalid, 'combo')
        with self.assertRaises(ValueError):
            create_vfx_storyboard('Coral_Rescue', 'combo', reduced_motion='false')
        left = create_vfx_storyboard('Coral_Rescue', 'fish')
        ref = copy.deepcopy(left)
        left['frames'][0]['elements'][0]['size'] = 0
        self.assertEqual(create_vfx_storyboard('Coral_Rescue', 'fish'), ref)


if __name__ == '__main__':
    unittest.main()
