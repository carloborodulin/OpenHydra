import type { ReactNode } from "react";

interface Props {
  title: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClass?: string;
}

export function Panel({ title, right, children, className = "", bodyClass = "" }: Props) {
  return (
    <section
      className={`panel brackets enter flex min-h-[20rem] flex-col lg:min-h-0 ${className}`}
    >
      <header className="flex items-center justify-between gap-2 border-b border-line px-4 pt-3 pb-2">
        <h2 className="panel-title min-w-0 truncate">{title}</h2>
        {right && <div className="shrink-0">{right}</div>}
      </header>
      <div className={`min-h-0 flex-1 p-4 ${bodyClass}`}>{children}</div>
    </section>
  );
}
