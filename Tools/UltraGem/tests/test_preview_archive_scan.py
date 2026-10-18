"""Actual ZIP byte-integrity regression for LFX-M09-010 (no extraction)."""
from __future__ import annotations
import hashlib
import io
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from preview_archive_scan import scan_preview_archive


class PreviewArchiveScanTests(unittest.TestCase):
    def zipbytes(self, files, *, method=zipfile.ZIP_DEFLATED):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', compression=method) as z:
            for name, data in files.items():
                z.writestr(name, data)
        return out.getvalue()

    def entry(self, path, raw, kind='LEVEL_JSON', rights='REFERENCE_ONLY'):
        return {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'sizeBytes':len(raw),
                'kind':kind, 'rightsStatus':rights}

    def fixture(self):
        data = b'{"level":1,"profile":"Coral_Rescue"}'
        art = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="2"/></svg>'
        files={'levels/demo.json':data,'media/neutral.svg':art}
        declared=[self.entry('levels/demo.json',data),self.entry('media/neutral.svg',art,'MEDIA','OWNER_ORIGINAL')]
        return files, declared

    def test_real_zip_bytes_all_hashes_paths_and_formats(self):
        files, declared = self.fixture()
        zipped=self.zipbytes(files)
        actual=scan_preview_archive(zipped,declared)
        self.assertEqual(actual['fileCount'],2)
        self.assertTrue(actual['runtimePackInspected'])
        self.assertFalse(actual['legalRightsIndependentlyVerified'])
        self.assertFalse(actual['signedReleaseVerified'])
        self.assertFalse(actual['productionReleaseAuthorized'])
        self.assertEqual(actual['engineStatus'],'BLOCKED_ENG_M24')
        self.assertEqual(actual,scan_preview_archive(zipped,list(reversed(declared))))
        self.assertEqual(actual['archiveSha256'],hashlib.sha256(zipped).hexdigest())

    def test_unknown_extra_missing_mismatched_and_case_rename_fail(self):
        files,declared=self.fixture()
        alternatives=[
            ({**files,'tools/execute.py':b'print(1)'},declared),
            ({'levels/demo.json':files['levels/demo.json']},declared),
            ({**files,'media/neutral.svg':files['media/neutral.svg']+b'x'},declared),
            ({**files,'Levels/demo.json':files['levels/demo.json']},declared),
        ]
        for f,d in alternatives:
            with self.subTest(paths=sorted(f)),self.assertRaises(ValueError):
                scan_preview_archive(self.zipbytes(f),d)

    def test_duplicate_json_properties_and_secrets_fail_closed(self):
        for invalid in (b'{"x":1,"x":2}',b'{"api_key":"abc"}',b'not JSON',b'{"x":'):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):
                scan_preview_archive(self.zipbytes({'levels/bad.json':invalid}),
                                     [self.entry('levels/bad.json',invalid)])

    def test_xml_external_script_entity_and_unlicensed_media_fail(self):
        for blob in (b'<svg xmlns="http://www.w3.org/2000/svg"><script>evil</script></svg>',
                     b'<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///x"/></svg>',
                     b'<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg/>'):
            with self.subTest(blob=blob[:40]),self.assertRaises(ValueError):
                scan_preview_archive(self.zipbytes({'media/file.svg':blob}),
                  [self.entry('media/file.svg',blob,'MEDIA','OWNER_ORIGINAL')])
        blob=b'<svg xmlns="http://www.w3.org/2000/svg"/>'
        with self.assertRaises(ValueError):
            scan_preview_archive(self.zipbytes({'media/file.svg':blob}),
                       [self.entry('media/file.svg',blob,'MEDIA','UNLICENSED')])

    def test_symlink_and_decompression_bomb_rejected(self):
        payload=b'large-but-highly-compressible'*2000
        with self.assertRaisesRegex(ValueError,'ratio'):
            scan_preview_archive(self.zipbytes({'levels/z.json':payload}),
                            [self.entry('levels/z.json',payload)])
        sym=zipfile.ZipInfo('levels/link.json')
        sym.create_system=3
        sym.external_attr=(0o120777<<16)
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            z.writestr(sym,b'{}')
        with self.assertRaisesRegex(ValueError,'symbolic'):
            scan_preview_archive(buffer.getvalue(),[self.entry('levels/link.json',b'{}')])

    def test_no_side_effects_bad_zip_and_unsupported_rights(self):
        files,declared=self.fixture()
        original=dict(files)
        with self.assertRaises(ValueError):
            scan_preview_archive(b'broken',declared)
        self.assertEqual(original,files)
        with self.assertRaises(ValueError):
            scan_preview_archive(self.zipbytes(files),declared+[self.entry('tests/proof.xml',b'1')])

if __name__=='__main__': unittest.main()
