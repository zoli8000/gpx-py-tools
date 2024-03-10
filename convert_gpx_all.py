# -*- coding: utf-8 -*-
"""
Converts a gpx file (gps coordinates) inside the boundaries of Budapest to
        -   a large image (25 x 25 meter pixels)
            showing roads walked and to be walked
        -   a small image (500 x 500 meter pixels) 
            showing if the area is completely, partially walked, or not visited 
"""


from collections import Counter
from datetime import date, timedelta

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

# Save np array as an image
from gps_utils import save_array_to_rgba_image, convert_gps_to_23700

from consts import \
    BUCKET_NAME, BASE_PATH, GPS_DATA_PATH, DATE_PIC_PATH,\
    DATE_DATA_PATH, ADMIN_ROADS_PATH, ADMIN_DATA_PATH,\
    ADMIN_ZONES_PATH, JSON_DATA_PATH, LARGE_PIC_PATH,\
    SMALL_PIC_PATH, COLUMNS, ROWS, COLORS, BASE_DATE

# Global file data
admin_roads = ["", ""]

# Zone pixels, 25x25m, 1 band
admin_zones = []

# Administrative data
df_admin_data: 'pd.DataFrame' = None

# Gps polyline data with dates and coordinates
df_gps_data: 'pd.DataFrame' = None

# np array containing all possible residential roads by zone, 8bit value, zones are 1..255
np_visitable_byzones_uint8: 'np.NDArray' = None

# np array - is it visited? 0: not yet, 1: visited. stored as uint8
np_isdone_uint8: 'np.NDArray' = None

# visited pixels by first visit date, uint32, data in band 1 and 2
np_visited_bydate_uint32: 'np.NDArray' = None

# visited pixels, with zone info, uint8
np_visited_byzones_uint8: 'np.NDArray' = None


def load_local_files():
    """ Read files:
            * gpx_all:     gps routes
            * admin_data:  administrative data (rasterized admin boundaries)
            * admin_roads: road data (rasterized)"""

    global df_gps_data, df_admin_data, admin_roads, admin_zones

    print(f"Reading {GPS_DATA_PATH}...")

    df_gps_data = pd.read_csv(GPS_DATA_PATH, sep=",", dtype=str)

    print(f"Reading {ADMIN_DATA_PATH}...")
    df_admin_data = pd.read_csv(ADMIN_DATA_PATH, sep=";")

    print(f"Reading {ADMIN_ROADS_PATH}...")
    admin_roads_png = Image.open(ADMIN_ROADS_PATH)
    admin_roads = list(admin_roads_png.getdata())

    print(f"Reading {ADMIN_ZONES_PATH}...")
    admin_zones_png = Image.open(ADMIN_ZONES_PATH)
    admin_zones = list(admin_zones_png.getdata())


def convert_gps_to_pixel(lat, lon):
    """ Convert gps coordinates to pixel coordinate in image """
    lat2, lon2 = convert_gps_to_23700(lat, lon)

    latp = (252143 - lat2) / 25
    lonp = (lon2 - 640790.6) / 25

    return [lonp, latp]


def get_rasterized_from_gps():
    """ Rasterizes a GPX file, the result is an array of numbers with 0 and 1 pixels. """

    print(f"Rasterizing gpx file...")

    routes_walked_image = Image.new("RGBA", (COLUMNS, ROWS), 0)
    routes_walked_draw = ImageDraw.Draw(routes_walked_image)
    end = 0

    for index, row in df_gps_data.iterrows():
        pix_lat0, pix_lon0 = convert_gps_to_pixel(
            float(row['lat0']), float(row['lon0']))
        pix_lat1, pix_lon1 = convert_gps_to_pixel(
            float(row['lat1']), float(row['lon1']))

        shape = [(pix_lat0, pix_lon0), (pix_lat1, pix_lon1)]
        walk_date = date(int(row['edate'][:4]), int(
            row['edate'][4:6]), int(row['edate'][6:8]))
        delta = (walk_date - BASE_DATE).days
        color = (delta >> 16, (delta >> 8) & 0xff, delta & 0xff)
        routes_walked_draw.line(shape, fill=color, width=3)

    # routes_walked_image.save(DATE_PIC_PATH)
    np_dates = np.array(routes_walked_image.getdata(1)) * \
        0x100 + np.array(routes_walked_image.getdata(2))

    return np.array(np_dates, dtype='uint32')


