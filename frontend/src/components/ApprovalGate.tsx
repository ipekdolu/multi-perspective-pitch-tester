interface Props {
  onApprove: () => void;
  onReject: () => void;
  busy: boolean;
}

export function ApprovalGate({ onApprove, onReject, busy }: Props) {
  return (
    <div className="approval-section">
      <button onClick={onApprove} disabled={busy}>
        Approve
      </button>
      <button onClick={onReject} disabled={busy}>
        Reject (another round)
      </button>
    </div>
  );
}
