import React from 'react';
import {
  Rocket,
  Play,
  Satellite,
  Brain,
  Map,
  Mountain,
  TrendingUp,
  ShieldCheck,
  ChevronRight,
  Database,
  Cpu,
  Layers,
  ArrowRight,
  Sparkles
} from 'lucide-react';

export default function HeroSection({
  onExploreDashboard,
  onWatchDemo,
  onSelectFeature,
  onOpenProductionForecast,
}) {
  const keyFeatures = [
    {
      id: 'satellite',
      title: 'Satellite Analysis',
      desc: 'Use Sentinel-2 data for spectral analysis and mineral detection.',
      icon: Satellite,
      color: '#38bdf8',
      action: () => onSelectFeature('satellite'),
    },
    {
      id: 'prediction',
      title: 'AI Prediction',
      desc: 'Machine learning models identify high-prospectivity areas with confidence scores.',
      icon: Brain,
      color: '#a855f7',
      action: () => onSelectFeature('prediction'),
    },
    {
      id: 'maps',
      title: 'Interactive Maps',
      desc: 'Explore 2D maps with candidate zones and detailed insights.',
      icon: Map,
      color: '#00f0ff',
      action: () => onSelectFeature('maps'),
    },
    {
      id: '3d',
      title: '3D Visualization',
      desc: 'View AI-derived prospectivity surfaces in 3D for better understanding.',
      icon: Mountain,
      color: '#f59e0b',
      action: () => onSelectFeature('3d'),
    },
    {
      id: 'production',
      title: 'Production Forecast',
      desc: 'Predict production shortfalls using historical and operational data.',
      icon: TrendingUp,
      color: '#ec4899',
      action: () => onOpenProductionForecast(),
    },
    {
      id: 'decision',
      title: 'Exploration Support',
      desc: 'Make data-driven decisions with explainable AI and comprehensive reports.',
      icon: ShieldCheck,
      color: '#10b981',
      action: () => onSelectFeature('decision'),
    },
  ];

  return (
    <div className="hero-container" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Background Graphic Ambient Lighting */}
      <div
        style={{
          position: 'absolute',
          top: '-150px',
          right: '5%',
          width: '550px',
          height: '550px',
          background: 'radial-gradient(circle, rgba(0, 240, 255, 0.15) 0%, rgba(168, 85, 247, 0.08) 50%, transparent 70%)',
          borderRadius: '50%',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      {/* Main Hero Grid (Left Copy + Right 3D Visual Centerpiece) */}
      <div className="hero-main-row">
        {/* Left Hero Content */}
        <div className="hero-copy-column">
          <div className="hero-badge">
            <Rocket size={16} color="#00f0ff" />
            <span>AI Mineral Intelligence</span>
          </div>

          <h1 className="hero-headline">
            AI Mineral Intelligence
          </h1>

          <h2 className="hero-subheadline">
            Satellite-Based Mineral Prospectivity and Exploration Decision Support System
          </h2>

          <p className="hero-description">
            Harnessing the power of satellite imagery, spectral analysis and machine learning to identify mineral-rich zones and support smarter exploration decisions across Coal, Manganese, Iron Ore, and Bauxite deposits.
          </p>

          <div className="hero-actions">
            <button
              type="button"
              className="hero-btn-primary"
              onClick={onExploreDashboard}
              id="btn-hero-explore-dashboard"
            >
              <Rocket size={18} />
              <span>Explore Dashboard</span>
              <ArrowRight size={18} />
            </button>

            <button
              type="button"
              className="hero-btn-secondary"
              onClick={onWatchDemo}
              id="btn-hero-watch-demo"
            >
              <Play size={16} color="#00f0ff" />
              <span>Watch Demo</span>
            </button>
          </div>
        </div>

        {/* Right Hero Visual Centerpiece (Inspired directly by the reference image) */}
        <div className="hero-visual-column">
          <div className="hero-prospectivity-card" onClick={onExploreDashboard} style={{ cursor: 'pointer' }}>
            {/* Visual Mesh Surface Graphic Container */}
            <div className="hero-mesh-canvas">
              {/* Top Satellite Scan Simulation */}
              <div className="hero-satellite-beam">
                <Satellite size={28} color="#38bdf8" className="hero-orbiting-sat" />
                <div className="hero-scan-cone" />
              </div>

              {/* Peak Callout Pin */}
              <div className="hero-callout-pin">
                <div className="hero-callout-box">
                  <div className="hero-callout-title">Manganese Prospectivity</div>
                  <div className="hero-callout-score">Score: 87% &rarr;</div>
                </div>
                <div className="hero-callout-stem" />
                <div className="hero-callout-dot" />
              </div>

              {/* 3D Prospectivity Terrain Mesh Graphic */}
              <div className="hero-terrain-spectral-mesh" />
            </div>

            {/* Right Side Vertical Nav Pills */}
            <div className="hero-vertical-pills">
              <div className="hero-pill-item" onClick={(e) => { e.stopPropagation(); onSelectFeature('satellite'); }}>
                <Satellite size={14} color="#38bdf8" />
                <span>Satellite Data</span>
              </div>
              <div className="hero-pill-item" onClick={(e) => { e.stopPropagation(); onSelectFeature('prediction'); }}>
                <Brain size={14} color="#a855f7" />
                <span>AI Analysis</span>
              </div>
              <div className="hero-pill-item" onClick={(e) => { e.stopPropagation(); onSelectFeature('3d'); }}>
                <Mountain size={14} color="#00f0ff" />
                <span>2D/3D Visualization</span>
              </div>
              <div className="hero-pill-item" onClick={(e) => { e.stopPropagation(); onSelectFeature('decision'); }}>
                <ShieldCheck size={14} color="#10b981" />
                <span>Better Decisions</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Key Features Section (6 Glowing Cards) */}
      <div className="key-features-container">
        <div className="key-features-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: 14, height: 14, background: '#00f0ff', borderRadius: '3px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 1, padding: 1 }}>
              <div style={{ background: '#0a0d14' }} />
              <div style={{ background: '#0a0d14' }} />
              <div style={{ background: '#0a0d14' }} />
              <div style={{ background: '#0a0d14' }} />
            </div>
            <h3 style={{ fontSize: '1.08rem', fontWeight: 800, color: '#f1f5f9', letterSpacing: '0.02em' }}>
              Key Features
            </h3>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.76rem', color: '#94a3b8' }}>
              From satellite to actionable insights
            </span>
            <div style={{ width: '45px', height: '3px', background: 'linear-gradient(to right, #00f0ff, transparent)', borderRadius: '2px' }} />
          </div>
        </div>

        <div className="features-grid-row">
          {keyFeatures.map((feat) => {
            const IconComponent = feat.icon;
            return (
              <div
                key={feat.id}
                className="feature-card"
                onClick={feat.action}
                style={{
                  '--card-glow': feat.color,
                }}
              >
                <div className="feature-icon-wrapper" style={{ background: `${feat.color}18`, borderColor: feat.color }}>
                  <IconComponent size={22} color={feat.color} />
                </div>
                <h4 className="feature-title">{feat.title}</h4>
                <p className="feature-desc">{feat.desc}</p>
                <div className="feature-link" style={{ color: feat.color }}>
                  <span>Learn More</span>
                  <ChevronRight size={14} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom Metrics Bar */}
      <div className="bottom-metrics-bar">
        <div className="metrics-brand-left">
          <div className="metrics-icon-cube">
            <Mountain size={18} color="#00f0ff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#f1f5f9', letterSpacing: '0.02em' }}>
              Smarter Exploration.
            </div>
            <div style={{ fontWeight: 800, fontSize: '0.88rem', color: '#00f0ff', letterSpacing: '0.02em' }}>
              A Richer Tomorrow.
            </div>
          </div>
        </div>

        <div className="metrics-stats-group">
          <div className="metric-stat-item">
            <div className="metric-icon-circle">
              <Satellite size={16} color="#38bdf8" />
            </div>
            <div>
              <div className="metric-num">6</div>
              <div className="metric-label">Satellite Bands</div>
            </div>
          </div>

          <div className="metric-stat-item">
            <div className="metric-icon-circle">
              <Cpu size={16} color="#a855f7" />
            </div>
            <div>
              <div className="metric-num">100%</div>
              <div className="metric-label">ML Powered</div>
            </div>
          </div>

          <div className="metric-stat-item">
            <div className="metric-icon-circle">
              <Sparkles size={16} color="#10b981" />
            </div>
            <div>
              <div className="metric-num">2</div>
              <div className="metric-label">AI Models</div>
            </div>
          </div>

          <div className="metric-stat-item">
            <div className="metric-icon-circle">
              <Database size={16} color="#f59e0b" />
            </div>
            <div>
              <div className="metric-num">4</div>
              <div className="metric-label">Minerals Supported</div>
            </div>
          </div>
        </div>

        <div
          className="metrics-callout-right"
          onClick={() => onSelectFeature('manganese')}
          style={{ cursor: 'pointer' }}
        >
          <span style={{ color: '#00f0ff', fontWeight: 700 }}>Manganese</span>
          <span style={{ color: '#94a3b8' }}> &mdash; Key to a Sustainable Future &rarr;</span>
        </div>
      </div>
    </div>
  );
}
