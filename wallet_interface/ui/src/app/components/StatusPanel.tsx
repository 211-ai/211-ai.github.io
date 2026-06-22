export function StatusPanel({ label, value, tone, onClick }: { label: string; value: string; tone: string; onClick?: () => void }) {
  return (
    <div className={`status-panel panel-${tone}${onClick ? " status-panel-clickable" : ""}`} onClick={onClick} role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined} onKeyDown={onClick ? (e) => (e.key === "Enter" || e.key === " ") && onClick() : undefined}>
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}
