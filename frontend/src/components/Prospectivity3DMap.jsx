import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RotateCcw, Eye, Layers, Compass, Zap, Info, ShieldAlert, Sparkles, Maximize2, Mountain } from 'lucide-react';

// Spectral Prospectivity Color Map (0.0 to 1.0 -> Blue, Cyan, Green, Yellow, Orange, Red)
function getProspectivityColor(val) {
  const clamped = Math.max(0, Math.min(1, val));
  const color = new THREE.Color();
  
  if (clamped < 0.2) {
    // Deep blue to cyan
    const t = clamped / 0.2;
    color.setRGB(0.05 + 0.05 * t, 0.15 + 0.35 * t, 0.6 + 0.35 * t);
  } else if (clamped < 0.45) {
    // Cyan to green
    const t = (clamped - 0.2) / 0.25;
    color.setRGB(0.1 + 0.1 * t, 0.5 + 0.45 * t, 0.95 - 0.7 * t);
  } else if (clamped < 0.7) {
    // Green to yellow
    const t = (clamped - 0.45) / 0.25;
    color.setRGB(0.2 + 0.75 * t, 0.95, 0.25 - 0.2 * t);
  } else if (clamped < 0.85) {
    // Yellow to orange
    const t = (clamped - 0.7) / 0.15;
    color.setRGB(0.95 + 0.05 * t, 0.95 - 0.45 * t, 0.05);
  } else {
    // Orange to fiery red-magenta peak
    const t = (clamped - 0.85) / 0.15;
    color.setRGB(1.0, 0.5 - 0.4 * t, 0.05 + 0.2 * t);
  }
  return color;
}

