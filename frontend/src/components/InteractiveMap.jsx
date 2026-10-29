import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import {
  Crosshair,
  Loader2,
  Navigation,
  AlertTriangle,
  Mountain,
  Map as MapIcon,
  Sparkles,
  Layers,
  Eye,
  CheckSquare,
  Square
} from 'lucide-react';
import TerrainMap3D from './TerrainMap3D';
import Prospectivity3DMap from './Prospectivity3DMap';
import { getApiUrl } from '../apiConfig';

// Fix default leaflet icon paths
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom Explorer Pin Icon
const explorerMarkerIcon = L.divIcon({
  className: 'custom-explorer-pin',
  html: `
    <div style="
      width: 28px;
      height: 28px;
      background: linear-gradient(135deg, #00f0ff, #0284c7);
      border: 2px solid #fff;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.75);
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        width: 10px;
        height: 10px;
        background: #0a0d14;
        border-radius: 50%;
        transform: rotate(45deg);
      "></div>
    </div>
  `,
  iconSize: [28, 28],
  iconAnchor: [14, 28],
  popupAnchor: [0, -28],
});

// Known reference mines and mineral occurrences across India
const REFERENCE_MINES = [
  // Manganese (Balaghat corridor)
  { name: 'Ghondi Manganese Mine (Reference Deposit)', lat: 21.9455, lon: 80.4295, mineral: 'Manganese', type: 'Open-Cast Working', ore: 'High Grade Braunite-Pyrolusite' },
  { name: 'Bharweli Manganese Mine (MOIL Deep Shaft)', lat: 21.8860, lon: 80.2240, mineral: 'Manganese', type: 'Underground Working', ore: 'Deep Seated Tabular Orebody' },
  { name: 'Ukwa Manganese Deposit', lat: 21.9720, lon: 80.4680, mineral: 'Manganese', type: 'Stratiform Gondite', ore: 'Bedded Sausar Manganese' },
  // Iron Ore (Singhbhum-Odisha Craton)
  { name: 'Noamundi Iron Mine (Tata Steel)', lat: 22.1500, lon: 85.5000, mineral: 'Iron Ore', type: 'Active Major Producer', ore: 'Hematite (64.5% Fe)' },
  { name: 'Joda East Iron Mine (Tata Steel)', lat: 22.0200, lon: 85.4300, mineral: 'Iron Ore', type: 'Active Major Producer', ore: 'Hematite (63.8% Fe)' },
  { name: 'Kiriburu Iron Mine (SAIL)', lat: 22.0900, lon: 85.3400, mineral: 'Iron Ore', type: 'Active Major Producer', ore: 'Hematite (64.0% Fe)' },
  { name: 'Gua Iron Mine (SAIL IISCO)', lat: 22.2100, lon: 85.3800, mineral: 'Iron Ore', type: 'Active Major Producer', ore: 'Hematite (63.5% Fe)' },
  // Coal (Gondwana Basins)
  { name: 'Manuguru Colliery Complex (SCCL)', lat: 17.9820, lon: 80.7450, mineral: 'Coal', type: 'Active Colliery Complex', ore: 'Barakar Bituminous Coal' },
  { name: 'Jharia Coalfield (BCCL)', lat: 23.7500, lon: 86.4200, mineral: 'Coal', type: 'Prime Coking Coalfield', ore: 'Prime Coking Coal (Seams I-XVIII)' },
  { name: 'Raniganj Coalfield (ECL)', lat: 23.6200, lon: 87.1200, mineral: 'Coal', type: 'Active Mining Area', ore: 'Superior Non-Coking Bituminous' },
  { name: 'Talcher Coalfield (MCL)', lat: 20.9500, lon: 85.2200, mineral: 'Coal', type: 'Major Power Coal Basin', ore: 'Thermal Non-Coking Coal' },
  // Bauxite (East Coast & Central India)
  { name: 'Panchpatmali Bauxite Mine (NALCO)', lat: 18.8200, lon: 83.0200, mineral: 'Bauxite', type: 'Active Major Producer', ore: 'Gibbsitic Bauxite (45.5% Al2O3)' },
  { name: 'Baphlimali Bauxite Plateau (Utkal)', lat: 19.3300, lon: 82.9800, mineral: 'Bauxite', type: 'Active Major Producer', ore: 'Plateau Duricrust (46.2% Al2O3)' },
  { name: 'Amarkantak Bauxite Belt', lat: 22.6800, lon: 81.7500, mineral: 'Bauxite', type: 'Patland Deposit', ore: 'Maikala Lateritic Bauxite' }
];

