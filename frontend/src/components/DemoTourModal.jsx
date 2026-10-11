import React, { useState } from 'react';
import {
  Play,
  X,
  Compass,
  Satellite,
  Layers,
  Cpu,
  MapPin,
  FileText,
  Mountain,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  Sparkles
} from 'lucide-react';

const STEPS = [
  {
    step: 1,
    title: '1. Exploration Target & Radius Selection',
    subtitle: 'Location Geocoding, Fixed 4 Minerals, and Buffer Area',
    desc: 'Enter coordinates or search by region (e.g. Balaghat Mining Belt). Select one of strictly 4 minerals: Coal, Manganese, Iron Ore, or Bauxite. Choose search buffer radius (1, 5, 10, or 25 km) with exact geographical surface area in km².',
    icon: Compass,
    color: '#00f0ff',
  },
  {
    step: 2,
    title: '2. Satellite Image Discovery & Selection',
    subtitle: 'Copernicus Sentinel-2 Level-2A Multi-Spectral Scenes',
    desc: 'Automatic footprint intersection discovers authentic Sentinel-2 scenes (such as S2A_MSIL2A_20260315_T44QMK). Inspect acquisition dates, cloud coverage percentage (<1%), 20-meter resolution, and bottom-of-atmosphere surface reflectance calibration status.',
    icon: Satellite,
    color: '#38bdf8',
  },
  {
    step: 3,
    title: '3. Supported Satellite-Band Processing',
    subtitle: '6 Optical Bands & Diagnostic Mineral Absorption Ratios',
    desc: 'Extract surface reflectance across B02 (Blue), B03 (Green), B04 (Red), B08 (NIR), B11 (SWIR-1), and B12 (SWIR-2). Calculate diagnostic indices: Clay Minerals Ratio (B11/B12), Iron Oxide Ratio (B04/B02), Ferrous Ratio (B11/B08), NDVI, and NDWI.',
    icon: Layers,
    color: '#10b981',
  },
  {
    step: 4,
    title: '4. Evidence-Based Mineral Prospectivity Analysis',
    subtitle: 'Authentic ML Random Forest Prediction with Zero Synthetic Data',
    desc: 'For Manganese inside Tile T44QMK, execute the trained Random Forest model to calculate relative prospectivity scores and match against 20 verified anomaly clusters. For Coal, Iron Ore, and Bauxite, return honest "INSUFFICIENT_DATA" without simulated scores.',
    icon: Cpu,
    color: '#a855f7',
  },
  {
    step: 5,
    title: '5. 2D Prospectivity Cartographic Map',
    subtitle: 'Anomaly Clusters, Footprint Overlays & Known Deposits',
    desc: 'Interactive Leaflet 2D explorer displaying query radius buffer, 20 high-prospectivity anomaly discovery zones with score tooltips, Tile T44QMK spatial boundary polygon, and verified reference mine pins (Ghondi reference deposit).',
    icon: MapPin,
    color: '#00f0ff',
  },
  {
    step: 6,
    title: '6. Explainable Analysis & Authoritative Evidence',
    subtitle: 'Feature Importance, Host Formations, and Scientific Limitations',
    desc: 'Review structured evidence vectors with hypothesis support (SUPPORTS, NEUTRAL, AWAITING OBSERVATION). Review host lithology (Sausar Group / Mansar Formation), data sources (ESA, GSI Bhukosh, MOIL), and scientific disclaimer notes.',
    icon: FileText,
    color: '#f59e0b',
  },
  {
    step: 7,
    title: '7. Distinct 3D Prospectivity Mesh Visualization',
    subtitle: 'AI Prospectivity Surface vs DEM Topographic Elevation',
    desc: 'Inspect the AI prospectivity surface in 3D where Z height represents mineral prospectivity intensity, shaded with spectral rainbow heatmap (blue -> cyan -> green -> yellow -> red peak) and callout pins, clearly demarcated from topographic DEM terrain.',
    icon: Mountain,
    color: '#f43f5e',
  },
  {
    step: 8,
    title: '8. Exploration Decision-Support Results',
    subtitle: 'Target Tier Ranking & 5-Phase Action Plan',
    desc: 'Receive exploration target tier classification (Tier-1, Tier-2, Tier-3), readiness rating, 5-phase field action plan (Reconnaissance -> Soil Grid XRF -> IP/ERT Geophysics -> Core Drilling -> Concession Clearance), and exportable exploration dossiers.',
    icon: ShieldCheck,
    color: '#10b981',
  },
];

