# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 11:08:24 2023

@author: zolta
"""

import re
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from collections import Counter

BUCKET_NAME='budapest-challenge-szz-2023'
SMALL_PIC_PATH = r"C:\Users\zoltan\OneDrive\tmp_bp/result_small.png"
LARGE_PIC_PATH = r"C:\Users\zoltan\OneDrive\tmp_bp/result.png"

with open(r"C:\Users\zoltan\OneDrive\gpx_all.gpx", "r") as f:
    xml = f.read()

admin_data = pd.read_csv(r"C:\Users\zoltan\OneDrive\tmp_bp/admin_data.csv", sep=";")    
    
# create an image
rows = 1168
columns = 1232


ymulti = 111188 # (max_my / max_gpsy)
xmulti = 75334 # (max_mx / max_gpsx)

def convert_from_gps_to23700(lat, lon):
    lon23700 = (lat - 47.144433) * ymulti + 200029
    lat23700 = (lon - 18.931005) * xmulti + 641228

    # print(lon23700, lat23700)
    return [lon23700, lat23700]


def convert_from_gps_to_pixel(lat, lon):
    lat2, lon2 = convert_from_gps_to23700(lat, lon)
    
    latp = (252143 - lat2) / 25
    lonp = (lon2 - 640790.6) / 25
    
    return [lonp, latp]

out = Image.new("1", (columns, rows), 0)

# Segments
end = 0
while True:
    start = xml.find("<trkseg>", end)    

    if start == -1:
        break
    
    end = xml.find("</trkseg>", start)
    
    block = xml[start + len("<trkseg>"):end - len("</trkseg>")]
    
    last_lat = -1
    last_lon = -1
    
    for line in block.split("\n"):
        m = re.match(r""".*lat=\"(?P<lat>[\d.]+)\" lon=\"(?P<lon>[\d.]+)\">.*""", line)
        if not m: continue
    
        md = m.groupdict()
        
        lat = md['lat']
        lon = md['lon']
        
        
        pix_lat, pix_lon = convert_from_gps_to_pixel(float(lat), float(lon))
        
        img1 = ImageDraw.Draw(out)  
        shape = [(last_lat, last_lon), (pix_lat, pix_lon)]
        
        if (last_lat > 0 and last_lon > 0):
            img1.line(shape, fill =1, width = 3)
        
        last_lat = pix_lat
        last_lon = pix_lon
        # print(lat, lon)

# out.show()

with open(r"C:\Users\zoltan\OneDrive\tmp_bp/admin_utcak25.raw", "rb") as f:
    admin_utcak = f.read()
    
np_routes_all = np.array(list(admin_utcak), dtype='uint8')
count_zones_all = Counter(np_routes_all)

admin_data['needed'] = admin_data['ID'].apply(lambda x: count_zones_all.get(x, 0))

np_routes_done = np.array(list(out.getdata()), dtype='uint8')
np_routes_done_clean = (np_routes_all > 0) * (np_routes_done)

# 
np_routes_done_zones = (np_routes_all) * (np_routes_done_clean)
count_zones_done = Counter(np_routes_done_zones)

admin_data['done'] = admin_data['ID'].apply(lambda x: count_zones_done.get(x, 0))
admin_data['percentage'] = admin_data['done'] / admin_data['needed']

# st.table(admin_data)
np_colors = [(0,0,0,0), (0x80, 0, 0, 0xff), (0, 0x80, 0, 0xff), (0xff, 0xff, 0, 0xff)]

np_result_8bit = (np_routes_all > 0) * (np_routes_done_clean + 1)
 

np_result_rgba = list(map(lambda x: np_colors[x], np_result_8bit))

np_res_reshaped = np.array(np_result_rgba, dtype='uint8').reshape((rows, columns, 4))


img_status = Image.fromarray(np_res_reshaped, "RGBA")


img_status.save(LARGE_PIC_PATH)
# img_status.show()

newPixels = []

for row in range(0, rows, 20):
    for column in range(0, columns, 20):
        boxData = np.array([], dtype='uint8')
        for line in range(20):
            pixelcount = 20 if column + 20 <= columns else columns % 20
            sourceData = np_result_8bit[row * columns + column + line : row * columns + column + line + pixelcount]
            boxData = np.concatenate([sourceData, boxData])
        
        pixels = Counter(boxData)
        allDone = pixels.get(2, 0)
        toBeDone = pixels.get(1, 0)
        
        doneShare = allDone / (allDone + toBeDone + 0.0001)
        
        print(row, column, pixels, doneShare)
        newPixelColor = 0
        
        if (allDone + toBeDone < 2): newPixelColor = 0
        elif (doneShare > 0.90 ): newPixelColor = 2
        elif (doneShare > 0.3): newPixelColor = 3
        else: newPixelColor = 1
        
        newPixels.append(newPixelColor) 

np_result_rgba = list(map(lambda x: np_colors[x], newPixels))
np_small_reshaped = np.array(np_result_rgba, dtype='uint8').reshape((59, 62, 4))
img_status2 = Image.fromarray(np_small_reshaped, "RGBA")

# img_status2.show()

img_status2.save(SMALL_PIC_PATH)
      
def write_to_s3():
    import boto3
    s3 = boto3.client('s3')
    s3.upload_file(SMALL_PIC_PATH, Bucket=BUCKET_NAME, Key="result_small.png")
    s3.upload_file(LARGE_PIC_PATH, Bucket=BUCKET_NAME, Key="result.png")

write_to_s3()


