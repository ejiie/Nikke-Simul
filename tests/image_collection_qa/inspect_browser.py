"""Read-only image rendering check against a Q-IMG isolated API."""
import argparse
import json
from pathlib import Path
import uuid
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, required=True)
args = parser.parse_args()
assert args.port not in (5180, 5181)
run = Path(__file__).resolve().parents[2] / 'artifacts/image-collection-qa' / ('visual-' + uuid.uuid4().hex[:12])
run.mkdir(parents=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width':1400, 'height':1000})
    page.goto(f'http://127.0.0.1:{args.port}/editor/')
    page.wait_for_selector('body[data-ready="true"]')
    result = page.evaluate('''async()=>{
      const p=await (await fetch('/api/presentation')).json();
      const state=await (await fetch('/api/presentation/status')).json();
      const host=document.createElement('section');host.id='qimg-visual';
      host.style.cssText='background:white;padding:24px;width:1300px;color:black';
      document.body.append(host);
      const {mountAccountCards}=await import('/editor/local-lab-account.js');
      mountAccountCards(host,{characters:[],consoles:{},cubeLevels:{}},p);
      for(const kind of ['equipment','collection']){
        const row=p.supportDefinitions.find(x=>x.kindCode===kind);
        const label=document.createElement('p');label.textContent=kind+': '+row.displayName+' ('+row.definitionUid+')';host.append(label);
        const img=document.createElement('img');img.dataset.qimg=kind;img.src=row.imagePath;host.append(img);
      }
      const imgs=[...host.querySelectorAll('img')];
      for(const img of imgs){img.loading='eager';await img.decode();}
      return {status:state, syntheticAccount:true, images:imgs.map(x=>({path:new URL(x.src).pathname,width:x.naturalWidth,height:x.naturalHeight}))};
    }''')
    assert len(result['images']) == 27
    assert all(row['width'] > 0 and row['height'] > 0 for row in result['images'])
    page.locator('#qimg-visual').screenshot(path=str(run / 'cache-renderer.png'))
    (run / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    browser.close()
print(str(run))
