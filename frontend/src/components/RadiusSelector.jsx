import React from 'react';
import { CircleDot } from 'lucide-react';

const RADIUS_OPTIONS = [1, 5, 10, 25];

export default function RadiusSelector({ selectedRadius, onRadiusChange }) {
  // Approximate circular area calculation: π * r²
  const areaSqKm = (Math.PI * Math.pow(selectedRadius, 2)).toFixed(2);

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
        <span>Survey Area Coverage:</span>
        <span className="area-val">≈ {areaSqKm} km²</span>
      </div>
    </div>
  );
}
