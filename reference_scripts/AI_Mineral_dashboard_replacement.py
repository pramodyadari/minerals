import os
import csv
import math
import json
import numpy as np
import streamlit as st

# Optional libraries used by the project
try:
    import requests
except Exception:
    requests = None

try:
    import rasterio
except Exception:
    rasterio = None

try:
    import plotly.graph_objects as go
except Exception:
    go = None

try:
    from sklearn.ensemble import RandomForestClassifier
    import joblib
except Exception:
    RandomForestClassifier = None
    joblib = None


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="AI Mineral Intelligence",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# PATHS
# ============================================================
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PROSPECTIVITY_PATH = os.path.join(
    ROOT, "data", "processed", "prospectivity_map.npy"
)
ZONES_PATH = os.path.join(
    ROOT, "outputs", "high_prospectivity_zones.csv"
)
B04_PATH = os.path.join(
    ROOT, "data", "raw",
    "T44QMK_20260621T050649_B04_20m.jp2"
)
PRODUCTION_MODEL_PATH = os.path.join(
    ROOT, "models", "production_random_forest.pkl"
)

# ============================================================
# KNOWN PROJECT LOCATION / FALLBACK
# ============================================================
KNOWN_MINE_LAT = 21.9455
KNOWN_MINE_LON = 80.4295

# ============================================================
# SUPPORTED MINERALS
# ============================================================
SUPPORTED_MINERALS = [
    "Manganese",
    "Bauxite",
    "Limestone",
    "Coal",
]

