#!/usr/bin/env python3
"""Géocode les adresses du guide (Nominatim / OpenStreetMap) et les écrit dans le HTML.
Usage : python3 geocode.py index.html
Reprenable : les résultats sont gardés dans geo_cache_v2.json. ~1 requête/seconde (règle de Nominatim)."""
import re, sys, json, time, os, urllib.request, urllib.parse
path = sys.argv[1]
html = open(path, encoding="utf-8").read()
ST = dict(re.findall(r'(\w):"([^"]+)"', re.search(r'const ST=\{(.*?)\};', html, re.S).group(1)))
raw = re.search(r'const RAW=`(.*?)`;', html, re.S).group(1)
places = {}
for line in raw.split("\n"):
    f = line.split("|")
    if len(f) < 4: continue
    name, a = f[1], f[3]
    m = re.match(r'^(\d+) ([A-Z])$', a)
    places[name] = f"{m.group(1)}, {ST[m.group(2)]}" if m else a
cache = json.load(open("geo_cache_v2.json")) if os.path.exists("geo_cache_v2.json") else {}
missing = [n for n in places if n not in cache]
print(f"{len(places)} adresses, {len(missing)} à géocoder")
for i, n in enumerate(missing, 1):
    def nom(bounded):
        p = {"format": "jsonv2", "limit": 1, "countrycodes": "ca", "q": places[n] + ", Québec"}
        if bounded: p.update({"viewbox": "-74.15,45.75,-73.30,45.35", "bounded": 1})  # région de Montréal
        req = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(p),
                                     headers={"User-Agent": "guide-montreal-geocoder/1.0"})
        return json.load(urllib.request.urlopen(req, timeout=20))
    try:
        r = nom(True)
        if not r: time.sleep(1.1); r = nom(False)
        cache[n] = [round(float(r[0]["lat"]), 5), round(float(r[0]["lon"]), 5)] if r else None
    except Exception as e:
        print("erreur", n, e); time.sleep(5); continue
    print(f"[{i}/{len(missing)}] {n} → {cache[n]}")
    json.dump(cache, open("geo_cache_v2.json", "w"), ensure_ascii=False)
    time.sleep(1.1)
geo = {n: c for n, c in cache.items() if c and n in places}
out = re.sub(r'/\*GEO\*/.*?/\*END\*/', lambda m: "/*GEO*/" + json.dumps(geo, ensure_ascii=False) + "/*END*/", html, flags=re.S)
open(path, "w", encoding="utf-8").write(out)
print(f"{len(geo)} coordonnées écrites dans {path}")
print("Sans résultat :", [n for n in places if not cache.get(n)] or "aucun")
