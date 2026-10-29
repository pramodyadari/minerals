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
  ArrowRight,
  Mountain
} from 'lucide-react';

import MultiMineralScorecards from './MultiMineralScorecards';
import EvidenceReliabilityPanel from './EvidenceReliabilityPanel';

export default function ResultsPanel({
  result,
  multiResult,
  isAnalyzing,
  error,
  selectedMineral,
  onSelectMineral,
  radiusKm,
  selectedLocation
}) {
  const [panelViewMode, setPanelViewMode] = useState('multi'); // 'multi' | 'dossier'
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'geology' | 'terrain' | 'matrix' | 'decision' | 'sources'
  const [expandedItem, setExpandedItem] = useState(null);
  const [showPipelineStages, setShowPipelineStages] = useState(false);

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
          Analyzing multi-spectral raster features, geological host formations, and spatial evidence across commodities.
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

  // When multiResult is available and multi view mode is active, display the 4-mineral scorecards
  if (multiResult && panelViewMode === 'multi') {
    return (
      <div className="results-wrapper">
        <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
          <button
            type="button"
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: '0.74rem',
              fontWeight: 700,
              borderRadius: '6px',
              border: '1.5px solid #00f0ff',
              background: 'rgba(0, 240, 255, 0.15)',
              color: '#00f0ff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6
            }}
            onClick={() => setPanelViewMode('multi')}
            id="tab-view-all-scorecards"
          >
            <Sparkles size={14} />
            <span>Unified 4-Mineral Comparison ({radiusKm || 10} km)</span>
          </button>
          <button
            type="button"
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: '0.74rem',
              fontWeight: 500,
              borderRadius: '6px',
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.04)',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6
            }}
            onClick={() => setPanelViewMode('dossier')}
            id="tab-view-focused-dossier"
          >
            <FileText size={14} />
            <span>Deep {selectedMineral} Dossier</span>
          </button>
        </div>

        <MultiMineralScorecards
          multiResult={multiResult}
          selectedMineral={selectedMineral}
          onSelectMineral={onSelectMineral}
          radiusKm={radiusKm}
          selectedLocation={selectedLocation}
        />
      </div>
    );
  }

  const effectiveResult = result || (multiResult && multiResult.minerals && multiResult.minerals[selectedMineral]);

  if (!effectiveResult) {
    return (
      <div className="results-card" style={{ textAlign: 'center', padding: '1.75rem 1rem' }}>
        <div style={{ color: '#00f0ff', marginBottom: '0.5rem' }}>
          <Info size={26} style={{ margin: '0 auto' }} />
        </div>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: '0.98rem', color: '#e5e0d4' }}>
          Awaiting Exploration Target
        </div>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginTop: '0.4rem', maxWidth: '300px', margin: '0.4rem auto 0' }}>
          Pick a map location, select radius, then click <b>Analyze All Four Minerals</b> to generate comprehensive scorecards and comparison summary.
        </p>
      </div>
    );
  }

  const activeResult = effectiveResult;

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
  } = activeResult;

  const isSuccess = status === 'SUCCESS';
  const isEvidenceOnly = status === 'EVIDENCE_ONLY_NO_PREDICTION';
  const isInsufficient = status === 'INSUFFICIENT_DATA';
  const isOutOfCoverage = status === 'OUT_OF_COVERAGE';
  const isOutsideIndia = status === 'OUTSIDE_INDIA_TERRITORY' || activeResult?.is_within_india === false;

  // Support counts
  const supportsCount = evidence_items?.filter(e => e.hypothesis_support === 'SUPPORTS').length || 0;
  const neutralCount = evidence_items?.filter(e => e.hypothesis_support === 'NEUTRAL / UNCONFIRMED').length || 0;
  const awaitingCount = evidence_items?.filter(e => e.hypothesis_support === 'AWAITING OBSERVATION').length || 0;

  // Export Dossier JSON
  const handleExportDossier = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(activeResult, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `Exploration_Dossier_${mineral}_${latitude.toFixed(2)}_${longitude.toFixed(2)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="results-wrapper">
      {multiResult && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
          <button
            type="button"
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: '0.74rem',
              fontWeight: 500,
              borderRadius: '6px',
              border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.04)',
              color: '#94a3b8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6
            }}
            onClick={() => setPanelViewMode('multi')}
            id="tab-view-back-to-all-scorecards"
          >
            <Sparkles size={14} />
            <span>&larr; Back to 4-Mineral Comparison</span>
          </button>
          <button
            type="button"
            style={{
              flex: 1,
              padding: '8px 12px',
              fontSize: '0.74rem',
              fontWeight: 700,
              borderRadius: '6px',
              border: '1.5px solid #00f0ff',
              background: 'rgba(0, 240, 255, 0.15)',
              color: '#00f0ff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6
            }}
            onClick={() => setPanelViewMode('dossier')}
            id="tab-view-focused-dossier"
          >
            <FileText size={14} />
            <span>Deep {mineral} Dossier</span>
          </button>
        </div>
      )}
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

      {/* 8-Stage Scientific Pipeline Lifecycle Breakdown */}
      {result?.pipeline_stages && (
        <div style={{ margin: '0.35rem 0 0.5rem 0' }}>
          <button
            type="button"
            onClick={() => setShowPipelineStages(!showPipelineStages)}
            style={{
              width: '100%',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: '#cbd5e1',
              fontSize: '0.72rem',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={13} color="#00f0ff" />
              <span><b>Scientific Pipeline Verification:</b> 8 Independent Stages</span>
            </div>
            {showPipelineStages ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>

          {showPipelineStages && (
            <div style={{
              background: 'rgba(10, 15, 26, 0.95)',
              border: '1px solid rgba(0, 240, 255, 0.25)',
              borderTop: 'none',
              borderRadius: '0 0 var(--radius-sm) var(--radius-sm)',
              padding: '8px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              fontSize: '0.71rem',
            }}>
              {[
                { stage: '1. Catalogue Discovery', val: result.pipeline_stages.catalogue_discovery?.status, detail: result.pipeline_stages.catalogue_discovery?.source },
                { stage: '2. Metadata Verification', val: result.pipeline_stages.product_metadata_verification?.status, detail: result.pipeline_stages.product_metadata_verification?.primary_scene_id || 'No Scene Metadata' },
                { stage: '3. Authentication Check', val: result.pipeline_stages.authentication?.status, detail: result.pipeline_stages.authentication?.authenticated ? 'Authenticated' : 'Credentials Not Configured (.env)' },
                { stage: '4. Remote Download', val: result.pipeline_stages.download?.status, detail: result.pipeline_stages.download?.status === 'COMPLETED_LOCAL_ARCHIVE' ? 'Local Archive Utilized' : result.pipeline_stages.download?.status === 'COMPLETED_LOCAL_CACHE' ? 'Processed Cache Utilized' : 'Protected Endpoint' },
                { stage: '5. Integrity & Extraction', val: result.pipeline_stages.extraction_and_integrity?.status, detail: `Bands: ${result.pipeline_stages.extraction_and_integrity?.bands_verified?.join(', ') || 'None'}` },
                { stage: '6. Raster Processing', val: result.pipeline_stages.raster_processing?.status, detail: `${result.pipeline_stages.raster_processing?.valid_pixels || 0} Valid 20m Pixels` },
                { stage: '7. Evidence Analysis', val: result.pipeline_stages.evidence_analysis?.status, detail: `${result.pipeline_stages.evidence_analysis?.total_evidence_items || 0} Verified Evidence Items` },
                { stage: '8. Spatial Model Prediction', val: result.pipeline_stages.validated_model_prediction?.status, detail: result.pipeline_stages.validated_model_prediction?.status === 'AVAILABLE' ? `Spatial Prospectivity Index: ${result.pipeline_stages.validated_model_prediction?.prospectivity_index}%` : 'Withheld (Model Unvalidated or Outside Domain)' }
              ].map((item, idx) => {
                const isGreen = item.val === 'AVAILABLE' || item.val === 'COMPLETED' || item.val === 'VERIFIED' || item.val === 'VERIFIED_VALID_BANDS' || item.val === 'AVAILABLE_LIVE' || item.val === 'AVAILABLE_ARCHIVED' || item.val === 'CREDENTIALS_CONFIGURED';
                const isBlue = item.val === 'COMPLETED_LOCAL_ARCHIVE' || item.val === 'COMPLETED_LOCAL_CACHE' || item.val === 'VERIFIED_LOCAL_ARCHIVE';
                const statusColor = isGreen ? '#10b981' : isBlue ? '#38bdf8' : '#f59e0b';
                return (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: idx < 7 ? '1px solid rgba(255, 255, 255, 0.05)' : 'none', paddingBottom: '3px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{item.stage}</span>
                      <span style={{ fontSize: '0.64rem', color: '#94a3b8' }}>{item.detail}</span>
                    </div>
                    <span style={{ fontWeight: 700, color: statusColor, fontSize: '0.68rem', fontFamily: 'var(--font-mono)' }}>
                      {item.val}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

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

      {/* Nationwide Geographic Eligibility Banner */}
      {result?.geographic_eligibility && (
        <div style={{
          background: result.geographic_eligibility.overall_eligibility === 'ELIGIBLE_FOR_ANALYSIS'
            ? 'rgba(16, 185, 129, 0.12)'
            : result.geographic_eligibility.overall_eligibility === 'EVIDENCE_ONLY'
            ? 'rgba(56, 189, 248, 0.12)'
            : 'rgba(245, 158, 11, 0.12)',
          border: `1px solid ${
            result.geographic_eligibility.overall_eligibility === 'ELIGIBLE_FOR_ANALYSIS'
              ? '#10b981'
              : result.geographic_eligibility.overall_eligibility === 'EVIDENCE_ONLY'
              ? '#38bdf8'
              : '#f59e0b'
          }`,
          borderRadius: 'var(--radius-sm)',
          padding: '8px 12px',
          margin: '0.45rem 0',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <ShieldCheck size={13} color={
                result.geographic_eligibility.overall_eligibility === 'ELIGIBLE_FOR_ANALYSIS' ? '#10b981' : '#38bdf8'
              } />
              Geographic Eligibility & Model Domain:
            </span>
            <span style={{
              fontSize: '0.68rem',
              fontWeight: 700,
              fontFamily: 'var(--font-mono)',
              padding: '2px 6px',
              borderRadius: '3px',
              background: 'rgba(0, 0, 0, 0.35)',
              color: result.geographic_eligibility.overall_eligibility === 'ELIGIBLE_FOR_ANALYSIS'
                ? '#34d399'
                : result.geographic_eligibility.overall_eligibility === 'EVIDENCE_ONLY'
                ? '#38bdf8'
                : '#fbbf24'
            }}>
              {result.geographic_eligibility.overall_eligibility}
            </span>
          </div>
          <p style={{ fontSize: '0.73rem', color: '#cbd5e1', margin: 0, lineHeight: 1.4 }}>
            {result.geographic_eligibility.explanation}
          </p>
        </div>
      )}

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

      {/* Standardized Mineral Evaluation & Scorecard (Steps 5 & 6) */}
      {result?.evaluation_summary && !isOutsideIndia && (
        <div style={{
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(0, 240, 255, 0.3)',
          borderRadius: 'var(--radius-sm)',
          padding: '12px 14px',
          margin: '0.6rem 0',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px'
        }}>
          {/* Card Title & Badges */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Sparkles size={16} color="#00f0ff" />
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {result.evaluation_summary.evidence_index_label || `${mineral} Evidence Analysis`}
              </span>
            </div>
            
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {/* Separate Evidence Quality Badge */}
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                background: result.evaluation_summary.evidence_quality === 'high' ? 'rgba(16, 185, 129, 0.2)' : result.evaluation_summary.evidence_quality === 'medium' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                color: result.evaluation_summary.evidence_quality === 'high' ? '#34d399' : result.evaluation_summary.evidence_quality === 'medium' ? '#38bdf8' : '#fbbf24',
                border: `1px solid ${result.evaluation_summary.evidence_quality === 'high' ? '#10b981' : result.evaluation_summary.evidence_quality === 'medium' ? '#38bdf8' : '#f59e0b'}`
              }}>
                Evidence Quality: {result.evaluation_summary.evidence_quality?.toUpperCase()}
              </span>

              {/* Simple Interpretation Badge */}
              <span style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                background: result.evaluation_summary.simple_tier === 'HIGHER' ? 'rgba(16, 185, 129, 0.25)' : result.evaluation_summary.simple_tier === 'MODERATE' ? 'rgba(56, 189, 248, 0.25)' : 'rgba(148, 163, 184, 0.25)',
                color: result.evaluation_summary.simple_tier === 'HIGHER' ? '#34d399' : result.evaluation_summary.simple_tier === 'MODERATE' ? '#38bdf8' : '#cbd5e1',
                border: '1px solid rgba(255, 255, 255, 0.15)'
              }}>
                {result.evaluation_summary.simple_tier} FAVORABILITY
              </span>
            </div>
          </div>

          {/* Dual Metrics: AI Prospectivity Score vs Multi-Criteria Evidence Index */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '10px',
            background: 'rgba(0, 0, 0, 0.35)',
            padding: '10px',
            borderRadius: 'var(--radius-sm)'
          }}>
            {/* 1. AI ML Model Prospectivity Score */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <span style={{ fontSize: '0.64rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                AI Model Prediction (0-100)
              </span>
              {result.evaluation_summary.prospectivity_score !== null ? (
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#00f0ff', fontFamily: 'var(--font-mono)' }}>
                    {result.evaluation_summary.prospectivity_score}%
                  </span>
                  <span style={{ fontSize: '0.68rem', color: '#34d399' }}>Validated</span>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f43f5e', fontFamily: 'var(--font-mono)' }}>
                    NULL (WITHHELD)
                  </span>
                  <span style={{ fontSize: '0.62rem', color: '#94a3b8' }}>
                    {result.evaluation_summary.prospectivity_status?.replace(/_/g, ' ')}
                  </span>
                </div>
              )}
            </div>

            {/* 2. Transparent Multi-Criteria Evidence Index */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              <span style={{ fontSize: '0.64rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Evidence Favorability Index (0-100)
              </span>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                  {result.evaluation_summary.evidence_index !== null ? `${result.evaluation_summary.evidence_index}` : 'N/A'}
                </span>
                <span style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>/ 100</span>
              </div>
            </div>
          </div>

          {/* Simple Interpretation Sentence */}
          <div style={{ fontSize: '0.76rem', color: '#e2e8f0', lineHeight: 1.45 }}>
            <b>Interpretation:</b> {result.evaluation_summary.simple_interpretation}
          </div>

          {/* Formula & Weight Transparency */}
          {result.evaluation_summary.evidence_formula && (
            <div style={{ fontSize: '0.67rem', color: '#94a3b8', background: 'rgba(255,255,255,0.03)', padding: '5px 8px', borderRadius: '4px', borderLeft: '2px solid #38bdf8' }}>
              <b>Evidence Index Formula:</b> {result.evaluation_summary.evidence_formula}
            </div>
          )}

          {/* What This Means vs Does NOT Mean */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px', marginTop: '2px' }}>
            <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.25)', borderRadius: '4px', padding: '6px 8px' }}>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#34d399', marginBottom: '3px' }}>
                What this result MEANS:
              </div>
              <div style={{ fontSize: '0.69rem', color: '#cbd5e1', lineHeight: 1.35 }}>
                {result.evaluation_summary.what_this_result_means}
              </div>
            </div>

            <div style={{ background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '4px', padding: '6px 8px' }}>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#f87171', marginBottom: '3px' }}>
                What this DOES NOT mean:
              </div>
              <div style={{ fontSize: '0.69rem', color: '#cbd5e1', lineHeight: 1.35 }}>
                {result.evaluation_summary.what_this_result_does_not_mean}
              </div>
            </div>
          </div>
        </div>
      )}

      {isEvidenceOnly && !result?.evaluation_summary && (
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
        gridTemplateColumns: 'repeat(7, 1fr)',
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
            fontSize: '0.66rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Verdict
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('reliability')}
          id="btn-tab-evidence-reliability"
          style={{
            background: activeTab === 'reliability' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'reliability' ? '1px solid #00f0ff' : 'none',
            color: activeTab === 'reliability' ? '#00f0ff' : '#38bdf8',
            padding: '6px 2px',
            fontSize: '0.66rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Reliability
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
          onClick={() => setActiveTab('terrain')}
          id="btn-tab-terrain"
          style={{
            background: activeTab === 'terrain' ? 'var(--bg-surface-elevated)' : 'transparent',
            border: activeTab === 'terrain' ? '1px solid #10b981' : 'none',
            color: activeTab === 'terrain' ? '#10b981' : 'var(--text-dim)',
            padding: '6px 2px',
            fontSize: '0.68rem',
            fontWeight: 700,
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Terrain
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

      {/* Tab: Evidence & Reliability Engine */}
      {activeTab === 'reliability' && (
        <EvidenceReliabilityPanel
          evidenceEngine={activeResult?.evidence_engine}
          selectedMineral={selectedMineral}
          locationName={location_name}
          radiusKm={radius_km}
        />
      )}

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

      {/* Tab: Terrain Geomorphology (Copernicus DEM GLO-30) */}
      {activeTab === 'terrain' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {/* Header Banner */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            padding: '0.85rem',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.78rem',
            color: '#e5e0d4',
            lineHeight: 1.5
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ fontWeight: 700, color: '#10b981', textTransform: 'uppercase', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Mountain size={15} />
                <span>Copernicus DEM (GLO-30 Public Elevation Model)</span>
              </div>
              <span style={{
                fontSize: '0.65rem',
                fontFamily: 'var(--font-mono)',
                color: result.terrain_evidence?.available ? '#34d399' : '#f59e0b',
                background: result.terrain_evidence?.available ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                padding: '2px 6px',
                borderRadius: '3px'
              }}>
                {result.terrain_evidence?.available ? 'VERIFIED ACTIVE' : (result.terrain_evidence?.status || 'AWAITING DEM TILE')}
              </span>
            </div>

            {result.terrain_evidence?.available ? (
              <div>
                <p style={{ color: '#cbd5e1', fontSize: '0.76rem', marginBottom: '0.5rem' }}>
                  Authentic 30-meter elevation and geomorphic metrics derived from official Copernicus DEM tiles.
                  Co-registered in UTM projection with EGM2008 vertical datum.
                </p>

                {/* Metrics 3-Col Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: '6px',
                  marginTop: '0.5rem'
                }}>
                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>Target Elevation</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#34d399', fontFamily: 'var(--font-mono)' }}>
                      {result.terrain_evidence.elevation_m !== null ? `${result.terrain_evidence.elevation_m} m` : 'N/A'}
                    </div>
                    <div style={{ fontSize: '0.62rem', color: '#64748b' }}>EGM2008 Geoid</div>
                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>Local Slope</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                      {result.terrain_evidence.slope_deg !== null ? `${result.terrain_evidence.slope_deg}°` : 'N/A'}
                    </div>
                    <div style={{ fontSize: '0.62rem', color: '#64748b' }}>Horn Metric Grid</div>
                  </div>

                  <div style={{ background: 'rgba(0,0,0,0.3)', padding: '6px 8px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase' }}>TPI (500m)</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#fcd34d', fontFamily: 'var(--font-mono)' }}>
                      {result.terrain_evidence.tpi_m !== null ? `${result.terrain_evidence.tpi_m > 0 ? '+' : ''}${result.terrain_evidence.tpi_m} m` : 'N/A'}
                    </div>
                    <div style={{ fontSize: '0.62rem', color: '#64748b' }}>{result.terrain_evidence.topographic_position || 'Morphology'}</div>
                  </div>
                </div>

                {/* Radius Regional Statistics if Audit Metrics exist */}
                {result.terrain_evidence.audit_metrics && (
                  <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.75rem', background: 'rgba(0,0,0,0.25)', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 4 }}>
                      Regional {radius_km} km Geomorphic Window Statistics:
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px', fontSize: '0.72rem', color: '#cbd5e1' }}>
                      <div>&bull; Elevation Range: <b>{result.terrain_evidence.audit_metrics.elevation_m.min}m – {result.terrain_evidence.audit_metrics.elevation_m.max}m</b></div>
                      <div>&bull; Mean Slope: <b>{result.terrain_evidence.audit_metrics.slope_degrees.mean}°</b> (Max: {result.terrain_evidence.audit_metrics.slope_degrees.max}°)</div>
                      <div>&bull; Ridge Crests (TPI &gt; 12m): <b>{result.terrain_evidence.audit_metrics.topographic_position_index.prominent_ridge_crests_tpi_over_12m_pct}%</b></div>
                      <div>&bull; Scarp Slopes (&gt; 15°): <b>{result.terrain_evidence.audit_metrics.slope_degrees.steep_scarp_slopes_over_15_deg_pct}%</b></div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ color: '#d5c4a1', fontSize: '0.75rem' }}>
                <p>{result.terrain_evidence?.message || `Local Copernicus GLO-30 DEM raster for (${latitude?.toFixed(4)}°N, ${longitude?.toFixed(4)}°E) is outside the downloaded Noamundi-Singhbhum tiles (Lat 21°–23°N, Lon 85°–86°E).`}</p>
                <div style={{ marginTop: 6, fontSize: '0.7rem', color: '#94a3b8' }}>
                  Awaiting automated DEM tile ingestion from AWS Open Data / CDSE for this coordinate.
                </div>
              </div>
            )}
          </div>

          {/* Geomorphic Context per Mineral */}
          <div style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-subtle)',
            padding: '0.75rem 0.85rem',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.74rem',
            color: '#e5e0d4',
            lineHeight: 1.45
          }}>
            <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: 4, textTransform: 'uppercase', fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: 5 }}>
              <Info size={13} />
              <span>Geomorphic Exploration Significance ({mineral})</span>
            </div>
            <p>
              {mineral === 'Iron Ore'
                ? 'Supergene hematite-martite ore bodies in the Singhbhum Craton are capped by resistant Banded Iron Formations (BIF/BHQ) forming prominent structural strike ridges (TPI > 12m, elevation 600m–900m ASL). Soft tuffaceous shales weather into valleys (TPI < -12m). Active open-cast mining benches produce localized steep scarp slopes (>15° up to 50°).'
                : mineral === 'Coal'
                ? 'Gondwana coal seams are preserved within down-faulted synclinal graben corridors. Topographic position analysis delineates regional fault-bounded basin floors from uplifted Precambrian crystalline basement.'
                : mineral === 'Manganese'
                ? 'Manganese gondites and braunite reefs in the Sausar Group form strike-parallel ridgelines and manganiferous gossans. Elevation and slope statistics map resistant metasedimentary strike ridges.'
                : 'Tertiary bauxite deposits in India are strictly preserved as flat-topped plateau duricrusts (high-elevation "pat" lands >900m ASL). Flat plateau tops with near-zero slope surrounded by steep scarp slopes are diagnostic.'}
            </p>
          </div>

          {/* Scientific Disclaimers & Integrity Policy */}
          <div style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.75rem 0.85rem',
            fontSize: '0.72rem',
            color: '#fde68a',
            lineHeight: 1.45
          }}>
            <div style={{ fontWeight: 700, color: '#f59e0b', marginBottom: 3, textTransform: 'uppercase', fontSize: '0.66rem', display: 'flex', alignItems: 'center', gap: 5 }}>
              <AlertTriangle size={13} />
              <span>Scientific Guardrails & Spatial Resolution Notice</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div>
                <b>Resolution:</b> Native Copernicus GLO-30 resolution is 1 arc-second (~30.87m). Resampling to 20m UTM grid provides geometric co-registration with Sentinel-2 L2A bands (B11, B12, SCL), but does <i>NOT</i> create new 20m spatial resolution.
              </div>
              <div>
                <b>Subsurface Limitation:</b> Topographic elevation and slope alone cannot prove subsurface mineral deposits, commercial ore grades, or thickness. Numerical AI prospectivity scores remain strictly withheld without subsurface drilling assays or aeromagnetics.
              </div>
            </div>
          </div>
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
    </div>
  );
}
