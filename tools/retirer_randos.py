# -*- coding: utf-8 -*-
"""Retire des randonnées de data/points.geojson (+ tracés éventuels).

À utiliser UNIQUEMENT pour les randonnées dont le routage a définitivement
échoué (règle : pas de randonnée sans tracé). Les ids retirés restent dans
tools/randos-registre.json et ne seront JAMAIS réattribués.

Usage : python tools/retirer_randos.py --ids rando-0021 rando-0034
"""

import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
POINTS = RACINE / "data" / "points.geojson"
TRACES = RACINE / "data" / "randos.geojson"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+", required=True)
    ids = set(ap.parse_args().ids)

    collection = json.loads(POINTS.read_text(encoding="utf-8"))
    avant = len(collection["features"])
    retires = [f["properties"]["id"] for f in collection["features"]
               if f["properties"].get("theme") == "randonnee"
               and f["properties"]["id"] in ids]
    collection["features"] = [
        f for f in collection["features"]
        if not (f["properties"].get("theme") == "randonnee"
                and f["properties"]["id"] in ids)]
    POINTS.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"points.geojson : {avant} → {len(collection['features'])} features "
          f"(retirés : {sorted(retires)})")
    if ids - set(retires):
        print(f"  introuvables (déjà absents ?) : {sorted(ids - set(retires))}")

    if TRACES.exists():
        traces = json.loads(TRACES.read_text(encoding="utf-8"))
        n = len(traces["features"])
        traces["features"] = [f for f in traces["features"]
                              if f.get("properties", {}).get("rando") not in ids]
        if len(traces["features"]) != n:
            TRACES.write_text(
                json.dumps(traces, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8")
            print(f"randos.geojson : {n} → {len(traces['features'])} tracés")
    return 0


if __name__ == "__main__":
    sys.exit(main())
