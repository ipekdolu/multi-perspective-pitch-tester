import type { Synthesis } from "../types";

export function SynthesisView({ synthesis }: { synthesis: Synthesis }) {
  return (
    <div className="synthesis-section">
      <h3>Synthesis</h3>
      <div className="synthesis-block">
        <h4>Agreement</h4>
        <ul>
          {synthesis.agreement.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
        <h4>Divergence</h4>
        <ul>
          {synthesis.divergence.map((point, i) => (
            <li key={i}>{point}</li>
          ))}
        </ul>
        <h4>Biggest risk</h4>
        <p>{synthesis.biggest_risk}</p>
      </div>
    </div>
  );
}