# ============================================================
# CUSTOM CSS
# ============================================================
st.markdown(
    """
    <style>
    .main {
        background: #0e1117;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }

    .hero {
        padding: 1.2rem 1.4rem;
        border-radius: 18px;
        border: 1px solid #303642;
        background: linear-gradient(135deg, #151a24, #10141c);
        margin-bottom: 1.4rem;
    }

    .hero h1 {
        margin: 0;
        font-size: 2.4rem;
    }

    .hero p {
        margin: .45rem 0 0 0;
        color: #aeb7c5;
        font-size: 1.05rem;
    }

    .metric-card {
        padding: 1.2rem;
        border: 1px solid #303642;
        border-radius: 16px;
        background: #151a24;
        min-height: 135px;
    }

    .metric-title {
        color: #9da7b5;
        font-size: .85rem;
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-top: .35rem;
    }

    .metric-note {
        color: #aeb7c5;
        font-size: .85rem;
        margin-top: .25rem;
    }

    .info-card {
        padding: 1.2rem;
        border-radius: 16px;
        border: 1px solid #303642;
        background: #151a24;
        margin-top: .7rem;
        margin-bottom: .7rem;
    }

    .small-note {
        color: #9da7b5;
        font-size: .88rem;
    }

    .status-good {
        color: #8bd17c;
        font-weight: 600;
    }

    .status-warn {
        color: #f0c674;
        font-weight: 600;
    }

    .status-bad {
        color: #ee8b8b;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================
@st.cache_data(show_spinner=False)
def load_prospectivity():
    if not os.path.exists(PROSPECTIVITY_PATH):
        return None
    try:
        arr = np.load(PROSPECTIVITY_PATH)
        arr = np.asarray(arr, dtype=np.float32)
        if arr.ndim > 2:
            arr = np.squeeze(arr)
        return arr
    except Exception:
        return None


@st.cache_resource(show_spinner=False)
def load_reference_raster():
    """
    B04 is used only as the geospatial reference:
    CRS + transform + bounds + pixel coordinates.

    It is NOT used as the AI prospectivity value.
    """
    if rasterio is None or not os.path.exists(B04_PATH):
        return None

    try:
        src = rasterio.open(B04_PATH)
        return src
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_zones():
    if not os.path.exists(ZONES_PATH):
        return []

    rows = []
    try:
        with open(ZONES_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception:
        return []

    return rows


def clamp(v, low, high):
    return max(low, min(high, v))


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def parse_coordinates(text):
    """
    Accepts:
      21.9455, 80.4295
      21.9455 80.4295
    """
    if not text:
        return None, None

    cleaned = (
        text.strip()
        .replace(";", ",")
        .replace("/", ",")
    )

    parts = [p.strip() for p in cleaned.replace(",", " ").split()]

    if len(parts) < 2:
        return None, None

    try:
        lat = float(parts[0])
        lon = float(parts[1])

        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
    except Exception:
        pass

    return None, None


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_place(place):
    """
    Normal location search using Nominatim.
    No Streamlit custom component is used.
    """
    if requests is None or not place.strip():
        return None

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": place.strip(),
                "format": "jsonv2",
                "limit": 1,
            },
            headers={
                "User-Agent": "AI-Mineral-Intelligence-Student-Project/1.0"
            },
            timeout=8,
        )

        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        return {
            "lat": float(data[0]["lat"]),
            "lon": float(data[0]["lon"]),
            "display": data[0].get("display_name", place),
        }

    except Exception:
        return None


def location_to_pixel(lat, lon, raster):
    """
    Convert WGS84 latitude/longitude to the Sentinel-2 raster
    pixel using the actual raster CRS and transform.

    This is what makes the 3D view location-dependent.
    """
    if raster is None or rasterio is None:
        return None

    try:
        xs, ys = rasterio.warp.transform(
            "EPSG:4326",
            raster.crs,
            [lon],
            [lat],
        )

        x = xs[0]
        y = ys[0]

        row, col = raster.index(x, y)

        if (
            row < 0
            or col < 0
            or row >= raster.height
            or col >= raster.width
        ):
            return None

        return {
            "row": int(row),
            "col": int(col),
            "x": float(x),
            "y": float(y),
        }

    except Exception:
        return None


def prospectivity_at_location(lat, lon, raster, prospectivity):
    pixel = location_to_pixel(lat, lon, raster)

    if pixel is None or prospectivity is None:
        return None, None

    r = pixel["row"]
    c = pixel["col"]

    if (
        r >= prospectivity.shape[0]
        or c >= prospectivity.shape[1]
    ):
        return None, pixel

    value = float(prospectivity[r, c])

    # Handle models stored as 0-1 or 0-100.
    if value > 1.5:
        value = value / 100.0

    value = clamp(value, 0.0, 1.0)

    return value, pixel


def classify_score(score):
    if score >= 0.95:
        return "VERY HIGH"
    if score >= 0.90:
        return "HIGH"
    if score >= 0.70:
        return "MODERATE"
    if score >= 0.40:
        return "LOW"
    return "VERY LOW"


def score_description(score):
    if score >= 0.95:
        return "Very strong AI prospectivity indication."
    if score >= 0.90:
        return "Strong AI prospectivity indication."
    if score >= 0.70:
        return "Moderate AI prospectivity indication."
    if score >= 0.40:
        return "Lower AI prospectivity indication."
    return "Very low AI prospectivity indication."


def get_local_surface(
    prospectivity,
    row,
    col,
    radius_pixels=90,
    output_size=110,
):
    """
    Extract a location-specific window from the real prospectivity
    raster and resize it for a fast interactive 3D display.

    IMPORTANT:
    The surface is NOT randomly generated.
    Every displayed 3D value comes from the saved AI prospectivity raster.
    """
    if prospectivity is None:
        return None

    h, w = prospectivity.shape

    radius_pixels = int(
        clamp(radius_pixels, 20, min(h, w) // 2)
    )

    r0 = max(0, row - radius_pixels)
    r1 = min(h, row + radius_pixels + 1)
    c0 = max(0, col - radius_pixels)
    c1 = min(w, col + radius_pixels + 1)

    crop = prospectivity[r0:r1, c0:c1]

    if crop.size == 0:
        return None

    crop = np.nan_to_num(
        crop,
        nan=0.0,
        posinf=1.0,
        neginf=0.0,
    )

    if np.nanmax(crop) > 1.5:
        crop = crop / 100.0

    crop = np.clip(crop, 0, 1)

    # Downsample without scipy.
    rows = np.linspace(
        0, crop.shape[0] - 1,
        min(output_size, crop.shape[0])
    ).astype(int)

    cols = np.linspace(
        0, crop.shape[1] - 1,
        min(output_size, crop.shape[1])
    ).astype(int)

    surface = crop[np.ix_(rows, cols)]

    return surface


def make_3d_figure(surface, title):
    if go is None or surface is None:
        return None

    h, w = surface.shape

    x = np.arange(w)
    y = np.arange(h)

    # Vertical exaggeration makes prospectivity differences visible,
    # while z still represents the AI score.
    z = surface * 100.0

    fig = go.Figure(
        data=[
            go.Surface(
                x=x,
                y=y,
                z=z,
                surfacecolor=z,
                colorscale=[
                    [0.00, "#2f6b2f"],
                    [0.25, "#78a85a"],
                    [0.50, "#e0cf54"],
                    [0.75, "#f0a23a"],
                    [1.00, "#b9362d"],
                ],
                cmin=0,
                cmax=100,
                colorbar={
                    "title": "AI Prospectivity",
                    "ticksuffix": "%",
                },
                hovertemplate=(
                    "Raster X: %{x}<br>"
                    "Raster Y: %{y}<br>"
                    "AI Prospectivity: %{z:.1f}%"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig.update_layout(
        title=title,
        height=650,
        margin=dict(l=0, r=0, t=60, b=0),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#e7eaf0"),
        scene=dict(
            xaxis_title="Local raster X",
            yaxis_title="Local raster Y",
            zaxis_title="AI prospectivity (%)",
            zaxis=dict(range=[0, 100]),
            camera=dict(
                eye=dict(x=1.55, y=1.55, z=1.15)
            ),
            bgcolor="#0e1117",
        ),
    )

    return fig


def count_supporting_pixels(surface, threshold=0.70):
    if surface is None:
        return 0
    return int(np.sum(surface >= threshold))


def count_candidate_zones(rows, lat, lon, radius_km):
    """
    Count CSV candidate zones that are inside the selected radius.
    Handles common latitude/longitude column names.
    """
    if not rows:
        return 0

    count = 0

    for row in rows:
        try:
            keys = {str(k).lower().strip(): k for k in row.keys()}

            lat_key = None
            lon_key = None

            for candidate in [
                "latitude", "lat", "center_lat", "zone_lat"
            ]:
                if candidate in keys:
                    lat_key = keys[candidate]
                    break

            for candidate in [
                "longitude", "lon", "lng",
                "center_lon", "zone_lon"
            ]:
                if candidate in keys:
                    lon_key = keys[candidate]
                    break

            if lat_key is None or lon_key is None:
                continue

            zlat = float(row[lat_key])
            zlon = float(row[lon_key])

            d = haversine_km(lat, lon, zlat, zlon)

            if d <= radius_km:
                count += 1

        except Exception:
            continue

    return count


def nearest_zone_distance(rows, lat, lon):
    if not rows:
        return None

    best = None

    for row in rows:
        try:
            keys = {str(k).lower().strip(): k for k in row.keys()}

            lat_key = next(
                (
                    keys[x]
                    for x in [
                        "latitude",
                        "lat",
                        "center_lat",
                        "zone_lat",
                    ]
                    if x in keys
                ),
                None,
            )

            lon_key = next(
                (
                    keys[x]
                    for x in [
                        "longitude",
                        "lon",
                        "lng",
                        "center_lon",
                        "zone_lon",
                    ]
                    if x in keys
                ),
                None,
            )

            if lat_key is None or lon_key is None:
                continue

            d = haversine_km(
                lat,
                lon,
                float(row[lat_key]),
                float(row[lon_key]),
            )

            if best is None or d < best:
                best = d

        except Exception:
            continue

    return best


# ============================================================
# SESSION STATE
# ============================================================
if "selected_lat" not in st.session_state:
    st.session_state.selected_lat = KNOWN_MINE_LAT

if "selected_lon" not in st.session_state:
    st.session_state.selected_lon = KNOWN_MINE_LON

if "selected_place" not in st.session_state:
    st.session_state.selected_place = "Known project reference area"

if "location_search" not in st.session_state:
    st.session_state.location_search = ""


# ============================================================
# LOAD DATA
# ============================================================
prospectivity = load_prospectivity()
reference_raster = load_reference_raster()
zones = load_zones()


# ============================================================
# HEADER
# ============================================================
st.markdown(
    """
    <div class="hero">
        <h1>⛏️ AI Mineral Intelligence</h1>
        <p>
            AI-assisted mineral prospectivity, location analysis,
            visualization and exploration decision support.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOCATION SECTION
# ============================================================
st.subheader("📍 Search Location")

col1, col2 = st.columns([4, 1])

with col1:
    place_text = st.text_input(
        "Place, city, district or latitude/longitude",
        placeholder="Example: Nagpur, Balaghat, Hyderabad or 21.9455, 80.4295",
        key="place_input",
    )

with col2:
    st.write("")
    st.write("")
    find_clicked = st.button(
        "Find Location",
        use_container_width=True,
    )

if find_clicked and place_text.strip():
    lat, lon = parse_coordinates(place_text)

    if lat is not None and lon is not None:
        st.session_state.selected_lat = lat
        st.session_state.selected_lon = lon
        st.session_state.selected_place = "Manual coordinates"
        st.success(
            f"Location selected: {lat:.6f}, {lon:.6f}"
        )
    else:
        result = geocode_place(place_text)

        if result:
            st.session_state.selected_lat = result["lat"]
            st.session_state.selected_lon = result["lon"]
            st.session_state.selected_place = result["display"]

            st.success(
                f"Location found: {result['display']}"
            )
        else:
            st.error(
                "Location could not be found. "
                "Try a place name or enter latitude, longitude."
            )


# ============================================================
# MANUAL LOCATION CONTROLS
# ============================================================
with st.expander("Use latitude / longitude manually"):
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        manual_lat = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=float(st.session_state.selected_lat),
            format="%.6f",
        )

    with c2:
        manual_lon = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=float(st.session_state.selected_lon),
            format="%.6f",
        )

    with c3:
        st.write("")
        st.write("")
        if st.button("Use Coordinates"):
            st.session_state.selected_lat = float(manual_lat)
            st.session_state.selected_lon = float(manual_lon)
            st.session_state.selected_place = "Manual coordinates"
            st.rerun()


