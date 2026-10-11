import pandas as pd
import folium
import os

# Load AI detected zones
csv_file = "outputs/high_prospectivity_zones.csv"
df = pd.read_csv(csv_file)

print("Zones loaded:", len(df))

# Known manganese mine location
mine_lat = 21.9455
mine_lon = 80.4295

# Create map
m = folium.Map(
    location=[mine_lat, mine_lon],
    zoom_start=9,
    tiles=None
)

# Add Esri map
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Esri World Street Map"
).add_to(m)


# Function to choose marker color
def get_color(score):

    if score >= 0.95:
        return "red"

    elif score >= 0.90:
        return "orange"

    else:
        return "yellow"


# Add known mine
folium.Marker(
    [mine_lat, mine_lon],
    popup="Known Manganese Mine - Training Location",
    tooltip="Known Mine",
    icon=folium.Icon(
        color="blue",
        icon="industry"
    )
).add_to(m)


# Add AI detected zones
for _, row in df.iterrows():

    score = row["Mean_Score"]

    color = get_color(score)

    popup_text = (
        f"<b>Zone ID:</b> {row['Zone_ID']}<br>"
        f"<b>Mean Prospectivity:</b> {row['Mean_Score']}<br>"
        f"<b>Maximum Score:</b> {row['Max_Score']}<br>"
        f"<b>Pixels:</b> {row['Pixels']}<br>"
        f"<b>Latitude:</b> {row['Latitude']}<br>"
        f"<b>Longitude:</b> {row['Longitude']}"
    )

    folium.CircleMarker(
        location=[
            row["Latitude"],
            row["Longitude"]
        ],
        radius=8,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        popup=folium.Popup(
            popup_text,
            max_width=300
        ),
        tooltip=f"Prospectivity Score: {score}"
    ).add_to(m)


# Add legend
legend_html = """
<div style="
position: fixed;
bottom: 40px;
left: 40px;
width: 210px;
background-color: white;
border: 2px solid grey;
z-index: 9999;
font-size: 14px;
padding: 10px;
">

<b>AI Prospectivity</b><br><br>

<span style="color:red;">●</span>
Very High (≥ 0.95)<br>

<span style="color:orange;">●</span>
High (0.90 - 0.95)<br>

<span style="color:yellow;">●</span>
Moderate (&lt; 0.90)<br>

<span style="color:blue;">●</span>
Known Mine

</div>
"""

m.get_root().html.add_child(
    folium.Element(legend_html)
)


# Save map
os.makedirs("outputs", exist_ok=True)

output_file = "outputs/manganese_zones_map.html"

m.save(output_file)

print("\nInteractive map created successfully!")
print("File:", output_file)