export default function DemoTourModal({ isOpen, onClose, onExploreDashboard }) {
  const [currentStep, setCurrentStep] = useState(0);

  if (!isOpen) return null;

  const active = STEPS[currentStep];
  const StepIcon = active.icon;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 8, 15, 0.88)',
        backdropFilter: 'blur(10px)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1.5px solid rgba(0, 240, 255, 0.4)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '720px',
          boxShadow: '0 25px 70px rgba(0, 0, 0, 0.9), 0 0 35px rgba(0, 240, 255, 0.25)',
          padding: '2rem',
          position: 'relative',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          style={{
            position: 'absolute',
            top: 20,
            right: 20,
            background: 'rgba(255, 255, 255, 0.08)',
            border: 'none',
            color: '#94a3b8',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <X size={18} />
        </button>

        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1.5rem' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.25), rgba(56, 189, 248, 0.35))',
              border: '1.5px solid #00f0ff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(0, 240, 255, 0.4)',
            }}
          >
            <Play size={20} color="#00f0ff" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', color: '#00f0ff', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Interactive System Walkthrough
            </div>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.3rem', color: '#f1f5f9' }}>
              8-Step Mineral Exploration Workflow
            </h2>
          </div>
        </div>

        {/* Progress Dots */}
        <div style={{ display: 'flex', gap: '6px', marginBottom: '1.75rem' }}>
          {STEPS.map((s, idx) => (
            <div
              key={idx}
              onClick={() => setCurrentStep(idx)}
              style={{
                flex: 1,
                height: '5px',
                borderRadius: '3px',
                background: idx === currentStep ? active.color : idx < currentStep ? '#00f0ff' : 'rgba(255,255,255,0.1)',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                boxShadow: idx === currentStep ? `0 0 10px ${active.color}` : 'none',
              }}
            />
          ))}
        </div>

        {/* Step Card Content */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.75)',
            border: `1px solid ${active.color}40`,
            borderRadius: '12px',
            padding: '1.5rem',
            marginBottom: '1.75rem',
            boxShadow: `0 8px 24px rgba(0, 0, 0, 0.4), inset 0 0 20px ${active.color}10`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '0.75rem' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '8px',
                background: `${active.color}20`,
                border: `1px solid ${active.color}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <StepIcon size={20} color={active.color} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#f1f5f9', fontWeight: 700 }}>
                {active.title}
              </h3>
              <div style={{ fontSize: '0.78rem', color: active.color, fontWeight: 600 }}>
                {active.subtitle}
              </div>
            </div>
          </div>

          <p style={{ fontSize: '0.88rem', color: '#cbd5e1', lineHeight: 1.6, marginTop: '0.75rem' }}>
            {active.desc}
          </p>
        </div>

        {/* Navigation & Explore Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
            disabled={currentStep === 0}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '8px 16px',
              color: currentStep === 0 ? '#475569' : '#cbd5e1',
              cursor: currentStep === 0 ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.82rem',
            }}
          >
            <ChevronLeft size={16} />
            <span>Previous Step</span>
          </button>

          <div style={{ display: 'flex', gap: '10px' }}>
            {currentStep < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={() => setCurrentStep((prev) => prev + 1)}
                style={{
                  background: 'linear-gradient(135deg, #00f0ff, #0284c7)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px 18px',
                  color: '#0a0d14',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: '0.82rem',
                  boxShadow: '0 0 15px rgba(0, 240, 255, 0.4)',
                }}
              >
                <span>Next Step</span>
                <ChevronRight size={16} />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  if (onExploreDashboard) onExploreDashboard();
                }}
                style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '8px 20px',
                  color: '#fff',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: '0.82rem',
                  boxShadow: '0 0 15px rgba(16, 185, 129, 0.4)',
                }}
              >
                <Sparkles size={16} />
                <span>Launch Exploration Console</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