export default function Prospectivity3DMap({
  selectedLocation,
  targetMineral,
  radiusKm,
  analysisResult,
  onLocationChange,
  onSwitchToTerrain,
  onSwitchTo2D
}) {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const meshRef = useRef(null);
  const wireframeMeshRef = useRef(null);
  const animFrameIdRef = useRef(null);

  const [wireframe, setWireframe] = useState(true);
  const [showCallout, setShowCallout] = useState(true);
  const [exaggeration, setExaggeration] = useState(1.8);
  const [isRotating, setIsRotating] = useState(true);
  const [peakScore, setPeakScore] = useState(null);
  const [peakZone, setPeakZone] = useState(null);

  // Mouse interaction state
  const isDraggingRef = useRef(false);
  const previousMousePositionRef = useRef({ x: 0, y: 0 });
  const rotationRef = useRef({ x: 0.65, y: -0.45 });
  const zoomRef = useRef(75);

  // Authoritative validation check: Genuine prediction and calibrated grid must exist for the active mineral
  // Validated strictly for Manganese within verified footprint (never for Coal, Iron Ore, Bauxite)
  const isProspectivityAvailable = Boolean(
    analysisResult &&
    targetMineral === 'Manganese' &&
    (!analysisResult.mineral || analysisResult.mineral === targetMineral) &&
    analysisResult.prediction &&
    typeof analysisResult.prediction.prospectivity_index === 'number' &&
    analysisResult.prospectivity_grid &&
    analysisResult.prospectivity_grid.status === 'AVAILABLE' &&
    analysisResult.prospectivity_grid.is_calibrated === true &&
    Array.isArray(analysisResult.prospectivity_grid.grid) &&
    analysisResult.prospectivity_grid.grid.length > 0
  );

  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0d14);
    scene.fog = new THREE.FogExp2(0x0a0d14, 0.008);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 1000);
    camera.position.set(0, -60, 50);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x00f0ff, 1.2);
    dirLight.position.set(40, -50, 70);
    scene.add(dirLight);

    const goldLight = new THREE.DirectionalLight(0xffb703, 0.8);
    goldLight.position.set(-50, 50, 50);
    scene.add(goldLight);

    // Grid Floor
    const gridHelper = new THREE.GridHelper(100, 30, 0x00f0ff, 0x1e293b);
    gridHelper.rotation.x = Math.PI / 2;
    gridHelper.position.z = -5;
    scene.add(gridHelper);

    let planeGeo;
    let colors;

    if (isProspectivityAvailable) {
      // Genuine spatial prediction output from calibrated model
      const gridValues = analysisResult.prospectivity_grid.grid;
      const rows = gridValues.length;
      const cols = gridValues[0]?.length || rows;
      planeGeo = new THREE.PlaneGeometry(80, 80, cols - 1, rows - 1);

      const posAttr = planeGeo.attributes.position;
      const count = posAttr.count;
      colors = new Float32Array(count * 3);

      for (let i = 0; i < count; i++) {
        const r = Math.floor(i / cols);
        const c = i % cols;
        const rawVal = gridValues[r] && gridValues[r][c] !== undefined ? gridValues[r][c] : 0.0;

        // Z height corresponds strictly to authentic prospectivity score
        const zHeight = rawVal * 18 * exaggeration;
        posAttr.setZ(i, zHeight);

        const clr = getProspectivityColor(rawVal);
        colors[i * 3] = clr.r;
        colors[i * 3 + 1] = clr.g;
        colors[i * 3 + 2] = clr.b;
      }
      setPeakScore(analysisResult.prediction.prospectivity_index);
      setPeakZone(analysisResult.prediction.candidate_zone || null);
    } else {
      // Clean flat reference plane — strictly NO fake peaks or default scores
      const gridSize = 32;
      planeGeo = new THREE.PlaneGeometry(80, 80, gridSize - 1, gridSize - 1);
      const posAttr = planeGeo.attributes.position;
      const count = posAttr.count;
      colors = new Float32Array(count * 3);

      for (let i = 0; i < count; i++) {
        posAttr.setZ(i, 0); // Flat neutral baseline
        colors[i * 3] = 0.12;
        colors[i * 3 + 1] = 0.16;
        colors[i * 3 + 2] = 0.24;
      }
      setPeakScore(null);
      setPeakZone(null);
    }

    planeGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    planeGeo.computeVertexNormals();

    // Solid Surface Mesh
    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: isProspectivityAvailable ? 0.35 : 0.7,
      metalness: isProspectivityAvailable ? 0.2 : 0.05,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(planeGeo, mat);
    scene.add(mesh);
    meshRef.current = mesh;

    // Wireframe Overlay
    const wireMat = new THREE.MeshBasicMaterial({
      color: isProspectivityAvailable ? 0x00f0ff : 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: isProspectivityAvailable ? 0.22 : 0.12,
    });
    const wireMesh = new THREE.Mesh(planeGeo, wireMat);
    wireMesh.position.z = 0.08;
    scene.add(wireMesh);
    wireframeMeshRef.current = wireMesh;

    // Orbiting Satellite simulation
    const satGroup = new THREE.Group();
    const satBody = new THREE.Mesh(
      new THREE.BoxGeometry(2.5, 1.2, 1.2),
      new THREE.MeshStandardMaterial({ color: 0x38bdf8, metalness: 0.9, roughness: 0.2 })
    );
    const satWingL = new THREE.Mesh(
      new THREE.BoxGeometry(4.5, 0.1, 1.5),
      new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.8 })
    );
    satWingL.position.x = -3.8;
    const satWingR = satWingL.clone();
    satWingR.position.x = 3.8;
    satGroup.add(satBody, satWingL, satWingR);
    satGroup.position.set(30, -30, 35);
    scene.add(satGroup);

    // Scanning Ray beam cone
    const beamGeo = new THREE.ConeGeometry(14, 38, 16, 1, true);
    const beamMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.15,
      side: THREE.DoubleSide,
      wireframe: true
    });
    const beam = new THREE.Mesh(beamGeo, beamMat);
    beam.rotation.x = Math.PI / 2;
    beam.position.set(0, 0, -19);
    satGroup.add(beam);

    // Animation Loop
    let angle = 0;
    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);

      if (isRotating) {
        rotationRef.current.y += 0.003;
      }

      // Rotate terrain mesh group
      mesh.rotation.z = rotationRef.current.y;
      wireMesh.rotation.z = rotationRef.current.y;

      // Orbit satellite
      angle += 0.008;
      satGroup.position.x = Math.cos(angle) * 38;
      satGroup.position.y = Math.sin(angle) * 38;
      satGroup.lookAt(0, 0, 0);

      // Camera view update
      const dist = zoomRef.current;
      camera.position.x = dist * Math.sin(rotationRef.current.x) * Math.sin(rotationRef.current.y);
      camera.position.y = -dist * Math.cos(rotationRef.current.x);
      camera.position.z = dist * Math.sin(rotationRef.current.x) * Math.cos(rotationRef.current.y);
      camera.lookAt(0, 0, 8);

      renderer.render(scene, camera);
    };
    animate();

    // Resize Handler & ResizeObserver
    const handleResize = () => {
      if (!container || !rendererRef.current || !cameraRef.current) return;
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 500;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    const ro = new ResizeObserver(() => {
      handleResize();
    });
    ro.observe(container);

    return () => {
      window.removeEventListener('resize', handleResize);
      ro.disconnect();
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [analysisResult, exaggeration, isRotating, targetMineral, isProspectivityAvailable]);

  // Wireframe toggle effect
  useEffect(() => {
    if (wireframeMeshRef.current) {
      wireframeMeshRef.current.visible = wireframe;
    }
  }, [wireframe]);

  // Mouse drag listeners for 3D orbit
  const handleMouseDown = (e) => {
    isDraggingRef.current = true;
    previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
    setIsRotating(false);
  };

  const handleMouseMove = (e) => {
    if (!isDraggingRef.current) return;
    const deltaX = e.clientX - previousMousePositionRef.current.x;
    const deltaY = e.clientY - previousMousePositionRef.current.y;

    rotationRef.current.y += deltaX * 0.008;
    rotationRef.current.x = Math.max(0.2, Math.min(1.4, rotationRef.current.x + deltaY * 0.008));

    previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleWheel = (e) => {
    zoomRef.current = Math.max(35, Math.min(130, zoomRef.current + e.deltaY * 0.05));
  };

  const resetView = () => {
    rotationRef.current = { x: 0.65, y: -0.45 };
    zoomRef.current = 75;
    setIsRotating(true);
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        minHeight: '480px',
        background: '#0a0d14',
        overflow: 'hidden',
        userSelect: 'none'
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
    >
      {/* Three.js Canvas Container */}
      <div ref={mountRef} style={{ width: '100%', height: '100%' }} />

      {/* Target Anomaly Callout Overlay — Rendered ONLY when a genuine, validated prediction exists */}
      {isProspectivityAvailable && showCallout && (
        <div
          style={{
            position: 'absolute',
            top: '22%',
            right: '25%',
            transform: 'translate(50%, -50%)',
            pointerEvents: 'none',
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.88)',
              border: '1.5px solid #00f0ff',
              boxShadow: '0 0 20px rgba(0, 240, 255, 0.45)',
              borderRadius: '8px',
              padding: '6px 14px',
              backdropFilter: 'blur(8px)',
              color: '#fff',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              animation: 'pulseGlow 2s infinite alternate',
            }}
          >
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', boxShadow: '0 0 8px #ef4444' }} />
            <div>
              <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {targetMineral} Prospectivity Peak
              </div>
              <div style={{ fontWeight: 800, color: '#38bdf8', fontSize: '0.92rem' }}>
                Score: {analysisResult.prediction.prospectivity_index}% &rarr;
              </div>
            </div>
          </div>
          {/* Stem line pointing to surface peak */}
          <div style={{ width: '2px', height: '36px', background: 'linear-gradient(to bottom, #00f0ff, transparent)' }} />
          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#00f0ff', boxShadow: '0 0 8px #00f0ff' }} />
        </div>
      )}

      {/* Scientific Distinction Notice Badge */}
      <div
        style={{
          position: 'absolute',
          top: 14,
          left: 16,
          right: 16,
          zIndex: 20,
          background: 'rgba(15, 23, 42, 0.88)',
          border: isProspectivityAvailable ? '1px solid rgba(0, 240, 255, 0.3)' : '1px solid rgba(245, 158, 11, 0.35)',
          borderRadius: '8px',
          padding: '8px 14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {isProspectivityAvailable ? (
            <>
              <Sparkles size={16} color="#00f0ff" />
              <span style={{ fontSize: '0.78rem', color: '#e2e8f0', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                3D Prospectivity Mesh &bull; <span style={{ color: '#00f0ff' }}>Z = AI Relative Prospectivity Score ({targetMineral})</span>
                <span style={{ fontSize: '0.65rem', padding: '1px 6px', borderRadius: '4px', background: 'rgba(0, 240, 255, 0.15)', border: '1px solid #00f0ff', color: '#00f0ff', fontWeight: 700 }}>
                  [PROSPECTIVITY_AVAILABLE]
                </span>
              </span>
            </>
          ) : (
            <>
              <ShieldAlert size={16} color="#f59e0b" />
              <span style={{ fontSize: '0.78rem', color: '#e2e8f0', fontWeight: 600 }}>
                3D Prospectivity Mesh &bull; <span style={{ color: '#f59e0b' }}>Spatial AI Model Unavailable for {targetMineral}</span>
              </span>
            </>
          )}
        </div>
        <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldAlert size={13} color="#f59e0b" />
          <span>Surface AI screening index — not subsurface drilling depth</span>
        </div>
      </div>

      {/* Dedicated Card when prospectivity model is unavailable */}
      {!isProspectivityAvailable && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 15,
            background: 'rgba(15, 23, 42, 0.92)',
            border: '1px solid rgba(245, 158, 11, 0.4)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px rgba(245, 158, 11, 0.15)',
            borderRadius: '12px',
            padding: '22px 26px',
            maxWidth: '460px',
            width: '90%',
            backdropFilter: 'blur(12px)',
            textAlign: 'center',
            color: '#f8fafc',
          }}
        >
          <div style={{ display: 'inline-flex', padding: '10px', borderRadius: '50%', background: 'rgba(245, 158, 11, 0.15)', marginBottom: '12px', color: '#f59e0b' }}>
            <ShieldAlert size={28} />
          </div>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: '0 0 8px 0', color: '#f1f5f9' }}>
            3D Prospectivity Mesh Unavailable
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.5, margin: '0 0 14px 0' }}>
            {!analysisResult
              ? `Select an exploration target and run geographical analysis to inspect available spatial data for ${targetMineral}.`
              : targetMineral !== 'Manganese'
              ? `No validated spatial machine-learning model exists for ${targetMineral}. Spatial AI scores and 3D prospectivity meshes are strictly withheld to preserve scientific integrity. Consult the evidence dossier below for certified geological records.`
              : 'The validated Manganese Random Forest model is trained specifically on Sentinel-2 Tile T44QMK (Balaghat corridor). Target coordinates lie outside this validated training footprint.'}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            {onSwitchToTerrain && (
              <button
                type="button"
                onClick={onSwitchToTerrain}
                style={{
                  background: 'linear-gradient(135deg, #d97706, #b45309)',
                  border: 'none',
                  borderRadius: '6px',
                  color: '#fff',
                  padding: '7px 14px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
                id="btn-prospectivity-switch-terrain"
              >
                <Mountain size={14} />
                <span>Switch to 3D Terrain View</span>
              </button>
            )}
            {onSwitchTo2D && (
              <button
                type="button"
                onClick={onSwitchTo2D}
                style={{
                  background: 'rgba(2, 132, 199, 0.25)',
                  border: '1px solid rgba(56, 189, 248, 0.4)',
                  borderRadius: '6px',
                  color: '#38bdf8',
                  padding: '7px 14px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
                id="btn-prospectivity-fallback-2d"
              >
                <span>Switch to 2D Map</span>
              </button>
            )}
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(255, 255, 255, 0.05)', padding: '6px 12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
              Status: <span style={{ color: '#f59e0b', fontWeight: 600 }}>{analysisResult?.coverage_status?.coverage_status || analysisResult?.prediction_availability || (analysisResult ? 'OUTSIDE_TRAINING_FOOTPRINT' : 'AWAITING_ANALYSIS')}</span>
            </div>
          </div>
        </div>
      )}

      {/* Floating 3D Controls Toolbar */}
      <div
        style={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: 20,
          display: 'flex',
          gap: 8,
          alignItems: 'center',
          background: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '8px',
          padding: '4px 8px',
          backdropFilter: 'blur(8px)',
        }}
      >
        <button
          type="button"
          onClick={() => setWireframe(!wireframe)}
          style={{
            background: wireframe ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
            border: '1px solid ' + (wireframe ? '#00f0ff' : 'rgba(255,255,255,0.15)'),
            color: wireframe ? '#00f0ff' : '#94a3b8',
            borderRadius: '6px',
            padding: '5px 10px',
            fontSize: '0.72rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 5
          }}
          title="Toggle Spectral Mesh Wireframe Grid"
        >
          <Layers size={13} />
          <span>Wireframe</span>
        </button>

        <button
          type="button"
          onClick={() => setIsRotating(!isRotating)}
          style={{
            background: isRotating ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
            border: '1px solid ' + (isRotating ? '#38bdf8' : 'rgba(255,255,255,0.15)'),
            color: isRotating ? '#38bdf8' : '#94a3b8',
            borderRadius: '6px',
            padding: '5px 10px',
            fontSize: '0.72rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 5
          }}
          title="Toggle Auto Orbit Rotation"
        >
          <RotateCcw size={13} />
          <span>{isRotating ? 'Rotating' : 'Paused'}</span>
        </button>

        {isProspectivityAvailable && (
          <button
            type="button"
            onClick={() => setShowCallout(!showCallout)}
            style={{
              background: showCallout ? 'rgba(245, 158, 11, 0.2)' : 'transparent',
              border: '1px solid ' + (showCallout ? '#f59e0b' : 'rgba(255,255,255,0.15)'),
              color: showCallout ? '#f59e0b' : '#94a3b8',
              borderRadius: '6px',
              padding: '5px 10px',
              fontSize: '0.72rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5
            }}
            title="Toggle High-Prospectivity Callout"
          >
            <Eye size={13} />
            <span>Callout Pin</span>
          </button>
        )}

        <button
          type="button"
          onClick={resetView}
          style={{
            background: 'transparent',
            border: '1px solid rgba(255,255,255,0.15)',
            color: '#cbd5e1',
            borderRadius: '6px',
            padding: '5px 10px',
            fontSize: '0.72rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 5
          }}
          title="Reset 3D Perspective"
        >
          <Compass size={13} />
          <span>Reset View</span>
        </button>
      </div>

      {/* Spectral Prospectivity Color Legend (Bottom Right) */}
      <div
        style={{
          position: 'absolute',
          bottom: 16,
          right: 16,
          zIndex: 20,
          background: 'rgba(15, 23, 42, 0.92)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: '8px',
          padding: '8px 12px',
          backdropFilter: 'blur(8px)',
          minWidth: '170px'
        }}
      >
        <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Prospectivity Index (Z)
        </div>
        {isProspectivityAvailable ? (
          <>
            <div
              style={{
                height: '10px',
                borderRadius: '4px',
                background: 'linear-gradient(to right, #0d2b6b, #00b4d8, #10b981, #facc15, #f97316, #ef4444)',
                marginBottom: 4
              }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#cbd5e1' }}>
              <span>Low (0%)</span>
              <span>Moderate (50%)</span>
              <span style={{ color: '#ef4444', fontWeight: 700 }}>Peak (&gt;85%)</span>
            </div>
          </>
        ) : (
          <div style={{ fontSize: '0.72rem', color: '#f59e0b', fontStyle: 'italic', padding: '4px 0' }}>
            Score: Unavailable (Withheld)
          </div>
        )}
      </div>
    </div>
  );
}
