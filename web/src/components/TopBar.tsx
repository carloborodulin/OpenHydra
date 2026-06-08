import { useEffect, useState } from "react";

export function TopBar({ window: win }: { window?: string }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const time = now.toLocaleTimeString("en-US", { hour12: false });
  const date = now.toISOString().slice(0, 10);

  return (
    <header className="panel flex items-center justify-between border-x-0 border-t-0 px-5 py-2.5">
      <div className="flex items-baseline gap-4">
        <span className="display glow text-2xl font-black tracking-[0.32em] text-accent">
          OPENHYDRA
        </span>
        <span className="mono hidden text-[0.6rem] tracking-[0.28em] text-muted uppercase md:block">
          UCR Command · FBI Crime Data Explorer
        </span>
      </div>
      <div className="mono flex items-center gap-5 text-[0.62rem] tracking-widest text-muted uppercase">
        {win && (
          <span>
            Window <span className="text-ink">{win}</span>
          </span>
        )}
        <span className="flex items-center gap-2">
          <span className="live-dot" />
          <span className="text-good">Live Feed</span>
        </span>
        <span className="text-ink tabular-nums">
          {date} · {time}
        </span>
      </div>
    </header>
  );
}
