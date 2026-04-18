import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

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
  const [error, setError] = useState("");

  async function refreshStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/status`);
      if (!response.ok) {
        throw new Error(`status ${response.status}`);
      }
      const data = await response.json();
      setMode(data.mode);
      setRemainingTime(data.remaining_time);
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
      const response = await fetch(commandUrl(command));
      if (!response.ok) {
        throw new Error(`${command} ${response.status}`);
      }
      const data = await response.json();
      setMode(data.mode);
      setRemainingTime(data.remaining_time);
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
      <section className="panel" aria-label="Pomodoro controls">
        <p className="label">Mode</p>
        <h1>{mode}</h1>
        <div className="timer">{formatTime(remainingTime)}</div>
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
          <button onClick={() => sendCommand("start")}>Start</button>
          <button onClick={() => sendCommand("pause")}>Pause</button>
          <button onClick={() => sendCommand("break")}>Break</button>
          <button onClick={() => sendCommand("reset")}>Reset</button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
