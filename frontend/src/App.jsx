import React, { useState, useEffect, useRef, useCallback } from "react";
import Camera from "./components/Camera";
import AlertOverlay from "./components/AlertOverlay";
import VoiceChat from "./components/VoiceChat";
import LanguageSelector from "./components/LanguageSelector";
import "./App.css";

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:7860";

// How often to send frames to backend (ms)
const FRAME_INTERVAL = 2000;

export default function App() {
  const [language, setLanguage]         = useState("en");
  const [isRunning, setIsRunning]       = useState(false);
  const [detections, setDetections]     = useState([]);
  const [depthZones, setDepthZones]     = useState([]);
  const [narration, setNarration]       = useState("");
  const [annotatedFrame, setAnnotated]  = useState(null);
  const [alertQueue, setAlertQueue]     = useState([]);
  const [backendStatus, setBackend]     = useState("idle"); // idle | ok | error
  const [cameraMode, setCameraMode]     = useState("environment"); // environment=rear, user=front
  const [isLowLight, setIsLowLight]     = useState(false);

  const intervalRef   = useRef(null);
  const lastNarration = useRef("");
  const audioRef      = useRef(null);
  const overlayTimeoutRef = useRef(null);

  // ── Check backend health on load ──────────────────────────
  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then(r => r.json())
      .then(() => setBackend("ok"))
      .catch(() => setBackend("error"));
  }, []);

  // ── Play audio from base64 (safely interrupts any prior clip) ─
  const playAudio = useCallback((audioB64) => {
    if (!audioB64) return;

    // Fully detach the previous Audio element before starting a new one.
    // Just calling pause() isn't enough — Chrome throws "play() request
    // was interrupted by a new load request" if a play() promise is still
    // resolving when a new src is assigned. Clearing src + calling load()
    // settles the old element first.
    if (audioRef.current) {
      const prev = audioRef.current;
      prev.pause();
      prev.onended = null;
      prev.src = "";
      prev.load();
    }

    const audio = new Audio(audioB64);
    audioRef.current = audio;

    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === "function") {
      playPromise.catch(() => {
        // Autoplay block or interruption — safe to ignore, not fatal.
      });
    }
  }, []);

  // ── Hard-stop any currently playing audio ─────────────────
  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.onended = null;
      audioRef.current.src = "";
      audioRef.current.load();
      audioRef.current = null;
    }
  }, []);

  // ── Send frame to backend ─────────────────────────────────
  const processFrame = useCallback(async (imageB64) => {
    try {
      const formData = new FormData();
      formData.append("image_b64", imageB64);
      formData.append("language", language);
      formData.append("mode", "navigation");

      const res = await fetch(`${API_URL}/api/process-frame`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) return;
      const data = await res.json();

      if (data.success) {
        setDetections(data.detections || []);
        setDepthZones(data.depth_zones || []);
        setAnnotated(data.annotated_frame || null);

        // Show the annotated (boxed) frame briefly, then fall back to the
        // live video. Without this, the annotated <img> sits on top of the
        // <video> for the entire FRAME_INTERVAL, which looks like the camera
        // is frozen/black and hides the live feed almost all the time.
        clearTimeout(overlayTimeoutRef.current);
        overlayTimeoutRef.current = setTimeout(() => {
          setAnnotated(null);
        }, 900);

        // Only speak if narration changed
        if (data.narration && data.narration !== lastNarration.current) {
          setNarration(data.narration);
          lastNarration.current = data.narration;
          playAudio(data.audio_b64);

          // Add to alert queue for visual display
          setAlertQueue(q => [
            { text: data.narration, time: Date.now() },
            ...q.slice(0, 4)
          ]);
        }
      }
    } catch (err) {
      console.error("Frame processing error:", err);
    }
  }, [language, playAudio]);

  // ── Start / stop processing ───────────────────────────────
  const toggleRunning = () => {
    setIsRunning(prev => {
      const next = !prev;
      if (!next) {
        // Stopping navigation should also silence any narration
        // that's mid-playback — otherwise audio outlives the session.
        stopAudio();
        setAnnotated(null);
      }
      return next;
    });
  };

  useEffect(() => {
    if (!isRunning) {
      clearInterval(intervalRef.current);
      clearTimeout(overlayTimeoutRef.current);
    }
    return () => {
      clearInterval(intervalRef.current);
      clearTimeout(overlayTimeoutRef.current);
    };
  }, [isRunning]);

  // ── Auto-expire old alerts ────────────────────────────────
  useEffect(() => {
    const timer = setInterval(() => {
      setAlertQueue(q => q.filter(a => Date.now() - a.time < 8000));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Count danger level of current scene
  const highDangerCount = detections.filter(d => d.danger_level === 3).length;
  const personCount     = detections.filter(d => d.label === "person").length;

  return (
    <div className="app" data-lang={language}>
      {/* ── Header ── */}
      <header className="app-header">
        <div className="logo">
          <span className="logo-eye">👁</span>
          <span className="logo-text">Drishti <em>AI</em></span>
        </div>
        <div className="header-right">
          <div className={`status-dot ${backendStatus}`} title={`Backend: ${backendStatus}`} />
          <LanguageSelector value={language} onChange={setLanguage} />
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="main">
        {/* Camera feed */}
        <section className="camera-section">
          <Camera
            isRunning={isRunning}
            onFrame={processFrame}
            frameInterval={FRAME_INTERVAL}
            cameraMode={cameraMode}
            annotatedFrame={annotatedFrame}
            onLowLight={setIsLowLight}
          />

          {/* Camera controls */}
          <div className="camera-controls">
            <button
              className={`btn-main ${isRunning ? "btn-stop" : "btn-start"}`}
              onClick={toggleRunning}
              aria-label={isRunning ? "Stop navigation" : "Start navigation"}
            >
              {isRunning ? "⏹ Stop" : "▶ Start Navigation"}
            </button>

            <button
              className="btn-icon"
              onClick={() => setCameraMode(m => m === "environment" ? "user" : "environment")}
              title="Flip camera"
              aria-label="Switch camera"
            >
              🔄
            </button>
          </div>

          {/* Scene stats bar */}
          {isRunning && (
            <div className="stats-bar">
              <span className={`stat ${highDangerCount > 0 ? "stat-danger" : ""}`}>
                🚨 {highDangerCount} High Risk
              </span>
              <span className="stat">👥 {personCount} People</span>
              <span className="stat">📦 {detections.length} Objects</span>
              {isLowLight && <span className="stat stat-warn">🌙 Low Light</span>}
            </div>
          )}
        </section>

        {/* Alert overlay panel */}
        <AlertOverlay
          alerts={alertQueue}
          detections={detections}
          depthZones={depthZones}
          language={language}
          isRunning={isRunning}
        />

        {/* Conversational AI panel */}
        <VoiceChat
          apiUrl={API_URL}
          language={language}
          sceneContext={{ detections, depth_zones: depthZones }}
          playAudio={playAudio}
        />
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        <span>Drishti AI • Indian Road Edition • Free &amp; Open</span>
      </footer>
    </div>
  );
}
