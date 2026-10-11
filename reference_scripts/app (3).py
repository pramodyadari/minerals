import math
from datetime import datetime, timezone

import folium
import joblib
import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
import rasterio
from pyproj import Transformer
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
from streamlit_searchbox import st_searchbox


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Mineral Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# UI STYLING
# ============================================================

st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }

    .block-container {
        max-width: 1400px;
        padding-left: 5%;
        padding-right: 5%;
    }

    .title {
        font-size: 2.4rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #9aa4b2;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    .info-card {
        padding: 18px;
        border-radius: 12px;
        background: #1f2937;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }

    .score-card {
        padding: 25px;
        border-radius: 15px;
        background: #111827;
        border: 1px solid #374151;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 20px;
    }

    .score-number {
        font-size: 3rem;
        font-weight: 800;
    }

    .explain-card {
        padding: 20px;
        border-radius: 14px;
        background: #151b2b;
        border: 1px solid #374151;
        margin-bottom: 15px;
    }

    .small-text {
        color: #9ca3af;
        font-size: 0.9rem;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 4%;
            padding-right: 4%;
        }

        .title {
            font-size: 1.8rem;
        }

        .subtitle {
            font-size: 0.9rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CONSTANTS
# ============================================================

KNOWN_MINE_LAT = 21.9455
KNOWN_MINE_LON = 80.4295

ESRI_TILES = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {
    "User-Agent": "AI-Mineral-Intelligence-Student-Project/1.0"
}

STAC_URL = "https://stac.dataspace.copernicus.eu/v1/search"

SUPPORTED_MINERALS = [
    "Manganese",
    "Iron Ore",
    "Coal",
    "Bauxite",
    "Copper",
    "Limestone",
    "Chromite",
]


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "selected_lat": KNOWN_MINE_LAT,
    "selected_lon": KNOWN_MINE_LON,
    "selected_place": "Known Manganese Mine Area",
    "last_search_place": "",
    "handled_map_click": None,
    "live_lat": None,
    "live_lon": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# LOAD MODELS AND DATA
# ============================================================

@st.cache_resource
def load_production_model():
    return joblib.load("models/production_random_forest.pkl")


@st.cache_resource
def load_manganese_model():
    return joblib.load("models/manganese_random_forest.pkl")


@st.cache_data
def load_prospectivity():
    return np.load("data/processed/prospectivity_map.npy")


@st.cache_data
def load_zones():
    return pd.read_csv("outputs/high_prospectivity_zones.csv")


try:
    production_model = load_production_model()
except Exception as e:
    production_model = None
    st.warning(f"Production model could not be loaded: {e}")

try:
    manganese_model = load_manganese_model()
except Exception as e:
    manganese_model = None
    st.warning(f"Manganese model could not be loaded: {e}")

try:
    prospectivity = load_prospectivity()
except Exception as e:
    prospectivity = None
    st.warning(f"Prospectivity data could not be loaded: {e}")

try:
    zones = load_zones()
except Exception as e:
    zones = pd.DataFrame()
    st.warning(f"Candidate-zone data could not be loaded: {e}")


required_zone_columns = [
    "Zone_ID",
    "Pixels",
    "Mean_Score",
    "Max_Score",
    "Latitude",
    "Longitude",
]

zones_ready = (
    not zones.empty
    and all(column in zones.columns for column in required_zone_columns)
)


# ============================================================
# LOCATION SEARCH
# ============================================================

def search_locations(searchterm):
    if not searchterm:
        return []

    searchterm = searchterm.strip()

    if len(searchterm) < 2:
        return []

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": searchterm + ", India",
                "format": "json",
                "limit": 8,
                "countrycodes": "in",
                "addressdetails": 1,
            },
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )

        if response.status_code != 200:
            return []

        results = response.json()
        return [
            result["display_name"]
            for result in results
            if result.get("display_name")
        ]

    except Exception:
        return []


def get_coordinates(place):
    if not place:
        return None, None

    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": place,
                "format": "json",
                "limit": 1,
            },
            headers=NOMINATIM_HEADERS,
            timeout=10,
        )

        if response.status_code != 200:
            return None, None

        results = response.json()

        if not results:
            return None, None

        return float(results[0]["lat"]), float(results[0]["lon"])

    except Exception:
        return None, None


# ============================================================
# DISTANCE
# ============================================================

def calculate_distance_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(a))
    return 6371.0 * c


# ============================================================
# SENTINEL-2 DISCOVERY
# ============================================================

def radius_to_bbox(lat, lon, radius_km):
    lat_delta = radius_km / 111.0

    lon_delta = radius_km / (
        111.0 * max(math.cos(math.radians(lat)), 0.01)
    )

    return [
        lon - lon_delta,
        lat - lat_delta,
        lon + lon_delta,
        lat + lat_delta,
    ]


