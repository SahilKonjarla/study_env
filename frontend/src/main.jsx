import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const ALARM_TRANSITIONS = new Set(["focus:break", "break:idle"]);

function positiveInteger(value, fallback) {
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safeSeconds / 60).toString().padStart(2, "0");
  const remainingSeconds = (safeSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${remainingSeconds}`;
}

function App() {
  const [mode, setMode] = useState("idle");
  const [remainingTime, setRemainingTime] = useState(0);
  const [focusMinutes, setFocusMinutes] = useState(25);
  const [breakMinutes, setBreakMinutes] = useState(5);
  const [agentStatus, setAgentStatus] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [error, setError] = useState("");
  const modeRef = useRef("idle");
  const audioContextRef = useRef(null);

  async function enableSound() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) {
      setError("Audio is not supported in this browser");
      return false;
    }

    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }

    if (audioContextRef.current.state === "suspended") {
      await audioContextRef.current.resume();
    }

    setSoundEnabled(true);
    return true;
  }

  function playAlarm() {
    const audioContext = audioContextRef.current;
    if (!soundEnabled || !audioContext) {
      return;
    }

    const now = audioContext.currentTime;
    const notes = [660, 880, 660];

    notes.forEach((frequency, index) => {
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      const start = now + index * 0.22;
      const stop = start + 0.16;

      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, start);
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.2, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, stop);

      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start(start);
      oscillator.stop(stop);
    });
  }

  function applyStatus(data) {
    const previousMode = modeRef.current;
    const nextMode = data.mode;

    setMode(nextMode);
    setRemainingTime(data.remaining_time);
    modeRef.current = nextMode;

    if (ALARM_TRANSITIONS.has(`${previousMode}:${nextMode}`)) {
      playAlarm();
    }
  }

  async function refreshStatus() {
    try {
      const [statusResponse, agentResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/status`),
        fetch(`${API_BASE_URL}/agent/status`),
      ]);
      const response = statusResponse;
      if (!response.ok) {
        throw new Error(`status ${response.status}`);
      }
      if (!agentResponse.ok) {
        throw new Error(`agent ${agentResponse.status}`);
      }
      const data = await response.json();
      const agentData = await agentResponse.json();
      applyStatus(data);
      setAgentStatus(agentData);
      setError("");
    } catch (err) {
      setError(`Backend unavailable: ${err.message}`);
    }
  }

  function commandUrl(command) {
    const url = new URL(`${API_BASE_URL}/${command}`);
    if (command === "start") {
      url.searchParams.set("focus_minutes", positiveInteger(focusMinutes, 25));
      url.searchParams.set("break_minutes", positiveInteger(breakMinutes, 5));
    }
    if (command === "break") {
      url.searchParams.set("break_minutes", positiveInteger(breakMinutes, 5));
    }
    return url;
  }

  async function sendCommand(command) {
    try {
      if (command === "start" && !soundEnabled) {
        await enableSound();
      }
      const response = await fetch(commandUrl(command));
      if (!response.ok) {
        throw new Error(`${command} ${response.status}`);
      }
      const data = await response.json();
      applyStatus(data);
      setError("");
    } catch (err) {
      setError(`Command failed: ${err.message}`);
    }
  }

  useEffect(() => {
    refreshStatus();
    const timer = window.setInterval(refreshStatus, 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <main>
      <section className="dashboard" aria-label="Pomodoro controls">
        <div className="timer-area">
          <div className="topline">
            <span className={`mode-pill ${mode}`}>{mode}</span>
            <span className={agentStatus?.online ? "agent online" : "agent offline"}>
              Agent {agentStatus?.online ? "connected" : "offline"}
              {agentStatus?.seconds_since_seen !== null && agentStatus?.seconds_since_seen !== undefined
                ? ` - ${agentStatus.seconds_since_seen}s`
                : ""}
            </span>
          </div>
          <div className="timer">{formatTime(remainingTime)}</div>
          <p className="status-line">
            {mode === "focus" && "Restrictions active"}
            {mode === "break" && "Break running"}
            {mode === "idle" && "Ready when you are"}
          </p>
        </div>

        <div className="control-area">
          <div className="settings">
            <label>
              Focus minutes
              <input
                min="1"
                max="240"
                type="number"
                value={focusMinutes}
                onChange={(event) => setFocusMinutes(event.target.value)}
              />
            </label>
            <label>
              Break minutes
              <input
                min="1"
                max="120"
                type="number"
                value={breakMinutes}
                onChange={(event) => setBreakMinutes(event.target.value)}
              />
            </label>
          </div>

          <div className="actions">
            <button className="primary" onClick={() => sendCommand("start")}>Start Focus</button>
            <button className="secondary" onClick={() => sendCommand("pause")}>Pause</button>
            <button className="secondary" onClick={() => sendCommand("break")}>Start Break</button>
            <button className="secondary" onClick={() => sendCommand("reset")}>Reset</button>
          </div>

          <div className="utility-actions">
            <button className="sound" onClick={enableSound}>
              {soundEnabled ? "Sound Enabled" : "Enable Sound"}
            </button>
            <button className="cleanup" onClick={() => sendCommand("reset")}>
              Remove Restrictions
            </button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
