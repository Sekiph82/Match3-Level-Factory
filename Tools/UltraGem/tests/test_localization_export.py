"""Actual UTF-8 locale bytes, SHA manifest, rights and fail-closed export gates."""
from __future__ import annotations
import hashlib
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from localization_export import export_localized_preview
from theme_contract import PROFILES


class LocalizationExportTests(unittest.TestCase):
    def sample(self):
        return {'ui.level': {'en':'Level {level}','tr':'Bölüm {level}'},
                'ui.won': {'en':'Level complete!','tr':'Bölüm tamamlandı!'}}

    def test_all_five_titles_export_five_locales_and_hash_exact_bytes(self):
        for profile in PROFILES:
            result=export_localized_preview(profile,self.sample(),{'ui.goal':'ref:Owner/original-001'})
            self.assertEqual(len(result['manifest']),5)
            self.assertEqual(len(result['bytesByPath']),5)
            self.assertEqual(result['engineStatus'],'BLOCKED_ENG_M24')
            self.assertFalse(result['productionExportAuthorized'])
            self.assertEqual(result,export_localized_preview(profile,self.sample(),{'ui.goal':'ref:Owner/original-001'}))
            for row in result['manifest']:
                payload=result['bytesByPath'][row['path']]
                self.assertEqual(row['sha256'],hashlib.sha256(payload).hexdigest())
                parsed=json.loads(payload)
                self.assertFalse(parsed['artworkRightsIndependentlyVerified'])
                self.assertEqual(parsed['profileId'],profile)
                if row['locale'] in ('de','fr','sw'):
                    self.assertEqual(row['fallbackCount'],2)
                if row['locale']=='tr':
                    self.assertIn('Bölüm',parsed['strings']['ui.level'])

    def test_wrong_slot_path_or_unapproved_translation_rejected(self):
        with self.assertRaises(ValueError):
            export_localized_preview('Coral_Rescue',self.sample(),{'ui.unknown':'ref:Owner/test-a'})
        with self.assertRaises(ValueError):
            export_localized_preview('Coral_Rescue',self.sample(),{'ui.goal':'ref:Owner/../secret'})
        with self.assertRaises(ValueError):
            export_localized_preview('Coral_Rescue',self.sample(),{'ui.goal':'https://example.com/unsafe'})
        data=self.sample();data['ui.level']['tr']='=CMD()'
        with self.assertRaises(ValueError):
            export_localized_preview('Wonder_Pop',data,{})

    def test_locale_without_english_rejected(self):
        with self.assertRaises(ValueError):
            export_localized_preview('Coral_Rescue',self.sample(),{},locales=('sw',))

if __name__=='__main__':unittest.main()
