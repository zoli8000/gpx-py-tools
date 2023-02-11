# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 10:09:45 2023
@author: zolta

Converts the qgis raster file with the district info.
Source:  gri format, dest: raw byte array. 
I couldn't find any documentations on this float format,
so I checked the frequency in QGIS and in the gri file to find a mapping for the 256 possible values.
"""

with open("F:/tmp_bp/admin_utcak25r.gri", "rb") as f:
    data = f.read()
    
converted = []

for i in range(0, len(data), 4):
    # num = data[i] * 0x100**3 + data[i+1] * 0x100**2 + data[i+2] * 0x100**1 + data[i+3]
    num_e = data[i+2]
    num_f = data[i+3]
    
    num = int((1+(num_e & 127)/128)*(1+(num_e>=128))*2*4**(num_f-64))
    
    if (num > 255): num = 0
    
    converted.append(num)
    
with open("F:/tmp_bp/admin_utcak25.raw", "wb") as f:
    f.write(bytes(converted))