import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from localization_qa import build_localization_qa
from theme_contract import PROFILES

class LocalizationQaTests(unittest.TestCase):
    def sample(self):
        return {'ui.level':{'en':'Level {level}','tr':'Bölüm {level}'},
                'ui.won':{'en':'Level finished','tr':'Bölüm bitti'}}
    def test_five_titles_use_explicit_unapproved_english_fallback(self):
        for profile in PROFILES:
            report=build_localization_qa(profile,self.sample())
            self.assertEqual(len(report['entries']),2)
            self.assertEqual(len(report['missingTranslations']),6)
            self.assertTrue(report['reviewRequired'])
            self.assertFalse(report['productionApproved'])
            self.assertFalse(report['storePriceInjected'])
            self.assertEqual(report,build_localization_qa(profile,self.sample()))
    def test_injection_bad_token_and_inconsistent_translations_fail(self):
        for text in ('=HYPERLINK("http://evil")','<script>alert(1)</script>',
                     'Price {price}','See https://example.com','Invalid {level'):
            data=self.sample();data['ui.level']['tr']=text
            with self.subTest(text=text),self.assertRaises(ValueError):
                build_localization_qa('Coral_Rescue',data)
        with self.assertRaises(ValueError):
            build_localization_qa('Coral_Rescue',{'fake':{'en':'missing dot'}})

if __name__=='__main__':unittest.main()
