import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from neutral_svg_preview import render_preview_svg,verify_scaling_contract
from theme_contract import PROFILES

class SvgEditorFixtureTests(unittest.TestCase):
    def test_editor_only_five_committed_svg_exports_are_source_identical(self):
        folder=ROOT.parents[1]/'Assets/Match3Factory/Editor/Previews/Neutral'
        self.assertEqual(sorted(p.name for p in folder.iterdir()),
                         sorted(profile+'.svg' for profile in PROFILES))
        for profile in PROFILES:
            path=folder/(profile+'.svg')
            self.assertEqual(path.read_text(encoding='utf-8'),render_preview_svg(profile))
            self.assertFalse(verify_scaling_contract(path.read_text(encoding='utf-8'),display_width=720)
                             ['unitySvgImporterValidated'])
            self.assertNotIn('href=',path.read_text(encoding='utf-8'))

if __name__=='__main__':unittest.main()
