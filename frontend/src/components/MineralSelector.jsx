import React from 'react';
import { Layers } from 'lucide-react';

const MINERAL_OPTIONS = [
  {
    id: 'Coal',
    name: 'Coal',
    symbol: 'C',
    category: 'Carbonaceous Energy Commodity',
    icon: '🪨',
    accentColor: '#8b9bb4',
    status: 'AWAITING_DATA',
    statusLabel: 'Awaiting Ground-Truth Data',
    description: 'Requires colliery ground-truth observations.'
  },
  {
    id: 'Manganese',
    name: 'Manganese',
    symbol: 'Mn',
    category: 'Strategic Ferroalloy Mineral',
    icon: '⛏️',
    accentColor: '#00b4d8',
    status: 'TRAINED',
    statusLabel: 'AI Model Active (Tile T44QMK)',
    description: 'Sentinel-2 trained RF model available.'
  },
  {
    id: 'Iron Ore',
    name: 'Iron Ore',
    symbol: 'Fe',
    category: 'Ferrous Metal Commodity',
    icon: '⛰️',
    accentColor: '#c85a32',
    status: 'AWAITING_DATA',
    statusLabel: 'Awaiting Ground-Truth Data',
    description: 'Requires ground-truth mine coordinates.'
  },
  {
    id: 'Bauxite',
    name: 'Bauxite',
    symbol: 'Al',
    category: 'Lateritic Aluminum Ore',
    icon: '🧱',
    accentColor: '#d97706',
    status: 'AWAITING_DATA',
    statusLabel: 'Awaiting Ground-Truth Data',
    description: 'Awaiting verified laterite deposit labels.'
  }
];

export default function MineralSelector({ selectedMineral, onSelectMineral }) {
  return (
    <div className="control-section">
      <div className="section-label-row">
        <label className="section-title">
          <Layers size={16} color="#c6a052" />
          <span>Target Mineral Class</span>
        </label>
        <span className="section-badge">Exactly 4 Classes</span>
      </div>

      <div className="mineral-cards-grid">
        {MINERAL_OPTIONS.map((min) => {
          const isSelected = selectedMineral === min.name;
          return (
            <div
              key={min.id}
              className={`mineral-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectMineral(min.name)}
              id={`mineral-card-${min.name.toLowerCase().replace(' ', '-')}`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onSelectMineral(min.name);
              }}
            >
              <div className="mineral-card-header">
                <div className="mineral-icon-box">
                  <span>{min.icon}</span>
                </div>
                <span className="mineral-symbol">{min.symbol}</span>
              </div>

              <div>
                <div className="mineral-name" style={{ color: isSelected ? min.accentColor : '#fff' }}>
                  {min.name}
                </div>
                <div
                  className={`mineral-status-tag ${
                    min.status === 'TRAINED' ? 'status-active' : 'status-awaiting'
                  }`}
                  style={{ marginTop: 4 }}
                >
                  {min.statusLabel}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
