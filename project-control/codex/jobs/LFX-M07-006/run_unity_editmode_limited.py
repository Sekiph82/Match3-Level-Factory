import datetime, json, os, sys, xml.etree.ElementTree as ET
from pathlib import Path
repo = Path(r'C:\Users\sekip\Desktop\GAMES\MATCH3 GAMES\Match3-Level-Factory')
evidence = repo / 'project-control/codex/jobs/LFX-M07-006'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
xml_path = evidence / f'unity-editmode-performance-{stamp}.xml'
log_path = evidence / f'unity-editmode-performance-{stamp}.log'
execution_path = evidence / f'unity-editmode-performance-{stamp}-execution.json'
unity = Path(r'C:\Program Files\Unity\Hub\Editor\6000.6.5f1\Editor\Unity.exe')
args = [str(unity), '-batchmode', '-nographics', '-projectPath', str(repo), '-runTests', '-testPlatform', 'EditMode', '-testFilter', 'Match3Factory.Tests.M07PerformanceBaselineTests.CapturesUnityEditorLevelDraftPerformanceBaseline', '-testResults', str(xml_path), '-logFile', str(log_path)]
sys.path.insert(0, str(repo / 'Tools/UltraGem'))
from hard_process_limits import run_limited_worker
result = run_limited_worker([sys.executable, str(repo / 'Tools/UltraGem/unity_limited_launcher.py'), *args], timeout_seconds=900, env={**os.environ, 'LFX_BENCHMARK_WAIT_FOR_LIMITS':'1', 'LFX_UNITY_RESULT_XML':str(xml_path), 'LFX_UNITY_LOG_FILE':str(log_path), 'LFX_UNITY_EXIT_GRACE_SECONDS':'8'}, memory_limit_bytes=4*1024**3, cpu_time_limit_seconds=600)
root = ET.parse(xml_path).getroot() if xml_path.exists() else None
summary = {key: root.attrib.get(key) for key in ('result','total','passed','failed','skipped','duration','asserts')} if root is not None else None
payload = {'argv':args,'wrapper':'unity_limited_launcher.py','launcherExitCode':result.returncode,'timedOut':result.timed_out,'cpuLimitExceeded':result.cpu_limit_exceeded,'runnerConfiguration':{'wallTimeTimeoutSeconds':900,'processAndJobCpuTimeLimitSeconds':600,'jobCommittedMemoryLimitBytes':4*1024**3,'cpuAffinityLogicalCores':1,'cpuRatePer10000MachineCycles':625},'limits':result.limits,'launcherStdout':result.stdout,'launcherStderr':result.stderr,'testResultsPath':str(xml_path),'unityLogPath':str(log_path),'xmlCreated':xml_path.exists(),'nunitResult':summary}
execution_path.write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'stamp':stamp,'execution':str(execution_path),'xml':str(xml_path),'log':str(log_path),'nunit':summary,'launcherExitCode':result.returncode,'timedOut':result.timed_out,'limits':result.limits},indent=2))
