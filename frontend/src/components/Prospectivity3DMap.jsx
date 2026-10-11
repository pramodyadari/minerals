import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RotateCcw, Eye, Layers, Compass, Zap, Info, ShieldAlert, Sparkles, Maximize2 } from 'lucide-react';

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
  onLocationChange
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
  const [peakScore, setPeakScore] = useState(87.5);
  const [peakZone, setPeakZone] = useState('Zone 67684');

  // Mouse interaction state
  const isDraggingRef = useRef(false);
  const previousMousePositionRef = useRef({ x: 0, y: 0 });
  const rotationRef = useRef({ x: 0.65, y: -0.45 });
  const zoomRef = useRef(75);

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

    // Build 3D Prospectivity Mesh from analysis grid or default synthetic surface
    const gridSize = 40;
    const planeGeo = new THREE.PlaneGeometry(80, 80, gridSize - 1, gridSize - 1);
    
    // Obtain raw grid
    let gridValues = [];
    if (analysisResult?.prospectivity_grid?.grid) {
      gridValues = analysisResult.prospectivity_grid.grid;
    } else {
      // Default ridge-anomaly prospectivity pattern around center
      for (let r = 0; r < gridSize; r++) {
        const row = [];
        const dy = (r - gridSize / 2) / (gridSize / 2);
        for (let c = 0; c < gridSize; c++) {
          const dx = (c - gridSize / 2) / (gridSize / 2);
          const dist = Math.sqrt(dx * dx + dy * dy);
          // High peak anomaly at (dx: 0.1, dy: -0.15) representing Balaghat corridor
          const peak1 = 0.88 * Math.exp(-((dx - 0.1) ** 2 + (dy + 0.15) ** 2) / 0.12);
          const peak2 = 0.72 * Math.exp(-((dx + 0.35) ** 2 + (dy - 0.25) ** 2) / 0.25);
          const ridge = 0.45 * Math.exp(-Math.abs(dy - 0.5 * dx) / 0.3);
          const val = Math.max(0.08, Math.min(0.98, peak1 + peak2 * 0.5 + ridge * 0.4));
          row.push(val);
        }
        gridValues.push(row);
      }
    }

    const posAttr = planeGeo.attributes.position;
    const count = posAttr.count;
    const colors = new Float32Array(count * 3);

    let maxVal = 0;
    for (let i = 0; i < count; i++) {
      const r = Math.floor(i / gridSize);
      const c = i % gridSize;
      const rawVal = gridValues[r] && gridValues[r][c] !== undefined ? gridValues[r][c] : 0.2;
      if (rawVal > maxVal) maxVal = rawVal;

      // Z height corresponds to prospectivity score
      const zHeight = rawVal * 18 * exaggeration;
      posAttr.setZ(i, zHeight);

      const clr = getProspectivityColor(rawVal);
      colors[i * 3] = clr.r;
      colors[i * 3 + 1] = clr.g;
      colors[i * 3 + 2] = clr.b;
    }
    setPeakScore(Math.round(maxVal * 100));

    planeGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    planeGeo.computeVertexNormals();

    // Solid Surface Mesh
    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.35,
      metalness: 0.2,
      side: THREE.DoubleSide,
    });
    const mesh = new THREE.Mesh(planeGeo, mat);
    scene.add(mesh);
    meshRef.current = mesh;

    // Wireframe Overlay
    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.22,
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

    // Resize Handler
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      if (renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [analysisResult, exaggeration, isRotating]);

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

      {/* Target Anomaly Callout Overlay (Inspired directly by reference image) */}
      {showCallout && (
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
                Score: {analysisResult?.prediction?.prospectivity_index || peakScore}% &rarr;
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
          background: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid rgba(0, 240, 255, 0.3)',
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
          <Sparkles size={16} color="#00f0ff" />
          <span style={{ fontSize: '0.78rem', color: '#e2e8f0', fontWeight: 600 }}>
            3D Prospectivity Mesh &bull; <span style={{ color: '#00f0ff' }}>Z = AI Relative Prospectivity Score</span>
          </span>
        </div>
        <div style={{ fontSize: '0.7rem', color: '#94a3b8', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: 6 }}>
          <ShieldAlert size={13} color="#f59e0b" />
          <span>Surface AI screening index — not subsurface drilling depth</span>
        </div>
      </div>

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
      </div>
    </div>
  );
}
