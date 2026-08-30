/**
 * WinBack.AI wordmark and mark.
 *
 * Drawn as SVG rather than shipped as PNGs: the mark appears at 20px in a
 * sidebar and 40px in a nav, it has to sit on both white and Prussian Blue,
 * and an inline path costs nothing to load and never goes soft on a retina
 * screen. Swap in the raster originals by dropping them in frontend/public and
 * pointing `MarkImage` at them if exact brand files are ever required.
 *
 * `variant="dark"` is for placement on a dark ground (the product sidebar),
 * not a dark-mode theme: the strokes go white and the arrow keeps the accent.
 */

const BRAND = "#2f80f0";

export function LogoMark({ size = 32, variant = "light", className = "" }) {
  const dark = variant === "dark";
  const stroke = dark ? "#ffffff" : BRAND;
  const arrow = dark ? "#4da3ff" : BRAND;

  return (
    <svg
      className={`logo-mark ${className}`}
      width={size}
      height={size * (104 / 128)}
      viewBox="0 0 128 104"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* The W, drawn as one continuous zigzag that turns upward at the end. */}
      <path
        d="M12 26 L38 86 L60 30 L82 76 L106 32"
        stroke={stroke}
        strokeWidth="17"
        strokeLinejoin="miter"
        strokeLinecap="butt"
      />
      {/* The rise breaking out of the W — the whole point of the mark. */}
      <path d="M118 10 L118.8 40 L92.4 25.6 Z" fill={arrow} />
    </svg>
  );
}

export default function Logo({ size = 30, variant = "light", showWord = true, className = "" }) {
  return (
    <span className={`logo logo-${variant} ${className}`}>
      <LogoMark size={size} variant={variant} />
      {showWord && (
        <span className="logo-word" style={{ fontSize: size * 0.62 }}>
          WinBack<span className="logo-dot">.</span>
          <span className="logo-ai">AI</span>
        </span>
      )}
    </span>
  );
}
