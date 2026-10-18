"""LFX-M07-005 fail-closed Unity Editor assembly static firewall tests."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from unity_firewall import inspect_assembly_firewall, inspect_local_project


def good():
    a = {
        "Assets/Match3/Match3.Reference.asmdef": {"name":"Match3.Reference", "defineConstraints":["UNITY_EDITOR"], "autoReferenced":False},
        "Assets/Match3Factory/Core/Match3Factory.Core.asmdef": {"name":"Match3Factory.Core", "includePlatforms":["Editor"]},
        "Assets/Match3Factory/Editor/Match3Factory.Editor.asmdef": {"name":"Match3Factory.Editor", "includePlatforms":["Editor"], "references":["Match3.Reference"]},
        "Assets/Match3Factory/SDKBridge/Match3Factory.SDKBridge.asmdef": {"name":"Match3Factory.SDKBridge", "includePlatforms":["Editor"]},
        "Assets/Match3Factory/Tests/Editor/Match3Factory.Editor.Tests.asmdef": {"name":"Match3Factory.Editor.Tests", "includePlatforms":["Editor"],"autoReferenced":False},
        "Assets/Match3Factory/Tests/PlayMode/Match3Factory.PlayMode.Tests.asmdef": {"name":"Match3Factory.PlayMode.Tests","defineConstraints":["UNITY_EDITOR"],"autoReferenced":False},
    }
    scripts = [
        "Assets/Match3/Scripts/GemSO.cs",
        "Assets/Match3Factory/Core/LevelDraft.cs",
        "Assets/Match3Factory/Editor/LevelDraftStudioWindow.cs",
        "Assets/Match3Factory/SDKBridge/Match3SdkLevelDraftAdapter.cs",
        "Assets/Match3Factory/Tests/Editor/LevelDraftIntegrationTests.cs",
        "Assets/Match3Factory/Tests/PlayMode/SampleBotPlayModeTests.cs",
    ]
    return a, scripts


class UnityFirewallTests(unittest.TestCase):
    def test_all_six_known_assemblies_editor_only(self):
        a,paths=good()
        report=inspect_assembly_firewall({p:json.dumps(d) for p,d in a.items()},paths)
        self.assertEqual(report['protectedAssemblyCount'],6)
        self.assertEqual(report['protectedScriptCount'],6)
        self.assertEqual(report['findings'],[])
        self.assertFalse(report['actualWindowsPlayerBuildPerformed'])
        self.assertFalse(report['releaseAuthorized'])
    def test_changing_any_editor_only_assembly_blocks(self):
        a,paths=good()
        path='Assets/Match3Factory/Core/Match3Factory.Core.asmdef'
        a[path].pop('includePlatforms')
        r=inspect_assembly_firewall({p:json.dumps(d) for p,d in a.items()},paths)
        self.assertIn('PROTECTED_ASSEMBLY_COMPILABLE_IN_PLAYER',{x['code'] for x in r['findings']})
        self.assertEqual(r['resultStatus'],'STATIC_FIREWALL_BLOCKED')
    def test_unowned_script_and_runtime_reference_blocked(self):
        a,paths=good()
        paths.append('Assets/Match3Factory/Unknown/LooseScript.cs')
        a['Assets/UnrelatedGame/Runtime.asmdef']={'name':'Game.Runtime','references':['Match3.Reference']}
        r=inspect_assembly_firewall({p:json.dumps(d) for p,d in a.items()},paths)
        self.assertIn('UNPROTECTED_EDITOR_SCRIPT',{x['code'] for x in r['findings']})
        self.assertIn('RUNTIME_ASSEMBLY_REFERENCES_EDITOR',{x['code'] for x in r['findings']})
    def test_project_file_read_no_mutation(self):
        a,paths=good()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for path, definition in a.items():
                f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(definition))
            for path in paths:
                f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('public class Empty {}')
            (root/'Assets'/'Match3Factory'/'Previews').mkdir(exist_ok=True)
            original=(root/'Assets'/'Match3Factory'/'Core'/'LevelDraft.cs').read_bytes()
            self.assertEqual(inspect_local_project(root)['findings'],[])
            self.assertEqual((root/'Assets'/'Match3Factory'/'Core'/'LevelDraft.cs').read_bytes(),original)
    def test_symlinks_and_duplicate_assembly_names_fail(self):
        a,paths=good()
        k='Assets/Match3Factory/SDKBridge/Match3Factory.SDKBridge.asmdef'
        a[k]['name']='Match3Factory.Core'
        with self.assertRaises(ValueError):
            inspect_assembly_firewall({p:json.dumps(d) for p,d in a.items()},paths)
        a,paths=good()
        with self.assertRaises(ValueError):
            inspect_assembly_firewall({p:json.dumps(d) for p,d in a.items()},['Assets/Match3/../escape.cs'])

if __name__=='__main__':unittest.main()
