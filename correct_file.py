import glob
import os
import ntpath
import webbrowser
from gps_utils import simplify_gpx_route

# Use BASE_PATH to define root directory for input and output files
ONE_DRIVE_PATH = os.environ['ONEDRIVE']
BASE_PATH = rf"{ONE_DRIVE_PATH}/tmp_bp"
CORRECTION_PATH = rf"{BASE_PATH}/gpx/jav"
SIMPLIFIED_PATH = rf"{os.environ['TMP']}/"

for fname in glob.glob(rf"{CORRECTION_PATH}/*.gpx"""):
    with open(fname, "r") as f:
        print(f"Simplifying file {fname} for correction...")   
        f_lines = f.read()        
    
    gpx_coords = simplify_gpx_route(f_lines)

    simplified_gpx_data = "<trkseg>\n"
    
    for i in range(len(gpx_coords)):
        lat, lon = gpx_coords[i]
        simplified_gpx_data += f"""  <trkpt lat="{lat:8.5f}" lon="{lon:8.5f}"></trkpt>\n"""
        
    simplified_gpx_data += "</trkseg>\n"

    file_txt = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <gpx>
        <trk >
    """ + simplified_gpx_data + """
        </trk>
    </gpx>"""

    output_filename = SIMPLIFIED_PATH + "/simplified_" + ntpath.basename(fname)
    with open(output_filename, "w") as f:
        f.write(file_txt)

    print(f"Output is in {output_filename}")
    print(f"Directory: {SIMPLIFIED_PATH}")

# https://opoto.github.io/wtracks/
webbrowser.open('https://opoto.github.io/wtracks/')