# ============================================================
# ANALYSIS SETTINGS
# ============================================================
st.subheader("⚙️ Analysis Settings")

c1, c2 = st.columns(2)

with c1:
    radius_label = st.selectbox(
        "Analysis Radius",
        ["10 km", "25 km", "50 km", "100 km"],
        index=3,
    )

radius_km = int(radius_label.split()[0])

with c2:
    mineral = st.selectbox(
        "Select Mineral",
        SUPPORTED_MINERALS,
        index=0,
    )


# ============================================================
# SELECTED AREA
# ============================================================
st.subheader("📌 Selected Area")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Latitude",
        f"{st.session_state.selected_lat:.6f}",
    )

with c2:
    st.metric(
        "Longitude",
        f"{st.session_state.selected_lon:.6f}",
    )

with c3:
    st.metric(
        "Radius",
        f"{radius_km} km",
    )

st.caption(
    f"Selected location: {st.session_state.selected_place}"
)


# ============================================================
# MAP
# ============================================================
st.subheader("🗺️ Selected Location Map")

map_data = {
    "latitude": [st.session_state.selected_lat],
    "longitude": [st.session_state.selected_lon],
}

st.map(map_data, zoom=7 if radius_km >= 50 else 9)


# ============================================================
# MODEL STATUS
# ============================================================
st.subheader("🤖 AI Model Status")

