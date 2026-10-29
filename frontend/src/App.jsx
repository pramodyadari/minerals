import React, { useState, useRef, useEffect } from 'react';
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
import FieldObservationModal from './components/FieldObservationModal';
import FieldObservationDrawer from './components/FieldObservationDrawer';
import { getApiUrl } from './apiConfig';
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

  // Step 5: Search radius (1, 5, 10, 25, 50 km - default 10 km)
  const [selectedRadius, setSelectedRadius] = useState(10);

  // Step 6 & 7: Analysis execution and results
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzingMode, setAnalyzingMode] = useState(null); // 'all' | 'single' | null
  const [analysisResult, setAnalysisResult] = useState(null);
  const [multiResult, setMultiResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  // Map visualization mode: '2d' | '3d-terrain' | '3d-prospectivity' (maintained across views and selections)
  const [mapMode, setMapMode] = useState('2d');

  // Abort controller ref for managing in-flight analysis requests
  const abortControllerRef = useRef(null);

  // Clean up in-flight requests on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Safe state transitions that abort in-flight queries and prevent stale results
  const handleLocationChange = (loc) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsAnalyzing(false);
    setAnalyzingMode(null);
    setSelectedLocation(loc);
    setAnalysisResult(null);
    setMultiResult(null);
    setAnalysisError(null);
  };

  const handleMineralChange = (m) => {
    setSelectedMineral(m);
    // If we have an active multi-mineral result, seamlessly synchronize the active 2D/3D single view to that mineral
    if (multiResult && multiResult.minerals && multiResult.minerals[m]) {
      setAnalysisResult(multiResult.minerals[m]);
    }
  };

  const handleRadiusChange = (rad) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsAnalyzing(false);
    setAnalyzingMode(null);
    setSelectedRadius(rad);
    setAnalysisResult(null);
    setMultiResult(null);
    setAnalysisError(null);
  };

  // Multi-mineral custom selection mode state (Part B)
  const [analysisMode, setAnalysisMode] = useState('all_four'); // 'all_four' | 'choose_minerals'
  const [customMinerals, setCustomMinerals] = useState(['Coal', 'Manganese']);

  // Modals state
  const [isSpecimenModalOpen, setIsSpecimenModalOpen] = useState(false);
  const [isProductionModalOpen, setIsProductionModalOpen] = useState(false);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const [isObservationModalOpen, setIsObservationModalOpen] = useState(false);
  const [isObservationDrawerOpen, setIsObservationDrawerOpen] = useState(false);
  const [obsRefreshTrigger, setObsRefreshTrigger] = useState(0);

  // Analyze Button Click Handler with Bounded Timeout and Abort Controller
  // mode: 'all' (primary default: executes all 4 minerals or custom 2/3 selection) or 'single' (optional single-commodity pipeline)
  const handleRunAnalysis = async (mode = 'all') => {
    if (!selectedLocation || !selectedRadius || isAnalyzing) return;
    if (mode === 'single' && !selectedMineral) return;
    if (mode === 'all' && analysisMode === 'choose_minerals' && (customMinerals.length < 2 || customMinerals.length > 3)) return;

    // Abort previous in-flight request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsAnalyzing(true);
    setAnalyzingMode(mode);
    setAnalysisError(null);

    // Bounded client safety timeout: 22s for multi-mineral run, 12s for single
    const timeoutDuration = mode === 'all' ? 22000 : 12000;
    const timeoutId = setTimeout(() => {
      controller.abort('TIMEOUT');
    }, timeoutDuration);

    try {
      const url = mode === 'all' ? getApiUrl('/analyze-all') : getApiUrl('/analyze');
      const payload = mode === 'all'
        ? {
            location_name: selectedLocation.name,
            latitude: parseFloat(selectedLocation.lat),
            longitude: parseFloat(selectedLocation.lon),
            radius_km: parseFloat(selectedRadius),
            minerals: analysisMode === 'choose_minerals' ? customMinerals : null,
          }
        : {
            location_name: selectedLocation.name,
            latitude: parseFloat(selectedLocation.lat),
            longitude: parseFloat(selectedLocation.lon),
            mineral: selectedMineral,
            radius_km: parseFloat(selectedRadius),
          };

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server returned HTTP status ${response.status}`);
      }

      const data = await response.json();

      if (mode === 'all') {
        setMultiResult(data);
        // Default the single focused dossier/3D view to the user's currently selectedMineral if available
        if (data.minerals && data.minerals[selectedMineral]) {
          setAnalysisResult(data.minerals[selectedMineral]);
        } else if (data.minerals) {
          const firstKey = Object.keys(data.minerals)[0];
          setAnalysisResult(data.minerals[firstKey]);
        }
      } else {
        setAnalysisResult(data);
        setMultiResult(null);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError' || controller.signal.aborted) {
        if (controller.signal.reason === 'TIMEOUT') {
          setAnalysisError(`The analysis request timed out after ${timeoutDuration / 1000} seconds. Remote service did not respond in time.`);
        }
      } else {
        setAnalysisError(err.message || 'Geographical analysis request failed.');
      }
      if (mode === 'single') {
        setAnalysisResult(null);
      }
    } finally {
      clearTimeout(timeoutId);
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setIsAnalyzing(false);
      setAnalyzingMode(null);
    }
  };

  const isCustomModeInvalid = analysisMode === 'choose_minerals' && (customMinerals.length < 2 || customMinerals.length > 3);
  const isAnalyzeDisabled = !selectedLocation || !selectedRadius || isAnalyzing || isCustomModeInvalid;

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

  // Navigation tab change handler: when user opens map explorer tab, load and maintain 3D terrain view
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'map') {
      setMapMode((current) => (current === '2d' ? '3d-terrain' : current));
    }
  };

  return (
    <div className="app-container">
      {/* Top Header matching reference image */}
      <Header
        activeTab={activeTab}
        onTabChange={handleTabChange}
        onOpenSpecimenClassifier={() => setIsSpecimenModalOpen(true)}
        onOpenProductionForecast={() => setIsProductionModalOpen(true)}
        onOpenFieldVerification={() => setIsObservationDrawerOpen(true)}
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
                  onLocationSelect={handleLocationChange}
                />

                <InteractiveMap
                  selectedLocation={selectedLocation}
                  radiusKm={selectedRadius}
                  targetMineral={selectedMineral}
                  analysisResult={analysisResult}
                  onLocationChange={handleLocationChange}
                  mapMode={mapMode}
                  onMapModeChange={setMapMode}
                  onOpenCreateObservation={() => setIsObservationModalOpen(true)}
                  refreshObservationsTrigger={obsRefreshTrigger}
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
                    onSelectMineral={handleMineralChange}
                    analysisMode={analysisMode}
                    onAnalysisModeChange={setAnalysisMode}
                    customMinerals={customMinerals}
                    onCustomMineralsChange={setCustomMinerals}
                  />

                  <RadiusSelector
                    selectedRadius={selectedRadius}
                    onRadiusChange={handleRadiusChange}
                  />

                  <button
                    type="button"
                    className="analyze-btn"
                    onClick={() => handleRunAnalysis('all')}
                    disabled={isAnalyzeDisabled}
                    id="btn-analyze-all-minerals"
                    style={{
                      background: isCustomModeInvalid ? 'rgba(255, 255, 255, 0.08)' : 'linear-gradient(135deg, #00f0ff, #3b82f6)',
                      boxShadow: isCustomModeInvalid ? 'none' : '0 4px 15px rgba(0, 240, 255, 0.25)',
                      fontWeight: 700
                    }}
                  >
                    {isAnalyzing && analyzingMode === 'all' ? (
                      <>
                        <Loader2 size={20} className="animate-spin" />
                        <span>{analysisMode === 'choose_minerals' ? `Analyzing Selected ${customMinerals.length} Minerals...` : 'Analyzing All 4 Minerals...'}</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={20} />
                        <span>
                          {analysisMode === 'choose_minerals'
                            ? (customMinerals.length === 2
                                ? 'Analyze Selected 2 Minerals'
                                : customMinerals.length === 3
                                ? 'Analyze Selected 3 Minerals'
                                : 'Select 2 or 3 Minerals to Analyze')
                            : 'Analyze All Four Minerals'}
                        </span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    className="analyze-btn-secondary"
                    onClick={() => handleRunAnalysis('single')}
                    disabled={isAnalyzeDisabled}
                    id="btn-analyze-geographical"
                    style={{
                      marginTop: '8px',
                      width: '100%',
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      color: '#cbd5e1',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: isAnalyzeDisabled ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 6,
                      opacity: isAnalyzeDisabled ? 0.6 : 1,
                      transition: 'all 0.2s ease'
                    }}
                    title={`Analyze only ${selectedMineral} at selected coordinates`}
                  >
                    {isAnalyzing && analyzingMode === 'single' ? (
                      <>
                        <Loader2 size={15} className="animate-spin" />
                        <span>Analyzing {selectedMineral}...</span>
                      </>
                    ) : (
                      <>
                        <Compass size={15} />
                        <span>Analyze {selectedMineral} Only (Single Mode)</span>
                      </>
                    )}
                  </button>

                  <ResultsPanel
                    result={analysisResult}
                    multiResult={multiResult}
                    isAnalyzing={isAnalyzing}
                    error={analysisError}
                    selectedMineral={selectedMineral}
                    onSelectMineral={handleMineralChange}
                    radiusKm={selectedRadius}
                    selectedLocation={selectedLocation}
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
              onLocationSelect={handleLocationChange}
            />

            <InteractiveMap
              selectedLocation={selectedLocation}
              radiusKm={selectedRadius}
              targetMineral={selectedMineral}
              analysisResult={analysisResult}
              onLocationChange={handleLocationChange}
              mapMode={mapMode}
              onMapModeChange={setMapMode}
              onOpenCreateObservation={() => setIsObservationModalOpen(true)}
              refreshObservationsTrigger={obsRefreshTrigger}
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
                onSelectMineral={handleMineralChange}
                analysisMode={analysisMode}
                onAnalysisModeChange={setAnalysisMode}
                customMinerals={customMinerals}
                onCustomMineralsChange={setCustomMinerals}
              />

              <RadiusSelector
                selectedRadius={selectedRadius}
                onRadiusChange={handleRadiusChange}
              />

              <button
                type="button"
                className="analyze-btn"
                onClick={() => handleRunAnalysis('all')}
                disabled={isAnalyzeDisabled}
                id="btn-analyze-all-minerals-dashboard"
                style={{
                  background: isCustomModeInvalid ? 'rgba(255, 255, 255, 0.08)' : 'linear-gradient(135deg, #00f0ff, #3b82f6)',
                  boxShadow: isCustomModeInvalid ? 'none' : '0 4px 15px rgba(0, 240, 255, 0.25)',
                  fontWeight: 700
                }}
              >
                {isAnalyzing && analyzingMode === 'all' ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>{analysisMode === 'choose_minerals' ? `Analyzing Selected ${customMinerals.length} Minerals...` : 'Analyzing All 4 Minerals...'}</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={20} />
                    <span>
                      {analysisMode === 'choose_minerals'
                        ? (customMinerals.length === 2
                            ? 'Analyze Selected 2 Minerals'
                            : customMinerals.length === 3
                            ? 'Analyze Selected 3 Minerals'
                            : 'Select 2 or 3 Minerals to Analyze')
                        : 'Analyze All Four Minerals'}
                    </span>
                  </>
                )}
              </button>

              <button
                type="button"
                className="analyze-btn-secondary"
                onClick={() => handleRunAnalysis('single')}
                disabled={isAnalyzeDisabled}
                id="btn-analyze-geographical-dashboard"
                style={{
                  marginTop: '8px',
                  width: '100%',
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#cbd5e1',
                  padding: '8px 12px',
                  borderRadius: '8px',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: isAnalyzeDisabled ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  opacity: isAnalyzeDisabled ? 0.6 : 1,
                  transition: 'all 0.2s ease'
                }}
                title={`Analyze only ${selectedMineral} at selected coordinates`}
              >
                {isAnalyzing && analyzingMode === 'single' ? (
                  <>
                    <Loader2 size={15} className="animate-spin" />
                    <span>Analyzing {selectedMineral}...</span>
                  </>
                ) : (
                  <>
                    <Compass size={15} />
                    <span>Analyze {selectedMineral} Only (Single Mode)</span>
                  </>
                )}
              </button>

              <ResultsPanel
                result={analysisResult}
                multiResult={multiResult}
                isAnalyzing={isAnalyzing}
                error={analysisError}
                selectedMineral={selectedMineral}
                onSelectMineral={handleMineralChange}
                radiusKm={selectedRadius}
                selectedLocation={selectedLocation}
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
              onLocationChange={handleLocationChange}
              mapMode={mapMode}
              onMapModeChange={setMapMode}
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

      {/* Field Verification System Modals */}
      <FieldObservationModal
        isOpen={isObservationModalOpen}
        onClose={() => setIsObservationModalOpen(false)}
        initialLocation={selectedLocation}
        initialMineral={selectedMineral}
        analysisId={analysisResult ? `ANL-${selectedLocation.lat?.toFixed(2)}-${selectedLocation.lon?.toFixed(2)}` : null}
        onObservationCreated={() => {
          setObsRefreshTrigger(prev => prev + 1);
        }}
      />

      <FieldObservationDrawer
        isOpen={isObservationDrawerOpen}
        onClose={() => setIsObservationDrawerOpen(false)}
        onOpenCreateModal={() => {
          setIsObservationDrawerOpen(false);
          setIsObservationModalOpen(true);
        }}
        onSelectObservationOnMap={(obs) => {
          setIsObservationDrawerOpen(false);
          handleLocationChange({
            name: `Field Obs #${obs.id} (${obs.mineral})`,
            lat: obs.latitude,
            lon: obs.longitude
          });
        }}
        selectedLocation={selectedLocation}
      />
    </div>
  );
}
