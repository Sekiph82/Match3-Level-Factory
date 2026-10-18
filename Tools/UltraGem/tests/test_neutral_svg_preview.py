import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from neutral_svg_preview import render_preview_svg,verify_scaling_contract
from theme_contract import PROFILES

class SvgPreviewTests(unittest.TestCase):
    def test_five_svg_prototypes_have_three_distinct_shapes_without_assets(self):
        for profile in PROFILES:
            svg=render_preview_svg(profile)
            doc=ET.fromstring(svg)
            self.assertEqual(doc.attrib['data-engine-status'],'BLOCKED_ENG_M24')
            self.assertNotIn('<script',svg)
            self.assertNotIn('<image',svg)
            self.assertNotIn('href=',svg)
            self.assertEqual(svg,render_preview_svg(profile))
            for width in (320,390,720):
                report=verify_scaling_contract(svg,display_width=width)
                self.assertFalse(report['rasterResamplingRequired'])
                self.assertFalse(report['unitySvgImporterValidated'])
                self.assertEqual(len(report['pieceKinds']),3)
    def test_malformed_or_external_svg_and_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):render_preview_svg('Unknown')
        example=render_preview_svg('Wonder_Pop')
        with self.assertRaises(ValueError):verify_scaling_contract(example.replace('BLOCKED_ENG_M24','CERTIFIED'),display_width=390)
        with self.assertRaises(ValueError):verify_scaling_contract(example.replace('</svg>','<script/> </svg>'),display_width=390)
        with self.assertRaises(ValueError):verify_scaling_contract(example,display_width=99)

if __name__=='__main__':unittest.main()
