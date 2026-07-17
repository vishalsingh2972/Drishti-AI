import React, { useState, useRef } from "react";

/**
 * VoiceChat.jsx
 * Conversational AI: user holds button → speaks → AI answers
 * Uses MediaRecorder to capture audio → sends to /api/chat
 * AI responds in the user's chosen language
 */
export default function VoiceChat({ apiUrl, language, sceneContext, playAudio }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isThinking, setIsThinking]   = useState(false);
  const [history, setHistory]         = useState([]);
  const [textInput, setTextInput]     = useState("");
  const [inputMode, setInputMode]     = useState("voice"); // voice | text

  const mediaRecorderRef = useRef(null);
  const chunksRef        = useRef([]);

  // ── Start recording ─────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = e => chunksRef.current.push(e.data);
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        sendAudio(blob);
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (err) {
      console.error("Mic error:", err);
      alert("Microphone access denied. Try text mode.");
    }
  };

  // ── Stop recording ────────────────────────────────────────
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // ── Send audio to backend ──────────────────────────────────
  const sendAudio = async (audioBlob) => {
    setIsThinking(true);
    try {
      const formData = new FormData();
      formData.append("audio_file", audioBlob, "question.webm");
      formData.append("language", language);
      formData.append("scene_context", JSON.stringify(sceneContext));

      const res  = await fetch(`${apiUrl}/api/chat`, { method: "POST", body: formData });
      const data = await res.json();

      if (data.success) {
        addToHistory(data.question, data.answer);
        playAudio(data.audio_b64);
      }
    } catch (err) {
      console.error("Chat error:", err);
    } finally {
      setIsThinking(false);
    }
  };

  // ── Send text question ─────────────────────────────────────
  const sendText = async () => {
    if (!textInput.trim()) return;
    const question = textInput.trim();
    setTextInput("");
    setIsThinking(true);

    try {
      const formData = new FormData();
      formData.append("text_question", question);
      formData.append("language", language);
      formData.append("scene_context", JSON.stringify(sceneContext));

      const res  = await fetch(`${apiUrl}/api/chat`, { method: "POST", body: formData });
      const data = await res.json();

      if (data.success) {
        addToHistory(question, data.answer);
        playAudio(data.audio_b64);
      }
    } catch (err) {
      console.error("Chat error:", err);
    } finally {
      setIsThinking(false);
    }
  };

  const addToHistory = (q, a) => {
    setHistory(h => [{ q, a, time: Date.now() }, ...h.slice(0, 5)]);
  };

  // ── Example quick questions by language ─────────────────
  const QUICK_QUESTIONS = {
    en: ["What's in front of me?", "Is it safe to cross?", "How many people nearby?"],
    ta: ["என் முன்னால் என்ன இருக்கிறது?", "கடந்து செல்வது பாதுகாப்பானதா?", "அருகில் எத்தனை பேர்?"],
    hi: ["मेरे सामने क्या है?", "क्या पार करना सुरक्षित है?", "पास में कितने लोग हैं?"],
    ml: ["എന്റെ മുന്നിൽ എന്തുണ്ട്?", "കടന്നുപോകാൻ സുരക്ഷിതമാണോ?"],
    kn: ["ನನ್ನ ಮುಂದೆ ಏನಿದೆ?", "ದಾಟುವುದು ಸುರಕ್ಷಿತವೇ?"],
    te: ["నా ముందు ఏముంది?", "దాటడం సురక్షితమా?"],
  };
  const quickQs = QUICK_QUESTIONS[language] || QUICK_QUESTIONS["en"];

  return (
    <div className="voice-chat">
      <div className="chat-header">
        <h3 className="panel-title">🗣️ Ask Drishti AI</h3>
        <div className="mode-toggle">
          <button
            className={`mode-btn ${inputMode === "voice" ? "active" : ""}`}
            onClick={() => setInputMode("voice")}
          >🎤 Voice</button>
          <button
            className={`mode-btn ${inputMode === "text" ? "active" : ""}`}
            onClick={() => setInputMode("text")}
          >⌨️ Text</button>
        </div>
      </div>

      {/* Quick question chips */}
      <div className="quick-questions">
        {quickQs.map((q, i) => (
          <button
            key={i}
            className="quick-chip"
            onClick={() => {
              setTextInput(q);
              setInputMode("text");
            }}
          >{q}</button>
        ))}
      </div>

      {/* Voice input */}
      {inputMode === "voice" && (
        <div className="voice-input">
          <button
            className={`btn-mic ${isRecording ? "btn-mic-active" : ""}`}
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            disabled={isThinking}
            aria-label={isRecording ? "Release to send" : "Hold to speak"}
          >
            {isThinking ? "⏳" : isRecording ? "🔴" : "🎤"}
          </button>
          <p className="mic-hint">
            {isThinking ? "Thinking..." : isRecording ? "Listening... release to send" : "Hold to ask a question"}
          </p>
        </div>
      )}

      {/* Text input */}
      {inputMode === "text" && (
        <div className="text-input-row">
          <input
            className="text-input"
            type="text"
            value={textInput}
            onChange={e => setTextInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendText()}
            placeholder="Type your question..."
            disabled={isThinking}
            aria-label="Type question"
          />
          <button
            className="btn-send"
            onClick={sendText}
            disabled={isThinking || !textInput.trim()}
            aria-label="Send question"
          >
            {isThinking ? "⏳" : "➤"}
          </button>
        </div>
      )}

      {/* Conversation history */}
      {history.length > 0 && (
        <div className="chat-history">
          {history.map((item, i) => (
            <div key={i} className="chat-turn">
              <div className="chat-q">❓ {item.q}</div>
              <div className="chat-a">🤖 {item.a}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
