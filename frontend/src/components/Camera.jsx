import React, { useRef, useEffect, useCallback, useState } from "react";

/**
 * Camera.jsx
 * - Works on laptop webcam, Android, iPhone via browser getUserMedia()
 * - QR code link so user can open on phone
 * - Sends frames to parent via onFrame callback
 * - Shows annotated frame overlay from backend
 * - Low-light detection
 */
export default function Camera({
  isRunning,
  onFrame,
  frameInterval = 2000,
  cameraMode = "environment",
  annotatedFrame,
  onLowLight,
}) {
  const videoRef      = useRef(null);
  const canvasRef     = useRef(null);
  const streamRef     = useRef(null);
  const intervalRef   = useRef(null);
  const [camError, setCamError]   = useState("");
  const [camReady, setCamReady]   = useState(false);
  const [showQR, setShowQR]       = useState(false);

  // ── Start camera stream ────────────────────────────────────
  const startCamera = useCallback(async () => {
    try {
      // Stop existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
      setCamReady(false);

      const constraints = {
        video: {
          facingMode: cameraMode,       // "environment" = rear cam, "user" = front
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 15 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        const playPromise = videoRef.current.play();
        if (playPromise && typeof playPromise.catch === "function") {
          playPromise.catch(() => {
            // Interrupted by a subsequent load/srcObject swap — harmless,
            // the most recent stream still wins and renders correctly.
          });
        }
        setCamReady(true);
        setCamError("");
      }
    } catch (err) {
      console.error("Camera error:", err);
      setCamError(
        err.name === "NotAllowedError"
          ? "Camera permission denied. Please allow camera access."
          : "Camera not available. Try opening on your phone via the QR code."
      );
      setCamReady(false);
    }
  }, [cameraMode]);

  useEffect(() => {
    startCamera();
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, [startCamera]);

  // ── Capture frame → base64 → send to parent ───────────────
  const captureFrame = useCallback(() => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !camReady) return;

    const ctx = canvas.getContext("2d");
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Low-light detection: check average brightness
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imgData.data;
    let brightness = 0;
    for (let i = 0; i < data.length; i += 4) {
      brightness += (data[i] * 0.299 + data[i+1] * 0.587 + data[i+2] * 0.114);
    }
    brightness /= (data.length / 4);
    onLowLight && onLowLight(brightness < 60);

    // Low-light enhancement: CLAHE-like boost via canvas
    if (brightness < 60) {
      const scale = Math.min(2.5, 120 / brightness);
      ctx.filter = `brightness(${scale})`;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      ctx.filter = "none";
    }

    const imageB64 = canvas.toDataURL("image/jpeg", 0.7);
    onFrame(imageB64);
  }, [camReady, onFrame, onLowLight]);

  // ── Start/stop frame capture interval ─────────────────────
  useEffect(() => {
    if (isRunning && camReady) {
      intervalRef.current = setInterval(captureFrame, frameInterval);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [isRunning, camReady, captureFrame, frameInterval]);

  // ── Build QR code link (current page URL) ────────────────
  // IMPORTANT: if you're viewing this on your laptop as "localhost:3000",
  // window.location.href will literally contain "localhost", which on a
  // phone resolves to the phone itself — not your laptop. To make the QR
  // code work, open the app on your laptop using your laptop's network IP
  // (e.g. http://192.168.1.23:3000) instead of localhost, *then* the QR
  // code generated here will correctly point your phone at your laptop.
  const phoneLink = window.location.href;
  const isLocalhost = /^https?:\/\/(localhost|127\.0\.0\.1)/i.test(phoneLink);
  const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(phoneLink)}`;

  return (
    <div className="camera-wrapper">
      {/* Live video feed */}
      <div className="video-container">
        <video
          ref={videoRef}
          className="video-feed"
          playsInline
          muted
          aria-label="Camera feed"
        />

        {/* Annotated frame overlay from backend */}
        {annotatedFrame && isRunning && (
          <img
            src={annotatedFrame}
            className="annotated-overlay"
            alt="Detection overlay"
          />
        )}

        {/* Recording indicator */}
        {isRunning && <div className="rec-dot" aria-label="Recording" />}
      </div>

      {/* Hidden canvas for frame capture */}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Error message */}
      {camError && (
        <div className="cam-error" role="alert">
          ⚠️ {camError}
        </div>
      )}

      {/* QR Code for phone */}
      <div className="qr-section">
        <button
          className="btn-qr"
          onClick={() => setShowQR(s => !s)}
          aria-expanded={showQR}
        >
          📱 {showQR ? "Hide" : "Use Phone Camera"}
        </button>

        {showQR && (
          <div className="qr-panel">
            {isLocalhost ? (
              <p className="qr-hint" style={{ color: "var(--danger, #e54)" }}>
                ⚠️ This page is open at "localhost" — your phone can't reach that.
                Open this app on your laptop using your laptop's network IP
                (e.g. http://192.168.x.x:3000) instead, then scan again.
              </p>
            ) : (
              <>
                <p>Scan with any phone — works on Android &amp; iPhone</p>
                <img src={qrSrc} alt="QR code to open on phone" className="qr-img" />
                <p className="qr-hint">No app install needed — opens in mobile browser</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
