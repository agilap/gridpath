type BadgeVariant = "feature" | "refactor" | "bugfix" | "test" | "arch" | "consistency";

const DATA_COLORS: Record<BadgeVariant, string> = {
  feature:     "#2FD4A7",
  refactor:    "#6E8BFF",
  bugfix:      "#FF6E8A",
  test:        "#38E1FF",
  arch:        "#B98CFF",
  consistency: "#7AE0FF",
};

interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant, children, className = "" }: BadgeProps) {
  const color = DATA_COLORS[variant];
  return (
    <span
      className={`badge${className ? ` ${className}` : ""}`}
      style={{
        background: `color-mix(in oklab, ${color} 14%, transparent)`,
        border:     `1px solid color-mix(in oklab, ${color} 35%, transparent)`,
        color,
      }}
    >
      {children}
    </span>
  );
}
