"""Backend-owned synthetic path/failure tests. No live CDN or account data."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import presentation_assets as p
import account_presentation_assets as account
import spec_presentation_assets as spec


def seed(root):
    out=root/'presentation'
    p.json_write(root/'calculation/current.json', {'id':'version'})
    p.json_write(root/'calculation/version/cube_effect_table.json', {})
    p.json_write(root/'game-catalog.json', {'optionSteps':{key:[.01] for _,key,_ in spec.OPTIONS}})
    for _,code,_,_ in account.CONSOLES:
        p.atomic(out/f'catalog/console-{code}.html', b'<meta property="og:image" content="https://static.dotgg.gg/nikke/items/mock.webp">')
        p.atomic(out/f'assets/consoles/{code}.webp', b'RIFF0000WEBPsynthetic')
    p.json_write(out/'catalog/equipment-official.json', {'records':[]})
    p.json_write(out/'catalog/favorite-map.json', {})
    return out


class ImageCatalogPaths(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{},clear=False);self.env.start()
        os.environ.pop('NIKKE_DATA_ROOT',None)
    def tearDown(self):self.env.stop();self.temp.cleanup()

    def test_root_precedence_and_legacy_default(self):
        with patch.object(p,'ROOT',self.root/'code'):
            self.assertEqual(self.root/'code/data/local',p.resolve_data_root())
            self.assertEqual(self.root/'external',p.resolve_data_root(output=self.root/'external/presentation'))
            os.environ['NIKKE_DATA_ROOT']=str(self.root/'env')
            self.assertEqual(self.root/'env',p.resolve_data_root(output=self.root/'external/presentation'))
            self.assertEqual(self.root/'explicit',p.resolve_data_root(self.root/'explicit',self.root/'external/presentation'))

    def test_helpers_output_only_external_and_default_without_code_data(self):
        out=seed(self.root/'external')
        with patch.object(p,'ROOT',self.root/'absent-code'), patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
            first=account.prepare(out); second=spec.prepare(out)
            self.assertEqual(9,len(first['consoles']));self.assertEqual(9,len(second['overloadOptions']))
            self.assertEqual(100,second['overloadOptions'][0]['legalValues'][0]['unscaledValue'])
            self.assertFalse((self.root/'absent-code').exists())
        default=seed(self.root/'code/data/local')
        with patch.object(p,'ROOT',self.root/'code'),patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
            account.prepare();spec.prepare()
        self.assertTrue((default/'spec-presentation.json').exists())

    def test_explicit_input_can_differ_from_output_and_missing_metadata_preserves_manifest(self):
        out=seed(self.root/'source'); target=self.root/'source/presentation'
        account.prepare(target,data_root=self.root/'source');spec.prepare(target,data_root=self.root/'source')
        before={f.name:f.read_bytes() for f in target.glob('*presentation.json')}
        for helper in (account,spec):
            with self.assertRaises(FileNotFoundError):helper.prepare(target,data_root=self.root/'missing')
        self.assertEqual(before,{f.name:f.read_bytes() for f in target.glob('*presentation.json')})

    def test_asset_vs_metadata_errors_and_verified_cache_fallback(self):
        out=self.root/'out'; image=p.PNG+b'synthetic'
        cache=p.CatalogCache(out,'manifest.json');cache.get('assets/a.png','https://example.test',lambda _:image,True);cache.commit()
        p.json_write(out/'manifest.json',{'assets':cache.assets})
        for error,code in ((HTTPError('https://example.test',503,'error',{},None),'http_error'),(ValueError('bad'),'invalid_content')):
            cache=p.CatalogCache(out,'manifest.json',True)
            def fail(_):raise error
            self.assertEqual(image,cache.get('assets/a.png','https://example.test',fail,True))
            self.assertEqual(('image',code,True),tuple(cache.issues[0][k] for k in ('kind','code','cached')))
        cache=p.CatalogCache(out,'manifest.json',True)
        with self.assertRaises(p.PreparationError):cache.get('assets/new.png','https://example.test',lambda _:b'<html>',True)
        self.assertFalse(cache.issues[0]['cached']);self.assertFalse((out/'assets/new.png').exists())
        with self.assertRaises(p.PreparationError):cache.get('catalog/new.json','https://example.test',lambda _:b'bad')
        self.assertEqual('catalog',cache.issues[-1]['kind'])

    def test_failed_catalog_does_not_publish_staged_replacements(self):
        out=seed(self.root)
        spec.prepare(out)
        before=(out/'spec-presentation.json').read_bytes()
        original=(out/'catalog/equipment-official.json').read_bytes()
        def response(url):
            if url==p.normal_resource_uri('equip/ItemEquipTable-ko.json'):return b'{"records":[],"fresh":true}'
            return b'not-json'
        with patch.object(p,'download',side_effect=response):
            # Invalid refresh falls back to cached JSON and reports its failure.
            result=spec.prepare(out,refresh=True)
        self.assertEqual('catalog',result['unresolved'][0]['kind'])
        self.assertTrue(result['unresolved'][0]['cached'])
        # Without fallback, no pending metadata replaces old files/manifest.
        (out/'catalog/favorite-map.json').unlink()
        prior=(out/'spec-presentation.json').read_bytes()
        with patch.object(p,'download',side_effect=response),self.assertRaises(p.PreparationError):spec.prepare(out,refresh=True)
        self.assertEqual(prior,(out/'spec-presentation.json').read_bytes())

    def test_build_classifies_mixed_errors_and_recovery_clears_previous_issues(self):
        out=seed(self.root)
        rows=[dict(name_code=i,resource_id=i,name_localkey={'name':str(i)}) for i in range(100)]
        p.json_write(out/'blablalink-index.json',rows)
        with patch.object(p,'download',return_value=p.PNG+b'image'),contextlib.redirect_stdout(io.StringIO()):
            good=p.build(out,include_account_assets=True)
        self.assertEqual([],good['unresolved'])
        (self.root/'game-catalog.json').rename(self.root/'game.saved')
        def download(url):
            if url.endswith('.json'):return json.dumps(rows).encode()
            raise HTTPError(url,503,'unavailable',{},None)
        with patch.object(p,'download',side_effect=download),contextlib.redirect_stdout(io.StringIO()):
            # update-index avoids refreshing valid helper caches, but one damaged image requires fetch.
            (out/'assets/characters/0.png').unlink()
            bad=p.build(out,update_index=True,include_account_assets=True)
        summary=p.receipt(bad,out)
        self.assertEqual(1,summary['failureSummary']['imageFailures'])
        self.assertEqual(1,summary['failureSummary']['catalogFailures'])
        self.assertEqual('partial',summary['status'])
        (self.root/'game.saved').rename(self.root/'game-catalog.json')
        with patch.object(p,'download',return_value=p.PNG+b'image'),contextlib.redirect_stdout(io.StringIO()):
            fixed=p.build(out,include_account_assets=True)
        self.assertEqual([],fixed['unresolved']);self.assertEqual('succeeded',p.receipt(fixed,out)['status'])

    def test_receipt_without_cache_is_failed_not_partial(self):
        receipt=p.receipt({'unresolved':[p.failure('account-presentation.json',FileNotFoundError())]},self.root)
        self.assertEqual('failed',receipt['status']);self.assertEqual(0,receipt['failureSummary']['availableImages'])

    def test_malformed_index_rows_do_not_replace_previous_index_or_manifest(self):
        out=seed(self.root)
        rows=[dict(name_code=i,resource_id=i,name_localkey={'name':str(i)}) for i in range(100)]
        p.json_write(out/'blablalink-index.json',rows)
        with patch.object(p,'download',return_value=p.PNG+b'image'),contextlib.redirect_stdout(io.StringIO()):p.build(out)
        before={name:(out/name).read_bytes() for name in ('blablalink-index.json','presentation.json')}
        with patch.object(p,'download',return_value=json.dumps([{}]*100).encode()),self.assertRaises(KeyError):p.build(out,update_index=True)
        self.assertEqual(before,{name:(out/name).read_bytes() for name in before})


if __name__=='__main__':unittest.main()