def create_aggr_table():
    """ Set road length by administrative areas in the admin_data table """

    global np_visitable_byzones_uint8, np_isdone_uint8, np_visited_bydate_uint32

    np_visitable_byzones_uint8 = np.array(admin_roads, dtype='uint8')
    np_zone_data_uint8 = np.array(admin_zones, dtype='uint8')

    count_zones_all = Counter(np_visitable_byzones_uint8)

    df_admin_data['Total'] = df_admin_data['ID'].apply(
        lambda x: count_zones_all.get(x, 0))

    # Rasterize gps data, and keep only pixels in the proximity of residential roads.
    np_visited_bydate_uint32_raw = get_rasterized_from_gps()
    np_visited_bydate_uint32_raw[np_visited_bydate_uint32_raw ==
                                 0] = 0xff00ffff
    np_visited_bydate_uint32 = np_visited_bydate_uint32_raw * \
        (np_visitable_byzones_uint8 > 0)
    np_isdone_uint8 = (np_visited_bydate_uint32 > 0) & (
        np_visited_bydate_uint32 < 0xffff)

    # Save image - date info as RG, and zone info as B.
    # Kept a distinct file for zone data, size is not less with a single png file.
    # tmp_img_data = (np_visited_bydate_uint32  + 0xff000000) + np_zone_data_uint8 * 0x10000
    tmp_img_data = (np_visited_bydate_uint32 + 0xff000000) + \
        np_visitable_byzones_uint8 * 0x10000
    tmp_img_rgb = tmp_img_data.view(dtype='uint8').reshape((ROWS, COLUMNS, 4))
    save_array_to_rgba_image(tmp_img_rgb, DATE_PIC_PATH, "RGBA")

    min_date = 0
    # Get zone data

    """
    zone_data = {}
    for zone_id in range(1, len(count_zones_all)):
        np_visited_bydate_actzone = np_visited_bydate_uint32_raw * (np_visitable_byzones_uint8 == zone_id)
        date_list = Counter(np_visited_bydate_actzone)
        zone_data[zone_id] = date_list
    """

    date_pixels = Counter(np_visited_bydate_uint32)
    corrected_dict = {}

    for k, v in date_pixels.items():
        corrected_date = BASE_DATE + timedelta(days=int(k) & 0xffff)
        corrected_dict[corrected_date] = v

    # Write aggregated data
    df_date_freq = pd.DataFrame(
        {'date': corrected_dict.keys(), 'freq': corrected_dict.values()})
    df_date_freq['date'] = df_date_freq['date'].map(
        lambda d: d.strftime("%Y%m%d"))
    df_date_freq.to_json(DATE_DATA_PATH, orient='records')

    # Get finished pixels in each zone
    np_routes_done_zones = np_visitable_byzones_uint8 * np_isdone_uint8
    count_zones_done = Counter(np_routes_done_zones)

    # Add done and percentage finished to admin_data table
    df_admin_data['Done'] = df_admin_data['ID'].apply(
        lambda x: count_zones_done.get(x, 0))
    # df_admin_data['percentage'] = df_admin_data['done'] / df_admin_data['needed']

    print(f"Writing zone statistics to {JSON_DATA_PATH}...")
    df_admin_data.to_json(JSON_DATA_PATH, orient='records')


def create_large_result():
    global np_visited_byzones_uint8

    # Create colored map, red: not visited, green: completely visited, yellow: partially visited
    np_visited_byzones_uint8 = (
        np_visitable_byzones_uint8 > 0) * (np_isdone_uint8 + 1)
    np_result_rgba = list(map(lambda x: COLORS[x], np_visited_byzones_uint8))

    np_res_reshaped = np.array(
        np_result_rgba, dtype='uint8').reshape((ROWS, COLUMNS, 4))

    # Save image
    save_array_to_rgba_image(np_res_reshaped, LARGE_PIC_PATH, "RGBA")


