import json
import os
import sys

# Ensure backend root on path
sys.path.insert(0, os.getcwd())

from backend.app.mineral_service import analyze_location_for_mineral
from backend.app.raster_ingestion_service import ingest_and_process_satellite_rasters, analyze_tile_intersections

audit_targets = [
    {
        'name': 'Balaghat Sausar Belt, Madhya Pradesh',
        'lat': 21.9455,
        'lon': 80.4295,
        'mineral': 'Manganese',
        'radius': 10.0,
        'category': 'Validated Local Archive'
    },
    {
        'name': 'Balaghat-Ramtek Boundary, MP/Maharashtra',
        'lat': 21.5000,
        'lon': 79.8000,
        'mineral': 'Manganese',
        'radius': 25.0,
        'category': 'Multi-Tile Boundary Crossing'
    },
    {
        'name': 'Manuguru Godavari Valley, Telangana',
        'lat': 17.9800,
        'lon': 80.7600,
        'mineral': 'Coal',
        'radius': 10.0,
        'category': 'Coal Remote Discovery'
    },
    {
        'name': 'Jharia Coalfield, Dhanbad, Jharkhand',
        'lat': 23.7500,
        'lon': 86.4200,
        'mineral': 'Coal',
        'radius': 10.0,
        'category': 'Coal Remote Discovery'
    },
    {
        'name': 'Noamundi Iron Belt, Jharkhand/Odisha',
        'lat': 22.1500,
        'lon': 85.5000,
        'mineral': 'Iron Ore',
        'radius': 10.0,
        'category': 'Iron Ore Remote Discovery'
    },
    {
        'name': 'Panchpatmali Bauxite Plateau, Odisha',
        'lat': 18.8200,
        'lon': 83.0000,
        'mineral': 'Bauxite',
        'radius': 10.0,
        'category': 'Bauxite Remote Discovery'
    },
    {
        'name': 'Kolar Greenstone Belt, Karnataka',
        'lat': 12.9600,
        'lon': 78.2700,
        'mineral': 'Manganese',
        'radius': 10.0,
        'category': 'Outside Validated Domain'
    },
    {
        'name': 'Monsoon High Cloud Cover Sector, Meghalaya',
        'lat': 25.3000,
        'lon': 91.7000,
        'mineral': 'Coal',
        'radius': 10.0,
        'category': 'High Cloud Cover Rejection',
        'mock_error': 'HIGH_CLOUD_COVER'
    },
    {
        'name': 'Missing Spectral Band Granule Case',
        'lat': 21.9455,
        'lon': 80.4295,
        'mineral': 'Manganese',
        'radius': 10.0,
        'category': 'Missing Band Error',
        'mock_error': 'MISSING_DATA'
    },
    {
        'name': 'Outside India Territorial Envelope (Karachi)',
        'lat': 24.8600,
        'lon': 67.0000,
        'mineral': 'Coal',
        'radius': 10.0,
        'category': 'Sovereign Boundary Violation'
    }
]

results = []
for t in audit_targets:
    mock_err = t.get('mock_error')
    res = analyze_location_for_mineral(
        location_name=t['name'],
        lat=t['lat'],
        lon=t['lon'],
        mineral_name=t['mineral'],
        radius_km=t['radius'],
        mock_satellite_error=mock_err
    )
    t_info = analyze_tile_intersections(t['lat'], t['lon'], t['radius']) if res.get('is_within_india', True) else None
    item = {
        'target': t['name'],
        'mineral': t['mineral'],
        'category': t['category'],
        'lat': t['lat'],
        'lon': t['lon'],
        'radius_km': t['radius'],
        'overall_status': res.get('overall_status') or res.get('status'),
        'model_coverage': res.get('model_coverage'),
        'prediction_score': res.get('prediction', {}).get('prospectivity_index') if res.get('prediction') else None,
        'raster_pixels_processed': res.get('raster_pixels_processed'),
        'raster_processing_status': res.get('raster_processing_status'),
        'valid_pixels': res.get('raster_pixel_coverage', {}).get('valid_pixels') if res.get('raster_pixel_coverage') else 0,
        'cloud_mask_pct': res.get('raster_pixel_coverage', {}).get('cloud_mask_pct') if res.get('raster_pixel_coverage') else 0.0,
        'bands_available': res.get('satellite_scenes', [{}])[0].get('bands_available') if res.get('satellite_scenes') else ["B02", "B03", "B04", "B08", "B11", "B12"],
        'tile_boundary_crossed': t_info.get('tile_boundary_crossed') if t_info else False,
        'primary_tile': t_info.get('primary_tile') if t_info else None,
        'intersecting_tiles': t_info.get('intersecting_tiles') if t_info else []
    }
    results.append(item)
    print(f"AUDITED: {t['name']} | Status: {item['overall_status']} | Pixels Processed: {item['raster_pixels_processed']} | Valid Pixels: {item['valid_pixels']}")

out_file = os.path.join("scratch", "nationwide_raster_audit.json")
os.makedirs("scratch", exist_ok=True)
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nAll 10 nationwide targets successfully audited. Report written to {out_file}")
