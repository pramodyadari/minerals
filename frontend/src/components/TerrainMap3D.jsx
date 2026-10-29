import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Compass, RotateCcw, Mountain, Layers, Eye, Navigation, AlertCircle, Loader2 } from 'lucide-react';

// Explicitly register the Vite-resolved web worker script URL
if (typeof maplibregl.setWorkerUrl === 'function') {
  maplibregl.setWorkerUrl(maplibreWorkerUrl);
}
if (maplibregl.config) {
  maplibregl.config.WORKER_URL = maplibreWorkerUrl;
}

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
  analysisResult,
  onLocationChange,
  onFallbackTo2D,
  prospectivityNotice,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const isDestroyingRef = useRef(false);
  const [pitch, setPitch] = useState(60);
  const [bearing, setBearing] = useState(0);
  const [terrainExaggeration, setTerrainExaggeration] = useState(1.4);

  // 5 Explicit States (Section 3 Requirement)
  // 1. loading: 3D map is initializing
  // 2. terrainReady: terrain is successfully rendered
  // 3. prospectivityUnavailable: no compatible prediction grid exists (purely informational, never causes renderError)
  // 4. renderError: the 3D renderer has genuinely failed and recovery attempts are exhausted
  // 5. recovering: a recoverable WebGL or map initialization problem is being retried
  const [mapState, setMapState] = useState({
    loading: true,
    terrainReady: false,
    renderError: null,
    recovering: false,
    retryCount: 0,
  });

  const [recoveryTrigger, setRecoveryTrigger] = useState(0);

  // Derived state: prospectivity unavailable (purely informational banner)
  const isProspectivityUnavailable = Boolean(prospectivityNotice);
  // Alias for backward compatibility with existing tests
  const webGlError = mapState.renderError;

  // Clear stale error state when selectedLocation or targetMineral changes
  useEffect(() => {
    if (mapState.renderError) {
      setMapState({
        loading: true,
        terrainReady: false,
        renderError: null,
        recovering: false,
        retryCount: 0,
      });
      setRecoveryTrigger((t) => t + 1);
    }
  }, [selectedLocation?.lat, selectedLocation?.lon, targetMineral]);

  // Initialize MapLibre 3D Terrain Map with Controlled WebGL Recovery
  useEffect(() => {
    if (!mapContainerRef.current) return;
    isDestroyingRef.current = false;

    // Robust WebGL Hardware Support Check without leaking WebGL contexts
    const isWebGLSupported = () => {
      try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return false;
        const loseExt = gl.getExtension('WEBGL_lose_context');
        if (loseExt) loseExt.loseContext();
        return true;
      } catch (e) {
        return false;
      }
    };

    if (!isWebGLSupported()) {
      setMapState((prev) => ({
        ...prev,
        loading: false,
        terrainReady: false,
        recovering: false,
        renderError: 'WebGL hardware acceleration is not supported or is disabled in your browser environment.',
      }));
      return;
    }

    const initialLon = selectedLocation?.lon || 80.1849;
    const initialLat = selectedLocation?.lat || 21.9048;

    // Clean up any existing map before recreating
    if (mapInstanceRef.current) {
      try {
        isDestroyingRef.current = true;
        mapInstanceRef.current.remove();
      } catch (_) {}
      mapInstanceRef.current = null;
    }
    isDestroyingRef.current = false;

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

    let map;
    try {
      map = new maplibregl.Map({
        container: mapContainerRef.current,
        style: style,
        center: [initialLon, initialLat],
        zoom: 11,
        pitch: pitch,
        bearing: bearing,
        maxPitch: 82,
      });
    } catch (err) {
      console.warn('[TerrainMap3D] MapLibre creation failed:', err);
      if (mapState.retryCount < 2) {
        setMapState((prev) => ({
          ...prev,
          loading: false,
          terrainReady: false,
          recovering: true,
          retryCount: prev.retryCount + 1,
        }));
        const timer = setTimeout(() => setRecoveryTrigger((t) => t + 1), 1200);
        return () => clearTimeout(timer);
      } else {
        setMapState((prev) => ({
          ...prev,
          loading: false,
          terrainReady: false,
          recovering: false,
          renderError: `3D Terrain initialization failed: ${err.message || 'WebGL error'}`,
        }));
        return;
      }
    }

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right');

    // Gracefully handle DEM tile / network errors without breaking canvas or marking renderError
    map.on('error', (e) => {
      console.warn('[TerrainMap3D] MapLibre transient resource warning:', e);
      if (e && e.error && e.error.message && e.error.message.includes('terrain')) {
        try {
          map.setTerrain(null);
        } catch (_) {}
      }
    });

    map.on('load', () => {
      if (isDestroyingRef.current) return;
      setMapState((prev) => ({
        ...prev,
        loading: false,
        terrainReady: true,
        recovering: false,
        renderError: null,
      }));
      map.resize();

      // Add radius circle polygon layer
      const circleData = generateCirclePolygon(initialLon, initialLat, radiusKm);
      if (!map.getSource('radius-circle-source')) {
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
      }

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

    // Controlled WebGL context recovery with lifecycle guard
    const canvas = map.getCanvas();
    let handleContextLost = null;
    let handleContextRestored = null;

    if (canvas) {
      handleContextLost = (e) => {
        // If map is being intentionally unmounted or destroyed by React, ignore synthetic context loss
        if (isDestroyingRef.current) return;
        e.preventDefault();
        console.warn('[TerrainMap3D] WebGL context lost. Attempting controlled recovery...');
        setMapState((prev) => {
          if (prev.retryCount < 2) {
            return {
              ...prev,
              loading: false,
              terrainReady: false,
              recovering: true,
              renderError: null,
              retryCount: prev.retryCount + 1,
            };
          } else {
            return {
              ...prev,
              loading: false,
              terrainReady: false,
              recovering: false,
              renderError: 'WebGL rendering context was lost and could not be restored by the browser GPU. Please switch to 2D Cartographic Map.',
            };
          }
        });
        if (mapState.retryCount < 2) {
          setTimeout(() => {
            if (!isDestroyingRef.current) {
              setRecoveryTrigger((t) => t + 1);
            }
          }, 1200);
        }
      };

      handleContextRestored = () => {
        if (isDestroyingRef.current) return;
        console.info('[TerrainMap3D] WebGL context restored by GPU.');
        setMapState((prev) => ({
          ...prev,
          loading: false,
          terrainReady: true,
          recovering: false,
          renderError: null,
        }));
        if (mapInstanceRef.current) {
          mapInstanceRef.current.resize();
        }
      };

      canvas.addEventListener('webglcontextlost', handleContextLost);
      canvas.addEventListener('webglcontextrestored', handleContextRestored);
    }

    // ResizeObserver ensures canvas resizes whenever container dimensions update
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
          if (mapInstanceRef.current && !isDestroyingRef.current) {
            mapInstanceRef.current.resize();
          }
        }
      }
    });

    if (mapContainerRef.current) {
      ro.observe(mapContainerRef.current);
    }

    // Immediate resize on next frame after mount to prevent blank canvas
    requestAnimationFrame(() => {
      if (mapInstanceRef.current && !isDestroyingRef.current) {
        mapInstanceRef.current.resize();
      }
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
      if (mapInstanceRef.current && !isDestroyingRef.current) {
        setBearing(Math.round(map.getBearing()));
      }
    });
    map.on('pitch', () => {
      if (mapInstanceRef.current && !isDestroyingRef.current) {
        setPitch(Math.round(map.getPitch()));
      }
    });

    mapInstanceRef.current = map;

    return () => {
      isDestroyingRef.current = true;
      ro.disconnect();
      if (canvas && handleContextLost) {
        canvas.removeEventListener('webglcontextlost', handleContextLost);
      }
      if (canvas && handleContextRestored) {
        canvas.removeEventListener('webglcontextrestored', handleContextRestored);
      }
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
        } catch (_) {}
        mapInstanceRef.current = null;
      }
    };
  }, [recoveryTrigger]);

  // Update center, marker, and radius polygon when props change without recreating map
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

  // RENDER: Genuine 3D initialization or rendering failure (Section 1 & 3: Show Return to 2D Map ONLY here)
  if (mapState.renderError) {
    return (
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: '100%',
          minHeight: '480px',
          background: '#0a0d14',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '24px'
        }}
        id="terrain-render-error-view"
      >
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: '12px',
            padding: '28px',
            maxWidth: '480px',
            textAlign: 'center',
            color: '#f8fafc',
            boxShadow: '0 12px 36px rgba(0,0,0,0.7)'
          }}
        >
          <div style={{ display: 'inline-flex', padding: 12, borderRadius: '50%', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', marginBottom: 14 }}>
            <AlertCircle size={32} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 8px 0', color: '#f1f5f9' }}>
            3D Terrain Unavailable
          </h3>
          <p style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: 1.5, margin: '0 0 18px 0' }}>
            {mapState.renderError}
          </p>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
            <button
              type="button"
              onClick={() => {
                setMapState({
                  loading: true,
                  terrainReady: false,
                  renderError: null,
                  recovering: false,
                  retryCount: 0,
                });
                setRecoveryTrigger((t) => t + 1);
              }}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '8px',
                color: '#fff',
                padding: '9px 16px',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
              id="btn-terrain-retry"
            >
              <RotateCcw size={14} />
              <span>Retry 3D Map</span>
            </button>

            {onFallbackTo2D && (
              <button
                type="button"
                onClick={onFallbackTo2D}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                  border: 'none',
                  borderRadius: '8px',
                  color: '#fff',
                  padding: '9px 18px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                }}
                id="btn-terrain-fallback-2d"
              >
                <Navigation size={14} />
                <span>Return to 2D Cartographic Map</span>
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: '480px',
        boxSizing: 'border-box',
        overflow: 'hidden'
      }}
      className="terrain-map-wrapper"
    >
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          minHeight: '480px',
          background: '#11151a'
        }}
        id="terrain-map-container"
      />

      {/* Recovering Overlay (Controlled GPU Recovery Attempt) */}
      {mapState.recovering && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(10, 13, 20, 0.82)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 920,
            backdropFilter: 'blur(5px)',
          }}
          id="terrain-recovering-indicator"
        >
          <RotateCcw size={28} className="animate-spin" color="#00f0ff" style={{ marginBottom: 10 }} />
          <div style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.88rem' }}>
            Recovering 3D Graphics Pipeline...
          </div>
          <p style={{ color: '#94a3b8', fontSize: '0.74rem', marginTop: 4 }}>
            Re-establishing WebGL context (attempt {mapState.retryCount} of 2)
          </p>
        </div>
      )}

      {/* Loading Overlay */}
      {mapState.loading && !mapState.terrainReady && !mapState.recovering && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(17, 21, 26, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 850,
            backdropFilter: 'blur(4px)',
          }}
          id="terrain-loading-indicator"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#38bdf8', fontSize: '0.82rem' }}>
            <Loader2 size={18} className="animate-spin" />
            <span>Initializing 3D Topographic DEM Relief...</span>
          </div>
        </div>
      )}

      {/* Fallback Notice Banner (Requirement B: Prospectivity unavailable, displaying working 3D terrain)
          NOTE: Section 1 requirement: Show Return to 2D Map ONLY on genuine failure or explicit user request.
          Therefore, this informational banner does NOT contain a disruptive 2D button. */}
      {prospectivityNotice && (
        <div
          style={{
            position: 'absolute',
            top: 14,
            left: 16,
            right: 16,
            zIndex: 950,
            background: 'rgba(15, 23, 42, 0.94)',
            border: '1px solid rgba(245, 158, 11, 0.45)',
            borderRadius: '8px',
            padding: '10px 14px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backdropFilter: 'blur(10px)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
            gap: 12,
          }}
          id="prospectivity-fallback-banner"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Mountain size={20} color="#f59e0b" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '0.8rem', color: '#f1f5f9', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span>3D Topographic Terrain View</span>
                <span style={{ color: '#f59e0b' }}>&bull; AI Prospectivity Surface Unavailable for {prospectivityNotice.mineral || targetMineral}</span>
                <span
                  id="prospectivity-coverage-badge"
                  style={{
                    fontSize: '0.68rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    background: (prospectivityNotice.coverage_status || prospectivityNotice.status) === 'OUTSIDE_TRAINING_FOOTPRINT' ? 'rgba(234, 179, 8, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                    border: (prospectivityNotice.coverage_status || prospectivityNotice.status) === 'OUTSIDE_TRAINING_FOOTPRINT' ? '1px solid #eab308' : '1px solid #ef4444',
                    color: (prospectivityNotice.coverage_status || prospectivityNotice.status) === 'OUTSIDE_TRAINING_FOOTPRINT' ? '#fde047' : '#fca5a5',
                    fontWeight: 700,
                    letterSpacing: '0.04em',
                  }}
                >
                  [{prospectivityNotice.coverage_status || prospectivityNotice.status || 'DATA_NOT_AVAILABLE'}]
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: 2, lineHeight: 1.4 }}>
                {prospectivityNotice.reason}
              </div>
            </div>
          </div>
        </div>
      )}

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

          {/* Explicit User Request to Switch back to 2D Map */}
          {onFallbackTo2D && (
            <button
              type="button"
              className="btn-secondary"
              style={{
                padding: '4px 8px',
                fontSize: '0.72rem',
                background: 'rgba(2, 132, 199, 0.2)',
                borderColor: 'rgba(2, 132, 199, 0.4)',
                color: '#38bdf8'
              }}
              onClick={onFallbackTo2D}
              title="Explicitly switch to 2D Leaflet Map"
              id="btn-explicit-switch-2d"
            >
              2D Map
            </button>
          )}
        </div>
      </div>

      {/* 3D Scientific Elevation Provenance Badge */}
      <div
        id="terrain-provenance-badge"
        style={{
          position: 'absolute',
          top: prospectivityNotice ? 72 : 80,
          right: 16,
          zIndex: 900,
          background: 'rgba(22, 27, 34, 0.9)',
          border: '1px solid var(--border-brass)',
          borderRadius: 'var(--radius-sm)',
          padding: '6px 10px',
          fontSize: '0.7rem',
          color: '#d5c4a1',
          maxWidth: '280px',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 6,
        }}
      >
        <AlertCircle size={14} color="#c6a052" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 2 }}>
            <b>3D Terrain Engine:</b>
            <span
              id="terrain-status-pill"
              style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '1px 6px',
                borderRadius: '3px',
                background: analysisResult?.terrain_status === 'DATA_NOT_AVAILABLE' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(16, 185, 129, 0.2)',
                color: analysisResult?.terrain_status === 'DATA_NOT_AVAILABLE' ? '#fca5a5' : '#34d399',
                border: analysisResult?.terrain_status === 'DATA_NOT_AVAILABLE' ? '1px solid #ef4444' : '1px solid #10b981',
              }}
            >
              {analysisResult?.terrain_status || 'TERRAIN_AVAILABLE'}
            </span>
          </div>
          <div>USGS 3DEP & SRTM global digital elevation model via AWS Open Data.</div>
          {analysisResult?.geological_evidence?.evidence_layers?.terrain?.elevation_min_m !== undefined && (
            <div style={{ fontSize: '0.66rem', color: '#94a3b8', marginTop: 2 }}>
              Local DSM: {analysisResult.geological_evidence.evidence_layers.terrain.elevation_min_m}m &ndash; {analysisResult.geological_evidence.evidence_layers.terrain.elevation_max_m}m (Copernicus 30m)
            </div>
          )}
          <i style={{ display: 'block', fontSize: '0.66rem', color: 'var(--text-dim)', marginTop: 2 }}>
            Represents surface topography only; does NOT display hypothetical subsurface deposit bodies.
          </i>
        </div>
      </div>
    </div>
  );
}