def get_downscaled(np_source):
    """ Get a the downscaled list of numbers from the numpy array """
    new_pixels = []

    print("Downscaling gpx file...")
    for row in range(0, ROWS, 20):
        for column in range(0, COLUMNS, 20):
            boxData = np.array([], dtype='uint8')
            for line in range(20):
                pixelcount = 20
                start = (row + line) * COLUMNS + column
                sourceData = np_source[start: start + pixelcount]
                boxData = np.concatenate([sourceData, boxData])

            pixels = Counter(boxData)
            all_done = pixels.get(2, 0)
            to_be_done = pixels.get(1, 0)

            done_ratio = all_done / (all_done + to_be_done + 0.0001)

            # print(row, column, pixels, doneShare)
            new_pixel_color = 0

            if (all_done + to_be_done < 10):
                new_pixel_color = 0
            elif (done_ratio > 0.90):
                new_pixel_color = 2
            elif (done_ratio > 0.7):
                new_pixel_color = 3
            elif (done_ratio > 0.4):
                new_pixel_color = 4
            elif (done_ratio > 0.1):
                new_pixel_color = 5
            else:
                new_pixel_color = 1

            new_pixels.append(new_pixel_color)
    return new_pixels


def create_small_result():
    """ Create downscaled color map from 8bit numpy array """

    downscaled_list = get_downscaled(np_visited_byzones_uint8)

    # Convert values 0-2 to RGBA colors, and reshape flat list to 59x62 image
    rgba_list = list(map(lambda x: COLORS[x], downscaled_list))
    np_small_reshaped = np.array(rgba_list, dtype='uint8').reshape((59, 62, 4))

    save_array_to_rgba_image(np_small_reshaped, SMALL_PIC_PATH)


def convert_admin_data():
    """ Converts """
    zonedata = df_admin_data['Side'].str.slice(0, 1) +\
        df_admin_data['District'].str.replace(". kerület", "", regex=False) + \
        ";" + df_admin_data['Citypart']

    zoneraw = []

    for i in range(1, 204):
        zoneline = zonedata[df_admin_data['ID'] == i]
        if len(zoneline) == 0:
            zoneraw.append("")
        else:
            zoneraw.append(zoneline.iloc[0])

    with open(rf"{BASE_PATH}/zonedatastr.txt", "w") as f:
        f.write("|".join(zoneraw))


def write_to_s3():
    """ Write data to s3. """

    import boto3
    s3 = boto3.client('s3')

    """
    print("Uploading 'result_small.png' to S3...")
    s3.upload_file(SMALL_PIC_PATH, Bucket=BUCKET_NAME, Key="result_small.png")
    
    print("Uploading 'result.png' to S3...")
    s3.upload_file(LARGE_PIC_PATH, Bucket=BUCKET_NAME, Key="result.png")
    
    print("Uploading 'routes_done.json' to S3...")
    s3.upload_file(JSON_DATA_PATH, Bucket=BUCKET_NAME, Key="routes_done.json")

    print("Uploading 'date_stats.json' to S3...")
    s3.upload_file(DATE_DATA_PATH, Bucket=BUCKET_NAME, Key="date_stats.json")
    """

    print("Uploading 'date_result.png' to S3...")
    s3.upload_file(DATE_PIC_PATH, Bucket=BUCKET_NAME, Key="date_result.png")


def create_files(write_s3: bool):
    """ Main function, creates files.
     :param write_s3(bool) Whether to write files to S3. """

    load_local_files()
    convert_admin_data()
    create_aggr_table()
    create_large_result()
    create_small_result()

    if write_s3:
        print("Saving to s3.")
        write_to_s3()
    else:
        print("Saving to s3 disabled.")

    print("Done.")


if __name__ == "__main__":
    create_files(write_s3=True)
