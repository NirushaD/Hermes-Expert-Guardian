"""Real delayed-loopback HTTP transport through installed Hermes, no real credentials.

Runs in a temporary profile. An outbound socket guard refuses non-loopback destinations.
The host may retry transport requests; Guardian still permits one logical consultation.
"""
import argparse
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--runtime', required=True)
parser.add_argument('--output', type=Path, required=True)
options = parser.parse_args()
workspace = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(workspace))
sys.path.insert(0, options.runtime)
sys.dont_write_bytecode = True


class DelayedEndpoint(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))))
        self.requests.append(body)
        # Headers arrive only after the client's five-second request budget.
        time.sleep(7)
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'{}')
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *args):
        pass


with tempfile.TemporaryDirectory(dir=workspace / '.reference') as scratch, ExitStack() as stack:
    os.environ['HERMES_HOME'] = scratch
    os.environ['HERMES_DISABLE_DOTENV'] = '1'
    # Eliminate inherited provider configuration in this disposable test process.
    for key in list(os.environ):
        if any(part in key.upper() for part in ('API_KEY', 'AUTH_TOKEN', 'BEARER', 'OPENAI',
                                                'ANTHROPIC', 'OPENROUTER', 'AUXILIARY_', 'PROXY')):
            os.environ.pop(key, None)
    server = ThreadingHTTPServer(('127.0.0.1', 0), DelayedEndpoint)
    server.daemon_threads = True
    stack.callback(server.server_close)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stack.callback(server.shutdown)
    base = f'http://127.0.0.1:{server.server_port}/v1'
    original_connect = socket.socket.connect

    def loopback_only(sock, address):
        if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
            raise AssertionError('Non-loopback transport refused by test harness')
        return original_connect(sock, address)

    stack.enter_context(patch.object(socket.socket, 'connect', loopback_only))
    # The selected interpreter already contains Hermes dependencies. Suppress
    # launcher/update/environment management only; no transport or timeout code
    # is mocked, and the default profile is never adopted for this scratch root.
    stack.enter_context(patch('hermes_cli.venv_sync.prepare_launch', return_value=None))
    stack.enter_context(patch('pm.environments.activate_dependencies', return_value=None))
    stack.enter_context(patch('hermes_cli._early_recovery.recover_if_needed', return_value=None))
    stack.enter_context(patch('hermes_cli._early_recovery.restore_interrupted_pull', return_value=False))
    from agent import auxiliary_client as ac
    from agent.plugin_llm import PluginLlm
    from guardian.service import Guardian
    from guardian.state import Store

    logical_calls = []
    # Inject only the test destination. Host request planning, HTTP client,
    # actual read timeout and exception/retry paths remain real.
    def caller(**kwargs):
        logical_calls.append(1)
        response = ac.call_llm(task='guardian_expert', provider='custom', model='public-timeout-fixture',
                               base_url=base, api_key='synthetic-loopback-only', timeout=5,
                               max_tokens=64, messages=kwargs['messages'])
        return 'custom', 'public-timeout-fixture', response

    stack.enter_context(patch('agent.plugin_llm._resolve_task_ownership',
                              return_value=({'guardian_expert'}, set())))
    llm = PluginLlm(plugin_id='hermes-expert-guardian', sync_caller=caller)
    settings = {'mode': 'enforce', 'expert_enabled': True, 'expert_timeout': 5}
    guardian = Guardian(Store(Path(scratch) / 'guardian.sqlite3'), lambda k, d: settings.get(k, d), llm)
    arguments = {'path': 'public-fixture.txt'}
    for _ in range(2):
        guardian.post('read_file', arguments, session_id='transport', status='error',
                      result={'error': 'Synthetic missing resource'})
    item = guardian.view('transport')['incidents'][0]
    guardian.prepare('transport', item['id'], 'Public synthetic local timeout fixture', 'Stop safely')
    item = guardian.view('transport')['incidents'][0]
    started = time.monotonic()
    outcome = guardian.send('transport', item['id'], item['packet_hash'])
    elapsed = time.monotonic() - started
    record = guardian.view('transport')['incidents'][0]
    assert DelayedEndpoint.requests, 'No real HTTP request reached the loopback endpoint'
    assert outcome == 'ESCALATE_TO_USER' and record.get('expert_failure') == 'timeout', record
    assert record['escalations'] == 1 and len(logical_calls) == 1
    assert record.get('advice') is None
    assert guardian.pre('read_file', arguments, session_id='transport')['action'] == 'block'
    try:
        guardian.send('transport', item['id'], item['packet_hash'])
    except ValueError:
        pass
    else:
        raise AssertionError('Consultation repeated after transport timeout')
    for request in DelayedEndpoint.requests:
        assert 'tools' not in request and len(request['messages']) == 2
    report = dict(result='pass', transport='real delayed loopback HTTP via installed Hermes',
                  delay_seconds=7, request_timeout_seconds=5, elapsed_seconds=round(elapsed, 2),
                  logical_consultations=len(logical_calls), host_http_attempts=len(DelayedEndpoint.requests),
                  state=outcome, expert_failure=record['expert_failure'], retries_blocked=True,
                  repeated_consultation_refused=True, non_loopback_sockets_refused=True,
                  real_credentials_used=False, production_profile_modified=False)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
