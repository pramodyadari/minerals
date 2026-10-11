import React, { useState, useRef } from 'react';
import { X, UploadCloud, CheckCircle, AlertCircle, Loader2, Sparkles, Image as ImageIcon } from 'lucide-react';

const CLASS_COLORS = {
  'Coal': '#8b9bb4',
  'Manganese': '#00b4d8',
  'Iron Ore': '#c85a32',
  'Bauxite': '#d97706'
};

export default function SpecimenClassifierModal({ isOpen, onClose }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileChange = (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setError('Please upload a valid image file (JPEG, PNG, WebP).');
      return;
    }
    setError(null);
    setResult(null);
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
      const response = await fetch('http://127.0.0.1:8000/classify-image', {
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
              <b>Specimen Visual Classifier (PyTorch CNN):</b> Evaluates surface rock/ore photograph among the 4 mineral classes. 
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
                accept="image/*"
                style={{ display: 'none' }}
                onChange={(e) => handleFileChange(e.target.files[0])}
              />
              <UploadCloud size={42} color="#c6a052" style={{ margin: '0 auto 0.75rem' }} />
              <div style={{ fontWeight: 600, color: '#f3ede2', fontSize: '0.95rem' }}>
                Drag & Drop Mineral Specimen Photo Here
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                Supports JPEG, PNG, WebP (Max 15MB)
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

              <div style={{ display: 'flex', gap: '0.75rem', width: '100%' }}>
                <button
                  type="button"
                  className="analyze-btn"
                  style={{ flex: 1, padding: '0.75rem', fontSize: '0.9rem' }}
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
          {result && (
            <div style={{
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-brass-bright)',
              borderRadius: 'var(--radius-md)',
              padding: '1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                    Predicted Mineral Class
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-serif)',
                    fontSize: '1.6rem',
                    fontWeight: 800,
                    color: CLASS_COLORS[result.predicted_mineral] || '#fff'
                  }}>
                    {result.predicted_mineral}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>
                    Model Confidence
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.6rem', fontWeight: 800, color: '#10b981' }}>
                    {result.confidence_percentage}%
                  </div>
                </div>
              </div>

              {/* Class Probability Distribution */}
              <div className="probabilities-container">
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#dfd8c8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  4-Class Probability Spectrum
                </div>
                {result.class_probabilities_pct && Object.entries(result.class_probabilities_pct).map(([name, pct]) => (
                  <div key={name} className="prob-row">
                    <div className="prob-labels">
                      <span style={{ color: name === result.predicted_mineral ? '#fff' : 'var(--text-muted)' }}>
                        {name}
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
                          backgroundColor: CLASS_COLORS[name] || '#c6a052'
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div style={{
                fontSize: '0.7rem',
                color: 'var(--text-dim)',
                borderTop: '1px solid var(--border-subtle)',
                paddingTop: '0.5rem'
              }}>
                {result.notice}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