@st.cache_data(ttl=1800)
def search_sentinel_images(lat, lon, radius_km, max_cloud=30):
    bbox = radius_to_bbox(lat, lon, radius_km)

    end_date = datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT23:59:59Z"
    )

    payload = {
        "collections": ["sentinel-2-l2a"],
        "bbox": bbox,
        "datetime": f"2026-01-01T00:00:00Z/{end_date}",
        "query": {
            "eo:cloud_cover": {
                "lt": max_cloud
            }
        },
        "limit": 50,
        "sortby": [
            {
                "field": "datetime",
                "direction": "desc",
            }
        ],
    }

    try:
        response = requests.post(
            STAC_URL,
            json=payload,
            timeout=60,
        )

        if response.status_code != 200:
            return [], f"Copernicus search returned HTTP {response.status_code}."

        data = response.json()
        features = data.get("features", [])

        results = []

        for item in features:
            properties = item.get("properties", {})

            image_id = item.get("id", "Unknown")
            date_text = properties.get("datetime")
            cloud = properties.get("eo:cloud_cover")

            if not date_text:
                continue

            try:
                image_date = datetime.fromisoformat(
                    date_text.replace("Z", "+00:00")
                )
            except ValueError:
                continue

            try:
                cloud_value = float(cloud)
            except (TypeError, ValueError):
                cloud_value = 100.0

            results.append(
                {
                    "id": image_id,
                    "datetime": image_date,
                    "date": image_date.strftime("%d %b %Y"),
                    "cloud_cover": cloud_value,
                    "bbox": item.get("bbox"),
                }
            )

        return results, None

    except requests.RequestException as e:
        return [], f"Could not connect to Copernicus: {e}"

    except Exception as e:
        return [], f"Sentinel-2 search error: {e}"


def rank_sentinel_images(images):
    if not images:
        return []

    now = datetime.now(timezone.utc)

    ranked = []

    for image in images:
        age_days = max(
            (now - image["datetime"]).total_seconds() / 86400,
            0,
        )

        cloud_score = max(
            0,
            1 - image["cloud_cover"] / 30,
        )

        recency_score = max(
            0,
            1 - age_days / 365,
        )

        total_score = (
            0.70 * cloud_score
            + 0.30 * recency_score
        )

        item = image.copy()
        item["selection_score"] = total_score
        ranked.append(item)

    ranked.sort(
        key=lambda x: x["selection_score"],
        reverse=True,
    )

    return ranked


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title">AI Mineral Intelligence</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="subtitle">
    AI-assisted mineral prospectivity, location analysis and
    exploration decision support
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOCATION SEARCH
# ============================================================

st.subheader("Search Location")

search_result = st_searchbox(
    search_locations,
    key="location_search",
    placeholder="Type a place, city, district or village...",
)

if search_result and search_result != st.session_state.last_search_place:
    latitude, longitude = get_coordinates(search_result)

    if latitude is not None and longitude is not None:
        st.session_state.selected_lat = latitude
        st.session_state.selected_lon = longitude
        st.session_state.selected_place = search_result
        st.session_state.last_search_place = search_result
        st.session_state.handled_map_click = None
        st.rerun()


# ============================================================
# LIVE LOCATION
# ============================================================

st.subheader("Live Location")

st.write(
    "Use your current location only when you want to move the analysis area."
)

live_location = streamlit_geolocation()

if live_location:
    latitude = live_location.get("latitude")
    longitude = live_location.get("longitude")

    if latitude is not None and longitude is not None:
        st.session_state.live_lat = float(latitude)
        st.session_state.live_lon = float(longitude)

if (
    st.session_state.live_lat is not None
    and st.session_state.live_lon is not None
):
    st.success(
        f"Live location available: "
        f"{st.session_state.live_lat:.6f}, "
        f"{st.session_state.live_lon:.6f}"
    )

    if st.button("Use My Live Location", use_container_width=True):
        st.session_state.selected_lat = st.session_state.live_lat
        st.session_state.selected_lon = st.session_state.live_lon
        st.session_state.selected_place = "My Live Location"
        st.session_state.last_search_place = ""
        st.session_state.handled_map_click = None
        st.rerun()


# ============================================================
# ANALYSIS SETTINGS
# ============================================================

st.subheader("Analysis Settings")

col1, col2 = st.columns(2)

with col1:
    radius = st.selectbox(
        "Analysis Radius",
        [10, 25, 50, 75, 100],
        index=4,
        format_func=lambda x: f"{x} km",
    )

with col2:
    mineral = st.selectbox(
        "Select Mineral",
        SUPPORTED_MINERALS,
    )


# ============================================================
# SELECTED AREA
# ============================================================

st.subheader("Selected Area")

info_col1, info_col2, info_col3 = st.columns(3)

with info_col1:
    st.metric(
        "Latitude",
        f"{st.session_state.selected_lat:.6f}",
    )

with info_col2:
    st.metric(
        "Longitude",
        f"{st.session_state.selected_lon:.6f}",
    )

with info_col3:
    st.metric(
        "Radius",
        f"{radius} km",
    )

