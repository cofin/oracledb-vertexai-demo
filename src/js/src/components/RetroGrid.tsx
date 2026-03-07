interface RetroGridProps {
  className?: string
  angle?: number
}

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ")
}

export function RetroGrid({ className, angle = 65 }: RetroGridProps) {
  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden opacity-60 [perspective:200px] z-0",
        className,
      )}
      style={{ "--grid-angle": `${angle}deg` } as React.CSSProperties}
    >
      <style>{`
        @keyframes grid {
          0% { transform: translateY(-50%); }
          100% { transform: translateY(0); }
        }
        @keyframes star-drift {
          0% { background-position: 0 0; }
          100% { background-position: 140px -100px; }
        }
        .animate-grid {
          animation: grid 15s linear infinite;
        }
        .animate-star-drift {
          animation: star-drift 22s linear infinite;
        }
      `}</style>

      {/* Stars */}
      <div
        className="absolute inset-0 opacity-100 animate-star-drift motion-reduce:animate-none"
        style={{
          backgroundImage: [
            "radial-gradient(2px 2px at 15% 20%, var(--text-base) 0, transparent 60%)",
            "radial-gradient(1.5px 1.5px at 35% 12%, var(--text-base) 0, transparent 60%)",
            "radial-gradient(1.5px 1.5px at 65% 18%, var(--text-base) 0, transparent 60%)",
            "radial-gradient(2px 2px at 82% 26%, var(--text-base) 0, transparent 60%)",
            "radial-gradient(1.5px 1.5px at 55% 32%, var(--text-base) 0, transparent 60%)",
          ].join(","),
        }}
      />

      {/* Grid */}
      <div className="absolute inset-0 [transform:rotateX(var(--grid-angle))]">
        <div
          className={cn(
            "animate-grid motion-reduce:animate-none",
            "opacity-50 [background-repeat:repeat] [background-size:60px_60px] [height:300vh] [inset:0%_0px] [margin-left:-50%] [transform-origin:100%_0_0] [width:600vw]",
          )}
          style={{
            backgroundImage:
              "linear-gradient(to right, var(--text-muted) 1px, transparent 0), linear-gradient(to bottom, var(--text-muted) 1px, transparent 0)",
          }}
        />
        <div
          className={cn(
            "animate-grid motion-reduce:animate-none",
            "opacity-20 [background-repeat:repeat] [background-size:90px_90px] [height:240vh] [inset:0%_0px] [margin-left:-45%] [transform-origin:100%_0_0] [width:520vw]",
          )}
          style={{
            animationDuration: "22s",
            backgroundImage:
              "linear-gradient(to right, var(--text-muted) 1px, transparent 0), linear-gradient(to bottom, var(--text-muted) 1px, transparent 0)",
          }}
        />
      </div>

      {/* Gradient overlay */}
      <div
        className="absolute inset-0"
        style={{
          background: "linear-gradient(to top, var(--bg-canvas) 0%, transparent 80%)",
        }}
      />

      {/* Vignette + noise */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.15) 100%)" }}
      />
    </div>
  )
}
