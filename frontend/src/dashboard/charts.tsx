import { useEffect, useRef, useState, type ReactNode } from "react";
import { formatCount } from "../api";

export type Point = { date: string; value: number };

const HEIGHT = 220;
const PAD = { top: 18, right: 44, bottom: 28, left: 40 };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(600);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
}

function niceMax(value: number): number {
  if (value <= 4) return 4;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((s) => s * magnitude * 4 >= value) ?? 10;
  return step * magnitude * 4;
}

const shortDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });

export function ChartCard({ title, subtitle, children, table }: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  table?: { columns: string[]; rows: (string | number)[][] };
}) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className="dash-card chart-card">
      <header className="chart-head">
        <div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>
        {table && table.rows.length > 0 && (
          <button className="text-button" onClick={() => setShowTable(!showTable)}>{showTable ? "Chart" : "Table"}</button>
        )}
      </header>
      {showTable && table ? (
        <div className="table-wrap"><table className="data-table">
          <thead><tr>{table.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>{table.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>)}</tbody>
        </table></div>
      ) : children}
    </section>
  );
}

/** Single-series time chart: a line for levels (followers), columns for per-day totals. */
export function TimeChart({ points, kind, label }: { points: Point[]; kind: "line" | "column"; label: string }) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  if (points.length < 2) {
    return <div ref={ref} className="chart-empty">Not enough history yet. Each daily sync adds a point, so this fills in over the next few days.</div>;
  }

  const plotW = Math.max(width - PAD.left - PAD.right, 50);
  const plotH = HEIGHT - PAD.top - PAD.bottom;
  const max = niceMax(Math.max(...points.map((p) => p.value)));
  const ticks = [0, 1, 2, 3, 4].map((i) => (max / 4) * i);
  const band = plotW / points.length;
  const x = (i: number) => PAD.left + (kind === "column" ? band * i + band / 2 : (plotW * i) / (points.length - 1));
  const y = (v: number) => PAD.top + plotH - (v / max) * plotH;

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(i)},${y(p.value)}`).join("");
  const area = `${line}L${x(points.length - 1)},${y(0)}L${x(0)},${y(0)}Z`;
  const barW = Math.min(24, band - 2);
  const last = points.length - 1;

  function onMove(event: React.PointerEvent<SVGRectElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    const offset = event.clientX - box.left;
    const index = kind === "column" ? Math.floor(offset / band) : Math.round((offset / plotW) * last);
    setHover(Math.min(Math.max(index, 0), last));
  }

  return (
    <div ref={ref} className="chart">
      <svg width={width} height={HEIGHT} role="img" aria-label={`${label} over ${points.length} days`}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="grid" x1={PAD.left} x2={PAD.left + plotW} y1={y(t)} y2={y(t)} />
            <text className="tick" x={PAD.left - 8} y={y(t) + 4} textAnchor="end">{formatCount(t)}</text>
          </g>
        ))}
        <text className="tick" x={x(0)} y={HEIGHT - 8} textAnchor={kind === "column" ? "middle" : "start"}>{shortDate(points[0].date)}</text>
        <text className="tick" x={x(last)} y={HEIGHT - 8} textAnchor={kind === "column" ? "middle" : "end"}>{shortDate(points[last].date)}</text>

        {kind === "line" ? (
          <>
            <path className="area" d={area} />
            <path className="line" d={line} />
            <circle className="dot" cx={x(last)} cy={y(points[last].value)} r={4} />
            <text className="end-label" x={x(last) + 8} y={y(points[last].value) + 4}>{formatCount(points[last].value)}</text>
          </>
        ) : (
          points.map((p, i) => {
            const h = Math.max(y(0) - y(p.value), p.value ? 2 : 0);
            const left = x(i) - barW / 2;
            const top = y(0) - h;
            const r = Math.min(4, h, barW / 2);
            return (
              <path key={p.date} className={hover === i ? "bar active" : "bar"}
                d={`M${left},${y(0)}V${top + r}Q${left},${top} ${left + r},${top}H${left + barW - r}Q${left + barW},${top} ${left + barW},${top + r}V${y(0)}Z`} />
            );
          })
        )}

        {hover !== null && (
          <g pointerEvents="none">
            {kind === "line" && <line className="crosshair" x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={y(0)} />}
            {kind === "line" && <circle className="dot" cx={x(hover)} cy={y(points[hover].value)} r={5} />}
          </g>
        )}
        <rect x={PAD.left} y={PAD.top} width={plotW} height={plotH} fill="transparent"
          onPointerMove={onMove} onPointerLeave={() => setHover(null)} />
      </svg>
      {hover !== null && (
        <div className="tooltip" style={{ left: Math.min(x(hover) + 12, width - 150), top: y(points[hover].value) - 12 }}>
          <span>{new Date(points[hover].date).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</span>
          <strong>{points[hover].value.toLocaleString()} {label}</strong>
        </div>
      )}
    </div>
  );
}

export function BarList({ rows, limit = 8 }: { rows: { label: string; value: number }[]; limit?: number }) {
  if (!rows.length) return <div className="chart-empty">No data yet.</div>;
  const total = rows.reduce((sum, r) => sum + r.value, 0);
  const top = rows.slice(0, limit);
  const max = Math.max(...top.map((r) => r.value));
  return (
    <ul className="bar-list">
      {top.map((row) => (
        <li key={row.label} title={`${row.label}: ${row.value.toLocaleString()} (${Math.round((row.value / total) * 100)}%)`}>
          <span className="bar-label">{row.label}</span>
          <span className="bar-track"><span className="bar-fill" style={{ width: `${(row.value / max) * 100}%` }} /></span>
          <span className="bar-value">{Math.round((row.value / total) * 100)}%</span>
        </li>
      ))}
    </ul>
  );
}

export function StatTile({ label, value, delta, hint }: { label: string; value: number | null | undefined; delta?: number | null; hint?: string }) {
  return (
    <div className="stat-tile">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{formatCount(value)}</strong>
      {delta !== undefined && delta !== null && (
        <span className={delta > 0 ? "delta up" : delta < 0 ? "delta down" : "delta"}>
          {delta > 0 ? "▲ +" : delta < 0 ? "▼ −" : "• "}{formatCount(Math.abs(delta))} vs day before
        </span>
      )}
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

export function Meter({ value, total, label }: { value: number; total: number; label: string }) {
  const pct = total ? Math.min(100, (value / total) * 100) : 0;
  return (
    <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={total} aria-valuenow={value} aria-label={label}>
      <div className="meter-head"><span>{label}</span><strong>{value.toLocaleString()} / {total.toLocaleString()}</strong></div>
      <div className="meter-track"><div className="meter-fill" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}
