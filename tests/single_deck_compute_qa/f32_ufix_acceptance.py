"""Independent U-FIX checks. Real API data; explicit network fault injection only."""
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from actual_stats import metric

def verify(page,call,check,save,shot,traffic,base,b,st,warm):
    def body():return page.locator('#stats-content').inner_text()
    def load(id,fault=False):
        page.evaluate('(id)=>localStorage.setItem("nikke-single-deck-experiment",id)',id)
        page.reload();page.wait_for_selector('body[data-ready="true"]');page.locator('[data-tab="stats"]').click()
        if fault:
            page.wait_for_function('document.querySelector("#stats-content").innerText.includes("compute API 미연결")',timeout=30000)
        elif id=='qa-nonexistent-experiment':
            page.wait_for_function('document.querySelector("#stats-content").innerText.includes("실험 상태를 불러오지 못했습니다")',timeout=30000)
        else:page.wait_for_selector('[data-comparison-state="no_baseline"]',timeout=30000)
    def cards():return page.locator('#stats-content .metric-card').evaluate_all('(els)=>Object.fromEntries(els.map(e=>[e.querySelector("span").textContent,e.querySelector("strong").textContent]))')
    check('U-FIX real warmup409 remains connected','compute API 미연결' not in body() and '실제 API 응답' in body())
    load(b['id']);c=cards();save('ufix-n1-cards',c)
    check('U-FIX n1 four exact cards',all(c[label]==format(int(st['team'][key]),',') for label,key in [('평균 팀 피해','mean'),('중앙값','median'),('P5','p5'),('P95','p95')]))
    check('U-FIX n1 SD and CI only unsupported',c['표본 표준편차']=='미지원' and c['평균 CI']=='미지원' and c['컷 초과확률']!='미지원')
    table=page.locator('.compute-member-table tbody tr').all_inner_texts();save('ufix-n1-members',table)
    check('U-FIX n1 five member values',len(table)==5 and all(any(all(format(int(m[k]),',') in row for k in ['mean','median','p5','p95']) for row in table) for m in st['members'].values()))
    check('U-FIX baseline400 connected no-baseline explanation','실제 API 응답' in body() and '비교 기준 없음' in body() and any(t['status']==400 and 'baseline_required' in str(t['response']) for t in traffic))
    shot(page,'ufix-n1')
    page.locator('[data-tab="raid"]').click()
    if page.locator('[name="seconds"]').count():page.locator('[name="seconds"]').fill('10')
    else:page.evaluate('sessionStorage.setItem("qa-regression-frames","600")')
    page.locator('[data-tab="stats"]').click()
    page.locator('#compute-runs').fill('2')
    with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as pending:page.locator('#compute-start').click()
    batch=pending.value.json()
    for _ in range(300):
        state=call('compute/experiments/'+batch['id']).json()
        if state['state'] in ['completed','failed','cancelled']:break
        page.wait_for_timeout(200)
    assert state['state']=='completed'
    stats=call('compute/experiments/'+batch['id']+'/statistics').json();rows=call('compute/experiments/'+batch['id']+'/results').json()['runs']
    metric(stats['team'],[r['teamDamage'] for r in rows],None)
    load(batch['id']);c=cards();save('ufix-n2',dict(batch=state,statistics=stats,runs=rows,cards=c))
    check('U-FIX n2 real independent statistics',stats['team']['n']==2 and stats['team']['meanCi'] is not None)
    # Compare numeric display with the API with tolerance limited to displayed precision.
    def number(s):return float(s.replace(',',''))
    ci=stats['team']['meanCi'];bounds=c['평균 CI'].split(' ~ ')
    check('U-FIX n2 CI and SD displayed matching',len(bounds)==2 and all(abs(number(s)-ci[k])<=max(1e-9,abs(ci[k])*1e-14) for s,k in zip(bounds,['lower','upper'])) and abs(number(c['표본 표준편차'])-stats['team']['sampleSd'])<=max(1e-9,abs(stats['team']['sampleSd'])*1e-14))
    shot(page,'ufix-n2')
    # Real unknown experiment 404 through ordinary recovery, not a mocked response.
    load('qa-nonexistent-experiment');save('ufix-404',dict(text=body()))
    check('U-FIX real404 remains connected','실제 API 응답' in body() and 'compute API 미연결' not in body() and any(t['status']==404 for t in traffic));shot(page,'ufix-404')
    load(batch['id'])
    # Force two invalid outgoing requests through the real validation endpoint.
    for label,modify in [('invalid-runs',lambda req:req.update(runs=0)),('missing-snapshot',lambda req:req.update(snapshotId='qa-missing-snapshot'))]:
        def alter(route):
            req=route.request.post_data_json;modify(req);route.continue_(post_data=json.dumps(req))
        page.route('**/api/compute/experiments',alter)
        with page.expect_response(lambda r:r.url.endswith('/api/compute/experiments') and r.request.method=='POST') as result:page.locator('#compute-start').click()
        response=result.value;page.wait_for_timeout(300);save('ufix-'+label,dict(status=response.status,response=response.json(),text=body()))
        check('U-FIX real4xx '+label+' connected',400<=response.status<500 and '실제 API 응답' in body() and 'compute API 미연결' not in body())
        page.unroute('**/api/compute/experiments',alter)
    # n0 is a direct presentation-boundary probe, explicitly NOT an actual API n0 batch.
    empty=page.evaluate('''async()=>{const m=await import('/editor/compute-adapter.js');return m.describeMetricStatistics({n:0,mean:null,median:null,p5:null,p95:null,sampleSd:null,meanCi:null,unsupportedReason:'no_valid_runs'});}''')
    save('ufix-n0-boundary',empty);check('U-FIX n0 boundary never invents values',all(empty[k].get('value') is None for k in ['mean','median','p5','p95','sampleSd']) and empty['meanCi']['lower'] is None)
    # Real local HTTP503 service represents an upstream outage. No product API claim.
    class Unavailable(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(503);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(b'{"message":"qa_injected_upstream_unavailable"}')
        def do_OPTIONS(self):
            self.send_response(204);self.send_header('Access-Control-Allow-Origin','*');self.send_header('Access-Control-Allow-Headers','*');self.end_headers()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Unavailable);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        def outage(route):route.continue_(url=f'http://127.0.0.1:{server.server_port}/api/compute/experiments/outage')
        page.route('**/api/compute/**',outage);load(batch['id'],True);page.wait_for_timeout(500);save('ufix-503',dict(text=body(),faultPort=server.server_port))
        check('U-FIX injected realHTTP503 shows disconnected','compute API 미연결' in body() and any(t['status']==503 for t in traffic));shot(page,'ufix-503');page.unroute('**/api/compute/**',outage)
    finally:server.shutdown();server.server_close();thread.join()
    def offline(route):route.abort('connectionrefused')
    page.route('**/api/compute/**',offline);load(batch['id'],True);save('ufix-transport',dict(text=body()))
    check('U-FIX injected transport shows disconnected','compute API 미연결' in body());shot(page,'ufix-transport');page.unroute('**/api/compute/**',offline)
    load(batch['id']);check('U-FIX recovery after network faults','실제 API 응답' in body() and 'compute API 미연결' not in body())
