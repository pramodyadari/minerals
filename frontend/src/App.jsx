import React, { useState } from 'react';
import Header from './components/Header';
import HeroSection from './components/HeroSection';
import LocationSearch from './components/LocationSearch';
import InteractiveMap from './components/InteractiveMap';
import MineralSelector from './components/MineralSelector';
import RadiusSelector from './components/RadiusSelector';
import SatelliteDiscoveryCard from './components/SatelliteDiscoveryCard';
import ResultsPanel from './components/ResultsPanel';
import SpecimenClassifierModal from './components/SpecimenClassifierModal';
import ProductionForecastModal from './components/ProductionForecastModal';
import DemoTourModal from './components/DemoTourModal';
import {
  Compass,
  Loader2,
  Satellite,
  Layers,
  Brain,
  ShieldCheck,
  TrendingUp,
  Database,
  ExternalLink,
  Sparkles,
  MapPin,
  CheckCircle2,
  FileText
} from 'lucide-react';

export default function App() {
  // Navigation active tab: 'home' | 'dashboard' | 'map' | 'analytics' | 'settings'
  const [activeTab, setActiveTab] = useState('home');

  // Step 1 & 2: Location state (Defaults to Balaghat Manganese Mining Belt)
  const [selectedLocation, setSelectedLocation] = useState({
    name: 'Balaghat Mining Belt, Madhya Pradesh, India',
    lat: 21.9048,
    lon: 80.1849,
  });

  // Step 4: Mineral selection (Exactly 4 minerals: Coal, Manganese, Iron Ore, Bauxite)
  const [selectedMineral, setSelectedMineral] = useState('Manganese');

  // Step 5: Search radius (1, 5, 10, 25 km)
  const [selectedRadius, setSelectedRadius] = useState(5);

  // Step 6 & 7: Analysis execution and results
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  // Modals state
  const [isSpecimenModalOpen, setIsSpecimenModalOpen] = useState(false);
  const [isProductionModalOpen, setIsProductionModalOpen] = useState(false);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);

  // Analyze Button Click Handler (Priority 1 -> Priority 8)
  const handleRunAnalysis = async () => {
    if (!selectedLocation || !selectedMineral || !selectedRadius || isAnalyzing) return;

    setIsAnalyzing(true);
    setAnalysisError(null);

    try {
      const payload = {
        location_name: selectedLocation.name,
        latitude: parseFloat(selectedLocation.lat),
        longitude: parseFloat(selectedLocation.lon),
        mineral: selectedMineral,
        radius_km: parseFloat(selectedRadius),
      };

      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned status ${response.status}`);
      }

      const data = await response.json();
      setAnalysisResult(data);
    } catch (err) {
      setAnalysisError(err.message || 'Geographical analysis request failed.');
      setAnalysisResult(null);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const isAnalyzeDisabled = !selectedLocation || !selectedMineral || !selectedRadius || isAnalyzing;

  // Jump directly to dashboard view
  const handleExploreDashboard = () => {
    setActiveTab('dashboard');
    const el = document.getElementById('exploration-workbench');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  // Select feature callback from Hero cards
  const handleSelectFeature = (featId) => {
    if (featId === 'production') {
      setIsProductionModalOpen(true);
    } else {
      setActiveTab('dashboard');
    }
  };

  return (
    <div className="app-container">
      {/* Top Header matching reference image */}
      <Header
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
        onOpenSpecimenClassifier={() => setIsSpecimenModalOpen(true)}
        onOpenProductionForecast={() => setIsProductionModalOpen(true)}
      />

      {/* Main View Switching */}
      {activeTab === 'home' && (
        <div className="home-view-wrapper">
          {/* Hero Section matching target reference image */}
          <HeroSection
            onExploreDashboard={handleExploreDashboard}
            onWatchDemo={() => setIsDemoModalOpen(true)}
            onSelectFeature={handleSelectFeature}
            onOpenProductionForecast={() => setIsProductionModalOpen(true)}
          />

          {/* Inline Exploration Workbench Section */}
          <section id="exploration-workbench" className="workbench-section-container">
            <div className="workbench-section-title-bar">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Compass size={22} color="#00f0ff" />
                <div>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f1f5f9' }}>
                    Exploration Console & Analysis Workbench
                  </h2>
                  <p style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Select location, mineral commodity, and satellite footprint for evidence-based prospectivity analysis
                  </p>
                </div>
              </div>
            </div>

            <div className="main-layout">
              {/* Left: Map & Satellite Discovery */}
              <section className="map-section" style={{ position: 'relative' }}>
                <LocationSearch
                  selectedLocation={selectedLocation}
                  onLocationSelect={(loc) => {
                    setSelectedLocation(loc);
                    setAnalysisResult(null);
                    setAnalysisError(null);
                  }}
                />

                <InteractiveMap
                  selectedLocation={selectedLocation}
                  radiusKm={selectedRadius}
                  targetMineral={selectedMineral}
                  analysisResult={analysisResult}
                  onLocationChange={(loc) => {
                    setSelectedLocation(loc);
                    setAnalysisResult(null);
                    setAnalysisError(null);
                  }}
                />

                {/* Priority 2 & 3: Satellite Discovery and Spectral Ratios Card */}
                <SatelliteDiscoveryCard
                  selectedLocation={selectedLocation}
                  selectedMineral={selectedMineral}
                  selectedRadius={selectedRadius}
                  spectralData={analysisResult?.spectral_processing}
                  satelliteScenes={analysisResult?.satellite_scenes}
                />
              </section>

              {/* Right: Mineral Selector, Radius, Analyze Button, Results Dossier */}
              <aside className="sidebar-panel">
                <div className="sidebar-content">
                  <MineralSelector
                    selectedMineral={selectedMineral}
                    onSelectMineral={(m) => {
                      setSelectedMineral(m);
                      setAnalysisResult(null);
                      setAnalysisError(null);
                    }}
                  />

                  <RadiusSelector
                    selectedRadius={selectedRadius}
                    onRadiusChange={(r) => {
                      setSelectedRadius(r);
                      setAnalysisResult(null);
                      setAnalysisError(null);
                    }}
                  />

                  <button
                    type="button"
                    className="analyze-btn"
                    onClick={handleRunAnalysis}
                    disabled={isAnalyzeDisabled}
                    id="btn-analyze-geographical"
                  >
                    {isAnalyzing ? (
                      <>
                        <Loader2 size={20} className="animate-spin" />
                        <span>Analyzing Location...</span>
                      </>
                    ) : (
                      <>
                        <Compass size={20} />
                        <span>Analyze Selected Area</span>
                      </>
                    )}
                  </button>

                  <ResultsPanel
                    result={analysisResult}
                    isAnalyzing={isAnalyzing}
                    error={analysisError}
                  />
                </div>
              </aside>
            </div>
          </section>
        </div>
      )}

      {activeTab === 'dashboard' && (
        <main className="main-layout" style={{ padding: '1.25rem 2rem' }}>
          {/* Left: Map-Centered Dashboard */}
          <section className="map-section" style={{ position: 'relative' }}>
            <LocationSearch
              selectedLocation={selectedLocation}
              onLocationSelect={(loc) => {
                setSelectedLocation(loc);
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            />

            <InteractiveMap
              selectedLocation={selectedLocation}
              radiusKm={selectedRadius}
              targetMineral={selectedMineral}
              analysisResult={analysisResult}
              onLocationChange={(loc) => {
                setSelectedLocation(loc);
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            />

            {/* Satellite Discovery & Spectral Processing */}
            <SatelliteDiscoveryCard
              selectedLocation={selectedLocation}
              selectedMineral={selectedMineral}
              selectedRadius={selectedRadius}
              spectralData={analysisResult?.spectral_processing}
              satelliteScenes={analysisResult?.satellite_scenes}
            />
          </section>

          {/* Right: Controls & Results Panel */}
          <aside className="sidebar-panel">
            <div className="sidebar-content">
              <MineralSelector
                selectedMineral={selectedMineral}
                onSelectMineral={(m) => {
                  setSelectedMineral(m);
                  setAnalysisResult(null);
                  setAnalysisError(null);
                }}
              />

              <RadiusSelector
                selectedRadius={selectedRadius}
                onRadiusChange={(r) => {
                  setSelectedRadius(r);
                  setAnalysisResult(null);
                  setAnalysisError(null);
                }}
              />

              <button
                type="button"
                className="analyze-btn"
                onClick={handleRunAnalysis}
                disabled={isAnalyzeDisabled}
                id="btn-analyze-geographical-dashboard"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>Analyzing Location...</span>
                  </>
                ) : (
                  <>
                    <Compass size={20} />
                    <span>Analyze Selected Area</span>
                  </>
                )}
              </button>

              <ResultsPanel
                result={analysisResult}
                isAnalyzing={isAnalyzing}
                error={analysisError}
              />
            </div>
          </aside>
        </main>
      )}

      {activeTab === 'map' && (
        <div style={{ padding: '1.25rem 2rem', height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f1f5f9' }}>
                Dual-Engine 2D & 3D Geospatial Explorer
              </h2>
              <div style={{ fontSize: '0.76rem', color: '#94a3b8' }}>
                Toggle between 2D Cartography, 3D Topographic DEM Terrain, and 3D AI Prospectivity Surface Mesh
              </div>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setActiveTab('dashboard')}
                style={{ padding: '6px 14px', fontSize: '0.78rem' }}
              >
                Open Sidebar Controls &rarr;
              </button>
            </div>
          </div>
          <div style={{ flex: 1, position: 'relative', borderRadius: '12px', overflow: 'hidden', border: '1px solid rgba(0, 240, 255, 0.2)' }}>
            <InteractiveMap
              selectedLocation={selectedLocation}
              radiusKm={selectedRadius}
              targetMineral={selectedMineral}
              analysisResult={analysisResult}
              onLocationChange={(loc) => {
                setSelectedLocation(loc);
                setAnalysisResult(null);
                setAnalysisError(null);
              }}
            />
          </div>
        </div>
      )}

      {activeTab === 'analytics' && (
        <div style={{ padding: '1.5rem 2rem', maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f1f5f9' }}>
              Multi-Spectral Analytics & Discovery Zones
            </h2>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
              Detailed breakdown of satellite band absorption indices, trained Random Forest feature importances, and historical mine telemetry
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem' }}>
            {/* Satellite Feature Extraction */}
            <SatelliteDiscoveryCard
              selectedLocation={selectedLocation}
              selectedMineral={selectedMineral}
              selectedRadius={selectedRadius}
              spectralData={analysisResult?.spectral_processing}
              satelliteScenes={analysisResult?.satellite_scenes}
            />

            {/* Production Forecast Card Trigger */}
            <div
              style={{
                background: 'rgba(22, 27, 34, 0.95)',
                border: '1.5px solid rgba(236, 72, 153, 0.3)',
                borderRadius: '12px',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: '0.75rem' }}>
                  <TrendingUp size={20} color="#ec4899" />
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
                    Mine Operational Telemetry & Shortfall Forecasting
                  </h3>
                </div>
                <p style={{ fontSize: '0.8rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                  121-month historical database linking monthly rainfall, equipment downtime, and blasting delays with planned vs actual mining production in the Balaghat corridor.
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsProductionModalOpen(true)}
                style={{
                  background: 'linear-gradient(135deg, #ec4899, #d946ef)',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '10px',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.82rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  marginTop: '1rem',
                }}
              >
                <span>View 10-Year Telemetry & Predictive Model</span>
                <ExternalLink size={15} />
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div style={{ padding: '1.5rem 2rem', maxWidth: '900px', margin: '0 auto' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f1f5f9', marginBottom: '0.5rem' }}>
            System Architecture & Scientific Integrity
          </h2>
          <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1.5rem' }}>
            Configuration of the 4 supported mineral classes, models, and satellite pipelines
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1.25rem' }}>
              <h3 style={{ fontSize: '1rem', color: '#00f0ff', marginBottom: '0.5rem' }}>
                Strictly Fixed Mineral Classes (Exactly Four)
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                1. <b>Coal (C)</b> &bull; 2. <b>Manganese (Mn)</b> &bull; 3. <b>Iron Ore (Fe)</b> &bull; 4. <b>Bauxite (Al)</b>. No fifth mineral class exists or will ever be added.
              </p>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1.25rem' }}>
              <h3 style={{ fontSize: '1rem', color: '#10b981', marginBottom: '0.5rem' }}>
                Authentic ML Models
              </h3>
              <ul style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: 1.6, paddingLeft: '1.2rem' }}>
                <li><b>Sentinel-2 Random Forest Prospectivity Model:</b> Trained on Tile T44QMK surface reflectance and Ghondi ground-truth reference deposit.</li>
                <li><b>PyTorch 4-Class CNN Rock Specimen Classifier:</b> Genuine convolutional network trained on physical specimen photography. Visual specimen identification is strictly distinguished from underground deposit occurrence.</li>
              </ul>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '10px', padding: '1.25rem' }}>
              <h3 style={{ fontSize: '1rem', color: '#f59e0b', marginBottom: '0.5rem' }}>
                Scientific Integrity & Prohibition of Synthetic Data
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: 1.5 }}>
                For Coal, Iron Ore, and Bauxite, where ground-truth training coordinates are awaiting acquisition, the system returns honest <code>INSUFFICIENT_DATA</code>. Simulated or fake prospectivity scores are strictly prohibited.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Modals */}
      <SpecimenClassifierModal
        isOpen={isSpecimenModalOpen}
        onClose={() => setIsSpecimenModalOpen(false)}
      />

      <ProductionForecastModal
        isOpen={isProductionModalOpen}
        onClose={() => setIsProductionModalOpen(false)}
        selectedMineral={selectedMineral}
      />

      <DemoTourModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
        onExploreDashboard={handleExploreDashboard}
      />
    </div>
  );
}
