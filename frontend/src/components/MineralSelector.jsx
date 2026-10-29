import React from 'react';
import { Layers, CheckSquare, Square, Check, RotateCcw, Sparkles, SlidersHorizontal, AlertCircle } from 'lucide-react';

export const MINERAL_OPTIONS = [
  {
    id: 'Coal',
    name: 'Coal',
    symbol: 'C',
    category: 'Carbonaceous Energy Commodity',
    icon: '🪨',
    accentColor: '#8b9bb4',
    status: 'AWAITING_DATA',
    statusLabel: 'Evidence Active (No ML Model)',
    description: 'Gondwana basin stratigraphy & spectral evidence.'
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
    description: 'Sentinel-2 trained RF model on Balaghat belt.'
  },
  {
    id: 'Iron Ore',
    name: 'Iron Ore',
    symbol: 'Fe',
    category: 'Ferrous Metal Commodity',
    icon: '⛰️',
    accentColor: '#c85a32',
    status: 'AWAITING_DATA',
    statusLabel: 'Terrain & Evidence Active (AI Withheld)',
    description: 'Copernicus DEM & Sentinel-2; AI withheld until spatial validation.'
  },
  {
    id: 'Bauxite',
    name: 'Bauxite',
    symbol: 'Al',
    category: 'Lateritic Aluminum Ore',
    icon: '🧱',
    accentColor: '#d97706',
    status: 'AWAITING_DATA',
    statusLabel: 'Evidence Active (No ML Model)',
    description: 'Plateau morphology & SWIR Al-OH indicators.'
  }
];

