import { useId } from "react";
import type { WineColor } from "../types";

/** Teinte du vin dans le verre, selon la couleur choisie ou recommandée. */
export const LIQUID: Record<WineColor | "any", string> = {
  any: "#6B1430",
  red: "#6B1430",
  white: "#E4C96A",
  rose: "#EE9C93",
  sparkling: "#E6D49A",
  dessert: "#B4601C",
};

interface GlassProps {
  /** Niveau de remplissage entre 0 et 1. */
  level: number;
  color?: WineColor | "any";
  /** Affiche des bulles (vins effervescents). */
  bubbles?: boolean;
  className?: string;
  label?: string;
}

// Géométrie du verre (viewBox 200 × 320) : le calice va de y=24 (bord) à y=172 (fond).
const BOWL = "M44 24 H156 C157 112 146 166 100 172 C54 166 43 112 44 24 Z";
const FULL_Y = 52; // surface du liquide quand le verre est plein
const EMPTY_Y = 176; // surface du liquide quand il est vide

/**
 * Verre à vin dessiné en SVG. Le liquide monte avec `level` et prend la teinte du vin :
 * c'est le fil conducteur visuel du questionnaire (progression) et des résultats (score).
 */
export function Glass({ level, color = "any", bubbles = false, className, label }: GlassProps) {
  const clip = useId();
  const clamped = Math.min(1, Math.max(0, level));
  const surface = EMPTY_Y - clamped * (EMPTY_Y - FULL_Y);
  const tint = LIQUID[color];

  return (
    <svg
      className={`glass ${className ?? ""}`}
      viewBox="0 0 200 320"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <defs>
        <clipPath id={clip}>
          <path d={BOWL} />
        </clipPath>
      </defs>

      <g clipPath={`url(#${clip})`}>
        <g className="glass__liquid" style={{ transform: `translateY(${surface}px)`, color: tint }}>
          {/* Vague : deux périodes identiques qui défilent en boucle. */}
          <path
            className="glass__wave"
            d="M-200 6 Q-150 -2 -100 6 T0 6 T100 6 T200 6 T300 6 T400 6 V220 H-200 Z"
            fill="currentColor"
          />
          <rect x="0" y="12" width="200" height="220" fill="currentColor" />
          {bubbles &&
            [52, 78, 104, 128, 146].map((x, i) => (
              <circle
                key={x}
                className="glass__bubble"
                cx={x}
                cy={110}
                r={1.6 + (i % 2)}
                style={{ animationDelay: `${i * 0.45}s` }}
              />
            ))}
        </g>
      </g>

      {/* Contour, reflet, jambe et pied. */}
      <path d={BOWL} className="glass__outline" />
      <path d="M58 44 C57 96 62 130 76 150" className="glass__shine" />
      <path d="M100 172 V286" className="glass__outline" />
      <path d="M58 292 Q100 280 142 292" className="glass__outline" />
    </svg>
  );
}
