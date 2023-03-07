# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 21:49:36 2020

@author: zolta
"""

import os
import glob
from datetime import date
import pandas as pd
import re, math
import copy
import ntpath

from gps_utils import gps_estimated_meter_distance, convert_gpx_to_coords 
from gps_utils import filter_coords_with_min_distance, simplify_gpx_route

# Use BASE_PATH to define root directory for input and output files
ONE_DRIVE_PATH = os.environ['ONEDRIVE']
BASE_PATH = rf"{ONE_DRIVE_PATH}/tmp_bp"
GPX_PATH = rf"{BASE_PATH}/gpx/"

df = pd.DataFrame(columns=['edate', 'lat0', 'lon0', 'lat1', 'lon1']) 
                  
df = df.astype(dtype={'edate': str, 'lat0': float, 'lat1': float, 'lon0': float, 'lon1': float})


combined_gpx_str = ""
distall = []


err = []


idx = 0
lat0, lat1, lon0, lon1, edate = [], [], [], [], []

for fname in glob.glob(rf"{GPX_PATH}/*.gpx"""):
    date.today().strftime("yyyy")

    if "Amazfit" not in fname and "Zepp" not in fname:
        print(f"Skipping {fname}....")
        continue

    with open(fname, "r") as f:
        print(f"Reading file #{idx}, {fname}...")

        idx += 1
       
        f_lines = f.read()        
        gpx_coords = simplify_gpx_route(f_lines)

        combined_gpx_str += "<trkseg>\n"
        
        for i in range(len(gpx_coords)):
            lat, lon = gpx_coords[i]
            combined_gpx_str += f"""  <trkpt lat="{lat:8.5f}" lon="{lon:8.5f}"></trkpt>\n"""
            
        combined_gpx_str += "</trkseg>\n"
        date_str = ntpath.basename(fname).replace("Amazfit", "").replace("Zepp", "")[0:8]

        for i in range(len(gpx_coords) - 1):
            lat0.append(gpx_coords[i][0])
            lon0.append(gpx_coords[i][1])
            lat1.append(gpx_coords[i + 1][0])
            lon1.append(gpx_coords[i + 1][1])
            edate.append(date_str)
            
df = pd.DataFrame({'lat0': lat0, 'lon0': lon0, 'lat1': lat1, 'lon1': lon1, 'edate': edate}) 

df.sort_values(by='edate', ascending=False, inplace=True)

file_txt = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<gpx xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:ns2="http://www.garmin.com/xmlschemas/GpxExtensions/v3" xmlns:ns1="http://www.cluetrust.com/XML/GPXDATA/1/0" creator="Amazfit App" version="4.3.0" >
<trk ><name>Amazfit</name>
""" + combined_gpx_str + """
</trk>
</gpx>"""

print(f"{idx} files read, combined file wrote.")

# points_found = list(points_found)
df.to_csv(rf"""{BASE_PATH}/gpx_all.csv""")

output_file = rf"""{BASE_PATH}/gpx_all.gpx"""
with open (output_file, "w") as f:
    f.write(file_txt)