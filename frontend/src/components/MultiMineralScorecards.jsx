import React, { useState } from 'react';
import {
  Sparkles,
  Layers,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  Download,
  Eye,
  Mountain,
  CheckCircle2,
  FileText,
  MapPin,
  TrendingUp,
  Activity
} from 'lucide-react';

const MINERAL_INFO = {
  'Coal': {
    symbol: 'C',
    category: 'Carbonaceous Energy Commodity',
    icon: '🪨',
    color: '#8b9bb4',
    bgTint: 'rgba(139, 155, 180, 0.1)',
    borderTint: 'rgba(139, 155, 180, 0.35)',
  },
  'Manganese': {
    symbol: 'Mn',
    category: 'Strategic Ferroalloy Mineral',
    icon: '⛏️',
    color: '#00f0ff',
    bgTint: 'rgba(0, 240, 255, 0.1)',
    borderTint: 'rgba(0, 240, 255, 0.35)',
  },
  'Iron Ore': {
    symbol: 'Fe',
    category: 'Ferrous Metal Commodity',
    icon: '⛰️',
    color: '#c85a32',
    bgTint: 'rgba(200, 90, 50, 0.1)',
    borderTint: 'rgba(200, 90, 50, 0.35)',
  },
  'Bauxite': {
    symbol: 'Al',
    category: 'Lateritic Aluminum Ore',
    icon: '🧱',
    color: '#d97706',
    bgTint: 'rgba(217, 119, 6, 0.1)',
    borderTint: 'rgba(217, 119, 6, 0.35)',
  }
};

