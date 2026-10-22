import { useEffect, useState } from "react";
import { api, type Audience as AudienceData } from "../api";
import { BarList, ChartCard, Meter } from "./charts";

const SECTIONS = [
  { key: "age", title: "Age", subtitle: "Share of followers by age range" },
  { key: "gender", title: "Gender", subtitle: "F = female, M = male, U = unspecified" },
  { key: "country", title: "Top countries", subtitle: "Share of followers by country" },
  { key: "city", title: "Top cities", subtitle: "Share of followers by city" },
] as const;

export default function Audience({ onError }: { onError: (e: unknown) => void }) {
  const [data, setData] = useState<AudienceData | null>(null);

  useEffect(() => {
    api<AudienceData>("/api/v1/dashboard/audience").then(setData).catch(onError);
  }, [onError]);

  if (!data) return <div className="dash-loading">Loading audience…</div>;

  if (data.locked) {
    return (
      <div className="dash">
        <section className="dash-card locked-card">
          <h3>Audience insights unlock at 100 followers</h3>
          <p>Instagram only shares follower age, gender, country and city once an account has at least 100 followers. Keep posting; this page fills in automatically.</p>
          <Meter value={data.followers} total={100} label="Followers so far" />
        </section>
      </div>
    );
  }

  return (
    <div className="dash">
      <div className="chart-grid">
        {SECTIONS.map((s) => {
          const rows = data.demographics[s.key] ?? [];
          return (
            <ChartCard key={s.key} title={s.title} subtitle={s.subtitle}
              table={{ columns: [s.title, "Followers"], rows: rows.map((r) => [r.label, r.value]) }}>
              <BarList rows={rows} />
            </ChartCard>
          );
        })}
      </div>
    </div>
  );
}
