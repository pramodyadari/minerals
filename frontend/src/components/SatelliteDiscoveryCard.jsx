import React, { useState, useEffect } from 'react';
import {
  Satellite,
  Layers,
  Calendar,
  Cloud,
  CheckCircle2,
  Clock,
  AlertCircle,
  BarChart2,
  Cpu,
  ChevronDown,
  ChevronUp,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Grid
} from 'lucide-react';

export default function SatelliteDiscoveryCard({
  selectedLocation,
  selectedMineral,
  selectedRadius,
  spectralData,
  satelliteScenes,
  onSelectScene,
}) {
  const [selectedSceneId, setSelectedSceneId] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true);

  // Load scenes from props or backend
  useEffect(() => {
    if (satelliteScenes && satelliteScenes.length > 0) {
      setScenes(satelliteScenes);
      setSelectedSceneId(satelliteScenes[0].scene_id);
    } else if (selectedLocation?.lat && selectedLocation?.lon) {
      setLoading(true);
      fetch(
        `http://127.0.0.1:8000/satellite-scenes?latitude=${selectedLocation.lat}&longitude=${selectedLocation.lon}&mineral=${selectedMineral}`
      )
        .then((res) => res.json())
        .then((data) => {
          if (data?.scenes) {
            setScenes(data.scenes);
            setSelectedSceneId(data.scenes[0]?.scene_id);
          }
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [selectedLocation, selectedMineral, satelliteScenes]);

  const activeScene = scenes.find((s) => s.scene_id === selectedSceneId) || scenes[0];

  // Authentic raster processing indicators
  const pixelsProcessed = Boolean(spectralData?.raster_pixels_processed);
  const pixelCoverage = spectralData?.pixel_coverage;
  const tileInfo = spectralData?.tile_info;
  const scientificGuardrail = spectralData?.scientific_guardrail || (
    selectedMineral === 'Coal'
      ? 'CRITICAL SCIENTIFIC PRINCIPLE: Optical sensors measure surface opencast faces only. Never infer underground coal seams from optical satellite imagery alone.'
      : selectedMineral === 'Iron Ore'
      ? 'SCIENTIFIC INTEGRITY GUARDRAIL: Surface ferric iron staining (B04/B02) is common across Indian peninsular basements. Anomaly is NOT proof of economic ore without core drilling.'
      : selectedMineral === 'Bauxite'
      ? 'SCIENTIFIC INTEGRITY GUARDRAIL: Al-OH molecular absorption detects clay and lateritic weathering. It does NOT prove commercial bauxite without chemical assay.'
      : 'SCIENTIFIC INTEGRITY GUARDRAIL: Surface spectral ratios indicate alteration halos and gossans. Subsurface drilling is required to verify economic grade.'
  );

  const bandReflectances = spectralData?.band_reflectances || null;
  const spectralIndices = spectralData?.mineral_spectral_indices || [];

  const bandsList = [
    { name: 'B02 (Blue)', wavelength: '490 nm', val: bandReflectances?.B02_blue, color: '#38bdf8' },
    { name: 'B03 (Green)', wavelength: '560 nm', val: bandReflectances?.B03_green, color: '#10b981' },
    { name: 'B04 (Red)', wavelength: '665 nm', val: bandReflectances?.B04_red, color: '#f87171' },
    { name: 'B08 (NIR)', wavelength: '842 nm', val: bandReflectances?.B08_nir, color: '#a855f7' },
    { name: 'B11 (SWIR-1)', wavelength: '1610 nm', val: bandReflectances?.B11_swir1, color: '#f59e0b' },
    { name: 'B12 (SWIR-2)', wavelength: '2190 nm', val: bandReflectances?.B12_swir2, color: '#ec4899' },
  ];

  return (
    <div
      className="satellite-card"
      style={{
        background: 'rgba(22, 27, 34, 0.95)',
        border: '1.5px solid ' + (pixelsProcessed ? 'rgba(16, 185, 129, 0.35)' : 'rgba(0, 240, 255, 0.25)'),
        borderRadius: '12px',
        padding: '1.1rem',
        marginTop: '1rem',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: pixelsProcessed
                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.25), rgba(5, 150, 105, 0.4))'
                : 'linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(2, 132, 199, 0.3))',
              border: '1px solid ' + (pixelsProcessed ? '#10b981' : '#00f0ff'),
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Satellite size={18} color={pixelsProcessed ? '#10b981' : '#00f0ff'} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-serif)', fontSize: '0.98rem', fontWeight: 700, color: '#f1f5f9' }}>
              Satellite Discovery & Spectral Raster Ingestion
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Copernicus Sentinel-2 Level-2A Multi-Spectral Surface Reflectance (BOA)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '999px',
              background: pixelsProcessed ? 'rgba(16, 185, 129, 0.18)' : 'rgba(245, 158, 11, 0.18)',
              color: pixelsProcessed ? '#10b981' : '#f59e0b',
              border: '1px solid ' + (pixelsProcessed ? '#10b981' : '#f59e0b'),
            }}
          >
            {pixelsProcessed ? 'REAL PIXELS PROCESSED' : 'CATALOGUE METADATA ONLY'}
          </span>
          {isExpanded ? <ChevronUp size={16} color="#94a3b8" /> : <ChevronDown size={16} color="#94a3b8" />}
        </div>
      </div>

      {isExpanded && (
        <div style={{ marginTop: '1rem' }}>
          {/* Scientific Integrity Rule Banner */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              borderLeft: '3px solid ' + (pixelsProcessed ? '#10b981' : '#f59e0b'),
              borderRadius: '4px',
              padding: '8px 12px',
              marginBottom: '1rem',
              fontSize: '0.72rem',
              color: '#cbd5e1',
              lineHeight: 1.45,
            }}
          >
            <div style={{ fontWeight: 700, color: pixelsProcessed ? '#10b981' : '#f59e0b', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <ShieldCheck size={14} />
              <span>Mineral-Specific Scientific Guardrail:</span>
            </div>
            {scientificGuardrail}
          </div>

          {/* Multi-Tile Boundary Indicator */}
          {tileInfo?.tile_boundary_crossed && (
            <div
              style={{
                background: 'rgba(56, 189, 248, 0.1)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                borderRadius: '6px',
                padding: '6px 10px',
                marginBottom: '1rem',
                fontSize: '0.7rem',
                color: '#38bdf8',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Grid size={14} />
              <span>
                <b>Multi-Tile Boundary:</b> Analysis radius ({selectedRadius} km) crosses Sentinel-2 tiles ({tileInfo.intersecting_tiles.join(', ')}). Composite windowing active.
              </span>
            </div>
          )}

          {/* Pixel Coverage Statistics Pill */}
          {pixelsProcessed && pixelCoverage && (
            <div
              style={{
                display: 'flex',
                gap: '8px',
                flexWrap: 'wrap',
                marginBottom: '1rem',
                fontSize: '0.72rem',
              }}
            >
              <div style={{ background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '6px', padding: '4px 8px', color: '#10b981' }}>
                Valid Pixels: <b>{pixelCoverage.valid_pixels?.toLocaleString()}</b>
              </div>
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', padding: '4px 8px', color: '#cbd5e1' }}>
                Resolution: <b>{pixelCoverage.pixel_resolution_m}m</b>
              </div>
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', padding: '4px 8px', color: '#cbd5e1' }}>
                Cloud Masked: <b>{pixelCoverage.cloud_mask_pct}%</b>
              </div>
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '6px', padding: '4px 8px', color: '#cbd5e1' }}>
                CRS: <b>{tileInfo?.utm_bounding_box?.crs || 'UTM Grid'}</b>
              </div>
            </div>
          )}

          {/* Scene Selector */}
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '6px' }}>
              Discovered Copernicus Satellite Scenes ({selectedRadius} km buffer):
            </label>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {scenes.length === 0 && !loading && (
                <div style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px dashed rgba(255, 255, 255, 0.15)',
                  borderRadius: '8px',
                  padding: '12px 14px',
                  fontSize: '0.76rem',
                  color: '#94a3b8',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: '100%'
                }}>
                  <AlertCircle size={16} color="#f59e0b" />
                  <span>No Sentinel-2 Level-2A imagery found or catalogue query returned empty for this coordinate buffer.</span>
                </div>
              )}
              {scenes.map((scene) => {
                const isSelected = scene.scene_id === selectedSceneId;
                return (
                  <button
                    key={scene.scene_id}
                    type="button"
                    onClick={() => {
                      setSelectedSceneId(scene.scene_id);
                      if (onSelectScene) onSelectScene(scene);
                    }}
                    style={{
                      background: isSelected ? 'rgba(0, 240, 255, 0.15)' : 'rgba(15, 23, 42, 0.7)',
                      border: '1.5px solid ' + (isSelected ? '#00f0ff' : 'rgba(255, 255, 255, 0.1)'),
                      borderRadius: '8px',
                      padding: '8px 12px',
                      color: isSelected ? '#fff' : '#cbd5e1',
                      fontSize: '0.75rem',
                      textAlign: 'left',
                      cursor: 'pointer',
                      flex: '1 1 200px',
                      boxShadow: isSelected ? '0 0 12px rgba(0, 240, 255, 0.25)' : 'none',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, color: isSelected ? '#00f0ff' : '#f1f5f9' }}>
                        {scene.satellite} ({scene.instrument})
                      </span>
                      <span style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
                        {scene.acquisition_date}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '3px' }}>
                      ID: <span style={{ fontFamily: 'var(--font-mono)' }}>{scene.scene_id}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '4px', fontSize: '0.68rem', color: '#cbd5e1' }}>
                      <span>Cloud: {scene.cloud_cover_pct}%</span>
                      <span>Res: {scene.resolution_m}m</span>
                      <span>Tile: {scene.tile_id || 'MSIL2A'}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Band Reflectance Grid */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.65)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '8px',
              padding: '10px 14px',
              marginBottom: '1rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#e2e8f0', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Surface Reflectance Across 6 Multispectral Bands
              </span>
              <span style={{ fontSize: '0.68rem', color: pixelsProcessed ? '#10b981' : '#f59e0b', fontFamily: 'var(--font-mono)' }}>
                {pixelsProcessed ? 'BOA SURFACE REFLECTANCE' : 'AWAITING S3 INGESTION'}
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              {bandsList.map((b) => (
                <div
                  key={b.name}
                  style={{
                    background: 'rgba(22, 27, 34, 0.85)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '6px',
                    padding: '6px 8px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#94a3b8' }}>
                    <span>{b.name}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: b.val ? b.color : '#64748b', fontWeight: 700 }}>
                      {typeof b.val === 'number' ? b.val.toFixed(3) : 'Pending'}
                    </span>
                  </div>
                  {/* Visual mini bar */}
                  <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', marginTop: '4px', overflow: 'hidden' }}>
                    <div
                      style={{
                        height: '100%',
                        width: b.val ? `${Math.min(100, b.val * 200)}%` : '0%',
                        background: b.color,
                        borderRadius: '2px',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Diagnostic Spectral Ratios & Alteration Indicators */}
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#e2e8f0', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
              Diagnostic Spectral Ratios & Mineral Absorption Indices
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {spectralIndices.length === 0 ? (
                <div style={{
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px dashed rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  padding: '10px 12px',
                  fontSize: '0.72rem',
                  color: '#94a3b8'
                }}>
                  {spectralData?.raster_processing_details || 'Band GeoTIFF package awaiting download/decompression to calculate pixel ratios.'}
                </div>
              ) : (
                spectralIndices.map((idx, i) => (
                  <div
                    key={i}
                    style={{
                      background: 'rgba(15, 23, 42, 0.75)',
                      border: '1px solid rgba(255, 255, 255, 0.07)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#f1f5f9' }}>
                          {idx.index_name}
                        </span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: '#38bdf8' }}>
                          [{idx.formula}]
                        </span>
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#94a3b8', marginTop: '2px' }}>
                        {idx.target_feature}
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', fontWeight: 800, color: idx.value !== null ? '#00f0ff' : '#64748b' }}>
                        {idx.value !== null ? (typeof idx.value === 'number' ? idx.value.toFixed(2) : idx.value) : 'PENDING'}
                      </div>
                      <span
                        style={{
                          fontSize: '0.62rem',
                          fontWeight: 700,
                          padding: '1px 6px',
                          borderRadius: '4px',
                          background:
                            idx.significance === 'HIGH' || idx.significance === 'COAL PIT CONTRAST' || idx.significance === 'HIGH ANOMALY'
                              ? 'rgba(16, 185, 129, 0.2)'
                              : idx.significance === 'PERMISSIVE' || idx.significance === 'EXCAVATION BENCH'
                              ? 'rgba(56, 189, 248, 0.2)'
                              : 'rgba(148, 163, 184, 0.2)',
                          color:
                            idx.significance === 'HIGH' || idx.significance === 'COAL PIT CONTRAST' || idx.significance === 'HIGH ANOMALY'
                              ? '#10b981'
                              : idx.significance === 'PERMISSIVE' || idx.significance === 'EXCAVATION BENCH'
                              ? '#38bdf8'
                              : '#94a3b8',
                        }}
                      >
                        {idx.significance}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