if mineral == "Manganese" and prospectivity is not None:
    st.success(
        "Manganese prospectivity model is active."
    )
elif mineral != "Manganese":
    st.info(
        f"{mineral} is available in the interface, "
        "but the current trained prospectivity raster is for Manganese."
    )
else:
    st.warning(
        "The Manganese prospectivity raster could not be loaded."
    )


# ============================================================
# LOCATION-SPECIFIC PROSPECTIVITY
# ============================================================
score = None
selected_pixel = None
local_surface = None

if mineral == "Manganese" and prospectivity is not None:
    score, selected_pixel = prospectivity_at_location(
        st.session_state.selected_lat,
        st.session_state.selected_lon,
        reference_raster,
        prospectivity,
    )

    if selected_pixel is not None:
        # About 100 x 100 pixels gives a fast but detailed local surface.
        local_surface = get_local_surface(
            prospectivity,
            selected_pixel["row"],
            selected_pixel["col"],
            radius_pixels=100,
            output_size=110,
        )


# ============================================================
# INTELLIGENCE SCORE
# ============================================================
st.subheader("🧠 Mineral Intelligence Analysis")

if score is not None:
    intelligence_score = score * 100
    intelligence_level = classify_score(score)

    support_pixels = count_supporting_pixels(
        local_surface,
        threshold=0.70,
    )

    candidate_zones = count_candidate_zones(
        zones,
        st.session_state.selected_lat,
        st.session_state.selected_lon,
        radius_km,
    )

    nearest_distance = nearest_zone_distance(
        zones,
        st.session_state.selected_lat,
        st.session_state.selected_lon,
    )

    st.markdown(
        f"""
        <div class="metric-card" style="text-align:center;">
            <div class="metric-title">
                Mineral Intelligence Score
            </div>
            <div class="metric-value">
                {intelligence_score:.1f}/100
            </div>
            <div>{intelligence_level} PROSPECTIVITY</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Local AI Prospectivity
                </div>
                <div class="metric-value">
                    {intelligence_score:.1f}%
                </div>
                <div class="metric-note">
                    Value at selected raster location
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Supporting Pixels
                </div>
                <div class="metric-value">
                    {support_pixels:,}
                </div>
                <div class="metric-note">
                    Local pixels above 70%
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    Candidate Zones
                </div>
                <div class="metric-value">
                    {candidate_zones}
                </div>
                <div class="metric-note">
                    Within selected radius
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # EXPLAINABLE AI
    # ========================================================
    st.subheader("🔎 Explainable AI")

    st.markdown(
        f"""
        <div class="info-card">
            <h4>AI Interpretation</h4>
            <p>
                The selected location has an AI prospectivity score of
                <b>{intelligence_score:.1f}%</b>.
                The score is derived from the trained prospectivity raster
                generated from the project's Sentinel-2 satellite features.
            </p>
            <p>
                Current interpretation:
                <b>{score_description(score)}</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    e1, e2 = st.columns(2)

    with e1:
        st.markdown(
            """
            <div class="info-card">
                <h4>🛰️ Satellite / Spectral Evidence</h4>
                <p>
                    The project uses Sentinel-2 spectral bands including
                    B4, B5, B6, B8A, B11 and B12.
                </p>
                <p>
                    Derived features include vegetation/moisture and
                    SWIR-related spectral information such as NDVI,
                    NDMI and SWIR ratios.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with e2:
        nearest_text = (
            f"{nearest_distance:.1f} km"
            if nearest_distance is not None
            else "No zone distance available"
        )

        st.markdown(
            f"""
            <div class="info-card">
                <h4>📍 Candidate-Zone Support</h4>
                <p>
                    Candidate zones detected inside the selected
                    {radius_km} km analysis radius:
                    <b>{candidate_zones}</b>
                </p>
                <p>
                    Nearest available candidate zone:
                    <b>{nearest_text}</b>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # 3D PROSPECTIVITY
    # ========================================================
    st.subheader("🧊 3D Mineral Prospectivity Visualization")

    st.caption(
        "This 3D view is generated from the local portion of the "
        "AI prospectivity raster around the selected location. "
        "Changing the location changes the displayed surface."
    )

    if local_surface is not None and go is not None:
        fig = make_3d_figure(
            local_surface,
            (
                f"Local {mineral} Prospectivity Surface — "
                f"{st.session_state.selected_lat:.4f}, "
                f"{st.session_state.selected_lon:.4f}"
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
            },
        )

        st.markdown(
            """
            <div class="info-card">
                <h4>How to read the 3D view</h4>
                <p>
                    • Green = lower AI prospectivity<br>
                    • Yellow = moderate AI prospectivity<br>
                    • Orange = high AI prospectivity<br>
                    • Red = very high AI prospectivity
                </p>
                <p class="small-note">
                    The vertical axis represents the AI prospectivity
                    score, not the physical depth of an underground ore body.
                    This is an exploration-support visualization, not a
                    confirmed geological model.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if selected_pixel is not None:
            st.caption(
                f"Sentinel-2 raster pixel used for this location: "
                f"row {selected_pixel['row']}, "
                f"column {selected_pixel['col']}."
            )

    elif mineral == "Manganese" and reference_raster is None:
        st.warning(
            "The Sentinel-2 B04 reference raster is not available, "
            "so the selected latitude/longitude cannot be converted "
            "to a raster position."
        )
    elif mineral == "Manganese":
        st.warning(
            "The selected location is outside the current Sentinel-2 "
            "T44QMK raster coverage. Select a location inside the "
            "available study area to see its location-specific 3D surface."
        )

else:
    if mineral == "Manganese":
        st.warning(
            "No location-specific prospectivity value is available "
            "for the selected location."
        )
    else:
        st.info(
            f"The current trained raster model is for Manganese. "
            f"The {mineral} interface is prepared for future mineral-specific models."
        )


# ============================================================
# PROSPECTIVITY LEGEND
# ============================================================
st.subheader("🎨 Prospectivity Legend")

legend_cols = st.columns(5)

legend_items = [
    ("Very Low", "0–40%"),
    ("Low", "40–70%"),
    ("Moderate", "70–90%"),
    ("High", "90–95%"),
    ("Very High", "95–100%"),
]

for col, (name, value) in zip(legend_cols, legend_items):
    with col:
        st.markdown(
            f"""
            <div class="info-card">
                <b>{name}</b><br>
                <span class="small-note">{value}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# PRODUCTION SHORTFALL
# ============================================================
st.subheader("🏭 Production Shortfall Analysis")

if os.path.exists(PRODUCTION_MODEL_PATH) and joblib is not None:
    st.caption(
        "Uses the trained production Random Forest model from the project."
    )

    p1, p2, p3 = st.columns(3)

    with p1:
        rainfall = st.number_input(
            "Rainfall (mm)",
            min_value=0.0,
            value=150.0,
        )

    with p2:
        downtime = st.number_input(
            "Equipment Downtime (hr)",
            min_value=0.0,
            value=20.0,
        )

    with p3:
        blasting_delay = st.number_input(
            "Blasting Delay (hr)",
            min_value=0.0,
            value=8.0,
        )

    p4, p5 = st.columns(2)

    with p4:
        availability = st.number_input(
            "Equipment Availability (%)",
            min_value=0.0,
            max_value=100.0,
            value=85.0,
        )

    with p5:
        planned = st.number_input(
            "Planned Production (tonnes)",
            min_value=0.0,
            value=11000.0,
        )

    if st.button(
        "Predict Production Shortfall",
        use_container_width=True,
    ):
        try:
            model = joblib.load(PRODUCTION_MODEL_PATH)

            features = np.array(
                [[
                    rainfall,
                    downtime,
                    blasting_delay,
                    availability,
                    planned,
                ]],
                dtype=float,
            )

            predicted = float(model.predict(features)[0])
            shortfall = max(0.0, planned - predicted)

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "Predicted Production",
                    f"{predicted:,.0f} t",
                )

            with c2:
                st.metric(
                    "Expected Shortfall",
                    f"{shortfall:,.0f} t",
                )

            with c3:
                risk = (
                    "High"
                    if shortfall / max(planned, 1) >= 0.15
                    else "Moderate"
                    if shortfall / max(planned, 1) >= 0.07
                    else "Low"
                )
                st.metric(
                    "Shortfall Risk",
                    risk,
                )

        except Exception as e:
            st.error(
                f"Production model could not be loaded: {e}"
            )
else:
    st.info(
        "Production model file not found. The prospectivity dashboard "
        "can still be used."
    )


# ============================================================
# PROJECT NOTES
# ============================================================
st.subheader("ℹ️ Project Notes")

st.markdown(
    """
    <div class="info-card">
        <h4>Current implementation</h4>
        <ul>
            <li>Location search uses a normal text input and geocoding request.</li>
            <li>No Streamlit custom searchbox component is required.</li>
            <li>No Streamlit geolocation custom component is required.</li>
            <li>The current trained prospectivity raster is for Manganese.</li>
            <li>The 3D surface is extracted from the selected location in the real raster.</li>
            <li>B04 is used as the geospatial reference for CRS and pixel conversion.</li>
            <li>B04 is not used as the displayed AI prospectivity value.</li>
            <li>The 3D height represents AI prospectivity score, not underground depth.</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True,
)

st.caption(
    "AI prospectivity is an exploration indication and should be "
    "validated with geological, geochemical and field evidence."
)
