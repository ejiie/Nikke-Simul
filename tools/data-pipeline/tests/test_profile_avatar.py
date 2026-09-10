import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import profile_avatar_assets as assets
from collector import profile_icon_id

class ProfileAvatarTests(unittest.TestCase):
    def test_icon_selection_is_not_the_showcase_team(self):
        profile={'code':0,'data':{'basic_info':{'area_id':'83','icon_id':512401,'profile_team':[{'name_code':5004}]}}}
        self.assertEqual(512401,profile_icon_id(profile,83))
        self.assertIsNone(profile_icon_id(profile,81))
        profile['data']['basic_info']['icon_id']=True
        self.assertIsNone(profile_icon_id(profile,83))
    def test_official_mapping_preserves_the_selected_costume_and_offline_cache(self):
        rows=[{'id':512401,'resource_id':511,'costume_index':1}]
        with tempfile.TemporaryDirectory() as root:
            with patch.object(assets,'download',side_effect=[json.dumps(rows).encode(),assets.PNG+b'fixture']) as fetch:
                path=assets.prepare(512401,root)
                self.assertEqual(assets.normal_resource_uri('character/si/si_c511_01_s.png'),fetch.call_args.args[0])
                self.assertEqual('/editor/assets/account-avatars/512401.png',path)
            with patch.object(assets,'download',side_effect=AssertionError('Unexpected network access')):
                self.assertEqual(path,assets.prepare(512401,root))