export default function InteractiveMap({
  selectedLocation,
  radiusKm,
  targetMineral,
  onLocationChange,
  analysisResult,
  mapMode: controlledMapMode,
  onMapModeChange: controlledOnMapModeChange,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const circleRef = useRef(null);
  const anomalyLayerGroupRef = useRef(null);
  const tileBoundaryLayerRef = useRef(null);
  const minesLayerGroupRef = useRef(null);
  const fieldObservationsLayerRef = useRef(null);

  // 3-Way Mode Switcher: '2d' | '3d-terrain' | '3d-prospectivity'
  // Support controlled mapMode from App.jsx or internal fallback
  const [internalMapMode, setInternalMapMode] = useState('2d');
  const mapMode = controlledMapMode !== undefined ? controlledMapMode : internalMapMode;
  const setMapMode = controlledOnMapModeChange || setInternalMapMode;

  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState(null);

  // Layer Toggles
  const [showAnomalies, setShowAnomalies] = useState(true);
  const [showTileBoundary, setShowTileBoundary] = useState(true);
  const [showReferenceMines, setShowReferenceMines] = useState(true);
  const [showFieldObservations, setShowFieldObservations] = useState(true);
  const [fieldObservations, setFieldObservations] = useState([]);

  // Candidate Anomaly Zones (from analysis or backend)
  const candidateZones = analysisResult?.candidate_zones || [];

  // Authentic prospectivity grid check: genuine prediction and calibrated grid matching current mineral
  // Strictly validated only for Manganese within verified footprint (Never display for Coal, Iron Ore, or Bauxite)
  const isProspectivityAvailable = Boolean(
    analysisResult &&
    targetMineral === 'Manganese' &&
    (!analysisResult.mineral || analysisResult.mineral === targetMineral) &&
    analysisResult.prediction &&
    typeof analysisResult.prediction.prospectivity_index === 'number' &&
    analysisResult.prospectivity_grid &&
    analysisResult.prospectivity_grid.status === 'AVAILABLE' &&
    analysisResult.prospectivity_grid.is_calibrated === true &&
    Array.isArray(analysisResult.prospectivity_grid.grid) &&
    analysisResult.prospectivity_grid.grid.length > 0
  );

  // Initialize Leaflet 2D Map
  useEffect(() => {
    if (mapMode !== '2d') return;
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialLat = selectedLocation?.lat || 21.9048;
    const initialLon = selectedLocation?.lon || 80.1849;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLon],
      zoom: 11,
      zoomControl: false,
    });

    L.control.zoom({ position: 'topright' }).addTo(map);

    // Standard OpenStreetMap tiles (no API key required)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | AI Mineral Intelligence',
    }).addTo(map);

    anomalyLayerGroupRef.current = L.layerGroup().addTo(map);
    tileBoundaryLayerRef.current = L.layerGroup().addTo(map);
    minesLayerGroupRef.current = L.layerGroup().addTo(map);
    fieldObservationsLayerRef.current = L.layerGroup().addTo(map);

    map.on('click', async (e) => {
      const { lat, lng } = e.latlng;
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
      } catch (err) {}

      onLocationChange({
        name: locName,
        lat: roundedLat,
        lon: roundedLon,
      });
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
      circleRef.current = null;
    };
  }, [mapMode]);

  // Update target marker and search radius circle
  useEffect(() => {
    if (mapMode !== '2d') {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      if (circleRef.current) {
        circleRef.current.remove();
        circleRef.current = null;
      }
      return;
    }
    const map = mapInstanceRef.current;
    if (!map) return;

    if (!selectedLocation) {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      if (circleRef.current) {
        circleRef.current.remove();
        circleRef.current = null;
      }
      return;
    }

    const { lat, lon, name } = selectedLocation;
    const numLat = Number(lat);
    const numLon = Number(lon);
    const isValid = !isNaN(numLat) && !isNaN(numLon) && numLat >= -90 && numLat <= 90 && numLon >= -180 && numLon <= 180;

    if (!isValid) {
      if (markerRef.current) {
        markerRef.current.remove();
        markerRef.current = null;
      }
      if (circleRef.current) {
        circleRef.current.remove();
        circleRef.current = null;
      }
      return;
    }

    map.setView([numLat, numLon], map.getZoom() < 8 ? 10 : map.getZoom(), {
      animate: true,
      duration: 0.6,
    });

    const radiusMeters = Number(radiusKm) * 1000;
    const areaSqKm = (Math.PI * Math.pow(Number(radiusKm), 2)).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

    // 1. Center Marker: distinct pin at circle's exact center
    const markerPopupContent = `
      <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; line-height: 1.45;">
        <div style="font-weight: 700; color: #0284c7; font-size: 13px; margin-bottom: 2px;">
          ${name || 'Selected Target Location'}
        </div>
        <div>Coordinates: <b>${numLat.toFixed(4)}°N, ${numLon.toFixed(4)}°E</b></div>
        <div>Target Mineral: <b>${targetMineral}</b></div>
        <div>Exploration Radius: <b>${radiusKm} km</b> (≈ ${areaSqKm} km²)</div>
      </div>
    `;

    if (markerRef.current) {
      markerRef.current.setLatLng([numLat, numLon]);
      markerRef.current.setPopupContent(markerPopupContent);
    } else {
      markerRef.current = L.marker([numLat, numLon], { icon: explorerMarkerIcon }).addTo(map);
      markerRef.current.bindPopup(markerPopupContent);
    }

    // 2. Exploration-Radius Circle:
    // - Geographically accurate circle via L.circle() with radius in meters
    // - Semi-transparent amber/gold fill with clearly visible solid border
    // - Roads, labels, and map features remain visible underneath
    // - Displays place name, current radius, and approximate geometric survey area
    const circlePopupContent = `
      <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; line-height: 1.45; min-width: 190px;">
        <div style="font-weight: 700; color: #b45309; font-size: 13px; margin-bottom: 3px;">
          ${name || 'Exploration Survey Area'}
        </div>
        <div>Current Exploration Radius: <b>${radiusKm} km</b></div>
        <div>Approx. Geometric Survey Area: <b>≈ ${areaSqKm} km²</b></div>
        <div>Center: <b>${numLat.toFixed(4)}°N, ${numLon.toFixed(4)}°E</b></div>
        <div style="font-size: 10.5px; color: #64748b; margin-top: 4px; font-style: italic;">
          *Approximate geometric survey area, not confirmed mineral deposits.
        </div>
      </div>
    `;

    const circleTooltipContent = `<b>${name || 'Survey Area'}</b> &bull; ${radiusKm} km radius (≈ ${areaSqKm} km²)`;

    const circleStyle = {
      radius: radiusMeters,
      color: '#d97706',      // Solid amber/gold border
      weight: 2.5,
      opacity: 0.95,
      fillColor: '#f59e0b',  // Semi-transparent amber/gold fill
      fillOpacity: 0.16,     // Ensures roads/labels/features visible underneath
    };

    if (circleRef.current) {
      circleRef.current.setLatLng([numLat, numLon]);
      circleRef.current.setRadius(radiusMeters);
      circleRef.current.setStyle(circleStyle);
      circleRef.current.setPopupContent(circlePopupContent);
      circleRef.current.setTooltipContent(circleTooltipContent);
    } else {
      circleRef.current = L.circle([numLat, numLon], circleStyle).addTo(map);
      circleRef.current.bindPopup(circlePopupContent);
      circleRef.current.bindTooltip(circleTooltipContent, { direction: 'top', sticky: true });
    }
  }, [selectedLocation, radiusKm, targetMineral, mapMode]);

  // Render 20 Anomaly Discovery Zones Layer
  useEffect(() => {
    if (mapMode !== '2d') return;
    const group = anomalyLayerGroupRef.current;
    if (!group) return;

    group.clearLayers();
    if (!showAnomalies) return;

    // Fetch candidate zones if not already present in analysisResult
    const loadZones = async () => {
      let zones = candidateZones;
      if (!zones || zones.length === 0) {
        try {
          const resp = await fetch(getApiUrl('/candidate-zones'));
          if (resp.ok) {
            const data = await resp.json();
            zones = data.candidate_zones || [];
          }
        } catch (e) {}
      }

      zones.forEach((z) => {
        const scorePct = Math.round((z.mean_score || 0.96) * 100);
        const radius = Math.min(20, Math.max(8, Math.sqrt(z.pixels || 60) * 1.5));

        const circle = L.circleMarker([z.lat, z.lon], {
          radius: radius,
          fillColor: '#00f0ff',
          color: '#ffffff',
          weight: 1.5,
          opacity: 0.9,
          fillOpacity: 0.65,
        });

        circle.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px; min-width: 170px;">
            <div style="font-weight: 700; color: #0284c7; margin-bottom: 3px;">
              Discovery Zone #${z.zone_id}
            </div>
            <div style="color: #0f172a; margin-bottom: 2px;">
              Mean Prospectivity: <b>${scorePct}%</b> (Max: ${Math.round((z.max_score || 1.0) * 100)}%)
            </div>
            <div style="font-size: 11px; color: #64748b;">
              Cluster Size: ${z.pixels} pixels (20m Sentinel-2)
            </div>
            <div style="font-size: 11px; color: #64748b;">
              Coords: ${z.lat.toFixed(4)}°N, ${z.lon.toFixed(4)}°E
            </div>
          </div>
        `);

        circle.on('click', () => {
          onLocationChange({
            name: `Zone ${z.zone_id} Anomaly Cluster`,
            lat: z.lat,
            lon: z.lon,
          });
        });

        group.addLayer(circle);
      });
    };

    loadZones();
  }, [candidateZones, showAnomalies, mapMode]);

  // Render Tile Footprint Boundaries (Discovered Scene & Model Domain)
  useEffect(() => {
    if (mapMode !== '2d') return;
    const group = tileBoundaryLayerRef.current;
    if (!group) return;

    group.clearLayers();
    if (!showTileBoundary) return;

    // 1. Tile T44QMK Balaghat Model Domain bounds: Lat [21.4880, 22.4220], Lon [79.7900, 80.7600]
    const boundsPolygon = [
      [21.4880, 79.7900],
      [21.4880, 80.7600],
      [22.4220, 80.7600],
      [22.4220, 79.7900],
    ];

    const polyT44QMK = L.polygon(boundsPolygon, {
      color: '#38bdf8',
      weight: 1.5,
      dashArray: '6, 6',
      fillColor: '#38bdf8',
      fillOpacity: 0.04,
    });

    polyT44QMK.bindPopup(`
      <div style="font-family: sans-serif; font-size: 12px;">
        <b style="color: #0284c7;">Tile T44QMK Model Domain Boundary</b><br/>
        <span>Balaghat-Nagpur-Bhandara Manganese AI Model Training Domain</span><br/>
        <span>Lat: 21.488° to 22.422° &bull; Lon: 79.790° to 80.760°</span>
      </div>
    `);
    group.addLayer(polyT44QMK);

    // 2. Discovered Copernicus Scene Footprint (if different and polygon available)
    const activeScene = analysisResult?.satellite_scenes?.[0] || analysisResult?.satellite_coverage?.scenes?.[0];
    if (activeScene && activeScene.geofootprint && activeScene.geofootprint.coordinates) {
      try {
        const coords = activeScene.geofootprint.coordinates[0]; // GeoJSON [lon, lat]
        const leafletCoords = coords.map((c) => [c[1], c[0]]);
        const scenePoly = L.polygon(leafletCoords, {
          color: '#10b981',
          weight: 2,
          dashArray: '4, 4',
          fillColor: '#10b981',
          fillOpacity: 0.06,
        });
        scenePoly.bindPopup(`
          <div style="font-family: sans-serif; font-size: 12px;">
            <b style="color: #10b981;">Discovered Copernicus Sentinel-2 Footprint</b><br/>
            <span>Product: <b>${activeScene.scene_id}</b></span><br/>
            <span>Tile: <b>${activeScene.tile_id}</b> &bull; Cloud: <b>${activeScene.cloud_cover_pct}%</b></span><br/>
            <span>Acquired: ${activeScene.acquisition_date}</span>
          </div>
        `);
        group.addLayer(scenePoly);
      } catch (e) {}
    }
  }, [showTileBoundary, mapMode, analysisResult]);

  // Render Field Observations Layer with Status-Colored Markers
  useEffect(() => {
    if (mapMode !== '2d') return;
    const group = fieldObservationsLayerRef.current;
    if (!group) return;

    group.clearLayers();
    if (!showFieldObservations) return;

    const loadObservations = async () => {
      try {
        const resp = await fetch(getApiUrl('/api/observations?limit=200'));
        if (!resp.ok) return;
        const data = await resp.json();
        const obsList = data.observations || [];
        setFieldObservations(obsList);

        obsList.forEach((obs) => {
          let pinColor = '#94a3b8';
          const st = obs.verification_status || 'DRAFT';
          if (st === 'VERIFIED') pinColor = '#10b981';
          else if (st === 'UNDER_REVIEW' || st === 'SUBMITTED') pinColor = '#f59e0b';
          else if (st === 'REJECTED') pinColor = '#ef4444';
          else if (st === 'NEEDS_MORE_EVIDENCE') pinColor = '#a855f7';

          const obsIcon = L.divIcon({
            className: 'custom-obs-pin',
            html: `
              <div style="
                width: 22px;
                height: 22px;
                background: ${pinColor};
                border: 2px solid #ffffff;
                border-radius: 50%;
                box-shadow: 0 0 10px ${pinColor};
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                font-weight: 800;
                color: #0a0d14;
              ">
                F
              </div>
            `,
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            popupAnchor: [0, -11],
          });

          const obsMarker = L.marker([obs.latitude, obs.longitude], { icon: obsIcon });
          obsMarker.bindPopup(`
            <div style="font-family: sans-serif; font-size: 12px; color: #0f172a; min-width: 190px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <b style="color: #0284c7;">${obs.id}</b>
                <span style="font-size: 10px; padding: 1px 5px; border-radius: 3px; background: ${pinColor}; color: #fff; font-weight: 700;">
                  ${obs.verification_status}
                </span>
              </div>
              <div style="font-weight: 600; color: #334155; margin-bottom: 2px;">
                ${obs.mineral} &bull; ${obs.observation_type}
              </div>
              <div style="font-size: 11px; color: #475569; margin-bottom: 4px; line-height: 1.3;">
                ${obs.rock_soil_description ? obs.rock_soil_description.slice(0, 80) : ''}...
              </div>
              <div style="font-size: 10.5px; color: #64748b;">
                Observer: ${obs.observer_name}
              </div>
              <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; font-style: italic;">
                *Ground observation record, not confirmed deposit.
              </div>
            </div>
          `);

          group.addLayer(obsMarker);
        });
      } catch (e) {
        console.warn('Field observations layer fetch error:', e);
      }
    };

    loadObservations();
  }, [showFieldObservations, mapMode]);

  // Render Documented Mineral Occurrences (from Analysis or Baseline Reference Mines)
  useEffect(() => {
    if (mapMode !== '2d') return;
    const group = minesLayerGroupRef.current;
    if (!group) return;

    group.clearLayers();
    if (!showReferenceMines) return;

    const activeOccurrences = analysisResult?.documented_occurrences || analysisResult?.geological_evidence?.documented_occurrences;
    const mineralFilteredMines = REFERENCE_MINES.filter((m) => !m.mineral || m.mineral === targetMineral);
    const minesToRender = (activeOccurrences && activeOccurrences.length > 0) ? activeOccurrences : mineralFilteredMines;

    minesToRender.forEach((mine) => {
      let iconColor = '#f59e0b'; // default amber
      let iconEmoji = '⛏️';

      if (targetMineral === 'Coal' || mine.mineral === 'Coal') {
        iconColor = '#64748b';
        iconEmoji = '🪨';
      } else if (targetMineral === 'Iron Ore' || mine.mineral === 'Iron Ore') {
        iconColor = '#ef4444';
        iconEmoji = '⛰️';
      } else if (targetMineral === 'Bauxite' || mine.mineral === 'Bauxite') {
        iconColor = '#f59e0b';
        iconEmoji = '🧱';
      } else if (targetMineral === 'Manganese' || mine.mineral === 'Manganese') {
        iconColor = '#00f0ff';
        iconEmoji = '⛏️';
      }

      const mineIcon = L.divIcon({
        className: 'mine-marker-pin',
        html: `
          <div style="
            width: 22px;
            height: 22px;
            background: ${iconColor};
            border: 2px solid #fff;
            border-radius: 4px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #000;
            font-size: 11px;
            font-weight: 800;
          ">${iconEmoji}</div>
        `,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      const marker = L.marker([mine.lat, mine.lon], { icon: mineIcon });
      const distInfo = mine.distance_km !== undefined ? `<br/><span>Distance: <b>${mine.distance_km} km</b> from target</span>` : '';
      const verStatus = mine.verification_status ? `<br/><span style="color: #10b981; font-weight: 600;">Status: ${mine.verification_status}</span>` : '';
      const evidence = mine.supporting_evidence ? `<br/><span style="font-size: 11px; color: #475569;">${mine.supporting_evidence}</span>` : '';

      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 12px; max-width: 240px;">
          <b style="color: ${iconColor === '#00f0ff' ? '#0284c7' : iconColor};">${mine.name}</b><br/>
          <span>Type: <b>${mine.type || 'Mineral Occurrence'}</b> (${mine.status || 'Verified'})</span>
          ${distInfo}
          ${verStatus}
          ${evidence}
          <br/><span>Coords: ${mine.lat}°N, ${mine.lon}°E</span>
        </div>
      `);
      group.addLayer(marker);
    });
  }, [showReferenceMines, mapMode, analysisResult, targetMineral]);

  // Live GPS Handlers
  const handleUseLiveLocation = () => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.');
      return;
    }
    setGpsLoading(true);
    setGpsError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setGpsLoading(false);
        const lat = parseFloat(pos.coords.latitude.toFixed(5));
        const lon = parseFloat(pos.coords.longitude.toFixed(5));
        if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
          setGpsError('Received invalid GPS coordinates from device.');
          return;
        }
        let locName = `Live GPS (${lat}, ${lon})`;
        try {
          const resp = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=14`
          );
          if (resp.ok) {
            const data = await resp.json();
            if (data && data.display_name) {
              locName = data.display_name.split(',').slice(0, 3).join(', ');
            }
          }
        } catch (err) {}

        onLocationChange({
          name: locName,
          lat,
          lon,
          isGps: true,
        });
      },
      (err) => {
        setGpsLoading(false);
        if (err.code === 1) setGpsError('Location permission denied.');
        else if (err.code === 2) setGpsError('GPS signal unavailable.');
        else setGpsError('GPS request timed out.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  return (
    <div className="map-section" style={{ position: 'relative', width: '100%', height: '100%', minHeight: '520px' }}>
      {/* 3-Way Mode Viewports */}
      {mapMode === '2d' ? (
        <div ref={mapContainerRef} className="map-canvas-container" id="exploration-map" style={{ width: '100%', height: '100%' }} />
      ) : mapMode === '3d-terrain' ? (
        <TerrainMap3D
          key="terrain-3d"
          selectedLocation={selectedLocation}
          radiusKm={radiusKm}
          targetMineral={targetMineral}
          analysisResult={analysisResult}
          onLocationChange={onLocationChange}
          onFallbackTo2D={() => setMapMode('2d')}
        />
      ) : isProspectivityAvailable ? (
        <Prospectivity3DMap
          key="prospectivity-3d"
          selectedLocation={selectedLocation}
          targetMineral={targetMineral}
          radiusKm={radiusKm}
          analysisResult={analysisResult}
          onLocationChange={onLocationChange}
          onSwitchToTerrain={() => setMapMode('3d-terrain')}
          onSwitchTo2D={() => setMapMode('2d')}
        />
      ) : (
        /* Fallback Behavior B: If no valid prospectivity grid exists:
           Show the working 3D terrain visualization with an explanation that prospectivity predictions are unavailable */
        <TerrainMap3D
          key="terrain-3d-fallback"
          selectedLocation={selectedLocation}
          radiusKm={radiusKm}
          targetMineral={targetMineral}
          analysisResult={analysisResult}
          onLocationChange={onLocationChange}
          onFallbackTo2D={() => setMapMode('2d')}
          prospectivityNotice={{
            mineral: targetMineral,
            status: !analysisResult
              ? 'DATA_NOT_AVAILABLE'
              : analysisResult.status === 'OUTSIDE_INDIA_TERRITORY'
              ? 'DATA_NOT_AVAILABLE'
              : targetMineral === 'Manganese' && !isProspectivityAvailable
              ? 'OUTSIDE_TRAINING_FOOTPRINT'
              : 'DATA_NOT_AVAILABLE',
            coverage_status: !analysisResult
              ? 'DATA_NOT_AVAILABLE'
              : (analysisResult.coverage_status?.coverage_status || (targetMineral === 'Manganese' && !isProspectivityAvailable ? 'OUTSIDE_TRAINING_FOOTPRINT' : 'DATA_NOT_AVAILABLE')),
            reason: !analysisResult
              ? `Select an exploration target and run geographical analysis to inspect available spatial data for ${targetMineral}.`
              : targetMineral !== 'Manganese'
              ? `No validated spatial machine-learning model exists for ${targetMineral}. Spatial AI scores and 3D prospectivity meshes are strictly withheld to preserve scientific integrity. Consult the evidence dossier below for certified geological records.`
              : 'The validated Manganese Random Forest model is trained specifically on Sentinel-2 Tile T44QMK (Balaghat corridor). Target coordinates lie outside this validated training footprint.'
          }}
        />
      )}

      {/* Outside India Territorial Alert Banner */}
      {(analysisResult?.status === 'OUTSIDE_INDIA_TERRITORY' || analysisResult?.is_within_india === false) && (
        <div
          style={{
            position: 'absolute',
            top: 16,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 1000,
            background: 'rgba(220, 38, 38, 0.95)',
            border: '1px solid #fca5a5',
            color: '#fff',
            padding: '8px 18px',
            borderRadius: '8px',
            fontSize: '0.8rem',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            boxShadow: '0 6px 20px rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(6px)',
          }}
        >
          <AlertTriangle size={16} />
          <span>{analysisResult.message || 'Target coordinates lie outside sovereign Indian territory (Lat 6.5°N - 37.5°N, Lon 68.0°E - 97.5°E).'}</span>
        </div>
      )}

      {/* Floating 3-Way Mode Switcher & GPS Toolbar */}
      <div
        style={{
          position: 'absolute',
          top: 80,
          left: 16,
          zIndex: 900,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        {/* 3-Way Switcher: 2D Map / 3D Terrain / 3D Prospectivity */}
        <div
          style={{
            display: 'flex',
            background: 'rgba(15, 23, 42, 0.94)',
            border: '1.5px solid rgba(0, 240, 255, 0.3)',
            borderRadius: '8px',
            padding: '3px',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.6)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <button
            type="button"
            className="btn-mode-toggle"
            style={{
              padding: '6px 11px',
              fontSize: '0.75rem',
              fontWeight: mapMode === '2d' ? 700 : 500,
              border: 'none',
              borderRadius: '6px',
              background: mapMode === '2d' ? 'linear-gradient(135deg, #0284c7, #0369a1)' : 'transparent',
              color: mapMode === '2d' ? '#fff' : '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
            onClick={() => setMapMode('2d')}
            id="btn-switch-2d-map"
            title="Switch to 2D Cartographic Map (Leaflet)"
          >
            <MapIcon size={13} />
            <span>2D Map</span>
          </button>

          <button
            type="button"
            className="btn-mode-toggle"
            style={{
              padding: '6px 11px',
              fontSize: '0.75rem',
              fontWeight: mapMode === '3d-terrain' ? 700 : 500,
              border: 'none',
              borderRadius: '6px',
              background: mapMode === '3d-terrain' ? 'linear-gradient(135deg, #d97706, #b45309)' : 'transparent',
              color: mapMode === '3d-terrain' ? '#fff' : '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
            onClick={() => setMapMode('3d-terrain')}
            id="btn-switch-3d-terrain"
            title="Switch to 3D Topographic Terrain Elevation (MapLibre GL)"
          >
            <Mountain size={13} />
            <span>3D Terrain</span>
          </button>

          <button
            type="button"
            className="btn-mode-toggle"
            style={{
              padding: '6px 11px',
              fontSize: '0.75rem',
              fontWeight: mapMode === '3d-prospectivity' ? 700 : 500,
              border: 'none',
              borderRadius: '6px',
              background: mapMode === '3d-prospectivity' ? 'linear-gradient(135deg, #00f0ff, #0284c7)' : 'transparent',
              color: mapMode === '3d-prospectivity' ? '#0a0d14' : '#00f0ff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
            }}
            onClick={() => setMapMode('3d-prospectivity')}
            id="btn-switch-3d-prospectivity"
            title="Switch to 3D AI Prospectivity Surface Mesh (Three.js)"
          >
            <Sparkles size={13} />
            <span>3D Prospectivity</span>
          </button>
        </div>

        {/* GPS Live Button */}
        <button
          className={`gps-btn ${gpsLoading ? 'loading' : ''}`}
          onClick={handleUseLiveLocation}
          disabled={gpsLoading}
          id="btn-live-gps"
        >
          {gpsLoading ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Navigation size={14} color="#00f0ff" />
          )}
          <span>{gpsLoading ? 'Acquiring GPS...' : 'Use My Current Location'}</span>
        </button>

        {gpsError && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.9)',
              color: '#fff',
              fontSize: '0.72rem',
              padding: '6px 10px',
              borderRadius: '6px',
              maxWidth: '260px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <AlertTriangle size={14} />
            <span>{gpsError}</span>
          </div>
        )}

        {/* Layer Toggles (Visible in 2D mode) */}
        {mapMode === '2d' && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.88)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '8px 10px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              backdropFilter: 'blur(8px)',
            }}
          >
            <div style={{ fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Map Overlays
            </div>

            <label
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', color: '#e2e8f0', cursor: 'pointer' }}
              onClick={() => setShowAnomalies(!showAnomalies)}
            >
              {showAnomalies ? <CheckSquare size={13} color="#00f0ff" /> : <Square size={13} color="#64748b" />}
              <span>20 Anomaly Discovery Clusters</span>
            </label>

            <label
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', color: '#e2e8f0', cursor: 'pointer' }}
              onClick={() => setShowTileBoundary(!showTileBoundary)}
            >
              {showTileBoundary ? <CheckSquare size={13} color="#38bdf8" /> : <Square size={13} color="#64748b" />}
              <span>Tile T44QMK Footprint Boundary</span>
            </label>

            <label
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', color: '#e2e8f0', cursor: 'pointer' }}
              onClick={() => setShowReferenceMines(!showReferenceMines)}
            >
              {showReferenceMines ? <CheckSquare size={13} color="#f59e0b" /> : <Square size={13} color="#64748b" />}
              <span>Known Mines & Reference Deposits</span>
            </label>

            <label
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.74rem', color: '#e2e8f0', cursor: 'pointer' }}
              onClick={() => setShowFieldObservations(!showFieldObservations)}
            >
              {showFieldObservations ? <CheckSquare size={13} color="#10b981" /> : <Square size={13} color="#64748b" />}
              <span>Field Verification Records ({fieldObservations.length})</span>
            </label>
          </div>
        )}
      </div>

      {/* Floating Coordinates & Status Readout at bottom */}
      <div className="map-coordinates-badge">
        <div className="coord-dot" />
        <span>
          {selectedLocation ? (
            <>
              <b>{selectedLocation.name?.split(',')[0]}</b> &bull; Lat: {selectedLocation.lat?.toFixed(4)} &bull; Lon:{' '}
              {selectedLocation.lon?.toFixed(4)} &bull; Radius: {radiusKm} km &bull;{' '}
              <i>
                {mapMode === '2d'
                  ? '2D Cartographic Map'
                  : mapMode === '3d-terrain'
                  ? '3D Topographic Relief'
                  : '3D Prospectivity Mesh'}
              </i>
            </>
          ) : (
            'Click anywhere on map to select exploration target'
          )}
        </span>
      </div>
    </div>
  );
}