st.markdown(
    f"""
    <div class="info-card">
    <b>Selected Area:</b> {st.session_state.selected_place}
    <br><br>
    <b>Mineral:</b> {mineral}
    <br><br>
    <b>Analysis Radius:</b> {radius} km
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SENTINEL-2 AUTOMATIC DISCOVERY
# ============================================================

st.subheader("Sentinel-2 Satellite Data")

st.write(
    "The system searches the Copernicus Data Space catalogue "
    "for Sentinel-2 Level-2A imagery covering the selected area."
)

sentinel_images, sentinel_error = search_sentinel_images(
    st.session_state.selected_lat,
    st.session_state.selected_lon,
    radius,
    30,
)

ranked_images = rank_sentinel_images(sentinel_images)

if sentinel_error:
    st.error(sentinel_error)

elif not ranked_images:
    st.warning(
        "No suitable Sentinel-2 images were found for the selected area."
    )

else:
    best_image = ranked_images[0]

    st.markdown(
        f"""
        <div class="score-card">
        <div class="small-text">BEST SENTINEL-2 CANDIDATE</div>
        <div style="font-size:1.35rem;font-weight:700;">
        {best_image["date"]}
        </div>
        <div>
        Cloud cover: {best_image["cloud_cover"]:.2f}%
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    s1, s2, s3 = st.columns(3)

    with s1:
        st.metric(
            "Acquisition Date",
            best_image["date"],
        )

    with s2:
        st.metric(
            "Cloud Cover",
            f'{best_image["cloud_cover"]:.2f}%',
        )

    with s3:
        st.metric(
            "Images Found",
            len(ranked_images),
        )

    st.caption(
        "Candidate ranking balances cloud cover and image recency. "
        "This identifies a suitable image for analysis; it does not "
        "download or process the satellite product."
    )

    with st.expander("View available Sentinel-2 images"):
        sentinel_table = pd.DataFrame(
            [
                {
                    "Date": image["date"],
                    "Cloud Cover (%)": round(
                        image["cloud_cover"], 2
                    ),
                    "Product ID": image["id"],
                }
                for image in ranked_images[:20]
            ]
        )

        st.dataframe(
            sentinel_table,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# MINERAL MODEL STATUS
# ============================================================

st.subheader("Mineral Model Status")

if mineral == "Manganese":
    if manganese_model is not None:
        st.success(
            "Manganese prospectivity model is active."
        )
    else:
        st.error(
            "Manganese prospectivity model could not be loaded."
        )
else:
    st.info(
        f"{mineral} model is currently under development. "
        "The dashboard supports the mineral selection, while "
        "a mineral-specific training dataset and model are still required."
    )


# ============================================================
# MINERAL INTELLIGENCE ANALYSIS
# ============================================================

st.subheader("Mineral Intelligence Analysis")

nearby_zones = pd.DataFrame()
intelligence_score = None
mean_prospectivity = None
zone_count = 0
total_pixels = 0

# Current prototype candidate zones are manganese-specific.
if mineral == "Manganese" and zones_ready:

    zone_analysis = zones.copy()

    zone_analysis["Distance_km"] = calculate_distance_km(
        st.session_state.selected_lat,
        st.session_state.selected_lon,
        zone_analysis["Latitude"].values,
        zone_analysis["Longitude"].values,
    )

    nearby_zones = zone_analysis[
        zone_analysis["Distance_km"] <= radius
    ].copy()

    nearby_zones = nearby_zones.sort_values(
        by="Mean_Score",
        ascending=False,
    )


if mineral != "Manganese":
    st.info(
        f"Prospectivity scoring for {mineral} will become available "
        "after its mineral-specific model and training data are added."
    )

elif not nearby_zones.empty:

    zone_count = len(nearby_zones)

    mean_prospectivity = nearby_zones["Mean_Score"].mean()

    total_pixels = int(
        nearby_zones["Pixels"].sum()
    )

    prospectivity_component = mean_prospectivity * 100

    zone_support_component = min(
        zone_count / 10,
        1,
    ) * 100

    spatial_support_component = min(
        total_pixels / 500,
        1,
    ) * 100

    intelligence_score = (
        0.60 * prospectivity_component
        + 0.20 * zone_support_component
        + 0.20 * spatial_support_component
    )

    intelligence_score = max(
        0,
        min(100, intelligence_score),
    )

    if intelligence_score >= 75:
        intelligence_level = "HIGH"
    elif intelligence_score >= 50:
        intelligence_level = "MEDIUM"
    else:
        intelligence_level = "LOW"

    st.markdown(
        f"""
        <div class="score-card">
        <div class="small-text">MINERAL INTELLIGENCE SCORE</div>
        <div class="score-number">
        {intelligence_score:.1f}/100
        </div>
        <div>{intelligence_level} PROSPECTIVITY</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    score_col1, score_col2, score_col3 = st.columns(3)

    with score_col1:
        st.metric(
            "Average Prospectivity",
            f"{mean_prospectivity * 100:.1f}%",
        )

    with score_col2:
        st.metric(
            "Candidate Zones",
            zone_count,
        )

    with score_col3:
        st.metric(
            "Supporting Pixels",
            f"{total_pixels:,}",
        )

    st.caption(
        "Prototype score based on candidate-zone evidence within "
        "the selected radius."
    )

elif mineral == "Manganese":
    st.warning(
        f"No prototype candidate zones were found within {radius} km "
        "of the selected location."
    )

    st.write(
        "This does not mean the area has no minerals. It means the "
        "current manganese prototype dataset has no generated "
        "candidate zones inside this radius."
    )


# ============================================================
# EXPLAINABLE AI
# ============================================================

st.subheader("Explainable AI")

if (
    mineral == "Manganese"
    and not nearby_zones.empty
    and intelligence_score is not None
):

    st.markdown(
        f"""
        <div class="explain-card">
        <b>AI Interpretation</b><br><br>
        The selected area received an Intelligence Score of
        <b>{intelligence_score:.1f}/100</b> because the current
        prototype detected multiple high-prospectivity candidate
        zones within the selected {radius} km radius.
        </div>
        """,
        unsafe_allow_html=True,
    )

    exp1, exp2 = st.columns(2)

    with exp1:
        st.markdown(
            f"""
            <div class="explain-card">
            <b>Satellite and Prospectivity Evidence</b>
            <br><br>
            Average candidate-zone prospectivity:
            <b>{mean_prospectivity * 100:.1f}%</b>
            <br><br>
            The current prospectivity raster and trained model
            identified strong spectral patterns in the candidate zones.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with exp2:
        st.markdown(
            f"""
            <div class="explain-card">
            <b>Candidate-Zone Support</b>
            <br><br>
            Candidate zones detected:
            <b>{zone_count}</b>
            <br><br>
            Supporting pixels:
            <b>{total_pixels:,}</b>
            <br><br>
            Multiple nearby zones provide stronger spatial support
            than a single isolated pixel.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Model Feature Importance")

    if (
        manganese_model is not None
        and hasattr(manganese_model, "feature_importances_")
    ):

        feature_names = [
            "B04 - Red",
            "B05 - Red Edge",
            "B06 - Red Edge",
            "B8A - Narrow NIR",
            "B11 - SWIR",
            "B12 - SWIR",
            "NDVI",
            "NDMI",
            "SWIR Ratio",
            "Red/SWIR Ratio",
        ]

        importances = manganese_model.feature_importances_

        feature_df = pd.DataFrame(
            {
                "Feature": feature_names,
                "Importance (%)": importances * 100,
            }
        ).sort_values(
            by="Importance (%)",
            ascending=False,
        )

        st.dataframe(
            feature_df.head(5).round(2),
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            "Feature importance describes the Random Forest model's "
            "overall training behavior. It does not mean that one "
            "feature alone proves a mineral deposit."
        )

    top_zone = nearby_zones.iloc[0]

    st.markdown("### Strongest Nearby Candidate")

    st.markdown(
        f"""
        <div class="explain-card">
        <b>Candidate Zone {int(top_zone["Zone_ID"])}</b>
        <br><br>
        Mean prospectivity:
        <b>{float(top_zone["Mean_Score"]) * 100:.1f}%</b>
        <br><br>
        Distance:
        <b>{float(top_zone["Distance_km"]):.1f} km</b>
        <br><br>
        Supporting pixels:
        <b>{int(top_zone["Pixels"]):,}</b>
        <br><br>
        Location:
        <b>{float(top_zone["Latitude"]):.5f},
        {float(top_zone["Longitude"]):.5f}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Exploration Recommendation")

    if intelligence_score >= 75:
        recommendation = (
            "Prioritize this area for further investigation. "
            "The prototype indicates strong prospectivity and "
            "multiple supporting candidate zones."
        )
    elif intelligence_score >= 50:
        recommendation = (
            "Consider this area for secondary investigation. "
            "Additional geological and geophysical evidence should "
            "be examined before prioritization."
        )
    else:
        recommendation = (
            "Keep this area at lower exploration priority unless "
            "additional geological evidence supports it."
        )

    st.info(recommendation)

    st.warning(
        "AI prospectivity is an exploration indication. It does not "
        "confirm the presence, quantity or economic value of an "
        "underground mineral reserve. Geological, geochemical, "
        "geophysical and field validation are required."
    )

elif mineral == "Manganese":
    st.info(
        "Explainable analysis will appear when manganese "
        "candidate-zone evidence is available."
    )


# ============================================================
# 3D MINERAL PROSPECTIVITY VISUALIZATION
# ============================================================

st.subheader("3D Mineral Prospectivity Visualization")

if mineral == "Manganese" and prospectivity is not None:

    st.write(
        "Location-based 3D representation of the AI-derived "
        "manganese prospectivity surface."
    )

    try:
        # --------------------------------------------------------
        # SENTINEL-2 GEOGRAPHIC REFERENCE
        # --------------------------------------------------------
        # The prospectivity array was generated from the same
        # 20 m Sentinel-2 grid as the B04 reference raster.
        # B04 provides the real CRS and pixel-to-map transform.

        reference_raster = os.path.join(
            PROJECT_ROOT,
            "data",
            "raw",
            "T44QMK_20260621T050649_B04_20m.jp2",
        )

        if not os.path.exists(reference_raster):
            st.warning(
                "The Sentinel-2 geographic reference raster could not be found."
            )
        else:
            with rasterio.open(reference_raster) as src:
                raster_crs = src.crs
                transform = src.transform
                raster_width = src.width
                raster_height = src.height
                raster_left = src.bounds.left
                raster_right = src.bounds.right
                raster_bottom = src.bounds.bottom
                raster_top = src.bounds.top

            # ----------------------------------------------------
            # SELECTED LOCATION: WGS84 -> UTM
            # ----------------------------------------------------
            selected_lat = float(st.session_state.selected_lat)
            selected_lon = float(st.session_state.selected_lon)

            to_utm = Transformer.from_crs(
                "EPSG:4326",
                raster_crs,
                always_xy=True,
            )

            selected_x, selected_y = to_utm.transform(
                selected_lon,
                selected_lat,
            )

            # ----------------------------------------------------
            # LOCATION MUST FALL INSIDE THE CURRENT RASTER
            # ----------------------------------------------------
            location_inside_raster = (
                raster_left <= selected_x <= raster_right
                and raster_bottom <= selected_y <= raster_top
            )

            if not location_inside_raster:
                st.info(
                    "The selected location is outside the current "
                    "Sentinel-2 prospectivity raster. The 3D surface "
                    "is available for locations covered by this dataset."
                )
            else:
                # ------------------------------------------------
                # RADIUS-BASED WINDOW
                # ------------------------------------------------
                radius_m = float(radius) * 1000.0

                pixel_width = abs(float(transform.a))
                pixel_height = abs(float(transform.e))

                radius_pixels_x = max(
                    1,
                    int(radius_m / pixel_width),
                )
                radius_pixels_y = max(
                    1,
                    int(radius_m / pixel_height),
                )

                center_row, center_col = rasterio.transform.rowcol(
                    transform,
                    selected_x,
                    selected_y,
                )

                center_row = int(center_row)
                center_col = int(center_col)

                row_start = max(
                    0,
                    center_row - radius_pixels_y,
                )
                row_end = min(
                    min(raster_height, prospectivity.shape[0]),
                    center_row + radius_pixels_y + 1,
                )

                col_start = max(
                    0,
                    center_col - radius_pixels_x,
                )
                col_end = min(
                    min(raster_width, prospectivity.shape[1]),
                    center_col + radius_pixels_x + 1,
                )

                surface = prospectivity[
                    row_start:row_end,
                    col_start:col_end,
                ]

                surface = np.asarray(
                    surface,
                    dtype=np.float32,
                )

                surface = np.nan_to_num(
                    surface,
                    nan=0.0,
                    posinf=1.0,
                    neginf=0.0,
                )

                surface = np.clip(
                    surface,
                    0.0,
                    1.0,
                )

                if surface.size == 0:
                    st.warning(
                        "No prospectivity pixels are available around "
                        "the selected location."
                    )
                else:
                    # ------------------------------------------------
                    # DOWNSAMPLE ONLY FOR DISPLAY SPEED
                    # ------------------------------------------------
                    # The underlying prospectivity raster is unchanged.
                    # This only reduces the number of points rendered in
                    # the interactive 3D chart.

                    max_points_per_axis = 90

                    display_step_y = max(
                        1,
                        int(np.ceil(
                            surface.shape[0] / max_points_per_axis
                        )),
                    )

                    display_step_x = max(
                        1,
                        int(np.ceil(
                            surface.shape[1] / max_points_per_axis
                        )),
                    )

                    surface_display = surface[
                        ::display_step_y,
                        ::display_step_x,
                    ]

                    # ------------------------------------------------
                    # REAL UTM PIXEL-CENTER COORDINATES
                    # ------------------------------------------------
                    row_indices = (
                        row_start
                        + np.arange(
                            0,
                            surface.shape[0],
                            display_step_y,
                        )
                    )

                    col_indices = (
                        col_start
                        + np.arange(
                            0,
                            surface.shape[1],
                            display_step_x,
                        )
                    )

                    row_indices = row_indices[:surface_display.shape[0]]
                    col_indices = col_indices[:surface_display.shape[1]]

                    x_utm = (
                        transform.c
                        + (col_indices + 0.5) * transform.a
                    )

                    y_utm = (
                        transform.f
                        + (row_indices + 0.5) * transform.e
                    )

                    # ------------------------------------------------
                    # UTM -> WGS84
                    # ------------------------------------------------
                    to_wgs84 = Transformer.from_crs(
                        raster_crs,
                        "EPSG:4326",
                        always_xy=True,
                    )

                    # Each X coordinate is converted using the center
                    # latitude of the selected area; each Y coordinate
                    # is converted using the center longitude. For the
                    # relatively small display window this gives the
                    # geographic axes needed by the visualization.

                    lon_values, _ = to_wgs84.transform(
                        x_utm,
                        np.full(
                            len(x_utm),
                            selected_y,
                            dtype=float,
                        ),
                    )

                    _, lat_values = to_wgs84.transform(
                        np.full(
                            len(y_utm),
                            selected_x,
                            dtype=float,
                        ),
                        y_utm,
                    )

                    # ------------------------------------------------
                    # Z = AI PROSPECTIVITY PERCENT
                    # ------------------------------------------------
                    z = surface_display * 100.0

                    local_mean = float(
                        np.mean(surface)
                    ) * 100.0

                    local_max = float(
                        np.max(surface)
                    ) * 100.0

                    # ------------------------------------------------
                    # COLORS
                    # ------------------------------------------------
                    prospectivity_colorscale = [
                        [0.00, "#263238"],
                        [0.20, "#1565C0"],
                        [0.40, "#2E7D32"],
                        [0.60, "#F9A825"],
                        [0.80, "#EF6C00"],
                        [1.00, "#C62828"],
                    ]

                    # ------------------------------------------------
                    # 3D SURFACE
                    # ------------------------------------------------
                    fig = go.Figure()

                    fig.add_trace(
                        go.Surface(
                            x=lon_values,
                            y=lat_values,
                            z=z,
                            surfacecolor=surface_display,
                            colorscale=prospectivity_colorscale,
                            cmin=0,
                            cmax=1,
                            colorbar=dict(
                                title=dict(
                                    text="AI Prospectivity (%)",
                                    side="right",
                                ),
                                tickmode="array",
                                tickvals=[
                                    0,
                                    0.25,
                                    0.50,
                                    0.75,
                                    1.00,
                                ],
                                ticktext=[
                                    "0% - Very Low",
                                    "25% - Low",
                                    "50% - Moderate",
                                    "75% - High",
                                    "100% - Very High",
                                ],
                                len=0.72,
                                thickness=22,
                            ),
                            hovertemplate=(
                                "Longitude: %{x:.5f}<br>"
                                "Latitude: %{y:.5f}<br>"
                                "AI Prospectivity: %{surfacecolor:.1%}"
                                "<extra></extra>"
                            ),
                        )
                    )

                    # ------------------------------------------------
                    # SELECTED LOCATION MARKER
                    # ------------------------------------------------
                    marker_z = min(
                        100.0,
                        max(
                            local_max + 5.0,
                            5.0,
                        ),
                    )

                    fig.add_trace(
                        go.Scatter3d(
                            x=[selected_lon],
                            y=[selected_lat],
                            z=[marker_z],
                            mode="markers+text",
                            marker=dict(
                                size=7,
                                color="black",
                                symbol="diamond",
                            ),
                            text=["Selected location"],
                            textposition="top center",
                            hovertemplate=(
                                "Selected location<br>"
                                "Longitude: %{x:.5f}<br>"
                                "Latitude: %{y:.5f}<br>"
                                "<extra></extra>"
                            ),
                            showlegend=False,
                        )
                    )

                    # ------------------------------------------------
                    # LOCATION-BASED LAYOUT
                    # ------------------------------------------------
                    fig.update_layout(
                        height=700,
                        margin=dict(
                            l=0,
                            r=0,
                            t=55,
                            b=0,
                        ),
                        title=dict(
                            text=(
                                "AI Mineral Prospectivity — "
                                f"{radius:g} km Analysis Area"
                            ),
                            x=0.5,
                        ),
                        scene=dict(
                            xaxis=dict(
                                title="Longitude",
                                showgrid=True,
                            ),
                            yaxis=dict(
                                title="Latitude",
                                showgrid=True,
                            ),
                            zaxis=dict(
                                title="AI Prospectivity (%)",
                                range=[0, 100],
                                showgrid=True,
                            ),
                            camera=dict(
                                eye=dict(
                                    x=1.55,
                                    y=1.55,
                                    z=1.15,
                                )
                            ),
                        ),
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                        key=(
                            f"location_3d_{selected_lat:.5f}_"
                            f"{selected_lon:.5f}_{radius}"
                        ),
                    )

                    # ------------------------------------------------
                    # 3D INTERPRETATION
                    # ------------------------------------------------
                    st.markdown(
                        f"""
                        <div style="
                            padding:18px;
                            border-radius:12px;
                            border:1px solid #374151;
                            background:#151b2b;
                            margin-top:10px;
                        ">
                        <b>3D Prospectivity Interpretation</b>
                        <br><br>

                        The 3D surface is centered on the selected
                        geographic location and uses the corresponding
                        area of the current Sentinel-2 prospectivity raster.
                        <br><br>

                        <b>Latitude:</b> {selected_lat:.5f}<br>
                        <b>Longitude:</b> {selected_lon:.5f}<br>
                        <b>Analysis radius:</b> {radius:g} km<br>
                        <b>Local mean prospectivity:</b> {local_mean:.1f}%<br>
                        <b>Local maximum prospectivity:</b> {local_max:.1f}%
                        <br><br>

                        Higher surface values represent stronger
                        AI-derived prospectivity in the displayed area.
                        The visualization is an exploration indication
                        and does not independently confirm an underground
                        mineral reserve.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    except Exception as e:
        st.error(
            "The 3D prospectivity visualization could not be generated: "
            f"{e}"
        )

elif mineral == "Manganese":
    st.info(
        "The 3D prospectivity visualization will be available when the "
        "manganese prospectivity raster is available."
    )

else:
    st.info(
        f"The 3D prospectivity model for {mineral} will be available "
        "after its mineral-specific model and training data are developed."
    )


# ============================================================
# PROSPECTIVITY MAP
# ============================================================

st.subheader("Mineral Prospectivity Map")

map_center = [
    st.session_state.selected_lat,
    st.session_state.selected_lon,
]

m = folium.Map(
    location=map_center,
    zoom_start=8,
    tiles=None,
)

folium.TileLayer(
    tiles=ESRI_TILES,
    attr="Esri World Street Map",
    name="Esri",
).add_to(m)

folium.Marker(
    location=map_center,
    popup=(
        f"<b>{st.session_state.selected_place}</b><br>"
        f"Lat: {st.session_state.selected_lat:.6f}<br>"
        f"Lon: {st.session_state.selected_lon:.6f}"
    ),
    tooltip="Selected Location",
    icon=folium.Icon(
        color="blue",
        icon="map-marker",
    ),
).add_to(m)

folium.Circle(
    location=map_center,
    radius=radius * 1000,
    color="blue",
    fill=True,
    fill_opacity=0.08,
    popup=f"Analysis Radius: {radius} km",
).add_to(m)

if mineral == "Manganese":
    folium.Marker(
        location=[
            KNOWN_MINE_LAT,
            KNOWN_MINE_LON,
        ],
        popup="Known Manganese Mine Reference",
        tooltip="Known Mine",
        icon=folium.Icon(
            color="blue",
            icon="industry",
        ),
    ).add_to(m)

if mineral == "Manganese" and not nearby_zones.empty:

    for _, row in nearby_zones.head(50).iterrows():

        score = float(row["Mean_Score"])

        if score >= 0.95:
            zone_color = "red"
        elif score >= 0.90:
            zone_color = "orange"
        else:
            zone_color = "beige"

        folium.CircleMarker(
            location=[
                row["Latitude"],
                row["Longitude"],
            ],
            radius=7,
            color=zone_color,
            fill=True,
            fill_color=zone_color,
            fill_opacity=0.8,
            popup=(
                f"<b>Candidate Zone "
                f"{int(row['Zone_ID'])}</b><br>"
                f"Mean Score: {score:.3f}<br>"
                f"Max Score: "
                f"{float(row['Max_Score']):.3f}<br>"
                f"Pixels: "
                f"{int(row['Pixels'])}<br>"
                f"Distance: "
                f"{float(row['Distance_km']):.1f} km"
            ),
        ).add_to(m)

legend_html = """
<div style="
position: fixed;
bottom: 25px;
left: 25px;
z-index: 9999;
background-color: white;
padding: 10px;
border: 2px solid grey;
border-radius: 8px;
font-size: 13px;
">
<b>Prospectivity</b><br>
<span style="color:red;">●</span> Very High >= 0.95<br>
<span style="color:orange;">●</span> High 0.90-0.95<br>
<span style="color:#d6b656;">●</span> Moderate < 0.90<br>
<span style="color:blue;">●</span> Selected / Known location
</div>
"""

m.get_root().html.add_child(
    folium.Element(legend_html)
)

map_data = st_folium(
    m,
    width=None,
    height=550,
    returned_objects=["last_clicked"],
)


# ============================================================
# MAP CLICK
# ============================================================

if map_data:
    clicked = map_data.get("last_clicked")

    if clicked:
        clicked_lat = clicked.get("lat")
        clicked_lon = clicked.get("lng")

        if (
            clicked_lat is not None
            and clicked_lon is not None
        ):

            click_key = (
                round(float(clicked_lat), 6),
                round(float(clicked_lon), 6),
            )

            if click_key != st.session_state.handled_map_click:

                st.session_state.selected_lat = float(clicked_lat)
                st.session_state.selected_lon = float(clicked_lon)
                st.session_state.selected_place = "Map Selected Location"
                st.session_state.handled_map_click = click_key
                st.session_state.last_search_place = ""
                st.rerun()


# ============================================================
# CANDIDATE ZONE TABLE
# ============================================================

if mineral == "Manganese" and not nearby_zones.empty:

    st.subheader("Candidate Exploration Zones")

    display_zones = nearby_zones.head(20).copy()

    display_zones["Mean_Score"] = (
        display_zones["Mean_Score"].round(3)
    )

    display_zones["Max_Score"] = (
        display_zones["Max_Score"].round(3)
    )

    display_zones["Distance_km"] = (
        display_zones["Distance_km"].round(2)
    )

    display_zones = display_zones[
        [
            "Zone_ID",
            "Pixels",
            "Mean_Score",
            "Max_Score",
            "Distance_km",
            "Latitude",
            "Longitude",
        ]
    ]

    st.dataframe(
        display_zones,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# EXPLORATION INTERPRETATION
# ============================================================

st.subheader("Exploration Interpretation")

if mineral == "Manganese" and not nearby_zones.empty:

    top_zone = nearby_zones.iloc[0]

    st.info(
        f"The strongest manganese candidate zone within the selected "
        f"radius is Zone {int(top_zone['Zone_ID'])}. "
        f"Mean prospectivity: {float(top_zone['Mean_Score']):.3f}. "
        f"Distance from selected location: "
        f"{float(top_zone['Distance_km']):.1f} km. "
        "This is an AI-assisted prospectivity indication, not proof "
        "of an actual mineral reserve."
    )

elif mineral == "Manganese":

    st.info(
        "No prototype manganese candidate zones are currently "
        "available for this selected area."
    )

else:

    st.info(
        f"{mineral} exploration interpretation will be enabled "
        "after its mineral-specific model is developed."
    )


# ============================================================
# PRODUCTION FORECAST
# ============================================================

st.subheader("Production Shortfall Forecast")

if production_model is not None:

    st.write(
        "Estimate possible production based on operational "
        "and weather conditions."
    )

    p1, p2 = st.columns(2)

    with p1:
        rainfall = st.number_input(
            "Rainfall (mm)",
            min_value=0.0,
            max_value=500.0,
            value=150.0,
            step=10.0,
        )

        downtime = st.number_input(
            "Equipment Downtime (hours)",
            min_value=0.0,
            max_value=100.0,
            value=20.0,
            step=1.0,
        )

        blasting_delay = st.number_input(
            "Blasting Delay (hours)",
            min_value=0.0,
            max_value=100.0,
            value=8.0,
            step=1.0,
        )

    with p2:
        availability = st.number_input(
            "Equipment Availability (%)",
            min_value=0.0,
            max_value=100.0,
            value=85.0,
            step=1.0,
        )

        planned_production = st.number_input(
            "Planned Production (tonnes)",
            min_value=1000.0,
            max_value=50000.0,
            value=11000.0,
            step=500.0,
        )

    if st.button(
        "Predict Production",
        use_container_width=True,
    ):

        input_data = pd.DataFrame(
            [
                {
                    "Rainfall_mm": rainfall,
                    "Equipment_Downtime_hr": downtime,
                    "Blasting_Delay_hr": blasting_delay,
                    "Equipment_Availability_pct": availability,
                    "Planned_Production_tonnes": planned_production,
                }
            ]
        )

        predicted_production = (
            production_model.predict(input_data)[0]
        )

        shortfall = max(
            planned_production - predicted_production,
            0,
        )

        if shortfall > 2000:
            risk = "HIGH"
        elif shortfall > 1000:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        result1, result2, result3 = st.columns(3)

        with result1:
            st.metric(
                "Predicted Production",
                f"{predicted_production:,.0f} t",
            )

        with result2:
            st.metric(
                "Expected Shortfall",
                f"{shortfall:,.0f} t",
            )

        with result3:
            st.metric(
                "Risk",
                risk,
            )

        if risk == "HIGH":
            st.error(
                "High production shortfall risk. Consider equipment "
                "redeployment, blasting optimization and production-plan adjustment."
            )
        elif risk == "MEDIUM":
            st.warning(
                "Medium production shortfall risk. Monitor equipment "
                "downtime and blasting delays."
            )
        else:
            st.success(
                "Low production shortfall risk. Continue normal "
                "operations and monitor conditions."
            )

else:
    st.warning("Production model is not available.")


# ============================================================
# ABOUT PROJECT
# ============================================================

st.subheader("About This Project")

st.markdown(
    """
    ### AI-Driven Mineral Intelligence & Exploration Decision Support Platform

    This academic prototype combines:

    - Sentinel-2 satellite data discovery
    - Machine Learning
    - Interactive geospatial analysis
    - Location-based exploration
    - Radius-based regional analysis
    - Explainable AI
    - Candidate-zone identification
    - Production shortfall prediction

    The current trained prospectivity model is specifically for
    Manganese.

    The long-term objective is to develop mineral-specific models
    for multiple minerals and integrate satellite, geological,
    geochemical, geophysical and environmental information.

    Important:

    AI prospectivity results are indications for exploration
    prioritization. They do not independently confirm underground
    mineral reserves.
    """
)
