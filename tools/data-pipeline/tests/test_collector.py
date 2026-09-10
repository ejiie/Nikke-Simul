import asyncio
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import collector

class Response:
    def __init__(self, status=200, payload=None, headers=None):
        self.status, self.payload, self.headers = status, payload, headers or {}
        self.ok = 200 <= status < 300
    async def json(self): return self.payload

class Client:
    def __init__(self, responses): self.responses, self.calls = responses, 0
    async def post(self, *args, **kwargs):
        response = self.responses[self.calls]; self.calls += 1
        return response

class CollectorTests(unittest.IsolatedAsyncioTestCase):
    def test_runtime_error_distinguishes_network_denial_from_browser_install_without_leaking_details(self):
        cases = [('net::ERR_NETWORK_ACCESS_DENIED', 'network_access_denied'),
                 ("Executable doesn't exist", 'browser_missing'),
                 ('net::ERR_NAME_NOT_RESOLVED', 'network'), ('unexpected failure', 'collector_failure')]
        for text, code in cases:
            failure = collector.runtime_failure(Exception(text + ' https://example.test/?token=synthetic-secret'))
            self.assertEqual(code, failure.code)
            self.assertNotIn('synthetic-secret', str(failure))
            self.assertNotIn('example.test', str(failure))
    def test_nickname_uses_the_selected_server_and_a_real_nonempty_string(self):
        payload={'code':0,'data':{'basic_info':{'area_id':'83','nickname':' 묑카엘 '}}}
        self.assertEqual('묑카엘',collector.profile_nickname(payload,83))
        self.assertIsNone(collector.profile_nickname(payload,81))
        for name in [None,0,{},'   ']:
            payload['data']['basic_info']['nickname']=name
            self.assertIsNone(collector.profile_nickname(payload,83))
    async def test_interactive_login_does_not_inject_api_headers(self):
        class Browser:
            async def new_context(self, **kwargs):
                self.options = kwargs
                return object()
        browser = Browser()
        await collector.create_login_context(browser)
        self.assertEqual({"locale":"en-US"}, browser.options)
    async def test_session_expiry_does_not_retry(self):
        client = Client([Response(payload={"code":300001})])
        with self.assertRaises(collector.CollectorError) as ctx: await collector.post(client, "Game/GetUserCharacters", {})
        self.assertEqual("reauth_required", ctx.exception.code); self.assertEqual(1, client.calls)
    async def test_retry_only_transient_error(self):
        client = Client([Response(429, headers={"retry-after":"0"}), Response(payload={"code":0,"data":{}})])
        records = []; await collector.post(client, "Game/GetUserCharacters", {}, records)
        self.assertEqual(2, client.calls); self.assertEqual(1, len(records)); self.assertNotIn("headers", records[0])
    async def test_long_rate_limit_returns_without_hammering_server(self):
        client = Client([Response(429, headers={"retry-after":"120"})])
        with self.assertRaises(collector.CollectorError) as ctx: await collector.post(client, "Game/GetUserCharacters", {})
        self.assertEqual("rate_limited", ctx.exception.code); self.assertEqual(1, client.calls)
    def test_missing_details_is_not_an_empty_success(self):
        with self.assertRaises(collector.CollectorError): collector.checked({"code":0,"data":{}}, "character_details")
    def test_private_and_upstream_errors_are_distinct(self):
        for value, code in [(1301002,"private"),(900000,"upstream")]:
            with self.assertRaises(collector.CollectorError) as ctx: collector.checked({"code":value})
            self.assertEqual(code, ctx.exception.code)
    @unittest.skipUnless(sys.platform == "win32", "Windows DPAPI only")
    def test_session_is_encrypted_and_round_trips(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.bin"; data = {"openId":"synthetic","state":{"cookies":[{"value":"synthetic-secret"}]}}
            collector.save_session(path, data)
            self.assertNotIn(b"synthetic-secret", path.read_bytes()); self.assertEqual(data, collector.load_session(path))

if __name__ == "__main__": unittest.main()
