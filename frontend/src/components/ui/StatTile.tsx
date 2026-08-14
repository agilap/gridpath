interface StatTileProps {
  label: string;
  value: string | number;
  hero?: boolean;
  delta?: string;
  className?: string;
}

export function StatTile({ label, value, hero = false, delta, className = "" }: StatTileProps) {
  return (
    <div className={`stat-tile${className ? ` ${className}` : ""}`}>
      <span className="overline">{label}</span>
      <span className={`stat-number${hero ? " stat-number--hero" : ""}`}>{value}</span>
      {delta && (
        <span style={{ color: "var(--text-secondary)", fontSize: "0.875rem" }}>{delta}</span>
      )}
    </div>
  );
}
