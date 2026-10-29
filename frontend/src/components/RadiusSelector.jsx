import React from 'react';
import { CircleDot } from 'lucide-react';

const RADIUS_OPTIONS = [1, 5, 10, 25, 50];

export default function RadiusSelector({ selectedRadius, onRadiusChange }) {
  // Approximate circular geometric survey area: Area = π × radius²
  const areaSqKm = (Math.PI * Math.pow(selectedRadius, 2)).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <div className="control-section">
      <div className="section-label-row">
        <label className="section-title">
          <CircleDot size={16} color="#c6a052" />
          <span>Exploration Radius</span>
        </label>
        <span className="section-badge">{selectedRadius} km</span>
      </div>

      <div className="radius-pills">
        {RADIUS_OPTIONS.map((r) => (
          <button
            key={r}
            type="button"
            className={`radius-pill ${selectedRadius === r ? 'selected' : ''}`}
            onClick={() => onRadiusChange(r)}
            id={`radius-pill-${r}km`}
          >
            {r} km
          </button>
        ))}
      </div>

      <div className="radius-area-calc">
        <span title="Approximate geometric survey area, not the area of confirmed mineral deposits">
          Approx. Geometric Survey Area:
        </span>
        <span className="area-val">≈ {areaSqKm} km²</span>
      </div>
      <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.3rem', lineHeight: 1.35 }}>
        *Approximate geometric survey area, not confirmed mineral deposit area.
      </div>
    </div>
  );
}
