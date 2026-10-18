"""Bounded no-CI local source QA runner (LFX-M07-005, source-only).

AST parses Python source and runs stdlib unit tests in a child subprocess with
no network request, no Actions/paid runner, no cloud credentials and no build
claim. This does NOT compile Windows Unity, create a Player or check binaries.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

MAX_PY_FILES=300
MAX_STDOUT=32_768


def inspect_python_sources(source_dir: Path) -> dict[str,Any]:
    if not source_dir.is_dir():
        raise ValueError('source_dir must be a local directory')
    files=sorted(source_dir.rglob('*.py'))
    if not files or len(files)>MAX_PY_FILES:
        raise ValueError('empty or excessive source inventory')
    failed=[]
    for p in files:
        if p.is_symlink() or p.stat().st_size>500_000:
            raise ValueError('symlink or oversized source refused')
        try:
            ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
        except (SyntaxError,UnicodeError) as exc:
            failed.append({'relativePath':p.relative_to(source_dir).as_posix(),
                           'errorClass':type(exc).__name__})
    return {'fileCount':len(files),'parseFailures':failed,'allSourcesParsed':not failed}


def run_python_local_qa(source_dir: Path, *, timeout_seconds: int = 120) -> dict[str,Any]:
    if type(timeout_seconds) is not int or not 5<=timeout_seconds<=600:
        raise ValueError('timeout must be 5..600 seconds')
    scan=inspect_python_sources(source_dir)
    if not scan['allSourcesParsed']:
        return {'resultStatus':'LOCAL_QA_FAILURE','engineStatus':'BLOCKED_ENG_M24',
                'sourceScan':scan,'testsExecuted':False,'releaseAuthorized':False}
    tests=source_dir/'tests'
    if not tests.is_dir():
        raise ValueError('tests directory missing')
    argv=[sys.executable,'-B','-m','unittest','discover','-s',str(tests),'-v']
    env=dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE']='1'
    env['PYTHONPATH']=str(source_dir)
    try:
        result=subprocess.run(argv,cwd=str(source_dir),env=env,capture_output=True,
                              text=True,errors='replace',timeout=timeout_seconds,check=False)
        status='LOCAL_QA_SUCCESS' if result.returncode==0 else 'LOCAL_QA_FAILURE'
        log=(result.stdout+'\n'+result.stderr)[-MAX_STDOUT:]
        timed_out=False
        returncode=result.returncode
    except subprocess.TimeoutExpired as exc:
        status='LOCAL_QA_UNKNOWN_TIMEOUT'
        log='QA child process exceeded hard wall-clock bound; UNKNOWN, never PASS.'
        timed_out=True
        returncode=None
    return {'resultStatus':status,'engineStatus':'BLOCKED_ENG_M24',
            'sourceScan':scan,'testsExecuted':True,'subprocessTimedOut':timed_out,
            'testProcessExitCode':returncode,'boundedLogTail':log,
            'hostUnityCompiled':False,'buildProduced':False,'releaseAuthorized':False}

if __name__=='__main__':
    output=run_python_local_qa(Path(__file__).resolve().parent)
    print(json.dumps(output,ensure_ascii=False,sort_keys=True))
    raise SystemExit(0 if output['resultStatus']=='LOCAL_QA_SUCCESS' else 1)
