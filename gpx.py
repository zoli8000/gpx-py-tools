# -*- coding: utf-8 -*-
"""
Created on Sat Oct  3 21:49:36 2020

@author: zolta
"""

import glob
from datetime import date

tod = False                     # Show today with different color


fc = 0
old_gpx = ""
today = ""
amazf = ""
distall = []
import re, math
import copy
find_points = (47.507845, 19.055050)


rx_coord = r"""<trkpt lat="(?P<lat>[^"]+)" lon="(?P<lon>[^"]+)"\s*>"""

def meter_distance_from_gps(lat1, lon1, lat2, lon2):    
    lat = (lat1 - lat2)  * 111319
    lon = 111319 * math.cos(lat1 / 180 * math.pi) * (lon1 - lon2) 
    
    return math.sqrt(lat**2 + lon**2)

err = []
points_found = {}

def _clean(s):
    global fname, err
        
    tolerance = 10                       # Minimum relevant distance in meters
    new_str = "<trkseg>\n"
    
    # Read coords
    coords = []    
    
    i = 0
    lastx, lasty = 0, 0 
    for m in re.finditer(rx_coord, s, flags = re.M + re.I):        
        (x, y) = (float(m.group('lat')), float(m.group('lon')))

        # Point finder        
        dist = math.sqrt((find_points[0] - x)**2 + (find_points[1] - y)**2)
        if dist < 0.00002:
            print(f"Point found: {fname}, {x} {y}, distance: {dist}")
            points_found[fname] = dist

        # Point to nearest line
        # abs((x -lastx)*(lasty-find_points[1])-(lastx-find_points[0])*(y-lasty)) / math.sqrt((x-lastx)**2+(y-lasty)**2)
        if (x-lastx)**2+(y-lasty)**2>0:
            
            px = x-lastx
            py = y-lasty
        
            norm = px*px + py*py
        
            u =  ((find_points[0] - lastx) * px + (find_points[1] - lasty) * py) / float(norm)
        
            if u > 1:
                u = 1
            elif u < 0:
                u = 0
        
            vx = lastx + u * px
            vy = lasty + u * py
        
            dx = vx - find_points[0]
            dy = vy - find_points[1]
        
            # Note: If the actual distance does not matter,
            # if you only want to compare what this function
            # returns to other results of this function, you
            # can just return the squared distance instead
            # (i.e. remove the sqrt) to gain a little performance
        
            dist = (dx*dx + dy*dy)**.5


            # dist = abs((x -lastx)*(lasty-find_points[1])-(lastx-find_points[0])*(y-lasty)) / math.sqrt((x-lastx)**2+(y-lasty)**2)
            if dist < 0.0005:
                print(f"Point found on line: {fname}, {x} {y}, {lastx} {lasty} distance: {dist}")
                points_found[fname] = dist

        if meter_distance_from_gps(lastx, lasty, x, y) > 500 and i>0:
            print(f"More than 0.5 km in {fname}!!!")
            err.append(fname)
            
        coords.append( (x, y) )                                
        lastx, lasty = x, y
        i += 1

    coords_raw = [c for c in coords]
    
    wrotex, wrotey = (0, 0)
    lastdegr = 0
    points = 1
    write_point = True


    # Coords2: new coords only at least 2.5 meters from last    
    coords2 = []    
    wrotex, wrotey = (0, 0)
    for c in coords:
        if meter_distance_from_gps(wrotex, wrotey, c[0], c[1]) > tolerance // 4:
            coords2.append( (c[0], c[1], 1) )
            (wrotex, wrotey) = c
    
    coords = coords2
        
    
    def recurse(m, n):       
        # if len(coords) == 0: return
        # Get first and last coords
        # print(f"Range {m}..{n}")
        nonlocal coords_raw
        if m==n: return
        
        try:
            p1_lat, p1_lon, t = coords[m]
        except:
            print(f"{m}..{n}, len: {len(coords)}")
        p2_lat, p2_lon, t = coords[n]
        
        d = math.sqrt( (p2_lon-p1_lon)**2 + (p2_lat-p1_lat)**2 )
        
        # tol_gps = tolerance 
        
        tol_gps = tolerance  / 111319
        
        c_temp = []
        dist_max = 0
        i_max = -1
        for i in range(m+1, n):
            p_lat, p_lon, rel = coords[i]
            if rel == 0: continue
        
            dist = abs((p2_lon - p1_lon) * p_lat - (p2_lat - p1_lat) * p_lon + p2_lat * p1_lon - p2_lon * p1_lat) / d
            
            c_temp.append( (p_lat, p_lon, dist) )
                                    
            if dist > dist_max:
                dist_max = dist
                i_max = i
            
        if i_max == -1: return
        
        # print(f"Max: {i_max}")
        
        if dist_max < tol_gps:
            # print (f"Line: {m}, {n}")
            for i in range(m+1, n):
                coords[i] = (coords[i][0], coords[i][1], 0)
            return
                
        return recurse(m, i_max) or recurse(i_max, n)
        
    recurse (0, len(coords)-1)
    
    coords2 = []
    for c in coords:
        if c[2] == 1:
            coords2.append( (c[0], c[1]))
    
    coords = coords2
        
    for i in range(len(coords)):
        lat, lon = coords[i]
        new_str += f"""  <trkpt lat="{lat:8.5f}" lon="{lon:8.5f}"></trkpt>\n"""
        
        """
        if i > 0:
            lat0, lon0, t = coords[i-1]
            dist = meter_distance_from_gps(lat0, lon0, lat, lon)
        
        # Too far away - add a segment break
        if dist > 0.003:
            new_str += "</trkseg>\n<trkseg>\n"                                 
        """
    new_str += "</trkseg>\n"
    
    return new_str
    
    """
    add_str = "</trkseg>\n<trkseg>\n"
    corr_len = 0
    
    for i in correction:
        fr = i + corr_len
        s = s[:fr] + add_str + s[fr:]
        corr_len += len(add_str)
    
    return s
    """
    

