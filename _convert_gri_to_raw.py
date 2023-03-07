# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 10:09:45 2023
@author: zolta

Converts the qgis raster file with the district info.
Source:  gri format, dest: raw byte array. 
I couldn't find any documentations on this float format,
so I checked the frequency in QGIS and in the gri file to find a mapping for the 256 possible values.
"""

import os
import numpy as np

# Save np array as an image
from gps_utils import save_array_to_rgba_image

# Use BASE_PATH to define root directory for input and output files
ONE_DRIVE_PATH = os.environ['ONEDRIVE']
BASE_PATH = rf"{ONE_DRIVE_PATH}/tmp_bp"

STREET_GRI = rf"{BASE_PATH}/admin_utcak25r.gri"
STREET_RAW = rf"{BASE_PATH}/admin_roads25.raw"
STREET_PNG = rf"{BASE_PATH}/admin_roads25.png"

ADMIN_BND_GRI = rf"{BASE_PATH}/admin_boundaries25.gri"
ADMIN_BND_RAW = rf"{BASE_PATH}/admin_boundaries25.raw"
ADMIN_BND_PNG = rf"{BASE_PATH}/admin_boundaries25.png"

# Image size
ROWS = 1168
COLUMNS = 1232

def convert_gri_to_raw(src_file: str, dest_file: str):
    """ Converts a GRI file to raw bitmap. """

    print(f"Reading {src_file}...")

    with open(src_file, "rb") as f:
        data = f.read()

    print(f"Converting...")
        
    converted = []

    for i in range(0, len(data), 4):
        # num = data[i] * 0x100**3 + data[i+1] * 0x100**2 + data[i+2] * 0x100**1 + data[i+3]
        num_e = data[i+2]
        num_f = data[i+3]
        
        # A completely nonsense expression I came up with
        num = int((1+(num_e & 127)/128)*(1+(num_e>=128))*2*4**(num_f-64))
        if (num > 255): num = 0
        
        converted.append(num)
        
    # Write file
    print(f"Writing {dest_file}...")

    with open(dest_file, "wb") as f:
        f.write(bytes(converted))

def convert_raw_to_png(src_file: str, dest_file: str):
    """ Convert a raw file to png """

    print(f"Reading raw file {dest_file}...")
    with open(src_file, "rb") as f:
        raw_data = list(f.read())

    np_arr_flat = np.array(raw_data, dtype='uint8')
    np_arr_reshaped = np_arr_flat.reshape((ROWS, COLUMNS))

    print(f"Writing bitmap file as {dest_file}...")
    save_array_to_rgba_image(np_arr_reshaped, dest_file, "L", (20, 20))

def main():
    # Convert admin boundaries and street data to raw bitmap files
    convert_gri_to_raw(STREET_GRI, STREET_RAW)
    convert_gri_to_raw(ADMIN_BND_GRI, ADMIN_BND_RAW)
    
    convert_raw_to_png(STREET_RAW, STREET_PNG)
    convert_raw_to_png(ADMIN_BND_RAW, ADMIN_BND_PNG)

    print("Done.")

if __name__ == "__main__":
    main()