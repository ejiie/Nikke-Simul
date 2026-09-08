"""Integration test against an isolated NIKKE_TEST_FIXTURE backend on port 5181.

Requires a seeded synthetic snapshot (Nikke.SyncAudit), then tests browser and API behavior.
"""
import json
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5181"
ROOT = Path(__file__).resolve().parents[3]
fixture_path = ROOT / "artifacts/p01/synthetic-envelope.json"
original = fixture_path.read_text(encoding="utf-8")
checks = []

def request(path, method="GET", data=None, token=None, origin=None):
    headers = {"Content-Type":"application/json"}
    if token: headers["X-Nikke-Token"] = token
    if origin: headers["Origin"] = origin
    req = urllib.request.Request(BASE+"/api"+path, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

def finished(job_id):
    for _ in range(100):
        job = request("/sync-jobs/"+job_id)
        if job["status"] not in ("queued","running","cancelling"): return job
        time.sleep(.1)
    raise AssertionError("Job did not finish")

try:
    boot = request("/bootstrap")
    assert boot["testMode"]
    connection = boot["connections"][0]; token = boot["token"]
    account = connection["accountId"]
    before = request("/accounts/"+account+"/snapshot")
    for label, kwargs in [("missing_token",{}),("foreign_origin",{"token":token,"origin":"https://example.com"})]:
        try: request("/sync-jobs","POST",{"connectionId":connection["id"]},**kwargs)
        except urllib.error.HTTPError as error: assert error.code == 403
        else: raise AssertionError(label)
        checks.append(label)
    first = request("/sync-jobs","POST",{"connectionId":connection["id"]},token)
    second = request("/sync-jobs","POST",{"connectionId":connection["id"]},token)
    assert first["id"] == second["id"]; assert finished(first["id"])["status"] == "succeeded"; checks.append("duplicate_click")
    current = request("/accounts/"+account+"/snapshot")
    assert current["id"] != before["id"] and request("/snapshots/"+before["id"])["id"] == before["id"]; checks.append("immutable_history")
    incomplete = json.loads(original); incomplete["details"] = []
    fixture_path.write_text(json.dumps(incomplete),encoding="utf-8")
    failed = request("/sync-jobs","POST",{"connectionId":connection["id"]},token)
    assert finished(failed["id"])["errorCode"] == "validation_failed"
    assert request("/accounts/"+account+"/snapshot")["id"] == current["id"]; checks.append("failure_preserves_current")
    fixture_path.write_text(original,encoding="utf-8")
    cancelled = request("/sync-jobs","POST",{"connectionId":connection["id"]},token)
    request("/sync-jobs/"+cancelled["id"]+"/cancel","POST",{},token)
    assert finished(cancelled["id"])["status"] == "cancelled"
    assert request("/accounts/"+account+"/snapshot")["id"] == current["id"]; checks.append("cancel_preserves_current")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge",headless=True)
        page = browser.new_page(viewport={"width":1440,"height":1000})
        errors = []
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(BASE)
        page.get_by_role("heading",name="미등록 니케 101",exact=True).wait_for()
        assert "11.81%" in page.locator("#detail").inner_text()
        assert "검증용 데이터" in page.locator("body").inner_text(); checks.append("rendered_stored_equipment")
        page.get_by_role("combobox",name="머리 1줄 잠금",exact=True).select_option("locked")
        for _ in range(50):
            latest = request("/accounts/"+account+"/snapshot")
            if latest["characters"][0]["equipment"][0]["lines"][0]["lockState"] == "locked": break
            time.sleep(.1)
        else: raise AssertionError("Manual lock not saved")
        page.reload(); page.get_by_role("heading",name="미등록 니케 101",exact=True).wait_for()
        assert page.get_by_role("combobox",name="머리 1줄 잠금",exact=True).input_value() == "locked"; checks.append("manual_lock_reload")
        page.get_by_role("button",name="내 스펙 동기화",exact=False).click()
        for _ in range(80):
            state = request("/bootstrap"); job = state["jobs"][0]
            if job["status"] == "succeeded" and job["snapshotId"] != latest["id"]: break
            time.sleep(.1)
        else: raise AssertionError("Button sync failed")
        page.wait_for_timeout(1600)
        assert page.get_by_role("combobox",name="머리 1줄 잠금",exact=True).input_value() == "locked"; checks.append("button_sync_retains_manual")
        page.screenshot(path=str(ROOT/"artifacts/p01/ui-desktop.png"),full_page=True)
        page.set_viewport_size({"width":390,"height":844}); page.wait_for_timeout(200)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        page.screenshot(path=str(ROOT/"artifacts/p01/ui-mobile.png"),full_page=True); checks.append("mobile_no_overflow")
        assert not errors, errors; checks.append("no_browser_errors")
        browser.close()
finally:
    fixture_path.write_text(original,encoding="utf-8")
report = {"passed":len(checks),"checks":checks}
(ROOT/"artifacts/p01/api-ui-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report))
