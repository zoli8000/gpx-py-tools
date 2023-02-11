# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 11:08:24 2023
@author: zolta

Converts a gpx file (gps coordinates) inside the boundaries of Budapest to
        - a large image (25 x 25 meter pixels) showing roads walked and to be walked
        - a small image (500 x 500 meter pixels) showing if the area is completely, partially walked, or not visited 
"""

import re
import os
import numpy as np
import pandas as pd

from PIL import Image, ImageDraw
from collections import Counter

BUCKET_NAME='budapest-challenge-szz-2023'

# Use BASE_PATH to define root directory for input and output files
ONE_DRIVE_PATH = os.environ['ONEDRIVE']
BASE_PATH = rf"{ONE_DRIVE_PATH}/tmp_bp"

# GPS route data in xml format
GPS_DATA_PATH = rf"{BASE_PATH}/gpx_all.gpx"

# Source images with street and admin boundary info
ADMIN_DATA_PATH = rf"{BASE_PATH}/admin_data.csv"
ADMIN_ROADS_PATH = rf"{BASE_PATH}/admin_roads25.raw"

# Output images and data tables
SMALL_PIC_PATH = rf"{BASE_PATH}/result_small.png"
LARGE_PIC_PATH = rf"{BASE_PATH}/result.png"
JSON_DATA_PATH = rf"{BASE_PATH}/routes_done.json"

# Image size
ROWS = 1168
COLUMNS = 1232

# Colors
COLORS = [(0,0,0,0), (0x80, 0, 0, 0xff), (0, 0x80, 0, 0xff), (0xff, 0xff, 0, 0xff)]

# Global file data
gps_data, admin_roads = ["", ""]

# Numpy Arrays, dataframes
df_admin_data:          'pd.DataFrame' = None
np_routes_all:          'np.NDArray' = None
np_routes_done_clean:   'np.NDArray' = None
np_route_detailed_8bit: 'np.NDArray' = None

def load_local_files():
    """ Read files:
            * gpx_all:     gps routes
            * admin_data:  administrative data (rasterized admin boundaries)
            * admin_roads: road data (rasterized)"""

    global gps_data, df_admin_data, admin_roads


    print(f"Reading {GPS_DATA_PATH}...")

    with open(GPS_DATA_PATH, "r") as f:
        gps_data = f.read()

    print(f"Reading {ADMIN_DATA_PATH}...")
    df_admin_data = pd.read_csv(ADMIN_DATA_PATH, sep=";")    

    print(f"Reading {ADMIN_ROADS_PATH}...")
    with open(ADMIN_ROADS_PATH, "rb") as f:
        admin_roads = f.read()
    

def convert_from_gps_to_23700(lat, lon):
    """ Simplified convert from (EPSG:4326) to compressed meter-based EPSG:23700. """
    ymulti = 111188 # (max_my / max_gpsy)
    xmulti = 75334 # (max_mx / max_gpsx)

    lon23700 = (lat - 47.144433) * ymulti + 200029
    lat23700 = (lon - 18.931005) * xmulti + 641228

    # print(lon23700, lat23700)
    return [lon23700, lat23700]

def convert_from_gps_to_pixel(lat, lon):
    """ Convert gps coordinates to pixel coordinate in image """
    lat2, lon2 = convert_from_gps_to_23700(lat, lon)
    
    latp = (252143 - lat2) / 25
    lonp = (lon2 - 640790.6) / 25
    
    return [lonp, latp]

def save_array_to_rgba_image(np_array, dest_path):
    """ Save np array as an RGBA image """
    print(f"Saving image as {dest_path}...")
    img = Image.fromarray(np_array, "RGBA")
    img.save(dest_path)

def get_rasterized_from_gps():
    """ Rasterizes a GPX file, the result is an array of numbers with 0 and 1 pixels. """
    
    print(f"Rasterizing gpx file...")

    routes_walked_image = Image.new("1", (COLUMNS, ROWS), 0)
    routes_walked_draw = ImageDraw.Draw(routes_walked_image) 
    end = 0

    while True:
        # Find segment start end end
        start = gps_data.find("<trkseg>", end)    
        if start == -1: break
        end = gps_data.find("</trkseg>", start)
        
        # Segment data
        block = gps_data[start + len("<trkseg>"):end - len("</trkseg>")]
        
        last_lat = -1
        last_lon = -1
        
        # All lat-lon coordinates in segment
        for line in block.split("\n"):
            m = re.match(r""".*lat=\"(?P<lat>[\d.]+)\" lon=\"(?P<lon>[\d.]+)\">.*""", line)
            if not m: continue
        
            md = m.groupdict()
            
            lat = md['lat']
            lon = md['lon']
            
            pix_lat, pix_lon = convert_from_gps_to_pixel(float(lat), float(lon))
            
            shape = [(last_lat, last_lon), (pix_lat, pix_lon)]
            
            if (last_lat > 0 and last_lon > 0):
                routes_walked_draw.line(shape, fill =1, width = 3)
            
            last_lat = pix_lat
            last_lon = pix_lon
            # print(lat, lon)

    
    return list(routes_walked_image.getdata())

