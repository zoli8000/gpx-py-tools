# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 21:49:36 2020

@author: zolta
"""

import os
import glob
import ntpath
from datetime import date
import pandas as pd


from gps_utils import gps_estimated_meter_distance, simplify_gpx_route

# Use BASE_PATH to define root directory for input and output files
ONE_DRIVE_PATH = os.environ['ONEDRIVE']
BASE_PATH = rf"{ONE_DRIVE_PATH}/tmp_bp"
GPX_PATH = rf"{BASE_PATH}/gpx/"

# Combined gpx output
combined_gpx_str: str = ""

# Kms and files read
total_km: int = 0
file_km: int
idx: int


df = pd.DataFrame(columns=['edate', 'lat0', 'lon0', 'lat1', 'lon1'])

df = df.astype(dtype={'edate': str, 'lat0': float,
               'lat1': float, 'lon0': float, 'lon1': float})

distall = []
err = []

lat0, lat1, lon0, lon1, edate = [], [], [], [], []

idx = 0
for fname in glob.glob(rf"{GPX_PATH}/*.gpx"):
    date.today().strftime("yyyy")
    file_m = 0

    if "Amazfit" not in fname and "Zepp" not in fname:
        print(f"Skipping {fname}....")
        continue

    idx += 1
    with open(fname, "r", encoding="utf8") as f:
        print(f"Reading file #{idx}, {fname}...", end="")

        f_lines = f.read()
        gpx_coords = simplify_gpx_route(f_lines)

        combined_gpx_str += "<trkseg>\n"

        for lat, lon in gpx_coords:
            combined_gpx_str += f"""  <trkpt lat="{lat:8.5f}" lon="{lon:8.5f}"></trkpt>\n"""

        combined_gpx_str += "</trkseg>\n"
        date_str = ntpath.basename(fname).replace(
            "Amazfit", "").replace("Zepp", "")[0:8]

        for i in range(len(gpx_coords) - 1):
            lat0_coord, lon0_coord = gpx_coords[i]
            lat1_coord, lon1_coord = gpx_coords[i + 1]

            lat0.append(lat0_coord)
            lon0.append(lon0_coord)
            lat1.append(lat1_coord)
            lon1.append(lon1_coord)

            dist = gps_estimated_meter_distance(
                lat0_coord, lon0_coord, lat1_coord, lon1_coord)
            file_m += dist
            edate.append(date_str)

        file_km = int(file_m/100) / 10
        print(f" {file_km:0.1f} kms")

        total_km += file_km

df = pd.DataFrame({'lat0': lat0, 'lon0': lon0, 'lat1': lat1,
                  'lon1': lon1, 'edate': edate})

df.sort_values(by='edate', ascending=False, inplace=True)

file_txt = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<gpx xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:ns2="http://www.garmin.com/xmlschemas/GpxExtensions/v3" xmlns:ns1="http://www.cluetrust.com/XML/GPXDATA/1/0" creator="Amazfit App" version="4.3.0" >
<trk ><name>Amazfit</name>
""" + combined_gpx_str + """
</trk>
</gpx>"""

print(f"{total_km:0.1f} kms.")
print(f"{idx} files read, combined file wrote.")

# points_found = list(points_found)
df.to_csv(rf"""{BASE_PATH}/gpx_all.csv""")

output_file = rf"""{BASE_PATH}/gpx_all.gpx"""
with open(output_file, "w", encoding="utf8") as f:
    f.write(file_txt)