correction = False

# correction = True

if correction:
    import webbrowser
    # https://opoto.github.io/wtracks/
    webbrowser.open('https://opoto.github.io/wtracks/')

for fname in glob.glob(f"""C:/Users/zolta/Downloads/gpx/{"jav/" if correction else ""}*.gpx"""):
    date.today().strftime("yyyy")
    print(fname)    
    tod_str = "Amazfit"+date.strftime(date.today(), "%Y%m%d")
    
    is_today = False
    if (fname.split('\\')[-1][:len(tod_str)] == tod_str) and tod:
        is_today = True
        print(f"Today: {fname}")
    
    # if fname.split('\\')[-1] != "Amazfit20201003205358.gpx": continue
    
    with open(fname, "r") as f:
        f_lines = f.readlines()        
        
        if "Amazfit" in fname or "Zepp" in fname:            
            """
            gpx = ""
            i = 3
            while i < len(f_lines):
                gpx += ''.join(f_lines[i:i+4])
                i += 70
                        
            chk = gpx.split('\n')
            i = 0
            
            while not 'trkseg' in chk[0] :                
                chk.remove(0)                                
            
            i = len(chk)
            while not 'trkseg' in chk[i-1]:
                chk.pop()
                i -= 1
            gpx = '\n'.join(chk)
            """
            gpx = '\n'.join(f_lines)
                
        else:                
            txt = "".join(f_lines)
            start = txt.find("<trk")
            start = txt.find("<trkseg", start+5)
            
            end = txt.rfind("</trk")
            gpx = (txt[start:end])

        gpx = _clean(gpx)        
        if is_today:
            today += gpx
        elif  "Amazfit" in fname:  
            amazf += gpx
        elif  "Zepp" in fname:  
            amazf += gpx
        else:
            old_gpx += ""
    fc += 1


old_gpx = """
<trkseg>
<trkpt lat="47.48282" lon="19.01249"></trkpt>
</trkseg>
"""

if correction:
    file_txt = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<gpx>
	<trk >
""" + amazf + today + old_gpx + """
    </trk>
</gpx>"""
else:        
    file_txt = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<gpx xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" xmlns="http://www.topografix.com/GPX/1/1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:ns2="http://www.garmin.com/xmlschemas/GpxExtensions/v3" xmlns:ns1="http://www.cluetrust.com/XML/GPXDATA/1/0" creator="Amazfit App" version="4.3.0" >
	<trk ><name>Old</name>
""" + old_gpx + """
</trk>
<trk ><name>Amazfit</name>
""" + amazf + """
</trk>
<trk ><name>Today</name>
""" + today + """
</trk>
</gpx>"""

print(f"{fc} files read, file wrote.")

# points_found = list(points_found)
output_file = f"""C:/Users/zolta/Downloads/{"proba" if correction else "gpx_all"}.gpx"""
with open (output_file, "w") as f:
    f.write(file_txt)
    
if (not correction):
    import shutil
    shutil.copy2(output_file, "C:/Users/zolta/OneDrive/gpx_all.gpx")
