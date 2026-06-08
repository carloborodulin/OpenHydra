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
    <section className={`panel brackets enter flex min-h-0 flex-col ${className}`}>
      <header className="flex items-center justify-between border-b border-line px-4 pt-3 pb-2">
        <h2 className="panel-title">{title}</h2>
        {right}
      </header>
      <div className={`min-h-0 flex-1 p-4 ${bodyClass}`}>{children}</div>
    </section>
  );
}
