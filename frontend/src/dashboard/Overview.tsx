import { useCallback, useEffect, useState } from "react";
import { api, formatCount, type Overview as OverviewData, type Snapshot } from "../api";
import { ChartCard, Meter, StatTile, TimeChart } from "./charts";

const DAY_METRICS: { key: keyof Snapshot; label: string }[] = [
  { key: "reach", label: "Accounts reached" },
  { key: "views", label: "Views" },
  { key: "accounts_engaged", label: "Accounts engaged" },
  { key: "profile_views", label: "Profile visits" },
];

const PIPELINE = ["draft", "approved", "published", "failed", "rejected"] as const;

export default function Overview({ onError, onOpenContent }: { onError: (e: unknown) => void; onOpenContent: () => void }) {
  const [data, setData] = useState<OverviewData | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    setFailed(false);
    try {
      setData(await api<OverviewData>("/api/v1/dashboard/overview"));
    } catch (cause) {
      setFailed(true);
      onError(cause);
    }
  }, [onError]);

  useEffect(() => { void load(); }, [load]);

  async function sync() {
    setSyncing(true);
    try {
      await api("/api/v1/dashboard/sync", { method: "POST" });
      await load();
    } catch (cause) {
      onError(cause);
    } finally {
      setSyncing(false);
    }
  }

  if (!data) {
    return failed
      ? <div className="dash-loading">Couldn't load your account. <button className="text-button" onClick={() => void load()}>Retry</button></div>
      : <div className="dash-loading">Loading your account…</div>;
  }

  const snaps = data.snapshots;
  const latest = snaps[snaps.length - 1];
  const previous = snaps[snaps.length - 2];
  const delta = (key: keyof Snapshot) =>
    latest && previous ? Number(latest[key] ?? 0) - Number(previous[key] ?? 0) : null;
  const series = (key: keyof Snapshot) => snaps.map((s) => ({ date: s.taken_at, value: Number(s[key] ?? 0) }));
  const profile = data.profile;

  return (
    <div className="dash">
      {data.instagram_error && <div role="alert" className="message error">Instagram: {data.instagram_error}</div>}

      <section className="dash-card account-card">
        <div className="account-id">
          {profile?.profile_picture_url
            ? <img className="account-pic" src={profile.profile_picture_url} alt="" />
            : <div className="account-pic placeholder">{profile?.username?.[0]?.toUpperCase() ?? "?"}</div>}
          <div>
            <h2>@{profile?.username ?? "not connected"}</h2>
            {profile?.biography && <p>{profile.biography}</p>}
          </div>
        </div>
        <div className="hero-stat">
          <span className="stat-label">Followers</span>
          <strong className="hero-value">{formatCount(profile?.followers_count)}</strong>
          {delta("followers") !== null && <span className="stat-hint">{delta("followers")! >= 0 ? "+" : "−"}{Math.abs(delta("followers")!)} since last sync</span>}
        </div>
        <div className="account-meta">
          <div><strong>{formatCount(profile?.media_count)}</strong><span>posts</span></div>
          <div><strong>{formatCount(profile?.follows_count)}</strong><span>following</span></div>
        </div>
        <div className="sync-box">
          <button className="save-button" onClick={() => void sync()} disabled={syncing}>{syncing ? "Syncing…" : "Sync insights"}</button>
          <small>{data.last_synced_at ? `Last synced ${new Date(data.last_synced_at).toLocaleString()}` : "Never synced"}</small>
        </div>
      </section>

      <div className="stat-grid">
        {DAY_METRICS.map((m) => (
          <StatTile key={m.key} label={m.label} value={latest ? Number(latest[m.key] ?? 0) : null} delta={delta(m.key)} hint={latest ? undefined : "Sync to see yesterday's numbers"} />
        ))}
      </div>

      <div className="chart-grid">
        <ChartCard title="Followers" subtitle="Total at each daily sync"
          table={{ columns: ["Date", "Followers"], rows: snaps.map((s) => [new Date(s.taken_at).toLocaleDateString(), s.followers]) }}>
          <TimeChart points={series("followers")} kind="line" label="followers" />
        </ChartCard>
        <ChartCard title="Accounts reached per day" subtitle="Unique accounts that saw your content"
          table={{ columns: ["Date", "Reach"], rows: snaps.map((s) => [new Date(s.taken_at).toLocaleDateString(), s.reach ?? 0]) }}>
          <TimeChart points={series("reach")} kind="column" label="accounts reached" />
        </ChartCard>
      </div>

      <div className="chart-grid">
        <section className="dash-card">
          <header className="chart-head"><div><h3>Content pipeline</h3><p>Posts by status</p></div>
            <button className="text-button" onClick={onOpenContent}>Open content →</button></header>
          <div className="pipeline">
            {PIPELINE.map((s) => (
              <div key={s} className={`pipe pipe-${s}`}><strong>{data.post_counts[s] ?? 0}</strong><span>{s}</span></div>
            ))}
          </div>
        </section>
        <section className="dash-card">
          <header className="chart-head"><div><h3>Publishing limit</h3><p>Instagram limits how many posts you can publish from here in 24 hours</p></div></header>
          {data.quota ? <Meter value={data.quota.used} total={data.quota.total} label="Posts in the last 24h" /> : <div className="chart-empty">Connect Instagram to see your limit.</div>}
        </section>
      </div>
    </div>
  );
}
