"""Use own prior B-DATA live matrix; inspect real browser display functions, no response mocks."""
import shutil
import check_boss_static_api as api
from check_boss_static_readmission import extend

OUT=api.ROOT/'artifacts/single-deck-qa/bdata1r3'
def followup(s,catalog,file,write,endpoint):
 extend(s,catalog,file,write,endpoint)
 # Read actual server metadata, then exercise the modules served by this isolated API.
 _,wire=s.call(endpoint)
 page=s.api_browser_context.new_page()
 page.goto(s.base+'/editor/');page.wait_for_timeout(1200)
 result=page.evaluate('''async fields => {
  const labels=await import('/editor/display-labels.js');
  const registry=await import('/editor/registered-messages.js');
  return {size:registry.REGISTERED_MESSAGES.size,
   prepared:labels.koreanText('보스 속성 준비 필요','일반 안내'),
   fields:fields.flatMap(f=>['source','note'].map(key=>({field:f.key,key,raw:f[key],
    registered:labels.isRegisteredMessage(f[key]),
    friendly:labels.friendlyServerMessage(f[key]),korean:labels.koreanText(f[key],'상세 미확인')})))};
 }''',wire['fields'])
 s.save('actual-browser-metadata',result)
 s.check('browser registered preparation diagnostic and count',result['size']==213 and result['prepared']=='보스 속성 준비 필요')
 for item in result['fields']:
  s.check('browser internal '+item['field']+'.'+item['key']+' not displayed',not item['registered'] and item['friendly']=='요청을 처리하지 못했습니다.' and item['korean']=='상세 미확인',item)
 s.check('normal editor body has no internal field memo',all(item['raw'] not in page.locator('body').inner_text() for item in result['fields']))
 page.close()

if __name__=='__main__':
 # Context is created by our existing own harness; expose it to this additional check.
 api.OUT=OUT
 baseline=OUT/'unchanged-api-baseline'
 shutil.copytree(api.ROOT/'src/Nikke.Api/bin/Release/net10.0',baseline,dirs_exist_ok=True)
 from playwright.sync_api import Browser
 previous=Browser.new_context
 def context(browser,*args,**kwargs):
  created=previous(browser,*args,**kwargs)
  api.ChargeSession.api_browser_context=created
  return created
 Browser.new_context=context
 raise SystemExit(api.main(product='e21b774 on 020a6d2',baseline=baseline,extension=followup))
