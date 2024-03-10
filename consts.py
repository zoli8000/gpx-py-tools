import os
from datetime import date

BUCKET_NAME = 'budapest-challenge-szz-2023'

# Use BASE_PATH to define root directory for input and output files
ONE_DRIVE_PATH = os.environ['ONEDRIVE']
BASE_PATH = rf"{ONE_DRIVE_PATH}/tmp_bp"

# GPS route data in xml format
GPS_DATA_PATH = rf"{BASE_PATH}/gpx_all.csv"

# Source images with street and admin boundary info
ADMIN_DATA_PATH = rf"{BASE_PATH}/admin_data.csv"
ADMIN_ROADS_PATH = rf"{BASE_PATH}/admin_roads25.png"
ADMIN_ZONES_PATH = rf"{BASE_PATH}/admin_boundaries25.png"

# Output images and data tables
SMALL_PIC_PATH = rf"{BASE_PATH}/result_small.png"
LARGE_PIC_PATH = rf"{BASE_PATH}/result.png"
DATE_PIC_PATH = rf"{BASE_PATH}/date_result.png"
JSON_DATA_PATH = rf"{BASE_PATH}/routes_done.json"
DATE_DATA_PATH = rf"{BASE_PATH}/date_stats.json"

# Image size
ROWS = 1180  # 1168
COLUMNS = 1240  # 1232

# Colors
COLORS = [
    # Transparent, red, green
    (0, 0, 0, 0), (0x80, 0, 0, 0xff), (0, 0x80, 0, 0xff),

    # lime, yellow, orange
    (0x80, 0xff, 0, 0xff),  (0xff, 0xff, 0, 0xff), (0xff, 0x80, 0, 0xff)
]

# Rasterized date info: days since 2000.01.01.
BASE_DATE = date(2000, 1, 1)
