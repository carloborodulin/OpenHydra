import { useEffect, useState } from "react";
import { ThemeToggle } from "./ThemeToggle";

export function TopBar({ window: win, onMenuClick }: { window?: string; onMenuClick?: () => void }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const time = now.toLocaleTimeString("en-US", { hour12: false });
  const date = now.toISOString().slice(0, 10);

  return (
    <header className="panel flex items-center justify-between border-x-0 border-t-0 px-3 py-2 lg:px-5 lg:py-2.5">
      <div className="flex min-w-0 items-center gap-2 lg:gap-4">
        {onMenuClick && (
          <button
            type="button"
            onClick={onMenuClick}
            aria-label="Open navigation menu"
            className="flex h-12 w-12 shrink-0 cursor-pointer items-center justify-center border border-line text-accent transition hover:border-line-strong lg:hidden"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden
            >
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>
        )}
        <div className="flex min-w-0 items-baseline gap-4">
          <span className="display glow text-xl font-black tracking-[0.18em] text-accent lg:text-2xl lg:tracking-[0.32em]">
            OPENHYDRA
          </span>
          <span className="mono hidden text-[0.6rem] tracking-[0.28em] text-muted uppercase md:block">
            UCR Command · FBI Crime Data Explorer
          </span>
        </div>
      </div>
      <div className="mono flex items-center gap-2 text-[0.62rem] tracking-widest text-muted uppercase lg:gap-5">
        {win && (
          <span className="hidden sm:inline">
            Window <span className="text-ink">{win}</span>
          </span>
        )}
        <span className="flex items-center gap-2">
          <span className="live-dot" />
          <span className="hidden text-good sm:inline">Live Feed</span>
        </span>
        <span className="hidden text-ink tabular-nums sm:inline">
          {date} · {time}
        </span>
        <ThemeToggle />
      </div>
    </header>
  );
}
