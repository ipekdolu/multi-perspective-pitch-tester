interface Props {
  onApprove: () => void;
  onReject: () => void;
  busy: boolean;
}

export function ApprovalGate({ onApprove, onReject, busy }: Props) {
  return (
    <div className="card approval-section">
      <p className="section-label">Ready to synthesize?</p>
      <button onClick={onApprove} disabled={busy}>
        Approve
      </button>
      <button className="secondary" onClick={onReject} disabled={busy}>
        Reject (another round)
      </button>
    </div>
  );
}
