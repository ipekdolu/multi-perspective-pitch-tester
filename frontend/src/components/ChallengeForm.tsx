import { useState } from "react";

interface Props {
  personaIds: string[];
  onChallenge: (personaId: string, text: string) => void;
  onDone: () => void;
  busy: boolean;
}

export function ChallengeForm({ personaIds, onChallenge, onDone, busy }: Props) {
  const [personaId, setPersonaId] = useState(personaIds[0] ?? "");
  const [text, setText] = useState("");

  const submit = () => {
    if (!text.trim()) return;
    onChallenge(personaId, text.trim());
    setText("");
  };

  return (
    <div className="challenge-section">
      <div className="challenge-row">
        <select value={personaId} onChange={(e) => setPersonaId(e.target.value)} disabled={busy}>
          {personaIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Challenge text..."
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={busy}
        />
        <button onClick={submit} disabled={busy}>
          Send challenge
        </button>
      </div>
      <button onClick={onDone} disabled={busy}>
        Done challenging
      </button>
    </div>
  );
}
