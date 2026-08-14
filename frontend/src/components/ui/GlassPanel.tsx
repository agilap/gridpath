import React from "react";

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  as?: React.ElementType;
}

export function GlassPanel({ children, className = "", hover = false, as: Tag = "div" }: GlassPanelProps) {
  return (
    <Tag className={`glass${hover ? " glass-hover" : ""}${className ? ` ${className}` : ""}`}>
      {children}
    </Tag>
  );
}
