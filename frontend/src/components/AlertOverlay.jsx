import React from "react";

/**
 * AlertOverlay.jsx
 * Shows current detected objects with direction + danger level
 * Shows recent voice alert history
 */

const DANGER_ICONS = { 3: "🔴", 2: "🟡", 1: "🟢" };
const DIR_ARROWS   = { left: "←", center: "↑", right: "→" };
const ZONE_COLOR   = { near: "#ff4444", medium: "#ffaa00", far: "#44cc44", unknown: "#888" };

export default function AlertOverlay({ alerts, detections, depthZones, language, isRunning }) {
  if (!isRunning) return null;

  // Build combined detection+depth list
  const combined = detections.slice(0, 8).map(det => {
    const zone = depthZones.find(z => z.label === det.label) || {};
    return {
      ...det,
      depth_zone: zone.depth_zone || "unknown",
    };
  });

  return (
    <div className="alert-panel">

      {/* ── Object Detection List ── */}
      <div className="detection-list">
        <h3 className="panel-title">📍 Detected Objects</h3>
        {combined.length === 0 ? (
          <p className="empty-msg">No objects detected</p>
        ) : (
          combined.map((det, i) => (
            <div
              key={i}
              className={`detection-item danger-${det.danger_level}`}
              style={{ borderLeft: `4px solid ${ZONE_COLOR[det.depth_zone]}` }}
            >
              <span className="det-icon">{DANGER_ICONS[det.danger_level] || "⚪"}</span>
              <span className="det-label">
                {det.translations?.[language] || det.label.replace(/_/g, " ")}
              </span>
              <span className="det-dir">{DIR_ARROWS[det.direction]}</span>
              <span
                className="det-zone"
                style={{ color: ZONE_COLOR[det.depth_zone] }}
              >
                {det.depth_zone}
              </span>
              <span className="det-conf">{Math.round(det.confidence * 100)}%</span>
            </div>
          ))
        )}
      </div>

      {/* ── Recent Voice Alerts ── */}
      <div className="alert-history">
        <h3 className="panel-title">🔊 Voice Alerts</h3>
        {alerts.length === 0 ? (
          <p className="empty-msg">No alerts yet</p>
        ) : (
          alerts.map((a, i) => (
            <div key={i} className={`alert-item ${i === 0 ? "alert-latest" : ""}`}>
              <span className="alert-text">{a.text}</span>
            </div>
          ))
        )}
      </div>

    </div>
  );
}