export default function MultiMineralScorecards({
  multiResult,
  selectedMineral,
  onSelectMineral,
  radiusKm,
  selectedLocation
}) {
  const [expandedMineral, setExpandedMineral] = useState(null);

  if (!multiResult || !multiResult.minerals) return null;

  const { comparison_summary, minerals, location_name, latitude, longitude, area_sq_km, selected_minerals } = multiResult;
  const mineralKeys = selected_minerals || Object.keys(minerals || {});
  const mineralCount = mineralKeys.length;

  const toggleExpand = (mineralName) => {
    setExpandedMineral(expandedMineral === mineralName ? null : mineralName);
  };

  const handleExportMineral = (mineralName, mData) => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(mData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `Exploration_Dossier_${mineralName}_${latitude?.toFixed(2)}_${longitude?.toFixed(2)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="multi-scorecards-container" id="unified-multi-scorecards">
      {/* 1. Header Banner */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9))',
          border: '1.5px solid rgba(0, 240, 255, 0.3)',
          borderRadius: '12px',
          padding: '16px 20px',
          marginBottom: '16px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <Sparkles size={18} color="#00f0ff" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#f1f5f9', margin: 0 }}>
                {mineralCount === 4 ? 'Unified 4-Mineral Exploration Comparison' : `Selected ${mineralCount}-Mineral Exploration Comparison`}
              </h2>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#94a3b8', margin: 0 }}>
              Simultaneous independent evaluation of {mineralKeys.join(', ')} across <b>{radiusKm} km</b> radius ({area_sq_km || (Math.PI * radiusKm * radiusKm).toFixed(1)} km²).
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color: '#00f0ff',
                background: 'rgba(0, 240, 255, 0.12)',
                border: '1px solid rgba(0, 240, 255, 0.3)',
                borderRadius: '6px',
                padding: '4px 10px',
              }}
            >
              {mineralCount} {mineralCount === 1 ? 'Commodity' : 'Commodities'} Evaluated
            </span>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 600,
                color: '#cbd5e1',
                background: 'rgba(255, 255, 255, 0.06)',
                borderRadius: '6px',
                padding: '4px 8px',
              }}
            >
              Active 3D Focus: <b style={{ color: MINERAL_INFO[selectedMineral]?.color || '#00f0ff' }}>{selectedMineral}</b>
            </span>
          </div>
        </div>
      </div>

      {/* 2. Unified Comparison Summary Table (Section 5 Requirement) */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.92)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '20px',
          overflowX: 'auto',
          boxShadow: '0 6px 24px rgba(0,0,0,0.4)',
        }}
        id="multi-mineral-comparison-table-wrapper"
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={16} color="#c6a052" />
            <h3 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
              Overall Multi-Mineral Comparison Table
            </h3>
          </div>
          <div style={{ fontSize: '0.68rem', color: '#94a3b8', fontStyle: 'italic' }}>
            *Scores of different types (AI vs Evidence Index) are strictly non-comparable.
          </div>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.76rem', color: '#e2e8f0' }} id="comparison-summary-table">
          <thead>
            <tr style={{ background: 'rgba(255, 255, 255, 0.05)', borderBottom: '1px solid rgba(255, 255, 255, 0.15)', textAlign: 'left' }}>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8' }}>Mineral</th>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8' }}>AI Prediction Status</th>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8' }}>AI Score</th>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8' }}>Evidence Index</th>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8' }}>Evidence Quality</th>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8' }}>Main Explanation</th>
              <th style={{ padding: '8px 10px', fontWeight: 700, color: '#94a3b8', textAlign: 'center' }}>3D Focus</th>
            </tr>
          </thead>
          <tbody>
            {(comparison_summary || []).map((row) => {
              const info = MINERAL_INFO[row.mineral] || {};
              const isFocused = selectedMineral === row.mineral;
              const hasScore = row.ai_score !== null && row.ai_score !== undefined;

              return (
                <tr
                  key={row.mineral}
                  style={{
                    borderBottom: '1px solid rgba(255, 255, 255, 0.07)',
                    background: isFocused ? 'rgba(0, 240, 255, 0.08)' : 'transparent',
                    cursor: 'pointer',
                    transition: 'background 0.15s ease',
                  }}
                  onClick={() => onSelectMineral(row.mineral)}
                  className={`comparison-row ${isFocused ? 'focused-row' : ''}`}
                >
                  <td style={{ padding: '10px 10px', fontWeight: 700, whiteSpace: 'nowrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: '1.1rem' }}>{info.icon}</span>
                      <div>
                        <div style={{ color: info.color || '#fff' }}>{row.mineral}</div>
                        <div style={{ fontSize: '0.66rem', color: '#94a3b8' }}>{info.symbol} &bull; {info.category}</div>
                      </div>
                    </div>
                  </td>

                  <td style={{ padding: '10px 10px' }}>
                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: '4px',
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        background: row.ai_prediction_status?.includes('AVAILABLE') ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                        color: row.ai_prediction_status?.includes('AVAILABLE') ? '#10b981' : '#f59e0b',
                        border: '1px solid ' + (row.ai_prediction_status?.includes('AVAILABLE') ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'),
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {row.ai_prediction_status}
                    </span>
                  </td>

                  <td style={{ padding: '10px 10px', fontWeight: hasScore ? 800 : 500 }}>
                    {hasScore ? (
                      <span style={{ color: '#00f0ff', fontSize: '0.88rem' }}>{row.ai_score}%</span>
                    ) : (
                      <span style={{ color: '#94a3b8', fontSize: '0.72rem', fontStyle: 'italic' }}>
                        {row.ai_score_label || 'Not available'}
                      </span>
                    )}
                  </td>

                  <td style={{ padding: '10px 10px', fontWeight: 700 }}>
                    {row.evidence_index !== null && row.evidence_index !== undefined ? (
                      <span style={{ color: row.evidence_index >= 60 ? '#10b981' : row.evidence_index >= 30 ? '#38bdf8' : '#f59e0b' }}>
                        {row.evidence_index_label}
                      </span>
                    ) : (
                      <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.72rem' }}>Not available</span>
                    )}
                  </td>

                  <td style={{ padding: '10px 10px' }}>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        background: row.evidence_quality === 'high' ? 'rgba(16, 185, 129, 0.15)' : row.evidence_quality === 'medium' ? 'rgba(56, 189, 248, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                        color: row.evidence_quality === 'high' ? '#10b981' : row.evidence_quality === 'medium' ? '#38bdf8' : '#94a3b8',
                      }}
                    >
                      {row.evidence_quality}
                    </span>
                  </td>

                  <td style={{ padding: '10px 10px', fontSize: '0.72rem', color: '#cbd5e1', maxWidth: '320px', lineHeight: 1.4 }}>
                    {row.main_explanation}
                  </td>

                  <td style={{ padding: '10px 10px', textAlign: 'center', whiteSpace: 'nowrap' }}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectMineral(row.mineral);
                      }}
                      style={{
                        padding: '4px 10px',
                        borderRadius: '6px',
                        border: isFocused ? '1.5px solid #00f0ff' : '1px solid rgba(255,255,255,0.18)',
                        background: isFocused ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255,255,255,0.06)',
                        color: isFocused ? '#00f0ff' : '#e2e8f0',
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4
                      }}
                      title={`Focus 3D View and Details on ${row.mineral}`}
                    >
                      <Eye size={12} />
                      <span>{isFocused ? 'Active' : 'Focus'}</span>
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 3. Four Separate Mineral Scorecards Grid (Sections 3 & 4 Requirements) */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <ShieldCheck size={18} color="#00f0ff" />
          <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            Individual Mineral Scorecards & Evidence Dossiers
          </h3>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '16px',
          }}
          className="four-scorecards-grid"
        >
          {/* Four Commodities Scorecard Grid: ['Coal', 'Manganese', 'Iron Ore', 'Bauxite'].map */}
          {(multiResult.analysis_mode === 'custom' ? mineralKeys : ['Coal', 'Manganese', 'Iron Ore', 'Bauxite']).map((mName) => {
            const mData = minerals[mName] || {};
            const info = MINERAL_INFO[mName] || {};
            const evalSum = mData.evaluation_summary || {};
            const isFocused = selectedMineral === mName;
            const isExpanded = expandedMineral === mName;

            const hasValidScore = evalSum.prospectivity_score_available && typeof evalSum.prospectivity_score === 'number';
            const evidenceIdx = evalSum.evidence_index;
            const evidenceQuality = evalSum.evidence_quality || 'none';
            const status = mData.status || 'UNKNOWN';

            return (
              <div
                key={mName}
                style={{
                  background: 'rgba(15, 23, 42, 0.94)',
                  border: isFocused ? `2px solid ${info.color}` : '1px solid rgba(255, 255, 255, 0.12)',
                  borderRadius: '12px',
                  padding: '16px',
                  boxShadow: isFocused ? `0 0 24px ${info.bgTint}, 0 8px 30px rgba(0,0,0,0.6)` : '0 6px 20px rgba(0,0,0,0.4)',
                  transition: 'all 0.2s ease',
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
                className={`mineral-scorecard-box ${isFocused ? 'selected-scorecard' : ''}`}
                id={`scorecard-${mName.toLowerCase().replace(' ', '-')}`}
              >
                <div>
                  {/* Card Header: Icon, Name, Category, Status Badge */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div
                        style={{
                          width: 38,
                          height: 38,
                          borderRadius: '8px',
                          background: info.bgTint,
                          border: `1.5px solid ${info.borderTint}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '1.25rem',
                        }}
                      >
                        {info.icon}
                      </div>
                      <div>
                        <div style={{ fontSize: '1.05rem', fontWeight: 800, color: info.color }}>
                          {mName} <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 500 }}>({info.symbol})</span>
                        </div>
                        <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
                          {info.category}
                        </div>
                      </div>
                    </div>

                    <span
                      style={{
                        padding: '3px 8px',
                        borderRadius: '6px',
                        fontSize: '0.66rem',
                        fontWeight: 700,
                        background: status === 'SUCCESS' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.18)',
                        color: status === 'SUCCESS' ? '#10b981' : '#38bdf8',
                        border: '1px solid ' + (status === 'SUCCESS' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(56, 189, 248, 0.35)'),
                      }}
                    >
                      {status === 'EVIDENCE_ONLY_NO_PREDICTION' ? 'EVIDENCE ONLY' : status}
                    </span>
                  </div>

                  {/* Section A: AI Prediction Score */}
                  <div
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      marginBottom: 10,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: '0.68rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        AI Prediction Model
                      </span>
                      <span style={{ fontSize: '0.66rem', color: hasValidScore ? '#10b981' : '#f59e0b', fontWeight: 700 }}>
                        {mData.prediction_availability || 'UNAVAILABLE'}
                      </span>
                    </div>

                    {hasValidScore ? (
                      <div>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                          <span style={{ fontSize: '1.6rem', fontWeight: 900, color: '#00f0ff' }}>
                            {evalSum.prospectivity_score}%
                          </span>
                          <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                            Relative Screening Score
                          </span>
                        </div>
                        <div style={{ fontSize: '0.66rem', color: '#f59e0b', fontStyle: 'italic', marginTop: 2 }}>
                          *Uncalibrated Random Forest surface screening index (Tile T44QMK)
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginTop: 4 }}>
                        <ShieldAlert size={16} color="#f59e0b" style={{ flexShrink: 0, marginTop: 2 }} />
                        <div style={{ fontSize: '0.72rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                          <b>Score Withheld:</b>{' '}
                          {mName === 'Coal'
                            ? 'Predicting underground seams from surface optical satellite reflectance is scientifically invalid without core drilling.'
                            : mName === 'Iron Ore'
                            ? 'ML score withheld. Spatial cross-validation dropped to 47.7% due to regolith confounding.'
                            : mName === 'Bauxite'
                            ? 'Commercial gibbsitic grade requires chemical assays; AI model withheld.'
                            : 'Target coordinates lie outside the validated Sentinel-2 Tile T44QMK footprint.'}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Section B: Evidence Favorability Index & Quality */}
                  <div
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      marginBottom: 10,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: '0.68rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        Evidence Favorability Index
                      </span>
                      <span
                        style={{
                          fontSize: '0.66rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          background: evidenceQuality === 'high' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                          color: evidenceQuality === 'high' ? '#10b981' : '#38bdf8',
                        }}
                      >
                        Quality: {evidenceQuality}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                      <span style={{ fontSize: '1.35rem', fontWeight: 800, color: info.color }}>
                        {evidenceIdx !== null && evidenceIdx !== undefined ? `${evidenceIdx}%` : 'Not available'}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                        (0–100 Multi-Criteria Evidence Scale)
                      </span>
                    </div>

                    {/* Progress Bar */}
                    {evidenceIdx !== null && evidenceIdx !== undefined && (
                      <div style={{ width: '100%', height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, marginTop: 6, overflow: 'hidden' }}>
                        <div
                          style={{
                            width: `${Math.min(100, Math.max(0, evidenceIdx))}%`,
                            height: '100%',
                            background: `linear-gradient(90deg, ${info.color}, #10b981)`,
                            borderRadius: 3,
                          }}
                        />
                      </div>
                    )}
                    <div style={{ fontSize: '0.64rem', color: '#94a3b8', marginTop: 4 }}>
                      Formula: {evalSum.evidence_formula || 'GSI Host Lithology (40%) + Satellite Spectral (30%) + Deposit Proximity (30%)'}
                    </div>
                  </div>

                  {/* Section C: Geographic Model Eligibility */}
                  <div style={{ marginBottom: 10, fontSize: '0.72rem' }}>
                    <div style={{ color: '#94a3b8', fontSize: '0.66rem', textTransform: 'uppercase', fontWeight: 600, marginBottom: 2 }}>
                      Model Domain & Geographic Eligibility
                    </div>
                    <div style={{ color: '#e2e8f0', background: 'rgba(255,255,255,0.02)', padding: '5px 8px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
                      {mData.geographic_eligibility?.overall_eligibility || mData.model_coverage || 'NATIONWIDE_EVIDENCE_FRAMEWORK'}
                    </div>
                  </div>

                  {/* Section D: Supporting Evidence Highlights */}
                  <div style={{ marginBottom: 10 }}>
                    <div style={{ color: '#94a3b8', fontSize: '0.66rem', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                      Main Supporting Evidence
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 14, fontSize: '0.72rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                      {(evalSum.main_supporting_evidence || []).slice(0, 3).map((item, idx) => (
                        <li key={idx} style={{ marginBottom: 2 }}>{item}</li>
                      ))}
                      {(!evalSum.main_supporting_evidence || evalSum.main_supporting_evidence.length === 0) && (
                        <li style={{ color: '#94a3b8', fontStyle: 'italic' }}>No certified deposits within exploration radius.</li>
                      )}
                    </ul>
                  </div>

                  {/* Section E: Missing Data & Limitations */}
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ color: '#94a3b8', fontSize: '0.66rem', textTransform: 'uppercase', fontWeight: 600, marginBottom: 4 }}>
                      Missing Data & Boundaries
                    </div>
                    <div style={{ fontSize: '0.7rem', color: '#fca5a5', background: 'rgba(239, 68, 68, 0.08)', padding: '6px 8px', borderRadius: '6px', border: '1px solid rgba(239, 68, 68, 0.2)', lineHeight: 1.35 }}>
                      {(evalSum.contradicting_evidence_and_uncertainties || mData.limitations_and_warnings || [])[0] || 'Requires core drilling to verify subsurface continuity.'}
                    </div>
                  </div>

                  {/* Expandable Deep Dossier Accordion */}
                  {isExpanded && (
                    <div
                      style={{
                        background: 'rgba(10, 15, 26, 0.98)',
                        border: '1px solid rgba(0, 240, 255, 0.2)',
                        borderRadius: '8px',
                        padding: '12px',
                        marginBottom: 12,
                        fontSize: '0.72rem',
                      }}
                      className="expanded-dossier-panel"
                    >
                      <div style={{ fontWeight: 700, color: '#00f0ff', marginBottom: 6 }}>
                        Certified Evidence Layers & Vectors ({mName})
                      </div>

                      <div style={{ marginBottom: 6 }}>
                        <b>Geological Context:</b> {mData.geological_context || 'Regional lithology evaluated'}
                      </div>

                      <div style={{ marginBottom: 6 }}>
                        <b>Documented Occurrences:</b> {mData.documented_occurrences?.length || 0} occurrences in radius
                        {mData.nearest_occurrence_km !== null && mData.nearest_occurrence_km !== undefined && (
                          <span> (Nearest: <b>{mData.nearest_occurrence_km} km</b>)</span>
                        )}
                      </div>

                      <div style={{ marginBottom: 6 }}>
                        <b>Spectral Band Status:</b> {mData.spectral_processing?.pixel_processing_status || mData.spectral_processing?.status || 'Evaluated'}
                      </div>

                      <div>
                        <b>Scientific Guidance:</b> {evalSum.what_this_result_means || 'Exploration screening vector only.'}
                      </div>
                    </div>
                  )}
                </div>

                {/* Card Actions Footer */}
                <div style={{ display: 'flex', gap: 8, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 8 }}>
                  <button
                    type="button"
                    onClick={() => onSelectMineral(mName)}
                    style={{
                      flex: 1,
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: isFocused ? `1.5px solid ${info.color}` : '1px solid rgba(255,255,255,0.18)',
                      background: isFocused ? info.bgTint : 'rgba(255,255,255,0.05)',
                      color: isFocused ? info.color : '#e2e8f0',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 5,
                    }}
                    id={`btn-focus-${mName.toLowerCase().replace(' ', '-')}`}
                  >
                    <Eye size={13} />
                    <span>{isFocused ? 'Active on 3D Map' : 'Focus on 3D Map'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => toggleExpand(mName)}
                    style={{
                      padding: '7px 10px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.18)',
                      background: 'rgba(255,255,255,0.05)',
                      color: '#cbd5e1',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                    }}
                    title="Toggle Deep Geological Dossier Details"
                  >
                    <span>{isExpanded ? 'Less' : 'Dossier'}</span>
                    {isExpanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  </button>

                  <button
                    type="button"
                    onClick={() => handleExportMineral(mName, mData)}
                    style={{
                      padding: '7px 8px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.18)',
                      background: 'rgba(255,255,255,0.05)',
                      color: '#94a3b8',
                      cursor: 'pointer',
                    }}
                    title={`Export ${mName} Dossier JSON`}
                  >
                    <Download size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Scientific Interpretation Guidelines: Explicit Meaning of 0–100 Scales & Non-Comparability Warning */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
          borderRadius: '10px',
          padding: '14px 18px',
          marginTop: '16px',
          fontSize: '0.74rem',
          lineHeight: 1.5,
          color: '#cbd5e1'
        }}
        id="scale-interpretation-guidelines"
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#38bdf8', fontWeight: 700, marginBottom: 6 }}>
          <Info size={16} />
          <span>Scientific Interpretation Guidelines: 0–100 Normalized Scale Meaning</span>
        </div>
        <p style={{ margin: '0 0 8px 0' }}>
          <b>Do not directly compare numerical values between columns:</b>
        </p>
        <ul style={{ margin: 0, paddingLeft: 16, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <li>
            <b>AI Prediction Score (0–100): Valid ONLY for Manganese</b> within the verified Balaghat Sentinel-2 training tile (T44QMK). Represents Random Forest algorithmic classification of spectral absorption patterns. For Coal, Iron Ore, and Bauxite, AI Prediction Scores are withheld because appropriate subsurface seam training, chemical assays, and spatial cross-validation have not yet been established.
          </li>
          <li>
            <b>Evidence Favorability Index (0–100): Calculated from multi-criteria</b> spatial geological indicators, documented GSI occurrence proximity, lithological host formation presence, and multispectral band ratios. It reflects observed regional favorability, not a machine learning model output.
          </li>
          <li>
            <b>Evidence Quality:</b> Assessed independently from favorability (High / Medium / Low / None), based on the completeness and resolution of available satellite and geological datasets.
          </li>
          <li>
            <b>Direct numerical comparison between an AI Prediction and an Evidence Favorability Index is scientifically invalid</b> because they measure fundamentally different geological and algorithmic quantities.
          </li>
        </ul>
      </div>
    </div>
  );
}
