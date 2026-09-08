"""Explicit synthetic fixture for full API/UI tests; contains no user data."""
import json
from pathlib import Path
import sys

def make():
    roster = [{"name_code":101,"lv":400,"grade":3,"core":2}]
    detail = {"name_code":101,"lv":200,"attractive_lv":25,"skill1_lv":7,"skill2_lv":8,"ulti_skill_lv":9,
              "harmony_cube_tid":5,"harmony_cube_lv":7,"favorite_item_tid":0,"favorite_item_lv":0}
    for part in ("head","torso","arm","leg"):
        detail.update({part+"_equip_tid":1000,part+"_equip_tier":10,part+"_equip_lv":5,part+"_equip_corporation_type":4,
                       part+"_equip_option1_id":11 if part == "head" else 0,part+"_equip_option2_id":0,part+"_equip_option3_id":0})
    return {"schemaVersion":1,"source":"synthetic-test","collectorVersion":"fixture-v1","openId":"synthetic-account","area":83,
            "startedAt":"2026-09-08T00:00:00Z","completedAt":"2026-09-08T00:00:01Z","characters":roster,"rosterAfter":roster,
            "details":[detail],"stateEffects":[{"id":"11","function_details":[{"function_type":"StatAtk","function_value":1181,"function_value_type":"Percent"}]}],
            "outpost":{"synchro_level":400,"recycle_room_researches":[{"tid":1001,"lv":150}]}}

if __name__ == "__main__":
    path = Path(sys.argv[1]); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(make(), ensure_ascii=False), encoding="utf-8")
