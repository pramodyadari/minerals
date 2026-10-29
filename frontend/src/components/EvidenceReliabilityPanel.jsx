import React, { useState } from 'react';
import {
  ShieldCheck,
  Database,
  Layers,
  FileText,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Clock,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Activity,
  ArrowRight,
  Info,
  Calendar,
  Cpu,
  Compass,
  AlertOctagon,
  RefreshCw,
  Search
} from 'lucide-react';

export default function EvidenceReliabilityPanel({ evidenceEngine, selectedMineral, locationName, radiusKm }) {
  // Expandable sections state
  const [expandedSections, setExpandedSections] = useState({
    sources: true,
    inventory: true,
    geology: true,
    model: true,
    traceability: true
  });

  const toggleSection = (sec) => {
    setExpandedSections(prev => ({ ...prev, [sec]: !prev[sec] }));
  };

  if (!evidenceEngine) {
    return (
      <div style={{
        padding: '1.5rem',
        background: 'rgba(15, 23, 42, 0.6)',
        borderRadius: '8px',
        border: '1px dashed rgba(255, 255, 255, 0.15)',
        textAlign: 'center',
        color: '#94a3b8',
        fontSize: '0.82rem'
      }}>
        <Clock size={20} style={{ margin: '0 auto 8px auto', color: '#00f0ff' }} />
        <span>Evidence & Reliability Engine awaiting analysis execution...</span>
      </div>
    );
  }

  const {
    evaluated_at,
    evidence_inventory = [],
    geological_explanations = [],
    model_reliability = {},
    traceability = {},
    total_layers_audited = 0,
    layers_available_count = 0,
    layers_partial_count = 0,
    layers_unavailable_count = 0
  } = evidenceEngine;

  // Status badge styling helper
  const getStatusBadge = (status) => {
    switch (status) {
      case 'AVAILABLE':
      case 'VALIDATED_FOR_DOMAIN':
      case 'VALIDATED_ACTIVE':
        return { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', color: '#34d399', text: status };
      case 'PARTIAL':
      case 'EVIDENCE_ONLY':
        return { bg: 'rgba(56, 189, 248, 0.15)', border: '#38bdf8', color: '#7dd3fc', text: status };
      case 'UNAVAILABLE':
      case 'NO_VALIDATED_MODEL':
        return { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', color: '#fbbf24', text: status };
      case 'OUTSIDE_TRAINING_FOOTPRINT':
      case 'FAILED':
        return { bg: 'rgba(244, 63, 94, 0.15)', border: '#f43f5e', color: '#fda4af', text: status };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', border: '#94a3b8', color: '#cbd5e1', text: status || 'UNKNOWN' };
    }
  };

  const modelBadge = getStatusBadge(model_reliability.eligibility_status);

  return (
    <div className="evidence-reliability-panel" style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      margin: '8px 0',
      fontFamily: 'var(--font-sans, system-ui)'
    }}>
      {/* Header Summary Card */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.85), rgba(10, 15, 26, 0.95))',
        border: '1px solid rgba(0, 240, 255, 0.3)',
        borderRadius: '8px',
        padding: '12px 14px',
        boxShadow: '0 4px 20px rgba(0, 0, 0, 0.35)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ShieldCheck size={18} color="#00f0ff" />
            <h3 style={{ margin: 0, fontSize: '0.88rem', fontWeight: 700, color: '#f8fafc' }}>
              Evidence & Reliability Engine
            </h3>
          </div>
          <span style={{
            fontSize: '0.65rem',
            padding: '2px 8px',
            borderRadius: '12px',
            background: modelBadge.bg,
            border: `1px solid ${modelBadge.border}`,
            color: modelBadge.color,
            fontWeight: 700,
            fontFamily: 'var(--font-mono, monospace)'
          }}>
            {modelBadge.text}
          </span>
        </div>

        <p style={{ margin: '0 0 8px 0', fontSize: '0.74rem', color: '#94a3b8', lineHeight: 1.4 }}>
          Traceable data provenance, explicit inventory states, and scientific domain eligibility for <b>{selectedMineral}</b>.
        </p>

        {/* Quick Audit Counters */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '6px',
          background: 'rgba(0, 0, 0, 0.25)',
          borderRadius: '6px',
          padding: '6px 8px',
          textAlign: 'center'
        }}>
          <div>
            <div style={{ fontSize: '0.62rem', color: '#94a3b8', textTransform: 'uppercase' }}>Audited Layers</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#f1f5f9' }}>{total_layers_audited}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.62rem', color: '#34d399', textTransform: 'uppercase' }}>Available</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#34d399' }}>{layers_available_count}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.62rem', color: '#7dd3fc', textTransform: 'uppercase' }}>Partial</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#7dd3fc' }}>{layers_partial_count}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.62rem', color: '#fbbf24', textTransform: 'uppercase' }}>Unavailable</div>
            <div style={{ fontSize: '0.85rem', fontWeight: 800, color: '#fbbf24' }}>{layers_unavailable_count}</div>
          </div>
        </div>
      </div>

      {/* SECTION 1: Data Sources & Freshness */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <button
          type="button"
          onClick={() => toggleSection('sources')}
          style={{
            width: '100%',
            padding: '10px 14px',
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            color: '#f1f5f9',
            fontSize: '0.78rem',
            fontWeight: 700
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={15} color="#38bdf8" />
            <span>1. Data Sources & Freshness Provenance</span>
          </div>
          {expandedSections.sources ? <ChevronUp size={15} color="#94a3b8" /> : <ChevronDown size={15} color="#94a3b8" />}
        </button>

        {expandedSections.sources && (
          <div style={{ padding: '0 14px 12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {evidence_inventory.map((layer, idx) => {
              const b = getStatusBadge(layer.retrieval_status);
              return (
                <div key={idx} style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '6px',
                  padding: '8px 10px',
                  fontSize: '0.72rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
                    <div style={{ fontWeight: 700, color: '#e2e8f0' }}>{layer.dataset_name}</div>
                    <span style={{
                      fontSize: '0.62rem',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      background: b.bg,
                      border: `1px solid ${b.border}`,
                      color: b.color,
                      fontWeight: 700,
                      fontFamily: 'monospace'
                    }}>
                      {layer.retrieval_status}
                    </span>
                  </div>
                  <div style={{ color: '#94a3b8', marginBottom: 4 }}>
                    <b>Provider:</b> {layer.data_provider}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, color: '#cbd5e1', fontSize: '0.68rem', marginBottom: 4 }}>
                    <div><b>Acquisition Date:</b> {layer.acquisition_date || 'N/A (Historical/Regional)'}</div>
                    <div><b>Retrieved:</b> {new Date(layer.retrieval_timestamp).toLocaleString()}</div>
                    <div><b>Spatial Res:</b> {layer.spatial_resolution}</div>
                    <div><b>Freshness Policy:</b> {layer.freshness_policy}</div>
                  </div>
                  {layer.processing_transformation && (
                    <div style={{ color: '#94a3b8', fontSize: '0.68rem', marginBottom: 2 }}>
                      <b>Processing:</b> {layer.processing_transformation}
                    </div>
                  )}
                  {layer.missing_reason && (
                    <div style={{ color: '#fbbf24', fontSize: '0.68rem', marginTop: 4, background: 'rgba(245, 158, 11, 0.1)', padding: '4px 6px', borderRadius: '4px' }}>
                      <b>Missing/Withheld Reason:</b> {layer.missing_reason}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: Available & Missing Evidence Inventory */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <button
          type="button"
          onClick={() => toggleSection('inventory')}
          style={{
            width: '100%',
            padding: '10px 14px',
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            color: '#f1f5f9',
            fontSize: '0.78rem',
            fontWeight: 700
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Layers size={15} color="#00f0ff" />
            <span>2. Evidence Inventory & Quality Breakdown</span>
          </div>
          {expandedSections.inventory ? <ChevronUp size={15} color="#94a3b8" /> : <ChevronDown size={15} color="#94a3b8" />}
        </button>

        {expandedSections.inventory && (
          <div style={{ padding: '0 14px 12px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {evidence_inventory.map((layer, idx) => {
              const isAvail = layer.retrieval_status === 'AVAILABLE';
              const isPart = layer.retrieval_status === 'PARTIAL';
              return (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  padding: '6px 8px',
                  borderRadius: '5px',
                  background: isAvail ? 'rgba(16, 185, 129, 0.08)' : isPart ? 'rgba(56, 189, 248, 0.08)' : 'rgba(245, 158, 11, 0.08)',
                  borderLeft: `3px solid ${isAvail ? '#10b981' : isPart ? '#38bdf8' : '#f59e0b'}`
                }}>
                  {isAvail ? (
                    <CheckCircle2 size={14} color="#10b981" style={{ marginTop: 2, flexShrink: 0 }} />
                  ) : isPart ? (
                    <Activity size={14} color="#38bdf8" style={{ marginTop: 2, flexShrink: 0 }} />
                  ) : (
                    <AlertTriangle size={14} color="#f59e0b" style={{ marginTop: 2, flexShrink: 0 }} />
                  )}
                  <div style={{ fontSize: '0.72rem', flex: 1 }}>
                    <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{layer.dataset_name}</div>
                    <div style={{ color: '#94a3b8', fontSize: '0.68rem', marginTop: 1 }}>{layer.quality_summary}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 3: Geological Evidence & Explanations */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <button
          type="button"
          onClick={() => toggleSection('geology')}
          style={{
            width: '100%',
            padding: '10px 14px',
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            color: '#f1f5f9',
            fontSize: '0.78rem',
            fontWeight: 700
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={15} color="#a855f7" />
            <span>3. Geological Evidence & Explanations</span>
          </div>
          {expandedSections.geology ? <ChevronUp size={15} color="#94a3b8" /> : <ChevronDown size={15} color="#94a3b8" />}
        </button>

        {expandedSections.geology && (
          <div style={{ padding: '0 14px 12px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {geological_explanations.map((exp, idx) => (
              <div key={idx} style={{
                background: 'rgba(0, 0, 0, 0.35)',
                border: '1px solid rgba(255, 255, 255, 0.07)',
                borderRadius: '6px',
                padding: '10px',
                fontSize: '0.72rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <div style={{ fontWeight: 700, color: '#f8fafc', fontSize: '0.75rem' }}>{exp.name}</div>
                  <span style={{
                    fontSize: '0.62rem',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    background: exp.hypothesis_relation === 'SUPPORTS' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(148, 163, 184, 0.15)',
                    border: `1px solid ${exp.hypothesis_relation === 'SUPPORTS' ? '#10b981' : '#94a3b8'}`,
                    color: exp.hypothesis_relation === 'SUPPORTS' ? '#34d399' : '#cbd5e1'
                  }}>
                    {exp.hypothesis_relation}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, color: '#cbd5e1' }}>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Measurement:</span> {exp.measurement_representation}
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Geological Indication:</span> {exp.geological_indication}
                  </div>
                  <div>
                    <span style={{ color: '#00f0ff' }}>Mineral Relevance:</span> {exp.mineral_relevance}
                  </div>
                  <div style={{ color: '#fca5a5', background: 'rgba(239, 68, 68, 0.08)', padding: '5px 7px', borderRadius: '4px', marginTop: 2 }}>
                    <b>Limitations & Alternatives:</b> {exp.limitations_and_alternatives}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SECTION 4: Model Eligibility & Validation Panel */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <button
          type="button"
          onClick={() => toggleSection('model')}
          style={{
            width: '100%',
            padding: '10px 14px',
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            color: '#f1f5f9',
            fontSize: '0.78rem',
            fontWeight: 700
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={15} color="#ec4899" />
            <span>4. Model Eligibility & Domain Compliance</span>
          </div>
          {expandedSections.model ? <ChevronUp size={15} color="#94a3b8" /> : <ChevronDown size={15} color="#94a3b8" />}
        </button>

        {expandedSections.model && (
          <div style={{ padding: '0 14px 12px 14px', display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.72rem' }}>
            <div style={{
              background: modelBadge.bg,
              border: `1px solid ${modelBadge.border}`,
              borderRadius: '6px',
              padding: '8px 10px',
              display: 'flex',
              flexDirection: 'column',
              gap: 4
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 700, color: '#f8fafc' }}>{model_reliability.model_name}</span>
                <span style={{ fontWeight: 700, color: modelBadge.color, fontFamily: 'monospace' }}>
                  {model_reliability.eligibility_status}
                </span>
              </div>
              <div style={{ color: '#cbd5e1' }}>
                <b>Model ID:</b> {model_reliability.model_id} | <b>Target:</b> {model_reliability.target_mineral}
              </div>
              {model_reliability.score_unavailable_reason && (
                <div style={{ color: '#fde047', background: 'rgba(0,0,0,0.3)', padding: '5px 7px', borderRadius: '4px' }}>
                  <b>Reason Score Withheld:</b> {model_reliability.score_unavailable_reason}
                </div>
              )}
            </div>

            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '8px 10px', borderRadius: '6px', display: 'flex', flexDirection: 'column', gap: 4 }}>
              <div style={{ fontWeight: 600, color: '#94a3b8' }}>Scientific Guardrails & Validation:</div>
              <p style={{ margin: 0, color: '#cbd5e1', lineHeight: 1.4 }}>
                {model_reliability.scientific_guardrail}
              </p>
              <div style={{ color: '#94a3b8', fontSize: '0.68rem', marginTop: 2 }}>
                <b>Calibration Status:</b> {model_reliability.validation_diagnostics?.calibration_status || 'NOT_CALIBRATED'} (Accuracy is not calibrated probability).
              </div>
            </div>
          </div>
        )}
      </div>

      {/* SECTION 5: Traceability, Limitations & Next Steps */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <button
          type="button"
          onClick={() => toggleSection('traceability')}
          style={{
            width: '100%',
            padding: '10px 14px',
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            color: '#f1f5f9',
            fontSize: '0.78rem',
            fontWeight: 700
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Compass size={15} color="#10b981" />
            <span>5. Evidence Traceability & Recommended Next Steps</span>
          </div>
          {expandedSections.traceability ? <ChevronUp size={15} color="#94a3b8" /> : <ChevronDown size={15} color="#94a3b8" />}
        </button>

        {expandedSections.traceability && (
          <div style={{ padding: '0 14px 12px 14px', display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.72rem' }}>
            <p style={{ margin: 0, color: '#cbd5e1', lineHeight: 1.4 }}>
              {traceability.primary_synthesis}
            </p>

            {/* Traceability Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              <div style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '6px 8px', borderRadius: '5px' }}>
                <div style={{ fontWeight: 700, color: '#34d399', marginBottom: 2 }}>Supporting Evidence:</div>
                {traceability.supporting_evidence_ids && traceability.supporting_evidence_ids.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 16, color: '#cbd5e1' }}>
                    {traceability.supporting_evidence_ids.map((id, i) => <li key={i}>{id}</li>)}
                  </ul>
                ) : (
                  <span style={{ color: '#94a3b8' }}>None identified</span>
                )}
              </div>

              <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '6px 8px', borderRadius: '5px' }}>
                <div style={{ fontWeight: 700, color: '#fbbf24', marginBottom: 2 }}>Missing Essential Data:</div>
                {traceability.missing_evidence && traceability.missing_evidence.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 16, color: '#cbd5e1' }}>
                    {traceability.missing_evidence.map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                ) : (
                  <span style={{ color: '#94a3b8' }}>None</span>
                )}
              </div>
            </div>

            {/* Suggested Field Verification Steps */}
            <div style={{ background: 'rgba(0, 0, 0, 0.3)', border: '1px solid rgba(255, 255, 255, 0.08)', padding: '8px', borderRadius: '6px' }}>
              <div style={{ fontWeight: 700, color: '#00f0ff', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                <ArrowRight size={13} />
                <span>Suggested Verification & Field Exploration Steps:</span>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, color: '#cbd5e1', lineHeight: 1.5 }}>
                {(traceability.suggested_next_steps || []).map((step, idx) => (
                  <li key={idx}>{step}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
