"""Read-only conversion of an existing captured game response to the P01 envelope.

Use only for local replay verification. Authentication and unrelated packets are excluded.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--area", type=int, required=True)
    args = parser.parse_args()
    source = Path(args.source)
    captured = json.loads(source.read_text(encoding="utf-8-sig"))
    packets = captured.get("phase_1_initial_load", []) + captured.get("phase_2_after_click", [])
    stamp = dt.datetime.fromtimestamp(source.stat().st_mtime, dt.timezone.utc).isoformat()
    envelope = {"schemaVersion":1,"source":"legacy-stored-capture","collectorVersion":"legacy-replay-p01.1",
                "openId":str(captured["uid"]),"area":args.area,"startedAt":stamp,"completedAt":stamp,
                "characters":[],"details":[],"stateEffects":[],"outpost":None,"responses":[]}
    for packet in packets:
        route = packet.get("endpoint")
        if route not in ("GetUserCharacters","GetUserCharacterDetails","GetUserProfileOutpostInfo"):
            continue
        data = packet.get("data") or {}
        if route == "GetUserCharacters": envelope["characters"].extend(data.get("characters", []))
        if route == "GetUserCharacterDetails":
            envelope["details"].extend(data.get("character_details", []))
            envelope["stateEffects"].extend(data.get("state_effects", []))
        if route == "GetUserProfileOutpostInfo": envelope["outpost"] = data.get("outpost_info")
        envelope["responses"].append({"route":"Game/"+route,"observedAt":stamp,"response":{"code":0,"data":data}})
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    print(f"Stored capture replay prepared: roster={len(envelope['characters'])}, details={len(envelope['details'])}; not a live fetch")

if __name__ == "__main__": main()
