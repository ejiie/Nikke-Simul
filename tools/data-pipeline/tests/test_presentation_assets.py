"""Asset archive and CDN cache contracts, using synthetic local data only."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import presentation_assets as a

class PresentationTests(unittest.TestCase):
    def test_verified_zip_import_and_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); image=a.PNG+b'synthetic'
            def archive(relative,checksum):
                manifest={'contractId':'nll/local-ui-reuse-assets/v1','characters':[],
                    'files':[dict(path=relative,byteLength=len(image),sha256=checksum)]}
                with zipfile.ZipFile(root/'input.zip','w') as z:
                    z.writestr(relative,image);z.writestr('manifest.private.json',json.dumps(manifest))
            archive('assets/ui/star.png',a.digest(image))
            imported=a.import_zip(root/'input.zip',root/'out')
            self.assertEqual(image,(root/'out/assets/ui/star.png').read_bytes())
            self.assertTrue(imported['zipSha256'])
            archive('../escaped.png',a.digest(image))
            with self.assertRaises(ValueError):a.import_zip(root/'input.zip',root/'out')
            self.assertFalse((root/'escaped.png').exists())

    def test_bad_hash_does_not_overwrite_existing_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dest=root/'assets/a.png';dest.parent.mkdir();dest.write_bytes(b'original')
            image=a.PNG+b'bad'
            with zipfile.ZipFile(root/'input.zip','w') as z:
                z.writestr('assets/a.png',image)
                z.writestr('manifest.private.json',json.dumps({'contractId':'nll/local-ui-reuse-assets/v1','characters':[],
                    'files':[dict(path='assets/a.png',byteLength=len(image),sha256='wrong')]}))
            with self.assertRaises(ValueError):a.import_zip(root/'input.zip',root)
            self.assertEqual(b'original',dest.read_bytes())

    def test_duplicate_name_downloads_by_resource_and_refresh_failure_preserves_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);image=a.PNG+b'fixture'
            rows=[dict(name_code=i,resource_id=i,name_localkey={'name':f'캐릭터{i}'},original_rare='SSR',
                corporation='TETRA',**{'class':'Attacker'},use_burst_skill='AllStep',
                element_id={'element':{'element':'Electronic'}},shot_id={'element':{'weapon_type':'SR'}}) for i in range(101)]
            rows[0]['name_localkey']['name']=rows[1]['name_localkey']['name']='중복'
            a.json_write(root/'blablalink-index.json',rows)
            imported=root/'assets/characters/lab.png';imported.parent.mkdir(parents=True);imported.write_bytes(image)
            a.json_write(root/'import-manifest.private.json',{'characters':[dict(displayName='중복',portraitPath='assets/characters/lab.png',characterUid='lab')],
                'files':[dict(path='assets/characters/lab.png',byteLength=len(image),sha256=a.digest(image))]})
            with patch.object(a,'download',return_value=image),patch('builtins.print'):
                first=a.build(root)
            self.assertEqual('/editor/assets/characters/0.png',first['characters'][0]['portraitPath'])
            self.assertEqual('/editor/assets/characters/1.png',first['characters'][1]['portraitPath'])
            self.assertEqual(5,first['characters'][0]['burstStep'])
            self.assertEqual('electric',first['characters'][0]['elementCode'])
            urls={x.get('url') for x in first['assets']}
            self.assertIn(a.normal_resource_uri('character/mi/mi_c000_00_s.png'),urls)
            def fail_images(url):
                if url.endswith('.json'):return json.dumps(rows).encode()
                raise OSError('offline')
            with patch.object(a,'download',side_effect=fail_images),patch('builtins.print'):
                second=a.build(root,refresh=True)
            self.assertEqual(first['characters'],second['characters'])
            self.assertTrue(all(u.get('cached') for u in second['unresolved']))
            (root/'assets/characters/0.png').write_bytes(a.PNG+b'tampered')
            with patch.object(a,'download',return_value=image) as download,patch('builtins.print'):
                a.build(root)
            self.assertEqual(image,(root/'assets/characters/0.png').read_bytes())
            self.assertEqual(1,download.call_count)

if __name__=='__main__':unittest.main()
