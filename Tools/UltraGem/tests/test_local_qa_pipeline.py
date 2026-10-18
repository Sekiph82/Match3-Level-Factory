from __future__ import annotations
import tempfile
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local_qa_pipeline import inspect_python_sources,run_python_local_qa

class LocalQaPipelineTests(unittest.TestCase):
    def test_actual_qa_run_without_ci_network_or_build(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'sample.py').write_text('VALUE=123\n',encoding='utf-8')
            (root/'tests').mkdir()
            (root/'tests'/'test_sample.py').write_text(
                'import unittest\nfrom sample import VALUE\nclass Smoke(unittest.TestCase):\n def test_value(self): self.assertEqual(VALUE,123)\n',encoding='utf-8')
            out=run_python_local_qa(root,timeout_seconds=20)
            self.assertEqual(out['resultStatus'],'LOCAL_QA_SUCCESS')
            self.assertEqual(out['testProcessExitCode'],0)
            self.assertFalse(out['hostUnityCompiled'])
            self.assertFalse(out['buildProduced'])
            self.assertFalse(out['releaseAuthorized'])
            self.assertFalse(out['subprocessTimedOut'])
            self.assertTrue(out['sourceScan']['allSourcesParsed'])
    def test_parse_syntax_error_rejected_before_test_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'bad.py').write_text('def broken(:\n',encoding='utf-8')
            r=run_python_local_qa(root)
            self.assertEqual(r['resultStatus'],'LOCAL_QA_FAILURE')
            self.assertFalse(r['testsExecuted'])
    def test_bounded_timeout_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'ok.py').write_text('X=1\n',encoding='utf-8')
            (root/'tests').mkdir()
            (root/'tests'/'test_hang.py').write_text(
                'import time, unittest\nclass Slow(unittest.TestCase):\n def test_slow(self): time.sleep(10)\n',encoding='utf-8')
            r=run_python_local_qa(root,timeout_seconds=5)
            self.assertEqual(r['resultStatus'],'LOCAL_QA_UNKNOWN_TIMEOUT')
            self.assertTrue(r['subprocessTimedOut'])
            self.assertIsNone(r['testProcessExitCode'])
            with self.assertRaises(ValueError):run_python_local_qa(root,timeout_seconds=0)

if __name__=='__main__':unittest.main()
