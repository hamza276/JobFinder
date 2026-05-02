export function ScoreBar({ score = 0 }) {
  const percentage = Math.round(Math.max(0, Math.min(score, 1)) * 100);
  const color = percentage >= 70 ? "bg-forest" : percentage >= 40 ? "bg-gold" : "bg-rust";

  return (
    <div className="group flex items-center gap-2" title={`${percentage}% match`}>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-navy/10" aria-hidden="true">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-xs font-bold text-navy/60">{percentage}%</span>
    </div>
  );
}
