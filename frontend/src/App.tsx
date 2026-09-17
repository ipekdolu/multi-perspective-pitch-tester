import { useState } from "react";
import "./App.css";
import { approveRun, challengeRun, doneRun, rejectRun, startRun } from "./api";
import { ApprovalGate } from "./components/ApprovalGate";
import { ChallengeForm } from "./components/ChallengeForm";
import { PersonaPanel } from "./components/PersonaPanel";
import { SynthesisView } from "./components/SynthesisView";
import type { RunState } from "./types";

function App() {
  const [pitch, setPitch] = useState("");
  const [run, setRun] = useState<RunState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wrap = async (action: () => Promise<RunState>) => {
    setBusy(true);
    setError(null);
    try {
      setRun(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const handleStart = () => {
    if (!pitch.trim()) return;
    wrap(() => startRun(pitch.trim()));
  };

  const interruptType = run?.interrupt?.type ?? null;

  return (
    <div className="app">
      <h1>Multi-perspective pitch tester</h1>

      {!run && (
        <div className="start-section">
          <textarea
            placeholder="Describe your pitch..."
            value={pitch}
            onChange={(e) => setPitch(e.target.value)}
          />
          <button onClick={handleStart} disabled={busy}>
            {busy ? "Starting..." : "Start"}
          </button>
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {run && (
        <div className="run-section">
          {Object.entries(run.persona_threads).map(([personaId, messages]) => (
            <PersonaPanel key={personaId} personaId={personaId} messages={messages} />
          ))}

          {interruptType === "present_findings" && (
            <ChallengeForm
              personaIds={Object.keys(run.persona_threads)}
              busy={busy}
              onChallenge={(personaId, text) =>
                wrap(() => challengeRun(run.thread_id, personaId, text))
              }
              onDone={() => wrap(() => doneRun(run.thread_id))}
            />
          )}

          {interruptType === "human_approval_gate" && (
            <ApprovalGate
              busy={busy}
              onApprove={() => wrap(() => approveRun(run.thread_id))}
              onReject={() => wrap(() => rejectRun(run.thread_id))}
            />
          )}

          {run.synthesis && <SynthesisView synthesis={run.synthesis} />}
        </div>
      )}
    </div>
  );
}

export default App;
