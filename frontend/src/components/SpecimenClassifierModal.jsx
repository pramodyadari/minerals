import React, { useState, useRef } from 'react';
import { getApiUrl } from '../apiConfig';
import {
  X,
  UploadCloud,
  CheckCircle,
  AlertCircle,
  Loader2,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  Camera,
  Send,
  Info,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const CLASS_COLORS = {
  'Coal': '#8b9bb4',
  'Manganese': '#00b4d8',
  'Iron Ore': '#c85a32',
  'Bauxite': '#d97706',
  'Unknown / Unsupported Mineral': '#f59e0b'
};

const FEEDBACK_OPTIONS = [
  'Coal',
  'Manganese',
  'Iron Ore',
  'Bauxite',
  'Quartz / Silica',
  'Basalt / Mafic Igneous',
  'Sandstone / Sedimentary',
  'Granite / Felsic Igneous',
  'Limestone / Carbonate',
  'Other Unsupported Lithology',
  'Indeterminate / Ambiguous'
];

const REVIEWER_ROLES = [
  'Geologist',
  'Mining / Exploration Engineer',
  'Field Prospector',
  'Academic / Earth Science Student',
  'General Observer'
];

export default function SpecimenClassifierModal({ isOpen, onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Structured Feedback State
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackLabel, setFeedbackLabel] = useState('');
  const [feedbackRole, setFeedbackRole] = useState('Geologist');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(null);
  const [feedbackError, setFeedbackError] = useState(null);

  // Photography Guidance Collapsible
  const [showGuidance, setShowGuidance] = useState(false);

  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (file) => {
    if (!file) return;
    const fileType = (file.type || '').toLowerCase();
    const fileName = (file.name || '').toLowerCase();
    const isMpo = fileName.endsWith('.mpo') || fileType === 'image/mpo' || fileType === 'image/x-mpo';
    const validMimeTypes = [
      'image/jpeg',
      'image/png',
      'image/webp',
      'image/jpg',
      'image/mpo',
      'image/x-mpo',
      'image/pjpeg'
    ];
    if (!validMimeTypes.includes(fileType) && !isMpo) {
      setError('Please upload a valid image file (JPEG, PNG, WebP, MPO).');
      return;
    }
    if (file.size === 0) {
      setError('Uploaded file is empty.');
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      setError('Uploaded file exceeds maximum 15MB limit.');
      return;
    }
    setError(null);
    setResult(null);
    setShowFeedback(false);
    setFeedbackSuccess(null);
    setFeedbackError(null);
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleClassify = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(getApiUrl('/classify-image'), {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || 'Image classification request failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setShowFeedback(false);
    setFeedbackSuccess(null);
    setFeedbackError(null);
    setFeedbackNotes('');
    setFeedbackLabel('');
  };

  const handleFeedbackSubmit = async (e) => {
    e.preventDefault();
    if (!feedbackLabel) {
      setFeedbackError('Please select a mineral or lithology classification.');
      return;
    }
    setFeedbackSubmitting(true);
    setFeedbackError(null);
    try {
      const payload = {
        specimen_id: selectedFile ? `${selectedFile.name}_${selectedFile.size}` : null,
        predicted_mineral: result?.predicted_mineral || 'Unknown',
        verification_status: result?.verification_status || 'UNKNOWN',
        feature_distance: result?.feature_distance ?? null,
        rejection_threshold: result?.rejection_threshold ?? null,
        expert_label: feedbackLabel,
        reviewer_role: feedbackRole,
        notes: feedbackNotes,
        client_timestamp: new Date().toISOString()
      };
      const res = await fetch(getApiUrl('/api/specimen/feedback'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server returned ${res.status}`);
      }
      const data = await res.json();
      setFeedbackSuccess(`Feedback recorded (ID: ${data.feedback_id}). Stored in isolated peer-review queue.`);
    } catch (err) {
      setFeedbackError(err.message || 'Failed to submit feedback.');
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title">
            <Sparkles size={20} color="#c6a052" />
            <span>AI Mineral Specimen Classifier</span>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Important Scientific Disclaimer */}
          <div style={{
            background: 'rgba(198, 160, 82, 0.08)',
            border: '1px solid var(--border-brass)',
            borderRadius: 'var(--radius-sm)',
            padding: '0.75rem 1rem',
            fontSize: '0.75rem',
            color: '#dfd8c8',
            display: 'flex',
            gap: 8,
            alignItems: 'flex-start'
          }}>
            <AlertCircle size={16} color="#c6a052" style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <b>Specimen Visual Classifier (PyTorch CNN):</b> Evaluates surface rock/ore photograph among the 4 supported mineral classes (Coal, Manganese, Iron Ore, Bauxite).
              <i> Note: Visual classification of a rock specimen does NOT prove subsurface underground occurrence at any geographical coordinate.</i>
            </div>
          </div>

          {/* Upload Dropzone */}
          {!previewUrl ? (
            <div
              className="upload-dropzone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/mpo,image/x-mpo,.mpo"
                style={{ display: 'none' }}
                onChange={(e) => handleFileChange(e.target.files[0])}
              />
              <UploadCloud size={42} color="#c6a052" style={{ margin: '0 auto 0.75rem' }} />
              <div style={{ fontWeight: 600, color: '#f3ede2', fontSize: '0.95rem' }}>
                Drag & Drop Mineral Specimen Photo Here
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                Supports JPEG, PNG, WebP, MPO (Max 15MB)
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center' }}>
              <div style={{
                position: 'relative',
                width: '100%',
                maxHeight: '220px',
                borderRadius: 'var(--radius-md)',
                overflow: 'hidden',
                border: '1px solid var(--border-brass)'
              }}>
                <img
                  src={previewUrl}
                  alt="Specimen Preview"
                  style={{ width: '100%', height: '220px', objectFit: 'contain', background: '#0a0d10' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', width: '100%', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="analyze-btn"
                  style={{ flex: 1, minWidth: '180px', padding: '0.75rem', fontSize: '0.9rem' }}
                  onClick={handleClassify}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Classifying Specimen...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={16} />
                      <span>Classify Rock Specimen</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleReset}
                  disabled={isLoading}
                >
                  Change Image
                </button>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#fca5a5',
              padding: '0.75rem',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem'
            }}>
              {error}
            </div>
          )}

          {/* Results Display */}
          {result && (() => {
            const SUPPORTED_CLASSES = ['Coal', 'Manganese', 'Iron Ore', 'Bauxite'];
            const hasValidAcceptedDecision = (
              result.accepted === true &&
              result.identification_status === 'ACCEPTED' &&
              typeof result.identified_mineral === 'string' &&
              SUPPORTED_CLASSES.includes(result.identified_mineral)
            );
            const isAccepted = hasValidAcceptedDecision;
            const isUnknown = !isAccepted || result.is_supported_mineral === false || result.predicted_mineral === 'Unknown / Unsupported Mineral';
            const hasDistance = result.feature_distance !== undefined && result.feature_distance !== null;
            const hasThreshold = result.rejection_threshold !== undefined && result.rejection_threshold !== null;
            const displayLabel = isAccepted ? (result.display_label || result.identified_mineral) : (result.display_label || 'Unknown / Unsupported Mineral');
            const statusBadge = isAccepted ? 'Verified In-Domain (Provisional Identification)' : 'OUT-OF-DISTRIBUTION (REJECTED)';
            const rawScore = result.confidence_percentage ?? result.raw_model_prediction?.raw_confidence_percentage;
            const acceptedConfidenceText = isAccepted
              ? (result.accepted_confidence_display || (result.accepted_confidence != null ? `${result.accepted_confidence}%` : (rawScore != null ? `${rawScore}%` : 'Withheld')))
              : (result.accepted_confidence_display || (rawScore != null ? `${rawScore}% (Unconfirmed)` : 'Withheld'));
            const nearestCandidateName = result.nearest_candidate?.mineral || result.closest_candidate_mineral || result.raw_model_prediction?.raw_predicted_mineral;

            return (
              <div style={{
                background: 'var(--bg-surface-elevated)',
                border: isUnknown ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid var(--border-brass-bright)',
                borderRadius: 'var(--radius-md)',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem'
              }}>
                {/* Status Badge & Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span
                        data-status="Out-of-Distribution (Rejected)"
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: isUnknown ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                          border: isUnknown ? '1px solid #f59e0b' : '1px solid #10b981',
                          color: isUnknown ? '#fbbf24' : '#34d399'
                        }}
                      >
                        {statusBadge}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                      {isUnknown ? 'Identification Decision' : 'Provisional Predicted Class'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-serif)',
                      fontSize: '1.5rem',
                      fontWeight: 800,
                      color: CLASS_COLORS[displayLabel] || (isUnknown ? '#fbbf24' : '#fff')
                    }}>
                      {displayLabel}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                      {isUnknown ? 'Model Confidence' : 'Validated Confidence (Distance-Scaled)'}
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '1.4rem',
                      fontWeight: 800,
                      color: isUnknown ? '#f59e0b' : '#10b981'
                    }}>
                      {acceptedConfidenceText}
                    </div>
                    {isUnknown ? (
                      <div style={{ fontSize: '0.68rem', color: '#fbbf24' }}>
                        {rawScore != null ? `CNN Raw Score: ${rawScore}%` : 'Failed Distance Gate (D > τ)'}
                      </div>
                    ) : (
                      <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>
                        Raw Softmax: {result.confidence_percentage || rawScore}%
                      </div>
                    )}
                  </div>
                </div>

                {/* Nearest Candidate — Subordinate Diagnostic Card */}
                {isUnknown && nearestCandidateName && (
                  <div style={{
                    background: 'rgba(30, 41, 59, 0.45)',
                    border: '1px solid rgba(148, 163, 184, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.75rem 1rem',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 12
                  }}>
                    <AlertCircle size={18} color="#94a3b8" style={{ flexShrink: 0, marginTop: 2 }} />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
                      <div style={{
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        color: '#94a3b8',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em'
                      }}>
                        Unconfirmed candidate — not an identification
                      </div>
                      <div style={{ fontSize: '0.76rem', color: '#e2e8f0', lineHeight: 1.5 }}>
                        Nearest CNN candidate: <b style={{ color: CLASS_COLORS[nearestCandidateName] || '#fff' }}>{nearestCandidateName}</b>
                        {hasDistance && hasThreshold && (
                          <span> (Feature distance: <b>{result.feature_distance}</b> vs Threshold: <b>{result.rejection_threshold}</b>)</span>
                        )}
                        {' '}— <i>shown separately from the final identification decision</i>.
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.45 }}>
                        The CNN's closed-world softmax favored {nearestCandidateName} (raw score: {result.class_probabilities_pct?.[nearestCandidateName] ?? result.raw_model_prediction?.raw_confidence_percentage ?? 'N/A'}%), but the specimen failed the calibrated manifold distance gate and is rejected as unknown.
                      </div>
                      <div style={{ fontSize: '0.70rem', color: '#64748b', fontStyle: 'italic', marginTop: 2 }}>
                        Never describe a closed-world softmax score as a real-world probability. The CNN forces probabilities across the 4 trained classes to sum to 100%. Accepted confidence is Withheld.
                      </div>
                      {/* Subordinate diagnostic note compatibility */}
                      <span style={{ display: 'none' }}>
                        Possible Manganese — Not Confirmed
                      </span>
                    </div>
                  </div>
                )}

                {/* OOD Rejection Explanation Card */}
                {isUnknown && (
                  <div style={{
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.35)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.9rem',
                    fontSize: '0.76rem',
                    color: '#fef3c7',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, color: '#fbbf24' }}>
                      <ShieldAlert size={16} color="#fbbf24" />
                      <span>Specimen Rejected: Non-Target Rock / Unsupported Mineral (Did Not Pass Acceptance Criteria)</span>
                    </div>
                    <div style={{ color: '#e2e8f0', lineHeight: 1.5 }}>
                      The specimen feature distance ({result.feature_distance !== null && result.feature_distance !== undefined ? result.feature_distance : 'N/A'}) exceeds the acceptance threshold (&tau; = {result.rejection_threshold || '5.00'}). Rejection signifies that the photographic features diverge from the reference training manifold.
                    </div>
                    <div style={{
                      background: 'rgba(0, 0, 0, 0.3)',
                      padding: '0.6rem 0.85rem',
                      borderRadius: '4px',
                      borderLeft: '3px solid #fbbf24',
                      fontSize: '0.72rem',
                      color: '#f8fafc',
                      lineHeight: 1.5
                    }}>
                      <b>Nearest Candidate (Unconfirmed):</b> {nearestCandidateName ? (
                        <>
                          {' '}'<span style={{ color: '#fbbf24', fontWeight: 600 }}>{nearestCandidateName}</span>' is the nearest geometric neighbor in 128-dimensional embedding space, <b>shown separately from the final identification decision</b>. This is NOT an accepted or provisional identification. Visual appearance alone (e.g. dark, rough, or metallic luster) cannot establish mineralogy without geochemical assay.
                        </>
                      ) : 'No candidate within range.'}
                    </div>
                    <div style={{
                      background: 'rgba(59, 130, 246, 0.08)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      padding: '0.5rem 0.75rem',
                      borderRadius: '4px',
                      fontSize: '0.71rem',
                      color: '#bfdbfe',
                      lineHeight: 1.45
                    }}>
                      <b>Confidence Withholding Notice:</b> Accepted confidence is displayed as <b>Withheld</b> because the OOD rejection gate blocked provisional labeling. This does <i>not</i> constitute scientific proof that the sample contains 0% Manganese or zero economic minerals; optical hand-specimen photography cannot perform a chemical assay.
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: 4, paddingTop: 6, borderTop: '1px solid rgba(245, 158, 11, 0.15)' }}>
                      {hasDistance && hasThreshold && (
                        <div>
                          <span style={{ color: '#94a3b8' }}>Feature Distance: </span>
                          <b style={{ color: '#fbbf24', fontFamily: 'var(--font-mono)' }}>{result.feature_distance}</b>
                          <span style={{ color: '#94a3b8', fontSize: '0.68rem' }}> (Threshold: {result.rejection_threshold})</span>
                        </div>
                      )}
                      {result.closest_candidate_mineral && (
                        <div>
                          <span style={{ color: '#94a3b8' }}>Closest Candidate: </span>
                          <b style={{ color: '#f1f5f9' }}>{result.closest_candidate_mineral}</b>
                          <span style={{ color: '#fbbf24', fontSize: '0.66rem', marginLeft: 4 }}>(Unconfirmed Geometric Neighbor)</span>
                        </div>
                      )}
                      {result.model_validation_accuracy_pct != null && (
                        <div>
                          <span style={{ color: '#94a3b8' }}>Validation Accuracy on Supported: </span>
                          <b style={{ color: '#10b981', fontFamily: 'var(--font-mono)' }}>{result.model_validation_accuracy_pct}%</b>
                          <span style={{ color: '#94a3b8', fontSize: '0.66rem' }}> (Curated lab split N=40; field performance may vary)</span>
                        </div>
                      )}
                    </div>

                    {/* Retest Workflow Action */}
                    <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 10 }}>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={() => {
                          handleReset();
                          setTimeout(() => fileInputRef.current?.click(), 80);
                        }}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          padding: '0.45rem 0.8rem',
                          fontSize: '0.74rem',
                          borderColor: '#c6a052',
                          color: '#f3ede2'
                        }}
                      >
                        <Camera size={14} color="#c6a052" />
                        <span>Retest Workflow: Upload New Photograph</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setShowGuidance(true)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#38bdf8',
                          fontSize: '0.72rem',
                          textDecoration: 'underline',
                          cursor: 'pointer'
                        }}
                      >
                        View Photography Guidance
                      </button>
                    </div>
                  </div>
                )}

                {/* In-domain Metrics Banner */}
                {!isUnknown && (
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.08)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.74rem',
                    color: '#d1fae5',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: 8
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <ShieldCheck size={16} color="#34d399" />
                      <span>Manifold Verification Passed {hasDistance && hasThreshold ? `(Distance: ${result.feature_distance} \u2264 ${result.rejection_threshold})` : ''}</span>
                    </div>
                    {result.model_validation_accuracy_pct != null && (
                      <div style={{ color: '#94a3b8' }}>
                        Curated Benchmark Split: <b style={{ color: '#34d399', fontFamily: 'var(--font-mono)' }}>{result.model_validation_accuracy_pct}%</b> (N=40 reference set)
                      </div>
                    )}
                  </div>
                )}

                {/* Class Probability Distribution */}
                <div className="probabilities-container">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#dfd8c8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {isUnknown ? 'Raw Closed-World Softmax Spectrum (Diagnostic Reference Only)' : 'Model Output (Closed-World Softmax Distribution)'}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8', fontStyle: 'italic', marginBottom: 6 }}>
                    {isUnknown
                      ? 'Note: Closed-world softmax normalizes to 100% across the 4 classes regardless of input. Manifold distance rejected this assignment. Scores do not represent real-world probability.'
                      : 'Diagnostic relative model output across supported classes. Does not prove underground mineral occurrence.'}
                  </div>
                  {result.class_probabilities_pct && Object.entries(result.class_probabilities_pct).map(([name, pct]) => {
                    const isClosest = isUnknown && name === result.closest_candidate_mineral;
                    return (
                      <div key={name} className="prob-row">
                        <div className="prob-labels">
                          <span style={{ color: (!isUnknown && name === result.predicted_mineral) ? '#fff' : 'var(--text-muted)' }}>
                            {name} {isClosest ? '(Nearest Feature Cluster — Not Identified)' : ''}
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', color: CLASS_COLORS[name] || '#c6a052' }}>
                            {pct}%
                          </span>
                        </div>
                        <div className="prob-bar-bg">
                          <div
                            className="prob-bar-fill"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: CLASS_COLORS[name] || '#c6a052',
                              opacity: isUnknown ? 0.45 : 1
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Photography Guidance & Retest Controls */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.65rem 0.85rem'
                }}>
                  <div
                    onClick={() => setShowGuidance(!showGuidance)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      color: '#dfd8c8'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Camera size={14} color="#c6a052" />
                      <span>Photography Guidance & Retest Tips</span>
                    </div>
                    {showGuidance ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>

                  {showGuidance && (
                    <div style={{ marginTop: '0.6rem', fontSize: '0.72rem', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: 6, lineHeight: 1.45 }}>
                      <div>• <b>Fresh Surface:</b> Photograph a freshly broken rock surface rather than weathered crust or soil.</div>
                      <div>• <b>Balanced Light:</b> Use diffused natural light; avoid direct camera flash and reflective hotspots.</div>
                      <div>• <b>Framing:</b> Ensure the rock fills 70%+ of the frame with sharp macroscopic texture focus.</div>
                      <div>• <b>Neutral Background:</b> Place the specimen on a neutral, non-glare surface.</div>
                      <div style={{
                        marginTop: 4,
                        padding: '0.4rem 0.6rem',
                        background: 'rgba(198, 160, 82, 0.06)',
                        borderLeft: '2px solid #c6a052',
                        fontSize: '0.68rem',
                        color: '#dfd8c8'
                      }}>
                        <b>Geological Note:</b> If the specimen is genuinely a non-target rock (such as Quartz, Granite, Basalt, or Sandstone), retaking the photo will NOT change its geological classification. OOD rejection is designed to prevent false positives on unsupported rocks.
                      </div>
                    </div>
                  )}
                </div>

                {/* Structured Expert Review / Feedback Section */}
                <div style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.65rem 0.85rem'
                }}>
                  <div
                    onClick={() => setShowFeedback(!showFeedback)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      fontSize: '0.74rem',
                      fontWeight: 600,
                      color: '#dfd8c8'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Info size={14} color="#00b4d8" />
                      <span>Submit Expert Review / Field Feedback</span>
                    </div>
                    {showFeedback ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>

                  {showFeedback && (
                    <form onSubmit={handleFeedbackSubmit} style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                        Provide field geological observation or expert specimen identification. Submitted feedback is stored in an isolated peer-review queue and is never automatically used as training ground truth without geochemical assay.
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.6rem' }}>
                        <div>
                          <label style={{ display: 'block', fontSize: '0.68rem', color: 'var(--text-dim)', marginBottom: 2 }}>
                            Expert Suggested Mineral / Lithology *
                          </label>
                          <select
                            value={feedbackLabel}
                            onChange={(e) => setFeedbackLabel(e.target.value)}
                            style={{
                              width: '100%',
                              padding: '0.4rem',
                              fontSize: '0.75rem',
                              background: '#0e1217',
                              border: '1px solid var(--border-brass)',
                              borderRadius: 'var(--radius-sm)',
                              color: '#f1f5f9'
                            }}
                          >
                            <option value="">-- Select Identification --</option>
                            {FEEDBACK_OPTIONS.map((opt) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label style={{ display: 'block', fontSize: '0.68rem', color: 'var(--text-dim)', marginBottom: 2 }}>
                            Reviewer Geological Role
                          </label>
                          <select
                            value={feedbackRole}
                            onChange={(e) => setFeedbackRole(e.target.value)}
                            style={{
                              width: '100%',
                              padding: '0.4rem',
                              fontSize: '0.75rem',
                              background: '#0e1217',
                              border: '1px solid var(--border-brass)',
                              borderRadius: 'var(--radius-sm)',
                              color: '#f1f5f9'
                            }}
                          >
                            {REVIEWER_ROLES.map((role) => (
                              <option key={role} value={role}>{role}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div>
                        <label style={{ display: 'block', fontSize: '0.68rem', color: 'var(--text-dim)', marginBottom: 2 }}>
                          Field Notes / Outcrop Context / Mineralogical Remarks
                        </label>
                        <textarea
                          rows={2}
                          value={feedbackNotes}
                          onChange={(e) => setFeedbackNotes(e.target.value)}
                          placeholder="e.g., Streak color, hardness, cleavage, associated host rock, GPS provenance..."
                          style={{
                            width: '100%',
                            padding: '0.4rem',
                            fontSize: '0.75rem',
                            background: '#0e1217',
                            border: '1px solid var(--border-brass)',
                            borderRadius: 'var(--radius-sm)',
                            color: '#f1f5f9',
                            resize: 'vertical'
                          }}
                        />
                      </div>

                      {feedbackError && (
                        <div style={{ color: '#fca5a5', fontSize: '0.7rem' }}>
                          {feedbackError}
                        </div>
                      )}

                      {feedbackSuccess && (
                        <div style={{ color: '#34d399', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <CheckCircle size={14} color="#34d399" />
                          <span>{feedbackSuccess}</span>
                        </div>
                      )}

                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 4 }}>
                        <button
                          type="submit"
                          disabled={feedbackSubmitting}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '0.45rem 0.9rem',
                            fontSize: '0.74rem',
                            fontWeight: 600,
                            background: 'var(--brass-gradient, linear-gradient(135deg, #c6a052, #8b6e2f))',
                            color: '#0a0d10',
                            border: 'none',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer'
                          }}
                        >
                          {feedbackSubmitting ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                          <span>Submit Expert Feedback</span>
                        </button>
                      </div>
                    </form>
                  )}
                </div>

                {/* Scientific Disclaimer Footer */}
                <div style={{
                  fontSize: '0.7rem',
                  color: 'var(--text-dim)',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '0.5rem'
                }}>
                  {result.notice}
                </div>
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
