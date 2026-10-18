"""Proof scope and raw bytes cannot masquerade as independent Factory PASS."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from evidence_receipt import create_local_evidence_receipt, parse_nunit_xml, parse_python_unittest_log


def nunit(*, tamper=False):
    cases='<test-case result="Passed"/><test-case result="Skipped"/>'
    xml=f'<test-run total="2" passed="{2 if tamper else 1}" failed="0" skipped="1" inconclusive="0">{cases}</test-run>'
    return xml.encode('utf-8')


class EvidenceReceiptTests(unittest.TestCase):
    def test_actual_nunit_skips_are_partial_not_false_pass(self):
        r=parse_nunit_xml(nunit())
        self.assertEqual(r['scopeStatus'],'SCOPED_PARTIAL')
        self.assertEqual((r['passed'],r['skipped']),(1,1))
        self.assertFalse(r['independentAuditPass'])
        with self.assertRaises(ValueError):parse_nunit_xml(nunit(tamper=True))
        with self.assertRaises(ValueError):parse_nunit_xml(b'<!DOCTYPE x [<!ENTITY z "evil">]><test-run/>')
    def test_unittest_log_reports_omissions_without_full_suite_pass(self):
        log=b'INTENTIONAL NOT_RUN 6 legacy\n-----\nRan 141 tests in 30.644s\n\nOK\n'
        out=parse_python_unittest_log(log,excluded_tests=6)
        self.assertEqual(out['total'],141)
        self.assertEqual(out['excludedTests'],6)
        self.assertEqual(out['scopeStatus'],'SCOPED_PASS')
        self.assertFalse(out['fullSuiteCertified'])
        unknown=parse_python_unittest_log(b'...... interrupted',excluded_tests=6)
        self.assertEqual(unknown['scopeStatus'],'UNKNOWN_MISSING_TEST_SUMMARY')
        failed=parse_python_unittest_log(b'Ran 2 tests in 0.01s\nFAILED (failures=1)',excluded_tests=0)
        self.assertEqual(failed['scopeStatus'],'SCOPED_FAIL')
    def test_receipt_reproducibility_and_raw_hash(self):
        n=nunit()
        record={'name':'nunit/edit.xml','kind':'NUNIT_XML','bytes':n,'excludedTests':0}
        p={'name':'python/log.txt','kind':'PYTHON_UNITTEST_LOG',
           'bytes':b'Ran 3 tests in 0.1s\n\nOK\n','excludedTests':0}
        cmd=['python','-B','-m','unittest','discover']
        kw={'source_commit_sha':'a'*40,'command_argv':cmd,'artifacts':[record,p]}
        x=create_local_evidence_receipt(**kw)
        self.assertEqual(x,create_local_evidence_receipt(**dict(kw,artifacts=[p,record])))
        self.assertFalse(x['allListedScopesPassed'])
        self.assertFalse(x['independentAuditPerformed'])
        self.assertFalse(x['productionReleaseAuthorized'])
        self.assertEqual(len(x['receiptSha256']),64)
        self.assertTrue(all(v['excludeFromPlayer'] for v in x['files']))
        self.assertEqual(cmd,kw['command_argv'])
    def test_credentials_path_collisions_and_malformed_evidence_fail_closed(self):
        record={'name':'qa/result.xml','kind':'NUNIT_XML','bytes':nunit(),'excludedTests':0}
        kw=dict(source_commit_sha='b'*40,command_argv=['python'],artifacts=[record])
        for bad in ({**record,'name':'../x'},{**record,'bytes':b'Authorization: Bearer very-secret'},
                    {**record,'kind':'FAKE_PASS'},{**record,'excludedTests':3}):
            with self.subTest(bad=bad.get('name')),self.assertRaises(ValueError):
                create_local_evidence_receipt(**dict(kw,artifacts=[bad]))
        with self.assertRaises(ValueError):
            create_local_evidence_receipt(**dict(kw,artifacts=[record,{**record,'name':'QA/RESULT.XML'}]))
        with self.assertRaises(ValueError):
            create_local_evidence_receipt(**dict(kw,source_commit_sha='fake'))
    def test_realistic_47_case_nunit_explicit_skip(self):
        cases=''.join('<test-case result="Passed"/>' for _ in range(46)) + '<test-case result="Skipped"/>'
        raw=f'<test-run total="47" passed="46" failed="0" skipped="1" inconclusive="0">{cases}</test-run>'.encode()
        result=parse_nunit_xml(raw)
        self.assertEqual((result['total'],result['passed'],result['skipped']),(47,46,1))
        self.assertEqual(result['scopeStatus'],'SCOPED_PARTIAL')


if __name__=='__main__':unittest.main()
