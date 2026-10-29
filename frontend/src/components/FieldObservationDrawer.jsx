import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../apiConfig';
import {
  X,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Camera,
  FlaskConical,
  Eye,
  FileText,
  Download,
  Plus,
  RefreshCw,
  Loader2,
  ShieldCheck,
  ChevronRight,
  User,
  Building,
  Activity,
  Layers,
  MapPin
} from 'lucide-react';

export default function FieldObservationDrawer({
  isOpen,
  onClose,
  onOpenCreateModal,
  onSelectObservationOnMap,
  selectedLocation
}) {
  const [observations, setObservations] = useState([]);
  const [selectedObs, setSelectedObs] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isComparing, setIsComparing] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [mineralFilter, setMineralFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Status review state
  const [reviewStatus, setReviewStatus] = useState('');
  const [reviewReason, setReviewReason] = useState('');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  const fetchObservations = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (mineralFilter !== 'All') params.append('mineral', mineralFilter);
      if (statusFilter !== 'All') params.append('status', statusFilter);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());

      const resp = await fetch(getApiUrl(`/api/observations?${params.toString()}`));
      if (!resp.ok) throw new Error('Failed to fetch observations');
      const data = await resp.json();
      setObservations(data.observations || []);
    } catch (err) {
      setError(err.message || 'Error loading observations');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchObservations();
    }
  }, [isOpen, mineralFilter, statusFilter]);

  const handleSelectObservation = async (obsId) => {
    try {
      const resp = await fetch(getApiUrl(`/api/observations/${obsId}`));
      if (resp.ok) {
        const full = await resp.json();
        setSelectedObs(full);
        setComparisonData(null);
        setReviewStatus(full.verification_status);
        setReviewReason('');
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCompareWithModel = async (obsId) => {
    setIsComparing(true);
    try {
      const resp = await fetch(getApiUrl(`/api/observations/${obsId}/compare?radius_km=10`));
      if (resp.ok) {
        const comp = await resp.json();
        setComparisonData(comp);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsComparing(false);
    }
  };

  const handleUpdateStatus = async () => {
    if (!selectedObs || !reviewStatus) return;
    if (!reviewReason.trim()) {
      alert('Review rationale or audit note is required.');
      return;
    }

    setIsUpdatingStatus(true);
    try {
      const resp = await fetch(getApiUrl(`/api/observations/${selectedObs.id}/status`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': 'reviewer'
        },
        body: JSON.stringify({
          new_status: reviewStatus,
          changed_by: 'Authorized Reviewer',
          reason: reviewReason
        })
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Status transition failed.');
      }

      const resData = await resp.json();
      setSelectedObs(resData.observation);
      setReviewReason('');
      fetchObservations();
    } catch (err) {
      alert(err.message);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleExportGeoJSON = () => {
    window.open(getApiUrl('/api/observations/export/geojson'), '_blank');
  };

  if (!isOpen) return null;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'VERIFIED':
        return { bg: 'rgba(16, 185, 129, 0.15)', border: '#10b981', color: '#34d399' };
      case 'UNDER_REVIEW':
      case 'SUBMITTED':
        return { bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', color: '#fbbf24' };
      case 'REJECTED':
        return { bg: 'rgba(244, 63, 94, 0.15)', border: '#f43f5e', color: '#fda4af' };
      case 'NEEDS_MORE_EVIDENCE':
        return { bg: 'rgba(168, 85, 247, 0.15)', border: '#a855f7', color: '#d8b4fe' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.15)', border: '#94a3b8', color: '#cbd5e1' };
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(5px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9998,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: '#0a0f1d',
        border: '1px solid rgba(0, 240, 255, 0.3)',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '1050px',
        height: '88vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.85)',
        color: '#f8fafc',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{
          padding: '12px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.9)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <ShieldCheck size={22} color="#00f0ff" />
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800, color: '#f1f5f9' }}>
                Field Verification Feedback System
              </h3>
              <p style={{ margin: 0, fontSize: '0.72rem', color: '#94a3b8' }}>
                Ground-truth observations, scientific peer review, and spatial model feedback
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              type="button"
              onClick={handleExportGeoJSON}
              style={{
                padding: '6px 12px',
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                color: '#cbd5e1',
                fontSize: '0.74rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <Download size={13} />
              <span>Export GeoJSON</span>
            </button>
            <button
              type="button"
              onClick={onOpenCreateModal}
              style={{
                padding: '6px 14px',
                background: 'linear-gradient(135deg, #00f0ff, #0284c7)',
                border: 'none',
                borderRadius: '6px',
                color: '#0a0d14',
                fontWeight: 700,
                fontSize: '0.74rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <Plus size={14} />
              <span>Record Observation</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Filters Bar */}
        <div style={{
          padding: '10px 18px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
          display: 'flex',
          gap: 12,
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: '200px' }}>
            <Search size={14} color="#94a3b8" />
            <input
              type="text"
              placeholder="Search description, sample ID, observer..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchObservations()}
              style={{
                width: '100%',
                padding: '5px 8px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                borderRadius: '4px',
                color: '#fff',
                fontSize: '0.75rem'
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Mineral:</span>
            <select
              value={mineralFilter}
              onChange={e => setMineralFilter(e.target.value)}
              style={{ padding: '5px 8px', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255, 255, 255, 0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.74rem' }}
            >
              <option value="All">All Minerals</option>
              <option value="Manganese">Manganese</option>
              <option value="Iron Ore">Iron Ore</option>
              <option value="Coal">Coal</option>
              <option value="Bauxite">Bauxite</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Status:</span>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              style={{ padding: '5px 8px', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255, 255, 255, 0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.74rem' }}
            >
              <option value="All">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="UNDER_REVIEW">Under Review</option>
              <option value="VERIFIED">Verified</option>
              <option value="REJECTED">Rejected</option>
              <option value="NEEDS_MORE_EVIDENCE">Needs More Evidence</option>
            </select>
          </div>

          <button
            type="button"
            onClick={fetchObservations}
            style={{
              padding: '5px 8px',
              background: 'rgba(255, 255, 255, 0.06)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '4px',
              color: '#00f0ff',
              cursor: 'pointer'
            }}
          >
            <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Content Split: List on Left, Detail on Right */}
        <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', flex: 1, overflow: 'hidden' }}>
          {/* List Column */}
          <div style={{
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            overflowY: 'auto',
            padding: '10px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            background: 'rgba(10, 15, 26, 0.5)'
          }}>
            {isLoading && (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8', fontSize: '0.78rem' }}>
                <Loader2 size={20} className="animate-spin" style={{ margin: '0 auto 8px auto', color: '#00f0ff' }} />
                <span>Loading field observations...</span>
              </div>
            )}

            {!isLoading && observations.length === 0 && (
              <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: '#94a3b8', fontSize: '0.78rem' }}>
                <FileText size={24} style={{ margin: '0 auto 8px auto', color: '#64748b' }} />
                <div>No field observations found.</div>
                <button
                  type="button"
                  onClick={onOpenCreateModal}
                  style={{
                    marginTop: 10,
                    padding: '6px 12px',
                    background: 'rgba(0, 240, 255, 0.15)',
                    border: '1px solid #00f0ff',
                    borderRadius: '4px',
                    color: '#00f0ff',
                    fontSize: '0.72rem',
                    cursor: 'pointer'
                  }}
                >
                  + Add First Observation
                </button>
              </div>
            )}

            {!isLoading && observations.map(obs => {
              const b = getStatusBadge(obs.verification_status);
              const isSel = selectedObs?.id === obs.id;
              return (
                <div
                  key={obs.id}
                  onClick={() => handleSelectObservation(obs.id)}
                  style={{
                    padding: '9px 12px',
                    borderRadius: '6px',
                    background: isSel ? 'rgba(0, 240, 255, 0.12)' : 'rgba(0, 0, 0, 0.3)',
                    border: `1px solid ${isSel ? '#00f0ff' : 'rgba(255, 255, 255, 0.07)'}`,
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#f1f5f9', fontFamily: 'monospace' }}>
                      {obs.id}
                    </span>
                    <span style={{
                      fontSize: '0.6rem',
                      padding: '1px 5px',
                      borderRadius: '3px',
                      background: b.bg,
                      border: `1px solid ${b.border}`,
                      color: b.color,
                      fontWeight: 700
                    }}>
                      {obs.verification_status}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#00f0ff' }}>
                    <span>{obs.mineral} &bull; {obs.observation_type}</span>
                    {obs.sample_id && <span style={{ color: '#94a3b8' }}>{obs.sample_id}</span>}
                  </div>

                  <p style={{
                    margin: 0,
                    fontSize: '0.7rem',
                    color: '#cbd5e1',
                    lineHeight: 1.3,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden'
                  }}>
                    {obs.rock_soil_description}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#64748b', marginTop: 2 }}>
                    <span>{obs.latitude.toFixed(4)}°N, {obs.longitude.toFixed(4)}°E</span>
                    <span>{new Date(obs.observation_timestamp || obs.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Details Column */}
          <div style={{ overflowY: 'auto', padding: '16px 20px', background: 'rgba(15, 23, 42, 0.4)' }}>
            {!selectedObs ? (
              <div style={{ textAlign: 'center', padding: '4rem 2rem', color: '#94a3b8', fontSize: '0.82rem' }}>
                <Eye size={28} style={{ margin: '0 auto 8px auto', color: '#64748b' }} />
                <div>Select an observation from the list to inspect verified details, laboratory assays, photographs, and spatial model comparison.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {/* Header card */}
                <div style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start'
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: '0.95rem', fontWeight: 800, color: '#f8fafc', fontFamily: 'monospace' }}>
                        {selectedObs.id}
                      </span>
                      <span style={{
                        fontSize: '0.65rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        ...getStatusBadge(selectedObs.verification_status),
                        fontWeight: 700
                      }}>
                        {selectedObs.verification_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                      <b>Target:</b> <span style={{ color: '#00f0ff' }}>{selectedObs.mineral}</span> &bull; <b>Type:</b> {selectedObs.observation_type} &bull; <b>Sample ID:</b> {selectedObs.sample_id || 'None'}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: 4 }}>
                      <MapPin size={12} style={{ display: 'inline', marginRight: 4 }} />
                      <b>Coordinates:</b> {selectedObs.latitude.toFixed(5)}°N, {selectedObs.longitude.toFixed(5)}°E ({selectedObs.crs})
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 8 }}>
                    {onSelectObservationOnMap && (
                      <button
                        type="button"
                        onClick={() => onSelectObservationOnMap(selectedObs)}
                        style={{
                          padding: '6px 12px',
                          background: 'rgba(0, 240, 255, 0.15)',
                          border: '1px solid #00f0ff',
                          borderRadius: '6px',
                          color: '#00f0ff',
                          fontSize: '0.72rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 6
                        }}
                      >
                        <MapPin size={12} />
                        <span>View on Map</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Description & Characteristics */}
                <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>
                    Rock / Soil Description
                  </div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: '#f1f5f9', lineHeight: 1.4 }}>
                    {selectedObs.rock_soil_description}
                  </p>
                  {selectedObs.geological_characteristics && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>
                        Geological & Structural Characteristics
                      </div>
                      <p style={{ margin: 0, fontSize: '0.76rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                        {selectedObs.geological_characteristics}
                      </p>
                    </div>
                  )}
                </div>

                {/* Observer Attribution */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, fontSize: '0.74rem', background: 'rgba(0, 0, 0, 0.25)', padding: '10px', borderRadius: '6px' }}>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Observer:</span> <b>{selectedObs.observer_name}</b>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Organization:</span> <b>{selectedObs.observer_organization || 'Unspecified'}</b>
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Observation Date:</span> {new Date(selectedObs.observation_timestamp).toLocaleString()}
                  </div>
                  <div>
                    <span style={{ color: '#94a3b8' }}>Reviewed By:</span> {selectedObs.reviewed_by || 'Awaiting Reviewer'}
                  </div>
                </div>

                {/* Photographs */}
                {selectedObs.photos && selectedObs.photos.length > 0 && (
                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                    <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Camera size={14} color="#00f0ff" />
                      <span>Attached Field Photographs ({selectedObs.photos.length})</span>
                    </div>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {selectedObs.photos.map(p => (
                        <div key={p.id} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          <img
                            src={getApiUrl(`/api/observations/photos/${p.filename}`)}
                            alt={p.caption || 'Field photo'}
                            style={{ width: '130px', height: '100px', objectFit: 'cover', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.15)' }}
                          />
                          <span style={{ fontSize: '0.64rem', color: '#94a3b8', maxWidth: '130px' }}>
                            {p.caption || p.original_filename}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Laboratory Assays */}
                {selectedObs.assays && selectedObs.assays.length > 0 && (
                  <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                    <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                      <FlaskConical size={14} color="#00f0ff" />
                      <span>Laboratory Chemical Assays ({selectedObs.assays.length})</span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      {selectedObs.assays.map(a => (
                        <div key={a.id} style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          background: 'rgba(0, 240, 255, 0.08)',
                          padding: '6px 10px',
                          borderRadius: '4px',
                          fontSize: '0.74rem'
                        }}>
                          <span style={{ fontWeight: 700, color: '#f8fafc' }}>
                            {a.element_or_compound}: {a.value}{a.unit}
                          </span>
                          <span style={{ color: '#94a3b8' }}>
                            {a.laboratory_name || 'Independent Assay'} &bull; {a.report_reference || 'Cert on file'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Spatial Model Comparison Button & View */}
                <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(0, 240, 255, 0.25)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Activity size={15} color="#00f0ff" />
                      <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f1f5f9' }}>
                        Spatial Model vs Field Observation Feedback
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCompareWithModel(selectedObs.id)}
                      disabled={isComparing}
                      style={{
                        padding: '4px 10px',
                        background: 'rgba(0, 240, 255, 0.2)',
                        border: '1px solid #00f0ff',
                        borderRadius: '4px',
                        color: '#00f0ff',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        cursor: isComparing ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {isComparing ? 'Comparing...' : 'Run Spatial Comparison'}
                    </button>
                  </div>

                  {comparisonData && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.72rem', marginTop: 8 }}>
                      <div style={{ background: 'rgba(0, 0, 0, 0.3)', padding: '8px', borderRadius: '4px', color: '#cbd5e1' }}>
                        <b>Synthesis:</b> {comparisonData.comparison_synthesis}
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '6px', borderRadius: '4px' }}>
                          <span style={{ color: '#94a3b8' }}>Model Name:</span> {comparisonData.model_comparison?.model_name}
                        </div>
                        <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '6px', borderRadius: '4px' }}>
                          <span style={{ color: '#94a3b8' }}>Model Classification:</span> {comparisonData.model_comparison?.classification}
                        </div>
                      </div>
                      <div style={{ color: '#fbbf24', fontSize: '0.68rem' }}>
                        <b>Training Policy:</b> {comparisonData.training_curation_policy?.disclaimer}
                      </div>
                    </div>
                  )}
                </div>

                {/* Reviewer Status Workflow Form */}
                <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                  <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f1f5f9', marginBottom: 8 }}>
                    Peer Review & Status Transition
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr auto', gap: 8 }}>
                    <select
                      value={reviewStatus}
                      onChange={e => setReviewStatus(e.target.value)}
                      style={{ padding: '6px 8px', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.74rem' }}
                    >
                      <option value="DRAFT">DRAFT</option>
                      <option value="SUBMITTED">SUBMITTED</option>
                      <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                      <option value="VERIFIED">VERIFIED</option>
                      <option value="REJECTED">REJECTED</option>
                      <option value="NEEDS_MORE_EVIDENCE">NEEDS_MORE_EVIDENCE</option>
                    </select>

                    <input
                      type="text"
                      placeholder="Audit note / review rationale..."
                      value={reviewReason}
                      onChange={e => setReviewReason(e.target.value)}
                      style={{ padding: '6px 10px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.74rem' }}
                    />

                    <button
                      type="button"
                      onClick={handleUpdateStatus}
                      disabled={isUpdatingStatus}
                      style={{
                        padding: '6px 14px',
                        background: 'rgba(16, 185, 129, 0.2)',
                        border: '1px solid #10b981',
                        borderRadius: '4px',
                        color: '#34d399',
                        fontWeight: 700,
                        fontSize: '0.72rem',
                        cursor: isUpdatingStatus ? 'not-allowed' : 'pointer'
                      }}
                    >
                      {isUpdatingStatus ? 'Saving...' : 'Update Status'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
