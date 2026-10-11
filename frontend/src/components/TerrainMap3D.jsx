import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Compass, RotateCcw, Mountain, Layers, Eye, Navigation, AlertCircle } from 'lucide-react';

const MINERAL_COLORS = {
  'Coal': '#8b9bb4',
  'Manganese': '#00b4d8',
  'Iron Ore': '#c85a32',
  'Bauxite': '#d97706',
};

// Generate circular polygon GeoJSON coordinates draped over terrain
function generateCirclePolygon(centerLon, centerLat, radiusKm, points = 64) {
  const coords = [];
  const kmPerDegLat = 110.574;
  const kmPerDegLon = 111.32 * Math.cos((centerLat * Math.PI) / 180);

  for (let i = 0; i <= points; i++) {
    const angle = (i * 2 * Math.PI) / points;
    const dx = radiusKm * Math.cos(angle);
    const dy = radiusKm * Math.sin(angle);
    coords.push([centerLon + dx / kmPerDegLon, centerLat + dy / kmPerDegLat]);
  }

  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [coords],
        },
      },
    ],
  };
}

export default function TerrainMap3D({
  selectedLocation,
  radiusKm,
  targetMineral,
  onLocationChange,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const [pitch, setPitch] = useState(60);
  const [bearing, setBearing] = useState(0);
  const [terrainExaggeration, setTerrainExaggeration] = useState(1.4);
  const [is3DReady, setIs3DReady] = useState(false);

  // Initialize MapLibre 3D Terrain Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialLon = selectedLocation?.lon || 80.1849;
    const initialLat = selectedLocation?.lat || 21.9048;

    // Basemap style with OpenStreetMap tiles & AWS Terrarium 3D elevation
    const style = {
      version: 8,
      sources: {
        'osm-tiles': {
          type: 'raster',
          tiles: [
            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          ],
          tileSize: 256,
          attribution: '&copy; OpenStreetMap contributors | AWS Open Data Terrain',
        },
        'terrain-dem': {
          type: 'raster-dem',
          tiles: [
            'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png',
          ],
          encoding: 'terrarium',
          tileSize: 256,
          maxzoom: 15,
        },
      },
      layers: [
        {
          id: 'osm-layer',
          type: 'raster',
          source: 'osm-tiles',
          minzoom: 0,
          maxzoom: 19,
        },
      ],
      terrain: {
        source: 'terrain-dem',
        exaggeration: terrainExaggeration,
      },
      sky: {
        'sky-color': '#11151a',
        'sky-horizon-blend': 0.6,
        'horizon-color': '#2a323d',
        'horizon-fog-blend': 0.8,
        'fog-color': '#181d22',
        'fog-ground-blend': 0.5,
      },
    };

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: style,
      center: [initialLon, initialLat],
      zoom: 11,
      pitch: pitch,
      bearing: bearing,
      maxPitch: 82,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

    map.on('load', () => {
      setIs3DReady(true);

      // Add radius circle polygon layer
      const circleData = generateCirclePolygon(initialLon, initialLat, radiusKm);
      map.addSource('radius-circle-source', {
        type: 'geojson',
        data: circleData,
      });

      const color = MINERAL_COLORS[targetMineral] || '#c6a052';

      map.addLayer({
        id: 'radius-circle-fill',
        type: 'fill',
        source: 'radius-circle-source',
        paint: {
          'fill-color': color,
          'fill-opacity': 0.22,
        },
      });

      map.addLayer({
        id: 'radius-circle-stroke',
        type: 'line',
        source: 'radius-circle-source',
        paint: {
          'line-color': color,
          'line-width': 2.5,
          'line-dasharray': [3, 2],
        },
      });

      // Add center marker
      const markerEl = document.createElement('div');
      markerEl.className = 'custom-3d-pin';
      markerEl.innerHTML = `
        <div style="
          width: 26px;
          height: 26px;
          background: linear-gradient(135deg, #c6a052, #7a6348);
          border: 2px solid #ffffff;
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          box-shadow: 0 4px 14px rgba(0,0,0,0.7);
          display: flex;
          align-items: center;
          justify-content: center;
        ">
          <div style="width: 8px; height: 8px; background: #121518; border-radius: 50%; transform: rotate(45deg);"></div>
        </div>
      `;

      markerRef.current = new maplibregl.Marker({ element: markerEl })
        .setLngLat([initialLon, initialLat])
        .addTo(map);
    });

    // Click handler for 3D terrain selection
    map.on('click', async (e) => {
      const { lng, lat } = e.lngLat;
      const roundedLat = parseFloat(lat.toFixed(5));
      const roundedLon = parseFloat(lng.toFixed(5));

      let locName = `Location (${roundedLat}, ${roundedLon})`;
      try {
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${roundedLat}&lon=${roundedLon}&zoom=14`
        );
        if (resp.ok) {
          const data = await resp.json();
          if (data && data.display_name) {
            locName = data.display_name.split(',').slice(0, 3).join(', ');
          }
        }
      } catch (err) {
        // Fallback to coordinates
      }

      onLocationChange({
        name: locName,
        lat: roundedLat,
        lon: roundedLon,
      });
    });

    // Track pitch and bearing during user navigation
    map.on('rotate', () => {
      setBearing(Math.round(map.getBearing()));
    });
    map.on('pitch', () => {
      setPitch(Math.round(map.getPitch()));
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update center, marker, and radius polygon when props change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !selectedLocation) return;

    const { lon, lat } = selectedLocation;

    map.flyTo({
      center: [lon, lat],
      essential: true,
      duration: 1200,
    });

    if (markerRef.current) {
      markerRef.current.setLngLat([lon, lat]);
    }

    if (map.getSource('radius-circle-source')) {
      const circleData = generateCirclePolygon(lon, lat, radiusKm);
      map.getSource('radius-circle-source').setData(circleData);

      const color = MINERAL_COLORS[targetMineral] || '#c6a052';
      if (map.getLayer('radius-circle-fill')) {
        map.setPaintProperty('radius-circle-fill', 'fill-color', color);
      }
      if (map.getLayer('radius-circle-stroke')) {
        map.setPaintProperty('radius-circle-stroke', 'line-color', color);
      }
    }
  }, [selectedLocation, radiusKm, targetMineral]);

  // Adjust pitch helper
  const handlePitchChange = (targetPitch) => {
    const map = mapInstanceRef.current;
    if (!map) return;
    map.easeTo({ pitch: targetPitch, duration: 600 });
    setPitch(targetPitch);
  };

  // Reset bearing to North
  const handleResetNorth = () => {
    const map = mapInstanceRef.current;
    if (!map) return;
    map.easeTo({ bearing: 0, duration: 600 });
    setBearing(0);
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={mapContainerRef} style={{ width: '100%', height: '100%', background: '#11151a' }} />

      {/* 3D Terrain HUD Toolbar */}
      <div style={{
        position: 'absolute',
        bottom: 75,
        left: 16,
        zIndex: 900,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}>
        {/* Preset Tilt Buttons */}
        <div style={{
          background: 'rgba(22, 27, 34, 0.92)',
          border: '1px solid var(--border-brass)',
          borderRadius: 'var(--radius-sm)',
          padding: '4px',
          display: 'flex',
          gap: 4,
          backdropFilter: 'blur(8px)',
        }}>
          <button
            type="button"
            className="btn-secondary"
            style={{
              padding: '4px 8px',
              fontSize: '0.72rem',
              background: pitch < 15 ? 'linear-gradient(135deg, #7a6348, #4d3a24)' : 'transparent',
              borderColor: pitch < 15 ? 'var(--accent-gold)' : 'transparent',
            }}
            onClick={() => handlePitchChange(0)}
            title="Flat Top-Down View (0° Pitch)"
          >
            2D Top-Down (0°)
          </button>

          <button
            type="button"
            className="btn-secondary"
            style={{
              padding: '4px 8px',
              fontSize: '0.72rem',
              background: pitch >= 50 ? 'linear-gradient(135deg, #7a6348, #4d3a24)' : 'transparent',
              borderColor: pitch >= 50 ? 'var(--accent-gold)' : 'transparent',
            }}
            onClick={() => handlePitchChange(60)}
            title="3D Terrain Perspective View (60° Tilt)"
          >
            <Mountain size={13} style={{ marginRight: 3 }} />
            3D Relief (60°)
          </button>

          <button
            type="button"
            className="btn-secondary"
            style={{
              padding: '4px 8px',
              fontSize: '0.72rem',
              background: 'transparent',
              borderColor: 'transparent',
            }}
            onClick={handleResetNorth}
            title="Reset Compass to True North"
          >
            <RotateCcw size={13} style={{ marginRight: 3 }} />
            North ({bearing}°)
          </button>
        </div>
      </div>

      {/* 3D Scientific Elevation Provenance Badge */}
      <div style={{
        position: 'absolute',
        top: 80,
        right: 16,
        zIndex: 900,
        background: 'rgba(22, 27, 34, 0.9)',
        border: '1px solid var(--border-brass)',
        borderRadius: 'var(--radius-sm)',
        padding: '6px 10px',
        fontSize: '0.7rem',
        color: '#d5c4a1',
        maxWidth: '260px',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 6,
      }}>
        <AlertCircle size={14} color="#c6a052" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <b>3D Terrain Engine:</b> USGS 3DEP & SRTM global digital elevation model via AWS Open Data.
          <i style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginTop: 2 }}>
            Represents surface topography only; does NOT display hypothetical subsurface deposit bodies.
          </i>
        </div>
      </div>
    </div>
  );
}
