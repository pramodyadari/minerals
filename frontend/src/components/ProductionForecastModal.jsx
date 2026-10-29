import React, { useState, useEffect } from 'react';
import { getApiUrl } from '../apiConfig';
import {
  TrendingUp,
  X,
  CloudRain,
  Wrench,
  AlertOctagon,
  Calendar,
  CheckCircle2,
  FileSpreadsheet,
  Download,
  Activity,
  Layers
} from 'lucide-react';

export default function ProductionForecastModal({ isOpen, onClose, selectedMineral = 'Manganese' }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch(getApiUrl(`/production-forecast?mineral=${selectedMineral}`))
      .then((res) => res.json())
      .then((resData) => {
        setData(resData);
      })
      .catch((err) => {
        console.error('Failed to fetch production data:', err);
      })
      .finally(() => setLoading(false));
  }, [isOpen, selectedMineral]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(5, 8, 15, 0.85)',
        backdropFilter: 'blur(8px)',
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
          border: '1.5px solid rgba(236, 72, 153, 0.4)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '850px',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(236, 72, 153, 0.2)',
          padding: '1.75rem',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1.25rem' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.25), rgba(168, 85, 247, 0.35))',
              border: '1.5px solid #ec4899',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(236, 72, 153, 0.4)',
            }}
          >
            <TrendingUp size={22} color="#ec4899" />
          </div>
          <div>
            <h2 style={{ fontFamily: 'var(--font-serif)', fontSize: '1.25rem', color: '#f1f5f9' }}>
              Operational Production & Shortfall Forecast
            </h2>
            <div style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
              Predict production shortfalls using historical mine telemetry and operational parameters
            </div>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '3rem 0', color: '#ec4899' }}>
            <Activity size={32} className="animate-spin" style={{ margin: '0 auto 1rem' }} />
            <p>Loading historical mine operational database...</p>
          </div>
        ) : data?.status !== 'AVAILABLE' ? (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              borderRadius: '12px',
              padding: '2rem',
              textAlign: 'center',
            }}
          >
            <AlertOctagon size={36} color="#f59e0b" style={{ margin: '0 auto 0.75rem' }} />
            <h3 style={{ fontSize: '1.1rem', color: '#f1f5f9', marginBottom: '0.5rem' }}>
              Production Telemetry Awaiting Concession Data
            </h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8', maxWidth: '500px', margin: '0 auto' }}>
              {data?.message || 'Production telemetry is currently calibrated for Manganese operations in the Balaghat corridor.'}
            </p>
          </div>
        ) : (
          <div>
            {/* KPI Cards Row */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
                gap: '12px',
                marginBottom: '1.5rem',
              }}
            >
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Tracked Timeline</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#f1f5f9', marginTop: '2px' }}>
                  {data.total_months_tracked} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Months</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: '#38bdf8' }}>2016 – 2026 Monthly Log</div>
              </div>

              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Planned Production</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#f1f5f9', marginTop: '2px' }}>
                  {(data.overall_planned_tonnes / 1000).toFixed(1)}k <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>T</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Total Scheduled Volume</div>
              </div>

              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '10px',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase' }}>Actual Mined Volume</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#10b981', marginTop: '2px' }}>
                  {(data.overall_actual_tonnes / 1000).toFixed(1)}k <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>T</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: '#10b981' }}>Verified Dispatch</div>
              </div>

              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(236, 72, 153, 0.3)',
                  borderRadius: '10px',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: '0.72rem', color: '#ec4899', textTransform: 'uppercase' }}>Cumulative Shortfall</div>
                <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#ec4899', marginTop: '2px' }}>
                  {data.shortfall_pct}%
                </div>
                <div style={{ fontSize: '0.68rem', color: '#ec4899' }}>
                  {(data.overall_shortfall_tonnes / 1000).toFixed(1)}k Tonnes Gap
                </div>
              </div>
            </div>

            {/* Time Series Table / Preview */}
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '10px',
                padding: '14px',
                marginBottom: '1.5rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f1f5f9', textTransform: 'uppercase' }}>
                  Recent 24-Month Operations & Shortfall Trend (Balaghat Belt)
                </span>
                <span style={{ fontSize: '0.7rem', color: '#38bdf8', fontFamily: 'var(--font-mono)' }}>
                  Avg Availability: {data.avg_equipment_availability_pct}%
                </span>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                      <th style={{ padding: '6px 8px' }}>Month</th>
                      <th style={{ padding: '6px 8px' }}>Planned (T)</th>
                      <th style={{ padding: '6px 8px' }}>Actual (T)</th>
                      <th style={{ padding: '6px 8px' }}>Shortfall (T)</th>
                      <th style={{ padding: '6px 8px' }}>Rainfall (mm)</th>
                      <th style={{ padding: '6px 8px' }}>Downtime (hr)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_time_series.slice(-10).map((r, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)', color: '#e2e8f0' }}>
                        <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)' }}>{r.date}</td>
                        <td style={{ padding: '6px 8px' }}>{Math.round(r.planned_production_tonnes)}</td>
                        <td style={{ padding: '6px 8px', color: '#10b981' }}>{Math.round(r.actual_production_tonnes)}</td>
                        <td style={{ padding: '6px 8px', color: '#ec4899', fontWeight: 700 }}>
                          {Math.round(r.production_shortfall_tonnes)}
                        </td>
                        <td style={{ padding: '6px 8px' }}>{r.rainfall_mm} mm</td>
                        <td style={{ padding: '6px 8px' }}>{r.equipment_downtime_hr} hr</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Operational Risk Drivers */}
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f1f5f9', textTransform: 'uppercase', marginBottom: '8px' }}>
                Operational Shortfall Mitigation Factors
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '10px' }}>
                {data.key_risk_drivers.map((drv, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(15, 23, 42, 0.65)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: '8px',
                      padding: '10px 12px',
                    }}
                  >
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#38bdf8' }}>{drv.factor}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '3px' }}>{drv.impact}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