export default function MineralSelector({
  selectedMineral,
  onSelectMineral,
  analysisMode = 'all_four',
  onAnalysisModeChange,
  customMinerals = ['Coal', 'Manganese'],
  onCustomMineralsChange,
}) {
  const isCustomMode = analysisMode === 'choose_minerals';
  const customCount = customMinerals.length;
  const isCountValid = customCount === 2 || customCount === 3;

  const handleToggleCustomMineral = (mineralName) => {
    if (!onCustomMineralsChange) return;

    if (customMinerals.includes(mineralName)) {
      // Deselect
      const updated = customMinerals.filter((m) => m !== mineralName);
      onCustomMineralsChange(updated);
      // If the deselected mineral was the active 3D focus, switch focus to another selected mineral if possible
      if (selectedMineral === mineralName && updated.length > 0) {
        onSelectMineral(updated[0]);
      }
    } else {
      // Select (maximum 3 in custom mode)
      if (customMinerals.length >= 3) {
        return; // Prevent selecting more than 3
      }
      const updated = [...customMinerals, mineralName];
      onCustomMineralsChange(updated);
      onSelectMineral(mineralName);
    }
  };

  const handleSelectAllFour = () => {
    if (onAnalysisModeChange) {
      onAnalysisModeChange('all_four');
    }
    if (onCustomMineralsChange) {
      onCustomMineralsChange(['Coal', 'Manganese', 'Iron Ore', 'Bauxite']);
    }
  };

  const handleClearSelection = () => {
    if (onCustomMineralsChange) {
      onCustomMineralsChange([]);
    }
  };

  return (
    <div className="control-section" id="mineral-selector-control-section">
      <div className="section-label-row">
        <label className="section-title">
          <Layers size={16} color="#c6a052" />
          <span>Target Mineral Class</span>
        </label>
        <span className="section-badge" id="mineral-selection-badge">
          {isCustomMode ? `Selected ${customCount}/4 (Need 2 or 3)` : 'Exactly 4 Classes'}
        </span>
      </div>

      {/* Analysis Mode Selector Tabs */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 6,
          marginBottom: 10,
          background: 'rgba(15, 23, 42, 0.7)',
          padding: 3,
          borderRadius: 8,
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
        id="analysis-mode-selector-bar"
      >
        <button
          type="button"
          onClick={() => onAnalysisModeChange && onAnalysisModeChange('all_four')}
          style={{
            padding: '6px 10px',
            fontSize: '0.74rem',
            fontWeight: !isCustomMode ? 700 : 500,
            borderRadius: 6,
            border: 'none',
            background: !isCustomMode ? 'linear-gradient(135deg, #0284c7, #0369a1)' : 'transparent',
            color: !isCustomMode ? '#fff' : '#94a3b8',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 5,
            transition: 'all 0.15s ease',
          }}
          id="btn-mode-analyze-all-four"
        >
          <Sparkles size={13} />
          <span>Analyze All Four</span>
        </button>

        <button
          type="button"
          onClick={() => onAnalysisModeChange && onAnalysisModeChange('choose_minerals')}
          style={{
            padding: '6px 10px',
            fontSize: '0.74rem',
            fontWeight: isCustomMode ? 700 : 500,
            borderRadius: 6,
            border: 'none',
            background: isCustomMode ? 'linear-gradient(135deg, #d97706, #b45309)' : 'transparent',
            color: isCustomMode ? '#fff' : '#94a3b8',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 5,
            transition: 'all 0.15s ease',
          }}
          id="btn-mode-choose-minerals"
        >
          <SlidersHorizontal size={13} />
          <span>Choose Minerals</span>
        </button>
      </div>

      {/* Custom Mode Controls Bar */}
      {isCustomMode && (
        <div
          style={{
            background: 'rgba(22, 27, 34, 0.85)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            borderRadius: 8,
            padding: '8px 10px',
            marginBottom: 10,
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
          id="custom-mode-controls-panel"
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: '0.72rem', color: '#f1f5f9', fontWeight: 600 }}>
              Custom Selection: <b style={{ color: isCountValid ? '#10b981' : '#f59e0b' }}>{customCount} selected</b> (choose 2 or 3)
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                type="button"
                onClick={handleSelectAllFour}
                style={{
                  background: 'rgba(2, 132, 199, 0.15)',
                  border: '1px solid rgba(2, 132, 199, 0.3)',
                  borderRadius: 4,
                  padding: '3px 8px',
                  fontSize: '0.66rem',
                  color: '#38bdf8',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                id="btn-select-all-four-shortcut"
                title="Switch to Analyze All Four Minerals mode"
              >
                Select All Four
              </button>
              <button
                type="button"
                onClick={handleClearSelection}
                style={{
                  background: 'rgba(239, 68, 68, 0.12)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 4,
                  padding: '3px 8px',
                  fontSize: '0.66rem',
                  color: '#f87171',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
                id="btn-clear-minerals-selection"
                title="Clear mineral selection"
              >
                Clear Selection
              </button>
            </div>
          </div>

          {!isCountValid && (
            <div style={{ fontSize: '0.68rem', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: 4 }}>
              <AlertCircle size={12} />
              <span>
                {customCount < 2
                  ? `Select at least ${2 - customCount} more mineral(s) (custom mode requires exactly 2 or 3).`
                  : 'Maximum 3 minerals allowed. Please deselect one.'}
              </span>
            </div>
          )}
        </div>
      )}

      {/* 4 Mineral Cards Grid */}
      <div className="mineral-cards-grid">
        {MINERAL_OPTIONS.map((min) => {
          const isSelectedInCustom = customMinerals.includes(min.name);
          const isFocused = selectedMineral === min.name;
          const isSelected = isCustomMode ? isSelectedInCustom : isFocused;
          const isCardDisabled = isCustomMode && !isSelectedInCustom && customCount >= 3;

          return (
            <div
              key={min.id}
              className={`mineral-card ${isSelected ? 'selected' : ''}`}
              onClick={isCustomMode ? () => handleToggleCustomMineral(min.name) : (() => onSelectMineral(min.name))}
              data-on-select="onClick={() => onSelectMineral(min.name)}"
              id={`mineral-card-${min.name.toLowerCase().replace(' ', '-')}`}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  if (isCustomMode) handleToggleCustomMineral(min.name);
                  else onSelectMineral(min.name);
                }
              }}
              style={{
                opacity: isCardDisabled ? 0.45 : 1,
                cursor: isCardDisabled ? 'not-allowed' : 'pointer',
                position: 'relative',
              }}
              title={
                isCustomMode
                  ? isSelectedInCustom
                    ? `Click to deselect ${min.name}`
                    : customCount >= 3
                    ? 'Maximum 3 minerals selected. Deselect one first.'
                    : `Click to select ${min.name}`
                  : `Select ${min.name}`
              }
            >
              {/* Custom Mode Checkbox indicator */}
              {isCustomMode && (
                <div
                  style={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    width: 18,
                    height: 18,
                    borderRadius: 4,
                    background: isSelectedInCustom ? '#00f0ff' : 'rgba(255, 255, 255, 0.08)',
                    border: '1.5px solid ' + (isSelectedInCustom ? '#00f0ff' : 'rgba(255, 255, 255, 0.3)'),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#0a0d14',
                    fontWeight: 800,
                  }}
                  className="mineral-checkbox-indicator"
                >
                  {isSelectedInCustom && <Check size={12} strokeWidth={3} />}
                </div>
              )}

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

