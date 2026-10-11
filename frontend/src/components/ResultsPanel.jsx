import React, { useState } from 'react';
import {
  FileText,
  AlertTriangle,
  ShieldCheck,
  Database,
  Info,
  CheckCircle2,
  Clock,
  HelpCircle,
  Layers,
  ChevronDown,
  ChevronUp,
  MapPin,
  Sparkles,
  Download,
  CheckSquare,
  Activity,
  ArrowRight
} from 'lucide-react';

export default function ResultsPanel({ result, isAnalyzing, error }) {
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'geology' | 'matrix' | 'decision' | 'sources'
  const [expandedItem, setExpandedItem] = useState(null);

  if (isAnalyzing) {
    return (
      <div className="results-card" style={{ textAlign: 'center', padding: '2.5rem 1.5rem' }}>
        <div style={{ display: 'inline-block', marginBottom: '1rem' }}>
          <div className="status-dot" style={{ width: 14, height: 14, margin: '0 auto', animation: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite' }} />
        </div>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: '1.05rem', color: '#00f0ff' }}>
          Executing Geographical Prospectivity Pipeline...
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          Extracting multi-spectral raster features, geological host formations, and spatial evidence vectors.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="results-card" style={{ borderColor: 'var(--accent-danger)' }}>
        <div className="results-header">
          <div className="results-title" style={{ color: '#ef4444' }}>Analysis Request Error</div>
          <span className="results-status-badge badge-coverage">ERROR</span>
        </div>
        <p style={{ fontSize: '0.84rem', color: '#fca5a5' }}>{error}</p>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="results-card" style={{ textAlign: 'center', padding: '1.75rem 1rem' }}>
        <div style={{ color: '#00f0ff', marginBottom: '0.5rem' }}>
          <Info size={26} style={{ margin: '0 auto' }} />
        </div>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: '0.98rem', color: '#e5e0d4' }}>
          Awaiting Exploration Target
        </div>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '0.4rem', maxWidth: '300px', margin: '0.4rem auto 0' }}>
          Pick a map location, select one mineral class and radius, then click <b>Analyze Selected Area</b> to generate the explainable evidence dossier.
        </p>
      </div>
    );
  }

  const {
    location_name,
    latitude,
    longitude,
    mineral,
    radius_km,
    area_sq_km,
    status,
    overall_status,
    satellite_imagery_availability,
    geological_evidence_availability,
    model_coverage,
    prediction_availability,
    message,
    prediction,
    confidence_score,
    confidence_note,
    data_sources,
    geological_context,
    geological_province,
    documented_occurrences,
    nearest_occurrence_km,
    geological_source_attribution,
    scientific_interpretation_guidelines,
    evidence_items,
    evidence_conclusion,
    relevant_map_layers,
    evidence_explanation,
    limitations_and_warnings,
    decision_support
  } = result;

  const isSuccess = status === 'SUCCESS';
  const isEvidenceOnly = status === 'EVIDENCE_ONLY_NO_PREDICTION';
  const isInsufficient = status === 'INSUFFICIENT_DATA';
  const isOutOfCoverage = status === 'OUT_OF_COVERAGE';
  const isOutsideIndia = status === 'OUTSIDE_INDIA_TERRITORY' || result.is_within_india === false;

  // Support counts
  const supportsCount = evidence_items?.filter(e => e.hypothesis_support === 'SUPPORTS').length || 0;
  const neutralCount = evidence_items?.filter(e => e.hypothesis_support === 'NEUTRAL / UNCONFIRMED').length || 0;
  const awaitingCount = evidence_items?.filter(e => e.hypothesis_support === 'AWAITING OBSERVATION').length || 0;

  // Export Dossier JSON
  const handleExportDossier = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(result, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `Exploration_Dossier_${mineral}_${latitude.toFixed(2)}_${longitude.toFixed(2)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="results-card" id="results-dashboard-panel">
      {/* Header Summary */}
      <div className="results-header">
        <div>
          <div className="results-title">Geographical Analysis Dossier</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            Target: <b>{mineral}</b> &bull; Radius: {radius_km} km ({area_sq_km} km²)
          </div>
        </div>
        <span className={`results-status-badge ${
          isSuccess ? 'badge-success' : isEvidenceOnly ? 'badge-coverage' : isInsufficient ? 'badge-insufficient' : 'badge-coverage'
        }`} style={isEvidenceOnly ? { background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', borderColor: '#38bdf8' } : {}}>
          {isEvidenceOnly ? 'EVIDENCE ONLY (NO SCORE)' : status}
        </span>
      </div>

      {/* 5-Field Coverage Matrix (Section 4) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
        gap: '6px',
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '8px 10px',
        margin: '0.4rem 0'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Catalogue Discovery</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: satellite_imagery_availability?.includes('AVAILABLE') ? '#10b981' : '#f59e0b' }}>
            {satellite_imagery_availability || 'DISCOVERED'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Raster Pixels</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: result.raster_pixels_processed ? '#10b981' : '#f59e0b' }}>
            {result.raster_pixels_processed ? 'PROCESSED (BOA)' : 'PENDING S3'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Geology Records</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: geological_evidence_availability === 'RECORDS_IDENTIFIED' ? '#10b981' : geological_evidence_availability === 'REGIONAL_FRAMEWORK_ONLY' ? '#38bdf8' : '#94a3b8' }}>
            {geological_evidence_availability || 'IDENTIFIED'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Model Coverage</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: model_coverage === 'VALIDATED_ACTIVE' ? '#10b981' : '#f43f5e' }}>
            {model_coverage || 'UNVALIDATED'}
          </span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Prediction Status</span>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: prediction_availability === 'AVAILABLE' ? '#10b981' : '#f59e0b' }}>
            {prediction_availability || 'WITHHELD'}
          </span>
        </div>
      </div>

      {/* Meta Grid */}
      <div className="results-meta-grid">
        <div className="meta-field">
          <span className="meta-key">Exploration Target</span>
          <span className="meta-val" title={location_name}>
            {location_name?.split(',')[0]}
          </span>
        </div>
        <div className="meta-field">
          <span className="meta-key">Coordinates</span>
          <span className="meta-val">
            {latitude?.toFixed(4)}°N, {longitude?.toFixed(4)}°E
          </span>
        </div>
      </div>

      {/* Primary Verdict Card */}
      {isSuccess && prediction && (
        <div className="prediction-box">
          <div className="prediction-score-row">
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Spatial Prospectivity Index
              </div>
              <div className="score-number">{prediction.prospectivity_index}%</div>
            </div>
            <div className="score-classification">{prediction.classification} PRIORITY</div>
          </div>

          <div style={{ fontSize: '0.78rem', color: '#d8dee9' }}>
            {prediction.interpretation}
          </div>

          {prediction.candidate_zone && (
            <div style={{
              background: 'rgba(0,0,0,0.35)',
              padding: '0.4rem 0.6rem',
              borderRadius: '4px',
              fontSize: '0.74rem',
              fontFamily: 'var(--font-mono)',
              color: '#00f0ff',
              border: '1px solid rgba(0, 240, 255, 0.2)'
            }}>
              Cluster Match: {prediction.candidate_zone}
            </div>
          )}

          <div style={{
            fontSize: '0.72rem',
            color: 'var(--text-dim)',
            background: 'rgba(255,255,255,0.03)',
            padding: '0.4rem 0.6rem',
            borderRadius: '4px',
            borderLeft: '2px solid #00f0ff'
          }}>
            <b>Calibration Status:</b> {confidence_note}
          </div>
        </div>
      )}

      {isEvidenceOnly && (
        <div style={{
          background: 'rgba(56, 189, 248, 0.08)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.85rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#38bdf8', fontWeight: 700, fontSize: '0.85rem' }}>
            <ShieldCheck size={16} />
            <span>Genuine Evidence Discovered &bull; Prediction Score Withheld</span>
          </div>
          <p style={{ fontSize: '0.76rem', color: '#cbd5e1', lineHeight: 1.45 }}>
            {message}
          </p>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
            Scientific integrity policy: Machine-learning prospectivity scores are restricted to validated commodity and regional training bounds.
          </div>
        </div>
      )}

      {isOutsideIndia && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid rgba(239, 68, 68, 0.45)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.85rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#ef4444', fontWeight: 700, fontSize: '0.85rem' }}>
            <AlertTriangle size={15} />
            <span>Target Outside Sovereign Indian Territorial Boundary</span>
          </div>
          <p style={{ fontSize: '0.76rem', color: '#fca5a5', lineHeight: 1.45 }}>
            {message || "The selected coordinates lie outside India's geographic boundary envelope (Lat 6.5°N - 37.5°N, Lon 68.0°E - 97.5°E). This system evaluates locations strictly within Indian sovereign jurisdiction."}
          </p>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
            Statutory authority: Survey of India (SOI) & Geological Survey of India (GSI) National Territorial Baseline.
          </div>
        </div>
      )}

      {isInsufficient && (
        <div style={{
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.85rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#f59e0b', fontWeight: 700, fontSize: '0.85rem' }}>
            <AlertTriangle size={15} />
            <span>Insufficient Data for Reliable Geographical Assessment</span>
          </div>
          <p style={{ fontSize: '0.76rem', color: '#d5c4a1', lineHeight: 1.45 }}>
            {message || result.reason}
          </p>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
            Scientific integrity contract: Simulated, synthetic, or unvalidated prospectivity scores are strictly forbidden.
          </div>
        </div>
      )}

      {isOutOfCoverage && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.85rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.4rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#ef4444', fontWeight: 700, fontSize: '0.85rem' }}>
            <AlertTriangle size={15} />
            <span>Outside Active Satellite Footprint</span>
          </div>
          <p style={{ fontSize: '0.76rem', color: '#fca5a5', lineHeight: 1.45 }}>
            {message}
          </p>
        </div>
      )}

      {/* Tab Navigation for Deep Explainable Dossier */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '4px',
        background: 'rgba(0,0,0,0.3)',
        padding: '3px',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-subtle)',
        marginTop: '0.5rem'
      }}>
        <button
          type="button"
          onClick={() => setActiveTab('summary')}
          style={{
            background: activeTab === 'summary' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'summary' ? '1px solid #00f0ff' : 'none',
            color: activeTab === 'summary' ? '#00f0ff' : 'var(--text-dim)',
            padding: '6px 2px',
            fontSize: '0.68rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Verdict
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('geology')}
          style={{
            background: activeTab === 'geology' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'geology' ? '1px solid #00f0ff' : 'none',
            color: activeTab === 'geology' ? '#00f0ff' : 'var(--text-dim)',
            padding: '6px 2px',
            fontSize: '0.68rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Geology
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('matrix')}
          style={{
            background: activeTab === 'matrix' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'matrix' ? '1px solid #00f0ff' : 'none',
            color: activeTab === 'matrix' ? '#00f0ff' : 'var(--text-dim)',
            padding: '6px 2px',
            fontSize: '0.68rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Evidence
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('decision')}
          style={{
            background: activeTab === 'decision' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'decision' ? '1px solid #10b981' : 'none',
            color: activeTab === 'decision' ? '#10b981' : 'var(--text-dim)',
            padding: '6px 2px',
            fontSize: '0.68rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Decisions
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('sources')}
          style={{
            background: activeTab === 'sources' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'sources' ? '1px solid #00f0ff' : 'none',
            color: activeTab === 'sources' ? '#00f0ff' : 'var(--text-dim)',
            padding: '6px 2px',
            fontSize: '0.68rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Sources
        </button>
      </div>

      {/* Tab 1: Verdict & Evidence Summary */}
      {activeTab === 'summary' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {/* Support breakdown pills */}
          <div style={{ display: 'flex', gap: '6px' }}>
            <span style={{
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 600
            }}>
              Supports: {supportsCount}
            </span>
            <span style={{
              background: 'rgba(245, 158, 11, 0.15)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              color: '#fcd34d',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 600
            }}>
              Unconfirmed: {neutralCount}
            </span>
            <span style={{
              background: 'rgba(59, 130, 246, 0.15)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#93c5fd',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '0.72rem',
              fontWeight: 600
            }}>
              Awaiting Data: {awaitingCount}
            </span>
          </div>

          {/* Conclusion text */}
          <div style={{
            background: 'var(--bg-surface)',
            borderLeft: '3px solid #00f0ff',
            padding: '0.75rem',
            borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
            fontSize: '0.78rem',
            color: '#dfd8c8',
            lineHeight: 1.5
          }}>
            <div style={{ fontWeight: 700, color: '#00f0ff', marginBottom: 4, textTransform: 'uppercase', fontSize: '0.7rem' }}>
              Analytical Synthesis & Scientific Verdict
            </div>
            {evidence_conclusion || result.message}
          </div>
        </div>
      )}

      {/* Tab 2: Geological Context & Lithology */}
      {activeTab === 'geology' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            padding: '0.85rem',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.78rem',
            color: '#e5e0d4',
            lineHeight: 1.5
          }}>
            <div style={{ fontWeight: 700, color: '#00f0ff', marginBottom: 4, textTransform: 'uppercase', fontSize: '0.7rem' }}>
              Host Formations & Lithological Setting
            </div>
            <p>{geological_context}</p>
            {geological_source_attribution && (
              <div style={{ marginTop: '0.5rem', paddingTop: '0.4rem', borderTop: '1px solid rgba(255,255,255,0.06)', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                Source: <b>{geological_source_attribution.source}</b> ({geological_source_attribution.publication_year}, Scale {geological_source_attribution.map_scale})
              </div>
            )}
          </div>

          {/* Scientific Principle: Lack of Nearby Mine Record */}
          {result.absence_of_mine_records_assessment && (
            <div style={{
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.25)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.75rem',
              fontSize: '0.74rem',
              color: '#bae6fd',
              lineHeight: 1.45
            }}>
              <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: 3, textTransform: 'uppercase', fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Info size={13} />
                <span>Greenfield Potential & Scientific Evidence Principle</span>
              </div>
              <p>{result.absence_of_mine_records_assessment}</p>
            </div>
          )}

          {/* Documented GSI / IBM Mineral Occurrences */}
          {documented_occurrences && documented_occurrences.length > 0 && (
            <div className="evidence-block">
              <div className="evidence-heading">Verified Mineral Occurrences in Exploration Corridor</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '6px' }}>
                {documented_occurrences.map((occ, i) => (
                  <div key={i} style={{
                    background: 'rgba(0,0,0,0.3)',
                    padding: '8px 10px',
                    borderRadius: '4px',
                    border: '1px solid rgba(255,255,255,0.08)',
                    fontSize: '0.75rem'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, color: '#f1f5f9' }}>
                      <span>{occ.name}</span>
                      <span style={{ color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>{occ.distance_km} km away</span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: 2 }}>
                      Deposit Type: {occ.type} &bull; Status: <span style={{ color: '#10b981' }}>{occ.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {evidence_explanation?.top_spectral_features && (
            <div className="evidence-block">
              <div className="evidence-heading">Random Forest Feature Weightings (Tile T44QMK)</div>
              <div className="features-list">
                {evidence_explanation.top_spectral_features.slice(0, 5).map((f, i) => (
                  <div key={i} className="feature-bar-row">
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{f.feature}</span>
                    <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>{f.band_relation}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', color: '#00f0ff', fontWeight: 700 }}>{f.importance_pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Detailed Evidence Matrix */}
      {activeTab === 'matrix' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {evidence_items && evidence_items.map((item, idx) => {
            const isItemExpanded = expandedItem === idx;
            const isSupport = item.hypothesis_support === 'SUPPORTS';
            const isAwaiting = item.hypothesis_support === 'AWAITING OBSERVATION';

            return (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.65rem 0.75rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onClick={() => setExpandedItem(isItemExpanded ? null : idx)}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 6 }}>
                  <div>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f3ede2' }}>
                      {item.feature}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: 2 }}>
                      {item.category}
                    </div>
                  </div>
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: '3px',
                    textTransform: 'uppercase',
                    whiteSpace: 'nowrap',
                    background: isSupport ? 'rgba(16, 185, 129, 0.2)' : isAwaiting ? 'rgba(59, 130, 246, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                    color: isSupport ? '#34d399' : isAwaiting ? '#93c5fd' : '#fcd34d',
                  }}>
                    {item.hypothesis_support}
                  </span>
                </div>

                {isItemExpanded && (
                  <div style={{
                    marginTop: '0.65rem',
                    paddingTop: '0.5rem',
                    borderTop: '1px solid var(--border-subtle)',
                    fontSize: '0.73rem',
                    color: '#c9cfd8',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem'
                  }}>
                    <div><b>Relevance:</b> {item.relevance}</div>
                    <div><b>Data Source:</b> {item.source}</div>
                    <div><b>Spatial Coverage:</b> {item.spatial_coverage}</div>
                    <div style={{ color: '#fcd34d' }}><b>Limitations:</b> {item.limitations}</div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Tab 4: Exploration Decision Support (Priority 8) */}
      {activeTab === 'decision' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {decision_support ? (
            <>
              {/* Target Tier & Readiness */}
              <div
                style={{
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1.5px solid #10b981',
                  borderRadius: '8px',
                  padding: '10px 14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Exploration Ranking
                  </span>
                  <span
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      background: 'rgba(16, 185, 129, 0.2)',
                      color: '#10b981',
                    }}
                  >
                    {decision_support.exploration_readiness}
                  </span>
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 800, color: '#f1f5f9', marginTop: '4px' }}>
                  {decision_support.target_tier}
                </div>
                <p style={{ fontSize: '0.75rem', color: '#cbd5e1', marginTop: '4px' }}>
                  {decision_support.confidence_assessment}
                </p>
              </div>

              {/* 5-Phase Action Plan */}
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#f1f5f9', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Recommended 5-Phase Exploration Plan
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {decision_support.recommended_actions?.map((act) => (
                    <div
                      key={act.step}
                      style={{
                        background: 'rgba(15, 23, 42, 0.75)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '6px',
                        padding: '8px 10px',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px',
                      }}
                    >
                      <div
                        style={{
                          width: '20px',
                          height: '20px',
                          borderRadius: '50%',
                          background: '#0284c7',
                          color: '#fff',
                          fontSize: '0.7rem',
                          fontWeight: 800,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                        }}
                      >
                        {act.step}
                      </div>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#e2e8f0' }}>
                            {act.phase}
                          </span>
                          <span style={{ fontSize: '0.62rem', fontWeight: 700, color: '#00f0ff', padding: '1px 5px', borderRadius: '3px', background: 'rgba(0, 240, 255, 0.15)' }}>
                            {act.priority}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>
                          {act.action}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk Factors */}
              {decision_support.risk_factors && (
                <div style={{ background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '6px', padding: '8px 12px' }}>
                  <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#f87171', marginBottom: 4 }}>
                    Exploration Risks & Geological Traps
                  </div>
                  <ul style={{ paddingLeft: '1.1rem', margin: 0, fontSize: '0.72rem', color: '#cbd5e1' }}>
                    {decision_support.risk_factors.map((rf, idx) => (
                      <li key={idx} style={{ marginTop: 2 }}>{rf}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Export Dossier Button */}
              <button
                type="button"
                onClick={handleExportDossier}
                style={{
                  background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  marginTop: '4px',
                }}
              >
                <Download size={14} />
                <span>Export Complete Exploration Dossier (JSON)</span>
              </button>
            </>
          ) : (
            <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              Decision support matrix available upon analysis execution.
            </p>
          )}
        </div>
      )}

      {/* Tab 5: Sources, Map Layers & Limitations */}
      {activeTab === 'sources' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* Map layers */}
          {relevant_map_layers && (
            <div className="evidence-block">
              <div className="evidence-heading">Active Geological & Satellite Layers</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 3 }}>
                {relevant_map_layers.map((layer, i) => (
                  <li key={i} style={{ fontSize: '0.74rem', color: '#c9cfd8', display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Layers size={12} color="#00f0ff" />
                    <span>{layer}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Data sources */}
          {data_sources && (
            <div className="evidence-block">
              <div className="evidence-heading">Verified Survey & Data Sources</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 3 }}>
                {data_sources.map((src, i) => (
                  <li key={i} style={{ fontSize: '0.74rem', color: '#c9cfd8', display: 'flex', alignItems: 'center', gap: 5 }}>
                    <Database size={12} color="#00f0ff" />
                    <span>{src}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Limitations */}
          {limitations_and_warnings && (
            <div className="warning-callout">
              <div style={{ fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                <AlertTriangle size={13} />
                <span>Exploration Constraints & Disclaimers</span>
              </div>
              <ul style={{ paddingLeft: '1.2rem', margin: 0 }}>
                {limitations_and_warnings.map((warn, i) => (
                  <li key={i} style={{ marginTop: 2 }}>{warn}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
