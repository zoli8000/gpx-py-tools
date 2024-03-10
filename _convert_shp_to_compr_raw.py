# -*- coding: utf-8 -*-
"""
Created on Thu Feb  2 20:58:15 2023
@author: zoltan

Data from Openstreetmap Admin Boundaries.
Converts gps positions (EPSG:4326) to compressed meter-based EPSG:23700.
Each coordinate is stored on 12 bit pairs.
The 12 bit data is stored similar to base64, 0x40 is added to the 6bit value.
If the result is a special character, values '0'..'9' are used for special values.

"""

data = """
NAME	st_astext(st_transform(geometry,4326))
Spanyolrét	MULTIPOLYGON(((18.978703 47.468996...)))
"""

d = {}
import re

latw = 47.6158784396334 - 47.25015273209994
lonw = 19.353538269379524 - 18.825267559826718
compressed = ""

import math
chrs = {}

spec = [0x60, 0x5c, 0x7f]
def chr2(x):
    c2 = x
    if x in spec: c2 = spec.index(c2) + 48
    chrs[c2] = 1
    
    if c2 == 63:
        print(c2)
    return chr(c2)

def dechr2(x: str) -> int:
    if ord(x) <= 57:
        return spec[ord(x)-48]
    
    return ord(x) - 64
    
def decoded(x: str, base: float, width: float) -> float:
    codel = dechr2(x[0])
    codeh = dechr2(x[1])
    coded = codel + codeh * 0x40
    
    return (coded / (0x40 * 0x40 -1)) * width + base
    
def encoded(x: str, base: float, width: float) -> str:
    if (float(x) > base + width):
        print(x)
        
    code = math.floor((float(x) - base) / width * (0x40 * 0x40 - 1))
    codel = code & 0x3f
    codeh = code >> 6
    coded = chr2(codel+0x40)+chr2(codeh+0x40)
    
    # test
    n = decoded(coded, base, width)
    # print(n - float(x))
    if abs(n - float(x)) > 2 / width :
        print(n, x)
        raise Exception("")
    
    return coded
    
def latc(x):
    return encoded(x, 47.25015273209994, latw)

def lonc(x):
    return encoded(x, 18.825267559826718, lonw)

with open(r"C:\Users\zoltan\Downloads\kozighatarok\kozighatarok\district_data.js", "w", encoding="utf8") as f:
    f.write('import { LatLngTuple } from "leaflet";\n\n')
    f.write('export const geoms: Record<string, LatLngTuple[]> = {\n')
    
    f.write('export const geomCompr: Record<string, string> = {\n')
    for line in data.split("\n"):
        if line == "": continue
        key, value = line.split("\t")
        
        if key == 'NAME': continue
        
        coords = list(map(lambda x: re.sub(r"[^\d.]", "", x), value.split(" ")))
        coord_text = ", ".join([f"[{coords[i+1]}, {coords[i]}]" for i in range(0, len(coords) - 1, 2)])
        d[key] = f"[{coord_text}],"
        compressed = [f"{latc(coords[i+1])}{lonc(coords[i])}" for i in range(0, len(coords) - 1, 2)]
        
        compressed2 = ""
        for idx, c in enumerate(compressed):
            if idx == 0 or compressed[idx - 1] != c:
                compressed2 += c
        
        # f.write(f"    '{key}': {d[key]}\n")
        f.write(f"""    '{key}': String.raw`{compressed2}`,\n""")
    f.write("}")
      
    
    # [47.61308784396334, 18.925267559826718], [47.35015273209994, 19.333538269379524]