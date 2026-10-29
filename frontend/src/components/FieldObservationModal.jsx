import React, { useState } from 'react';
import { getApiUrl } from '../apiConfig';
import {
  X,
  MapPin,
  Camera,
  Upload,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileText,
  User,
  Building,
  Calendar,
  Layers,
  FlaskConical,
  Plus,
  Trash2
} from 'lucide-react';

export default function FieldObservationModal({
  isOpen,
  onClose,
  initialLocation,
  initialMineral = 'Manganese',
  analysisId,
  onObservationCreated
}) {
  const [formData, setFormData] = useState({
    latitude: initialLocation?.lat || 21.9048,
    longitude: initialLocation?.lon || 80.1849,
    crs: 'EPSG:4326 - WGS 84',
    mineral: initialMineral,
    observation_type: 'outcrop',
    sample_id: '',
    rock_soil_description: '',
    geological_characteristics: '',
    observer_name: '',
    observer_organization: '',
    verification_status: 'DRAFT',
    status_notes: '',
    general_notes: ''
  });

  // Photo state
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [photoCaption, setPhotoCaption] = useState('');

  // Lab assay state
  const [assays, setAssays] = useState([]);
  const [newAssay, setNewAssay] = useState({
    element_or_compound: 'Mn',
    value: '',
    unit: '%',
    laboratory_name: '',
    report_reference: ''
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: (name === 'latitude' || name === 'longitude') ? parseFloat(value) || value : value
    }));
  };

  const handlePhotoSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      setError('Photo exceeds 10MB limit.');
      return;
    }

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Only JPEG, PNG, or WebP images are allowed.');
      return;
    }

    setSelectedPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
    setError(null);
  };

  const handleAddAssay = () => {
    if (!newAssay.element_or_compound || newAssay.value === '') {
      setError('Please provide both analyte and value for laboratory assay.');
      return;
    }
    const val = parseFloat(newAssay.value);
    if (isNaN(val)) {
      setError('Assay value must be a valid number.');
      return;
    }

    setAssays(prev => [...prev, { ...newAssay, value: val }]);
    setNewAssay({
      element_or_compound: formData.mineral === 'Iron Ore' ? 'Fe' : formData.mineral === 'Bauxite' ? 'Al2O3' : 'Mn',
      value: '',
      unit: '%',
      laboratory_name: '',
      report_reference: ''
    });
    setError(null);
  };

  const handleRemoveAssay = (index) => {
    setAssays(prev => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    // Validation
    if (!formData.rock_soil_description.trim()) {
      setError('Rock or soil description is mandatory.');
      return;
    }
    if (!formData.observer_name.trim()) {
      setError('Observer name / attribution is required.');
      return;
    }
    if (formData.latitude < -90 || formData.latitude > 90) {
      setError('Latitude must be between -90 and 90.');
      return;
    }
    if (formData.longitude < -180 || formData.longitude > 180) {
      setError('Longitude must be between -180 and 180.');
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        ...formData,
        analysis_id: analysisId || null,
        assays: assays.length > 0 ? assays : undefined
      };

      const resp = await fetch(getApiUrl('/api/observations'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': 'geologist'
        },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned HTTP ${resp.status}`);
      }

      const created = await resp.json();
      const obsId = created.observation.id;

      // Upload photo if selected
      if (selectedPhoto) {
        const photoForm = new FormData();
        photoForm.append('file', selectedPhoto);
        if (photoCaption) {
          photoForm.append('caption', photoCaption);
        }

        const photoResp = await fetch(getApiUrl(`/api/observations/${obsId}/photos`), {
          method: 'POST',
          body: photoForm
        });

        if (!photoResp.ok) {
          console.warn('Observation created but photo upload encountered error.');
        }
      }

      setSuccessMsg(`Observation ${obsId} successfully recorded and persisted!`);
      if (onObservationCreated) {
        onObservationCreated(created.observation);
      }

      setTimeout(() => {
        onClose();
      }, 1500);

    } catch (err) {
      setError(err.message || 'Failed to submit observation.');
    } finally {
      setIsSubmitting(false);
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
      zIndex: 9999,
      padding: '1rem'
    }}>
      <div style={{
        backgroundColor: '#0a0f1d',
        border: '1px solid rgba(0, 240, 255, 0.3)',
        borderRadius: '12px',
        width: '100%',
        maxWidth: '680px',
        maxHeight: '90vh',
        overflowY: 'auto',
        boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8)',
        color: '#f8fafc'
      }}>
        {/* Header */}
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.8)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <MapPin size={20} color="#00f0ff" />
            <div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
                Record Field Verification Observation
              </h3>
              <p style={{ margin: 0, fontSize: '0.72rem', color: '#94a3b8' }}>
                Capture real ground observations separate from model predictions
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          {error && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: '6px',
              padding: '8px 12px',
              color: '#fca5a5',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              <AlertTriangle size={16} color="#ef4444" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div style={{
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid #10b981',
              borderRadius: '6px',
              padding: '8px 12px',
              color: '#34d399',
              fontSize: '0.78rem',
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              <CheckCircle2 size={16} color="#10b981" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Coordinates & CRS */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Latitude (°N) *
              </label>
              <input
                type="number"
                step="any"
                name="latitude"
                value={formData.latitude}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Longitude (°E) *
              </label>
              <input
                type="number"
                step="any"
                name="longitude"
                value={formData.longitude}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Spatial Datum (CRS)
              </label>
              <input
                type="text"
                name="crs"
                value={formData.crs}
                readOnly
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '6px',
                  color: '#94a3b8',
                  fontSize: '0.76rem'
                }}
              />
            </div>
          </div>

          {/* Mineral & Observation Type & Sample ID */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Target Mineral *
              </label>
              <select
                name="mineral"
                value={formData.mineral}
                onChange={handleChange}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(0, 240, 255, 0.4)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              >
                <option value="Manganese">Manganese</option>
                <option value="Iron Ore">Iron Ore</option>
                <option value="Coal">Coal</option>
                <option value="Bauxite">Bauxite</option>
                <option value="Other">Other Material</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Observation Type *
              </label>
              <select
                name="observation_type"
                value={formData.observation_type}
                onChange={handleChange}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(15, 23, 42, 0.9)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              >
                <option value="outcrop">Outcrop / Cliff</option>
                <option value="rock_sample">Rock Hand-Sample</option>
                <option value="soil_sample">Soil Sample</option>
                <option value="drill_core">Drill / Core Record</option>
                <option value="trench_exposure">Trench / Working</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Sample Tag / ID
              </label>
              <input
                type="text"
                name="sample_id"
                placeholder="e.g. SMP-2026-042"
                value={formData.sample_id}
                onChange={handleChange}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              />
            </div>
          </div>

          {/* Description & Geological Characteristics */}
          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
              Rock / Soil Physical Description *
            </label>
            <textarea
              name="rock_soil_description"
              rows={2}
              placeholder="e.g. Dark metallic steel-gray crystalline braunite bands intercalated with gonditic quartzite..."
              value={formData.rock_soil_description}
              onChange={handleChange}
              required
              style={{
                width: '100%',
                padding: '8px 10px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '0.78rem',
                resize: 'vertical'
              }}
            />
          </div>

          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
              Observed Geological & Structural Characteristics
            </label>
            <textarea
              name="geological_characteristics"
              rows={2}
              placeholder="e.g. Strike N65E, dip 70° NW; gossanous oxidation cap with secondary pyrolusite coatings..."
              value={formData.geological_characteristics}
              onChange={handleChange}
              style={{
                width: '100%',
                padding: '8px 10px',
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                color: '#fff',
                fontSize: '0.78rem',
                resize: 'vertical'
              }}
            />
          </div>

          {/* Observer Attribution */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Observer Name / Geologist Attribution *
              </label>
              <input
                type="text"
                name="observer_name"
                placeholder="e.g. Dr. A. Sharma"
                value={formData.observer_name}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
                Organization / Exploration Team
              </label>
              <input
                type="text"
                name="observer_organization"
                placeholder="e.g. Regional Field Operations Unit"
                value={formData.observer_organization}
                onChange={handleChange}
                style={{
                  width: '100%',
                  padding: '7px 10px',
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  color: '#fff',
                  fontSize: '0.8rem'
                }}
              />
            </div>
          </div>

          {/* Initial Status Selector */}
          <div>
            <label style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'block', marginBottom: 4 }}>
              Submission Workflow Status
            </label>
            <div style={{ display: 'flex', gap: 12 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.76rem', color: '#cbd5e1', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="verification_status"
                  value="DRAFT"
                  checked={formData.verification_status === 'DRAFT'}
                  onChange={handleChange}
                />
                <span>Draft (Personal Working Record)</span>
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.76rem', color: '#cbd5e1', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="verification_status"
                  value="SUBMITTED"
                  checked={formData.verification_status === 'SUBMITTED'}
                  onChange={handleChange}
                />
                <span>Submitted (Ready for Scientific Review)</span>
              </label>
            </div>
          </div>

          {/* Optional Laboratory Assays */}
          <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
              <FlaskConical size={14} color="#00f0ff" />
              <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f1f5f9' }}>
                Optional Laboratory Chemical Assays
              </span>
            </div>

            {assays.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 8 }}>
                {assays.map((a, i) => (
                  <div key={i} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    background: 'rgba(0, 240, 255, 0.08)',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '0.72rem'
                  }}>
                    <span><b>{a.element_or_compound}:</b> {a.value}{a.unit} {a.laboratory_name ? `(${a.laboratory_name})` : ''}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveAssay(i)}
                      style={{ background: 'transparent', border: 'none', color: '#f43f5e', cursor: 'pointer' }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 2fr auto', gap: 6 }}>
              <input
                type="text"
                placeholder="Analyte (Fe, Mn, Al2O3)"
                value={newAssay.element_or_compound}
                onChange={e => setNewAssay({ ...newAssay, element_or_compound: e.target.value })}
                style={{ padding: '5px 8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.72rem' }}
              />
              <input
                type="number"
                step="any"
                placeholder="Value"
                value={newAssay.value}
                onChange={e => setNewAssay({ ...newAssay, value: e.target.value })}
                style={{ padding: '5px 8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.72rem' }}
              />
              <select
                value={newAssay.unit}
                onChange={e => setNewAssay({ ...newAssay, unit: e.target.value })}
                style={{ padding: '5px 8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.72rem' }}
              >
                <option value="%">%</option>
                <option value="ppm">ppm</option>
                <option value="g/t">g/t</option>
              </select>
              <input
                type="text"
                placeholder="Lab Name / Report Ref"
                value={newAssay.laboratory_name}
                onChange={e => setNewAssay({ ...newAssay, laboratory_name: e.target.value })}
                style={{ padding: '5px 8px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '4px', color: '#fff', fontSize: '0.72rem' }}
              />
              <button
                type="button"
                onClick={handleAddAssay}
                style={{
                  padding: '5px 10px',
                  background: 'rgba(0, 240, 255, 0.2)',
                  border: '1px solid #00f0ff',
                  borderRadius: '4px',
                  color: '#00f0ff',
                  fontSize: '0.72rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                <Plus size={13} />
                <span>Add</span>
              </button>
            </div>
          </div>

          {/* Optional Photograph Attachment */}
          <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '10px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Camera size={14} color="#00f0ff" />
              <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#f1f5f9' }}>
                Optional Field Photograph (JPEG, PNG, WebP &le; 10MB)
              </span>
            </div>

            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handlePhotoSelect}
                style={{ fontSize: '0.72rem', color: '#94a3b8' }}
              />
              {photoPreview && (
                <div style={{ position: 'relative' }}>
                  <img
                    src={photoPreview}
                    alt="Preview"
                    style={{ width: '48px', height: '48px', objectFit: 'cover', borderRadius: '4px', border: '1px solid #00f0ff' }}
                  />
                </div>
              )}
            </div>
            {selectedPhoto && (
              <input
                type="text"
                placeholder="Photo caption (e.g. Outcrop facing South-West)"
                value={photoCaption}
                onChange={e => setPhotoCaption(e.target.value)}
                style={{
                  marginTop: 6,
                  width: '100%',
                  padding: '5px 8px',
                  background: 'rgba(0,0,0,0.4)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '4px',
                  color: '#fff',
                  fontSize: '0.72rem'
                }}
              />
            )}
          </div>

          {/* Scientific Disclaimer */}
          <div style={{
            fontSize: '0.68rem',
            color: '#94a3b8',
            background: 'rgba(0,0,0,0.3)',
            padding: '6px 10px',
            borderRadius: '4px',
            lineHeight: 1.4
          }}>
            <b>Scientific Guardrail:</b> Recording a field observation stores authentic ground observations. Submitting does not automatically mark it verified or feed into active models.
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              style={{
                padding: '8px 16px',
                borderRadius: '6px',
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                color: '#cbd5e1',
                fontSize: '0.78rem',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              style={{
                padding: '8px 20px',
                borderRadius: '6px',
                background: 'linear-gradient(135deg, #00f0ff, #0284c7)',
                border: 'none',
                color: '#0a0d14',
                fontWeight: 700,
                fontSize: '0.78rem',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  <span>Saving Record...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={15} />
                  <span>Save Field Observation</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
