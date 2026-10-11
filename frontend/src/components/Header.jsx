import React, { useEffect, useState } from 'react';
import {
  Compass,
  Sparkles,
  Home,
  LayoutDashboard,
  Map as MapIcon,
  BarChart3,
  Settings,
  User,
  Activity,
  CheckCircle2,
  ChevronDown
} from 'lucide-react';

export default function Header({
  activeTab = 'home',
  onTabChange,
  onOpenSpecimenClassifier,
  onOpenProductionForecast,
}) {
  const [healthStatus, setHealthStatus] = useState('checking');
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'healthy') {
          setHealthStatus('online');
        } else {
          setHealthStatus('degraded');
        }
      })
      .catch(() => {
        setHealthStatus('offline');
      });
  }, []);

  const navTabs = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'map', label: 'Map', icon: MapIcon },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <header className="top-header" style={{ position: 'sticky', top: 0, zIndex: 1000 }}>
      {/* Brand Logo & Name */}
      <div className="brand-wrapper" onClick={() => onTabChange && onTabChange('home')} style={{ cursor: 'pointer' }}>
        <div className="brand-icon-logo">
          <div className="brand-logo-glow" />
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M3 19L9 8L14 15L17 11L21 19H3Z" fill="url(#brandGrad)" />
            <circle cx="17.5" cy="6.5" r="2.5" fill="#00f0ff" />
            <path d="M15.5 4.5L19.5 8.5" stroke="#38bdf8" strokeWidth="1.5" />
            <defs>
              <linearGradient id="brandGrad" x1="3" y1="8" x2="21" y2="19" gradientUnits="userSpaceOnUse">
                <stop stopColor="#38bdf8" />
                <stop offset="1" stopColor="#a855f7" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div>
          <h1 className="brand-title-main">
            AI Mineral Intelligence
          </h1>
          <div className="brand-subtitle-tagline">
            Discover &bull; Analyze &bull; Explore
          </div>
        </div>
      </div>

      {/* Center Navigation Tabs (Home, Dashboard, Map, Analytics, Settings) */}
      <nav className="nav-tabs-bar">
        {navTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              className={`nav-tab-btn ${isActive ? 'active' : ''}`}
              onClick={() => onTabChange && onTabChange(tab.id)}
              id={`nav-tab-${tab.id}`}
            >
              <Icon size={15} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Right User & Specimen Classifier Actions */}
      <div className="header-actions-right">
        {/* Specimen Classifier Trigger */}
        <button
          className="btn-specimen-classifier"
          onClick={onOpenSpecimenClassifier}
          title="Classify rock or ore specimen image using PyTorch 4-class CNN"
          id="btn-open-specimen-modal"
        >
          <Sparkles size={15} color="#00f0ff" />
          <span>Specimen Classifier</span>
        </button>

        {/* User Profile Pill */}
        <div
          className="user-profile-badge"
          onClick={() => setUserDropdownOpen(!userDropdownOpen)}
          style={{ position: 'relative', cursor: 'pointer' }}
        >
          <div className="user-avatar-circle">
            <User size={15} color="#e2e8f0" />
          </div>
          <div className="user-info-text">
            <span className="user-welcome">Welcome</span>
            <span className="user-name">Researcher</span>
          </div>
          <ChevronDown size={14} color="#94a3b8" />

          {/* User Dropdown */}
          {userDropdownOpen && (
            <div
              className="user-dropdown-menu"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="dropdown-status-row">
                <div
                  className="status-dot"
                  style={{
                    backgroundColor:
                      healthStatus === 'online'
                        ? '#10b981'
                        : healthStatus === 'offline'
                        ? '#ef4444'
                        : '#f59e0b',
                  }}
                />
                <span>
                  {healthStatus === 'online'
                    ? 'Backend Engine Online (4 Minerals)'
                    : healthStatus === 'offline'
                    ? 'Backend Disconnected'
                    : 'Verifying Services...'}
                </span>
              </div>
              <div className="dropdown-divider" />
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setUserDropdownOpen(false);
                  onOpenSpecimenClassifier();
                }}
              >
                <Sparkles size={14} color="#00f0ff" />
                <span>AI Specimen Image Classifier</span>
              </button>
              <button
                type="button"
                className="dropdown-item"
                onClick={() => {
                  setUserDropdownOpen(false);
                  if (onOpenProductionForecast) onOpenProductionForecast();
                }}
              >
                <BarChart3 size={14} color="#ec4899" />
                <span>Operational Production Forecast</span>
              </button>
              <div className="dropdown-divider" />
              <div className="dropdown-footer-text">
                Fixed 4 Minerals: Coal, Manganese, Iron Ore, Bauxite
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
