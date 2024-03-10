import math
import re

from PIL import Image, ImageDraw


def save_array_to_rgba_image(
    np_array: 'np.NDArray',
    dest_path: str,
    img_format: str = "RGBA",
    expand_multiplier=(1, 1)
):
    """ Save np array as an RGBA image

    Args:
        np_array (np.NDArray): source np_array
        dest_path (str): output file path
        img_format (str): image format for PIL. Defaults to "RGBA".
        expand_multiplier (tuple): size expanded to be divisable by this. 
        Defaults to (1, 1).
    """
    print(f"Saving image as {dest_path}...")
    base_img = Image.fromarray(np_array, img_format)

    expand_rows, expand_cols = expand_multiplier
    base_rows, base_cols = np_array.shape[0], np_array.shape[1]

    dest_rows = (base_rows // expand_rows) * expand_rows
    dest_cols = (base_cols // expand_cols) * expand_cols

    if dest_rows < base_rows:
        dest_rows += expand_rows

    if dest_cols < base_cols:
        dest_cols += expand_cols

    dest_img = Image.new(base_img.mode, (dest_cols, dest_rows))
    dest_img.paste(base_img, (0, 0))

    dest_img.save(dest_path, optimize=True)


def convert_gps_to_23700(lat: float, lon: float):
    """ Simplified convert from (EPSG:4326) to compressed meter-based EPSG:23700. """
    ymulti = 111188  # (max_my / max_gpsy)
    xmulti = 75334  # (max_mx / max_gpsx)

    lat23700 = (lat - 47.144433) * ymulti + 200029
    lon23700 = (lon - 18.931005) * xmulti + 641228

    # print(lon23700, lat23700)
    return [lat23700, lon23700]


def gps_estimated_meter_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """ Estimated distance in meters """

    lat_diff = (lat1 - lat2) * 111319
    lon_diff = 111319 * math.cos(lat1 / 180 * math.pi) * (lon1 - lon2)

    return math.sqrt(lat_diff ** 2 + lon_diff ** 2)


def convert_gpx_to_coords(gpx_string: str, silent=True):
    """ Converts a gpx string to lat, lon coordinates """
    coords = []
    rx_coord = r"""<trkpt lat="(?P<lat>[^"]+)" lon="(?P<lon>[^"]+)"\s*>"""

    i = 0
    last_lat, last_lon = 0, 0

    for m in re.finditer(rx_coord, gpx_string, flags=re.M + re.I):
        (lat, lon) = (float(m.group('lat')), float(m.group('lon')))

        distance_m = gps_estimated_meter_distance(last_lat, last_lon, lat, lon)
        if distance_m > 500 and i > 0 and not silent:
            raise ValueError("Distance more than 0.5 km")

        coords.append((lat, lon))
        last_lat, last_lon = lat, lon
        i += 1

    return coords


def filter_coords_with_min_distance(coords: list, min_distance_m=2.5):
    """Filters distances lower than min_distance

    Args:
        coords (_type_): list of coordinates
        min_distance_m (float, optional): Minimum distance in meters. Defaults to 2.5.

    Returns:
        _type_: _description_
    """
    filtered_coords = []
    wrotex, wrotey = (0, 0)

    for c in coords:
        if gps_estimated_meter_distance(wrotex, wrotey, c[0], c[1]) >= min_distance_m:
            filtered_coords.append((c[0], c[1], 1))
            (wrotex, wrotey) = c

    return filtered_coords


def simplify_geometry(coords: list, m: int, n: int, tolerance_m=2.5):
    """ Simplify geometry between indexes m and n in list

    Args:
        coords (_type_): _description_
        m (int): _description_
        n (int): _description_
        tolerance (float, optional): tolerance in meters. Defaults to 2.5.

    Returns:
        _type_: simpified list
    """

    def simplify_geometry_recurse(coords, m: int, n: int, tolerance_m):
        if m == n:
            return

        try:
            p1_lat, p1_lon, t = coords[m]
        except Exception as e:
            print(f"{m}..{n}, len: {len(coords)}")

        p2_lat, p2_lon, t = coords[n]

        d = math.sqrt((p2_lon - p1_lon) ** 2 + (p2_lat - p1_lat) ** 2)

        tol_gps = tolerance_m / 111319

        dist_max = 0
        i_max = -1

        for i in range(m + 1, n):
            p_lat, p_lon, rel = coords[i]
            if rel == 0:
                continue

            dist = abs((p2_lon - p1_lon) * p_lat - (p2_lat - p1_lat)
                       * p_lon + p2_lat * p1_lon - p2_lon * p1_lat) / d

            if dist > dist_max:
                dist_max = dist
                i_max = i

        if i_max == -1:
            return

        # print(f"Max: {i_max}")

        if dist_max < tol_gps:
            # print (f"Line: {m}, {n}")
            for i in range(m+1, n):
                coords[i] = (coords[i][0], coords[i][1], 0)
            return

        return simplify_geometry_recurse(coords, m, i_max, tolerance_m)\
            or simplify_geometry_recurse(coords, i_max, n, tolerance_m)

    new_coords = []
    for c in coords:
        new_coords.append([item for item in c])

    # Mark items to be kept or removed
    simplify_geometry_recurse(new_coords, m, n, tolerance_m)

    # Keep only coords marked to keep
    filtered_coords = [(c[0], c[1]) for c in new_coords if c[2] == 1]

    return filtered_coords


def simplify_gpx_route(gpx_string: str, tolerance=2.5):
    """ Simplifies a gpx file, reduces detail and simplifies geometry

    Args:
        gpx_string (str): string with gpx data to be simplified
        tolerance (float, optional): tolerance in meters. Defaults to 2.5.

    Returns:
        _type_: list of coords
    """
    global fname, err

    # Gather coordinates, and prefilter with distance
    coords = convert_gpx_to_coords(gpx_string)
    coords = filter_coords_with_min_distance(coords, min_distance_m=tolerance)

    simplified_coords = simplify_geometry(
        coords, 0, len(coords)-1, tolerance * 4)

    return simplified_coords