def create_aggr_table():
    """ Set road length by administrative areas in the admin_data table """
    
    global np_routes_all, np_routes_done_clean

    np_routes_all = np.array(list(admin_roads), dtype='uint8')
    count_zones_all = Counter(np_routes_all)

    df_admin_data['Total'] = df_admin_data['ID'].apply(lambda x: count_zones_all.get(x, 0))

    # Rasterize gps data, and keep only pixels in the proximity of residential roads.
    rasterized_gpx = get_rasterized_from_gps()
    np_routes_done = np.array(rasterized_gpx, dtype='uint8')
    np_routes_done_clean = (np_routes_all > 0) * (np_routes_done)

    # Get finished pixels in each zone
    np_routes_done_zones = (np_routes_all) * (np_routes_done_clean)
    count_zones_done = Counter(np_routes_done_zones)

    # Add done and percentage finished to admin_data table
    df_admin_data['Done'] = df_admin_data['ID'].apply(lambda x: count_zones_done.get(x, 0))
    # df_admin_data['percentage'] = df_admin_data['done'] / df_admin_data['needed']

    print(f"Writing zone statistics to {JSON_DATA_PATH}...")
    df_admin_data.to_json(JSON_DATA_PATH, orient='records')

def create_large_result():
    global np_route_detailed_8bit
    
    # Create colored map, red: not visited, green: completely visited, yellow: partially visited 
    np_route_detailed_8bit = (np_routes_all > 0) * (np_routes_done_clean + 1)
    np_result_rgba = list(map(lambda x: COLORS[x], np_route_detailed_8bit))

    np_res_reshaped = np.array(np_result_rgba, dtype='uint8').reshape((ROWS, COLUMNS, 4))

    # Save image
    save_array_to_rgba_image(np_res_reshaped, LARGE_PIC_PATH)

def get_downscaled(np_source):
    """ Get a the downscaled list of numbers from the numpy array """
    new_pixels = []

    print("Downscaling gpx file...")
    for row in range(0, ROWS, 20):
        for column in range(0, COLUMNS, 20):
            boxData = np.array([], dtype='uint8')
            for line in range(20):
                pixelcount = 20 if column + 20 <= COLUMNS else COLUMNS % 20
                sourceData = np_source[row * COLUMNS + column + line : row * COLUMNS + column + line + pixelcount]
                boxData = np.concatenate([sourceData, boxData])
            
            pixels = Counter(boxData)
            all_done = pixels.get(2, 0)
            to_be_done = pixels.get(1, 0)
            
            done_ratio = all_done / (all_done + to_be_done + 0.0001)
            
            # print(row, column, pixels, doneShare)
            new_pixel_color = 0
            
            if (all_done + to_be_done < 2): new_pixel_color = 0
            elif (done_ratio > 0.90 ): new_pixel_color = 2
            elif (done_ratio > 0.3): new_pixel_color = 3
            else: new_pixel_color = 1
            
            new_pixels.append(new_pixel_color) 
    return new_pixels

def create_small_result():
    """ Create downscaled color map from 8bit numpy array """

    downscaled_list = get_downscaled(np_route_detailed_8bit)
    
    # Convert values 0-2 to RGBA colors, and reshape flat list to 59x62 image
    rgba_list = list(map(lambda x: COLORS[x], downscaled_list))
    np_small_reshaped = np.array(rgba_list, dtype='uint8').reshape((59, 62, 4))

    save_array_to_rgba_image(np_small_reshaped, SMALL_PIC_PATH)
      
def write_to_s3():
    """ Write data to s3 """
    import boto3
    s3 = boto3.client('s3')

    print("Uploading 'result_small.png' to S3...")
    s3.upload_file(SMALL_PIC_PATH, Bucket=BUCKET_NAME, Key="result_small.png")
    
    print("Uploading 'result.png' to S3...")
    s3.upload_file(LARGE_PIC_PATH, Bucket=BUCKET_NAME, Key="result.png")
    
    print("Uploading 'routes_done.json' to S3...")
    s3.upload_file(JSON_DATA_PATH, Bucket=BUCKET_NAME, Key="routes_done.json")

def create_files(write_s3: bool):
    """ Main function, creates files """
    load_local_files()
    create_aggr_table()
    create_large_result()
    create_small_result()

    if (write_s3): write_to_s3()

    print("Done.")

if __name__ == "__main__":
    create_files(write_s3=True)



