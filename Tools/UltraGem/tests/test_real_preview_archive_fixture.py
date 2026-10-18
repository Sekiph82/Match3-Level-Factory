"""Source-real seed712 and five neutral SVG archive integrator, still no Engine release."""
from __future__ import annotations
import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from preview_archive_scan import scan_preview_archive

class RealPreviewArchiveFixtureTests(unittest.TestCase):
    def test_exact_seed712_and_five_editor_svg_files(self):
        seed=(ROOT.parents[1]/'Assets/Match3Factory/Tests/Fixtures/ultragem_seed_712_draft.json').read_bytes()
        draft=json.loads(seed.decode('utf-8'))
        self.assertEqual(draft['seed'],712)
        self.assertEqual(draft['validationStatus'],'PROTOTYPE_ONLY')
        svg_dir=ROOT.parents[1]/'Assets/Match3Factory/Editor/Previews/Neutral'
        names=['Coral_Rescue','Garage_Legends','Dino_Islands','The_Fractured_Realms','Wonder_Pop']
        files={'levels/ultragem_seed712.json':(seed,'LEVEL_JSON','REFERENCE_ONLY')}
        for name in names:
            data=(svg_dir/(name+'.svg')).read_bytes()
            files['media/'+name+'.svg']=(data,'MEDIA','OWNER_ORIGINAL')
        package=io.BytesIO()
        with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as out:
            for name,(data,*_) in sorted(files.items()):
                out.writestr(name,data)
        index=[{'path':name,'sha256':hashlib.sha256(data).hexdigest(),'sizeBytes':len(data),
               'kind':kind,'rightsStatus':rights}
               for name,(data,kind,rights) in files.items()]
        result=scan_preview_archive(package.getvalue(),index)
        self.assertEqual(result['fileCount'],6)
        self.assertEqual(len(result['verifiedFiles']),6)
        self.assertFalse(result['legalRightsIndependentlyVerified'])
        self.assertFalse(result['productionReleaseAuthorized'])
        self.assertEqual(result['engineStatus'],'BLOCKED_ENG_M24')
        self.assertEqual(result,scan_preview_archive(package.getvalue(),list(reversed(index))))

if __name__=='__main__':unittest.main()
