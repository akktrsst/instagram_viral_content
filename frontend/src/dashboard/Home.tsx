import { FormEvent, useCallback, useEffect, useState } from "react";
import { api, fetchMedia, formatCount, formatSeconds, savedLanguage, saveLanguage, VIDEO_FORMATS, type BotPost, type IgMedia, type Language, type Overview, type PostFormat } from "../api";
import { Icon, type IconName } from "../icons";
import type { View } from "../shell/Shell";
import { ChartCard, Meter, TimeChart } from "./charts";

const FORMATS: { key: PostFormat; label: string; icon: IconName }[] = [
  { key: "story", label: "Story video", icon: "video" },
  { key: "reel", label: "Short reel", icon: "video" },
  { key: "explainer", label: "Explainer", icon: "layers" },
  { key: "carousel", label: "Carousel", icon: "grid" },
  { key: "photo", label: "AI photo", icon: "image" },
  { key: "image", label: "Quote", icon: "quote" },
];

function greeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

export default function Home({ onError, onNavigate }: { onError: (e: unknown) => void; onNavigate: (v: View) => void }) {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [posts, setPosts] = useState<BotPost[] | null>(null);
  const [media, setMedia] = useState<IgMedia[] | null>(null);
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState<PostFormat>("story");
  const [seconds, setSeconds] = useState(60);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [language, setLanguage] = useState(savedLanguage);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    api<Overview>("/api/v1/dashboard/overview").then(setOverview).catch(onError);
    api<BotPost[]>("/api/v1/dashboard/posts").then(setPosts).catch(onError);
    api<IgMedia[]>("/api/v1/dashboard/content").then(setMedia).catch(() => setMedia([]));
    api<Language[]>("/api/v1/dashboard/languages").then(setLanguages).catch(() => setLanguages([]));
  }, [onError]);

  useEffect(() => { load(); }, [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    try {
      await api<BotPost>("/api/v1/dashboard/posts", {
        method: "POST",
        body: JSON.stringify({ topic, format, skill_id: format === "story" ? "story" : null, target_seconds: format === "story" ? seconds : null, language: language || null }),
      });
      onNavigate("content");
    } catch (cause) {
      onError(cause);
      setCreating(false);
    }
  }

  const profile = overview?.profile;
  const snaps = overview?.snapshots ?? [];
  const latest = snaps[snaps.length - 1];
  const queue = (posts ?? []).filter((p) => ["generating", "draft", "approved", "failed"].includes(p.status)).slice(0, 4);
  const published = overview?.post_counts.published ?? 0;

  const tiles: { label: string; value: number | null | undefined; icon: IconName; hint: string }[] = [
    { label: "Followers", value: profile?.followers_count, icon: "users", hint: `${formatCount(profile?.follows_count)} following` },
    { label: "Accounts reached", value: latest?.reach ?? null, icon: "eye", hint: latest ? "Yesterday" : "Sync to see" },
    { label: "Views", value: latest?.views ?? null, icon: "video", hint: latest ? "Yesterday" : "Sync to see" },
    { label: "Posted with Studio", value: published, icon: "send", hint: `${formatCount(profile?.media_count)} ${profile?.media_count === 1 ? "post" : "posts"} on profile` },
  ];

  return (
    <div className="dash">
      <section className="welcome">
        <h2>{greeting()}{profile ? `, @${profile.username}` : ""} 👋</h2>
        <p>What should we post next? Describe it in your own words: topic, audience, mood or language.</p>
        <form className="quick-create" onSubmit={create}>
          <div className="quick-row">
            <input aria-label="Describe your post" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Any topic: e.g. 5 easy Diwali sweets in 20 minutes, a funny gym reel, our weekend offer…" minLength={3} maxLength={1000} required />
            <button className="btn btn-white btn-lg" type="submit" disabled={creating || topic.trim().length < 3}>
              {creating ? <><span className="spinner" /> Starting…</> : <><Icon name="sparkles" /> Generate</>}
            </button>
          </div>
          <div className="chips" role="radiogroup" aria-label="Format">
            {FORMATS.map((f) => (
              <button type="button" role="radio" aria-checked={format === f.key} key={f.key} className={format === f.key ? "chip active" : "chip"} onClick={() => setFormat(f.key)}>
                <Icon name={f.icon} /> {f.label}
              </button>
            ))}
            {format === "story" && (
              <select className="chip chip-select" aria-label="Video length" value={seconds} onChange={(e) => setSeconds(Number(e.target.value))}>
                {[20, 30, 45, 60, 90, 120].map((n) => <option key={n} value={n}>{formatSeconds(n)}</option>)}
              </select>
            )}
            <select className="chip chip-select" aria-label="Language" value={language} onChange={(e) => { setLanguage(e.target.value); saveLanguage(e.target.value); }}>
              <option value="">Language: auto</option>
              {languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)}
            </select>
          </div>
        </form>
      </section>

      <div className="stat-grid">
        {tiles.map((t) => (
          <div className="stat-tile" key={t.label}>
            <div className="stat-top"><span className="stat-label">{t.label}</span><span className="stat-ico"><Icon name={t.icon} /></span></div>
            <strong className="stat-value">{overview ? formatCount(t.value) : "…"}</strong>
            <span className="stat-hint">{t.hint}</span>
          </div>
        ))}
      </div>

      <div className="grid-main">
        <section className="dash-card">
          <header className="chart-head">
            <div><h3>Up next</h3><p>Drafts waiting for your review</p></div>
            <button className="btn btn-ghost" onClick={() => onNavigate("content")}>Open queue <Icon name="arrowRight" /></button>
          </header>
          {posts === null ? <div className="dash-loading">Loading…</div> : queue.length ? (
            <div className="list">
              {queue.map((p) => (
                <div className="list-row" key={p.id}>
                  <DraftThumb post={p} />
                  <div className="list-main">
                    <strong>{p.topic}</strong>
                    <small>{p.format === "photo" ? "AI photo" : p.format} · {new Date(p.created_at).toLocaleDateString()}</small>
                  </div>
                  <span className={`status status-${p.status}`}>{p.status}</span>
                </div>
              ))}
            </div>
          ) : <p className="library-empty">Nothing waiting. Generate a post above.</p>}
        </section>

        <section className="dash-card">
          <header className="chart-head"><div><h3>Publishing limit</h3><p>Posts published from here in the last 24 hours</p></div></header>
          {overview?.quota ? <Meter value={overview.quota.used} total={overview.quota.total} label="Posts used" /> : <div className="dash-loading">{overview ? "Instagram not connected" : "Loading…"}</div>}
          <div className="pipeline" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))", marginTop: 18 }}>
            {(["draft", "approved", "published"] as const).map((s) => (
              <div key={s} className="pipe"><strong>{overview?.post_counts[s] ?? 0}</strong><span>{s}</span></div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid-main">
        <ChartCard title="Followers" subtitle="Total at each daily sync"
          table={{ columns: ["Date", "Followers"], rows: snaps.map((s) => [new Date(s.taken_at).toLocaleDateString(), s.followers]) }}>
          <TimeChart points={snaps.map((s) => ({ date: s.taken_at, value: s.followers }))} kind="line" label="followers" />
        </ChartCard>

        <section className="dash-card">
          <header className="chart-head">
            <div><h3>Recent posts</h3><p>Latest synced numbers</p></div>
            <button className="btn btn-ghost" onClick={() => onNavigate("analytics")}>Analytics</button>
          </header>
          {media === null ? <div className="dash-loading">Loading…</div> : media.length ? (
            <div className="list">
              {media.slice(0, 4).map((m) => (
                <a className="list-row" key={m.id} href={m.permalink} target="_blank" rel="noreferrer">
                  {m.thumbnail_url || m.media_url ? <img className="thumb" src={m.thumbnail_url || m.media_url} alt="" /> : <span className="thumb ph"><Icon name="image" /></span>}
                  <div className="list-main">
                    <strong>{(m.caption ?? m.media_type).split("\n")[0]}</strong>
                    <small>{new Date(m.timestamp).toLocaleDateString()}</small>
                  </div>
                  <div className="list-metrics">
                    <span><Icon name="eye" />{formatCount(m.metrics?.reach)}</span>
                    <span><Icon name="heart" />{formatCount(m.metrics?.likes ?? m.like_count)}</span>
                  </div>
                </a>
              ))}
            </div>
          ) : <p className="library-empty">No posts on Instagram yet.</p>}
        </section>
      </div>
    </div>
  );
}

function DraftThumb({ post }: { post: BotPost }) {
  const [src, setSrc] = useState<string | null>(null);
  // A reel's media is [video, cover]; use the cover image.
  const path = VIDEO_FORMATS.includes(post.format) ? post.media_urls[1] : post.media_urls[0];

  useEffect(() => {
    if (!path) return;
    let url: string | null = null;
    fetchMedia(path).then((m) => { url = m.url; setSrc(m.url); }).catch(() => setSrc(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [path]);

  return src ? <img className="thumb" src={src} alt="" /> : <span className="thumb ph"><Icon name={VIDEO_FORMATS.includes(post.format) ? "video" : "image"} /></span>;
}
