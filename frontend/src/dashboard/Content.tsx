import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, fetchMedia, formatCount, formatSeconds, languageLabel, savedLanguage, saveLanguage, VIDEO_FORMATS, type BotPost, type IgMedia, type Language, type PostFormat, type Skill } from "../api";

const FORMAT_LABELS: Record<PostFormat, string> = {
  story: "Story video (20s – 2 min)",
  reel: "Short reel (20–40s)",
  explainer: "Explainer reel (animated diagram)",
  carousel: "Carousel (text slides)",
  photo: "AI photo",
  image: "Quote / text image",
};
const LENGTHS = [20, 30, 45, 60, 75, 90, 105, 120];
const LANGUAGE_NAMES: Record<string, string> = {
  "en-IN": "English", "en-US": "English (US)", hi: "Hindi", hinglish: "Hinglish", bho: "Bhojpuri", bn: "Bengali",
  mr: "Marathi", ta: "Tamil", te: "Telugu", gu: "Gujarati", kn: "Kannada", ml: "Malayalam", pa: "Punjabi", ur: "Urdu",
};
const POLL_MS = 4000;

type Tab = "queue" | "published" | "rejected";
export type ContentPreset = { skillId?: string; format?: PostFormat };

export default function Content({ onError, preset }: { onError: (e: unknown) => void; preset?: ContentPreset }) {
  const [tab, setTab] = useState<Tab>("queue");
  const [posts, setPosts] = useState<BotPost[] | null>(null);

  const load = useCallback(async () => {
    try {
      setPosts(await api<BotPost[]>("/api/v1/dashboard/posts"));
    } catch (cause) {
      onError(cause);
    }
  }, [onError]);

  useEffect(() => { void load(); }, [load]);

  const generating = posts?.some((p) => p.status === "generating") ?? false;
  useEffect(() => {
    if (!generating) return;
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [generating, load]);

  const replace = (updated: BotPost) =>
    setPosts((current) => current?.map((p) => (p.id === updated.id ? updated : p)) ?? null);

  const queue = posts?.filter((p) => ["generating", "draft", "approved", "failed", "publishing"].includes(p.status)) ?? [];
  const rejected = posts?.filter((p) => p.status === "rejected") ?? [];
  // Remount a card when its status changes so its editable fields pick up freshly written text.
  const card = (p: BotPost) => <QueueCard key={`${p.id}-${p.status}-${p.media_urls.length}`} post={p} onChange={replace} onError={onError} />;

  return (
    <div className="dash">
      <NewPostForm preset={preset} onCreated={(post) => { setPosts((current) => [post, ...(current ?? [])]); setTab("queue"); }} onError={onError} />

      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "queue"} className={tab === "queue" ? "tab active" : "tab"} onClick={() => setTab("queue")}>Review queue <span className="count">{queue.length}</span></button>
        <button role="tab" aria-selected={tab === "published"} className={tab === "published" ? "tab active" : "tab"} onClick={() => setTab("published")}>Published</button>
        <button role="tab" aria-selected={tab === "rejected"} className={tab === "rejected" ? "tab active" : "tab"} onClick={() => setTab("rejected")}>Rejected <span className="count">{rejected.length}</span></button>
      </div>

      {posts === null && <div className="dash-loading">Loading posts…</div>}
      {posts && tab === "queue" && (queue.length
        ? <div className="queue">{queue.map(card)}</div>
        : <p className="library-empty">Nothing waiting for review. Create a post above.</p>)}
      {tab === "published" && <Published onError={onError} />}
      {posts && tab === "rejected" && (rejected.length
        ? <div className="queue">{rejected.map(card)}</div>
        : <p className="library-empty">No rejected posts.</p>)}
    </div>
  );
}

function NewPostForm({ onCreated, onError, preset }: { onCreated: (p: BotPost) => void; onError: (e: unknown) => void; preset?: ContentPreset }) {
  const [topic, setTopic] = useState("");
  const [format, setFormat] = useState<PostFormat>(preset?.format ?? "story");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillId, setSkillId] = useState<string>(preset?.skillId ?? "story");
  const [seconds, setSeconds] = useState(60);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [language, setLanguage] = useState(savedLanguage);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Skill[]>("/api/v1/dashboard/skills").then(setSkills).catch(() => setSkills([]));
    api<Language[]>("/api/v1/dashboard/languages").then(setLanguages).catch(() => setLanguages([]));
  }, []);

  useEffect(() => {
    if (!preset?.skillId || !skills.length) return;
    const chosen = skills.find((s) => s.id === preset.skillId);
    if (chosen) { setFormat(chosen.kind); setSkillId(chosen.id); setSeconds(chosen.default_seconds); }
  }, [preset?.skillId, skills]);

  const options = useMemo(() => skills.filter((s) => s.kind === format), [skills, format]);

  function chooseFormat(next: PostFormat) {
    setFormat(next);
    const first = skills.find((s) => s.kind === next);
    setSkillId(next === "story" ? first?.id ?? "story" : "");
  }

  function chooseSkill(id: string) {
    setSkillId(id);
    const chosen = skills.find((s) => s.id === id);
    if (chosen && format === "story") setSeconds(chosen.default_seconds);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      onCreated(await api<BotPost>("/api/v1/dashboard/posts", {
        method: "POST",
        body: JSON.stringify({ topic, format, skill_id: skillId || null, target_seconds: format === "story" ? seconds : null, language: language || null }),
      }));
      setTopic("");
    } catch (cause) {
      onError(cause);
    } finally {
      setBusy(false);
    }
  }

  const minutes = Math.max(2, Math.round(seconds / 15));
  return (
    <form className="dash-card create-form" onSubmit={submit}>
      <div>
        <label htmlFor="new-topic">Describe your post</label>
        <textarea id="new-topic" rows={2} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Any topic, any style: e.g. a street dog who waits every evening at a railway station for a little girl" minLength={3} maxLength={1000} required />
      </div>
      <div className="create-row">
        <div>
          <label htmlFor="new-format">Format</label>
          <select id="new-format" value={format} onChange={(e) => chooseFormat(e.target.value as PostFormat)}>
            {(Object.keys(FORMAT_LABELS) as PostFormat[]).map((f) => <option key={f} value={f}>{FORMAT_LABELS[f]}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="new-skill">Skill</label>
          <select id="new-skill" value={skillId} onChange={(e) => chooseSkill(e.target.value)}>
            {format !== "story" && <option value="">General</option>}
            {options.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="new-language">Language</label>
          <select id="new-language" value={language} onChange={(e) => { setLanguage(e.target.value); saveLanguage(e.target.value); }}>
            <option value="">Same as my description</option>
            {languages.map((l) => <option key={l.code} value={l.code}>{languageLabel(l)}</option>)}
          </select>
        </div>
        {format === "story" && (
          <div className="length-field">
            <label htmlFor="new-length">Length <strong>{formatSeconds(seconds)}</strong></label>
            <input id="new-length" type="range" min={20} max={120} step={5} value={seconds} onChange={(e) => setSeconds(Number(e.target.value))} list="length-marks" />
            <datalist id="length-marks">{LENGTHS.map((n) => <option key={n} value={n} />)}</datalist>
          </div>
        )}
      </div>
      <div className="create-foot">
        <span className="fine-print">
          {format === "story"
            ? `About ${Math.round(seconds / 4.5)} scenes with narration, matching pictures and real motion for key moments. Takes about ${minutes} minutes; you can keep working meanwhile.`
            : options.find((s) => s.id === skillId)?.description ?? "Written in your brand voice for the topic you describe."}
        </span>
        <button className="save-button" type="submit" disabled={busy || topic.trim().length < 3}>{busy ? "Starting…" : "Create"}</button>
      </div>
    </form>
  );
}

function QueueCard({ post, onChange, onError }: { post: BotPost; onChange: (p: BotPost) => void; onError: (e: unknown) => void }) {
  const [caption, setCaption] = useState(post.caption);
  const [hashtags, setHashtags] = useState(post.hashtags.join(" "));
  const [collabs, setCollabs] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const editable = post.status === "draft" || post.status === "failed";
  const dirty = caption !== post.caption || hashtags !== post.hashtags.join(" ");

  async function act(name: string, path: string, body?: object, method = "POST") {
    setBusy(name);
    try {
      onChange(await api<BotPost>(`/api/v1/dashboard/posts/${post.id}${path}`, { method, body: body ? JSON.stringify(body) : undefined }));
    } catch (cause) {
      onError(cause);
    } finally {
      setBusy(null);
    }
  }

  const save = () => act("save", "", { caption, hashtags: hashtags.split(/[\s,]+/).filter(Boolean) }, "PATCH");
  const approve = async () => {
    if (dirty) await save();
    await act("approve", "/approve", { collaborators: collabs.split(/[\s,]+/).filter(Boolean) });
  };
  const publish = () => {
    if (window.confirm(`Publish post #${post.id} to Instagram now? It goes live publicly.`)) void act("publish", "/publish");
  };
  const postNow = async () => {
    if (!window.confirm(`Post #${post.id} to Instagram now? It goes live publicly.`)) return;
    if (dirty) await save();
    setBusy("publish");
    try {
      await api<BotPost>(`/api/v1/dashboard/posts/${post.id}/approve`, { method: "POST", body: JSON.stringify({ collaborators: collabs.split(/[\s,]+/).filter(Boolean) }) });
      onChange(await api<BotPost>(`/api/v1/dashboard/posts/${post.id}/publish`, { method: "POST" }));
    } catch (cause) {
      onError(cause);
      // Refresh the card: approval may have succeeded even if publishing failed.
      api<BotPost[]>("/api/v1/dashboard/posts").then((all) => { const fresh = all.find((p) => p.id === post.id); if (fresh) onChange(fresh); }).catch(() => undefined);
    } finally {
      setBusy(null);
    }
  };

  if (post.status === "generating") return <GeneratingCard post={post} />;

  return (
    <article className="dash-card queue-card">
      <Slides urls={post.media_urls} isReel={VIDEO_FORMATS.includes(post.format)} postId={post.id} />
      <div className="queue-body">
        <div className="queue-meta">
          <span className={`status status-${post.status}`}>{post.status}</span>
          <span>#{post.id} · {post.format} · {new Date(post.created_at).toLocaleDateString()}</span>
        </div>
        <h3>{post.topic}</h3>
        {post.error && (
          <div className="message warn verify-box">
            <span>{post.error}</span>
            {(editable || post.status === "approved") && <button className="text-button" onClick={() => void act("render", "/render")} disabled={!!busy}>Try again</button>}
          </div>
        )}
        {post.manual_post && <div className="message warn">Marked as needing a trending sound: download the video and post it from the Instagram app so you can add the sound.</div>}
        <label htmlFor={`cap-${post.id}`}>Caption</label>
        <textarea id={`cap-${post.id}`} value={caption} onChange={(e) => setCaption(e.target.value)} disabled={!editable} rows={7} maxLength={2000} />
        <label htmlFor={`tags-${post.id}`}>Hashtags</label>
        <input id={`tags-${post.id}`} value={hashtags} onChange={(e) => setHashtags(e.target.value)} disabled={!editable} />
        {editable && (
          <>
            <label htmlFor={`col-${post.id}`}>Invite collaborators (optional, up to 3 usernames)</label>
            <input id={`col-${post.id}`} value={collabs} onChange={(e) => setCollabs(e.target.value)} placeholder={post.collaborators.length ? `Suggested: ${post.collaborators.join(", ")}` : "username1, username2"} />
          </>
        )}
        {post.status === "approved" && post.collaborators.length > 0 && <p className="fine-print">Will invite: {post.collaborators.map((c) => "@" + c).join(", ")}</p>}
        <div className="queue-actions">
          {editable && <button className="text-button" onClick={() => void save()} disabled={!dirty || !!busy}>{busy === "save" ? "Saving…" : "Save edits"}</button>}
          {post.status !== "rejected" && post.status !== "publishing" && <button className="text-button danger" onClick={() => void act("reject", "/reject")} disabled={!!busy}>Reject</button>}
          {editable && <button className="text-button" onClick={() => void approve()} disabled={!!busy}>{busy === "approve" ? "Approving…" : "Approve for later"}</button>}
          {editable && !post.media_urls.length && !post.error && <button className="save-button" onClick={() => void act("render", "/render")} disabled={!!busy}>Generate media</button>}
          {editable && !post.manual_post && <button className="save-button" onClick={() => void postNow()} disabled={!!busy || !post.media_urls.length}>{busy === "publish" ? (VIDEO_FORMATS.includes(post.format) ? "Posting reel (can take a few minutes)…" : "Posting…") : "Post to Instagram ↗"}</button>}
          {post.status === "approved" && !post.manual_post && <button className="save-button" onClick={publish} disabled={!!busy || !post.media_urls.length}>{busy === "publish" ? "Publishing…" : "Publish now ↗"}</button>}
        </div>
      </div>
    </article>
  );
}

function GeneratingCard({ post }: { post: BotPost }) {
  const percent = post.progress?.percent ?? 0;
  return (
    <article className="dash-card generating-card" aria-busy="true">
      <div className="generating-art" aria-hidden="true"><span className="spinner" /></div>
      <div className="queue-body">
        <div className="queue-meta">
          <span className="status status-generating">Creating</span>
          <span>#{post.id} · {FORMAT_LABELS[post.format]?.split(" (")[0] ?? post.format}{post.target_seconds ? ` · ${formatSeconds(post.target_seconds)}` : ""}{post.language ? ` · ${LANGUAGE_NAMES[post.language] ?? post.language}` : ""}</span>
        </div>
        <h3>{post.topic}</h3>
        <div className="meter" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label="Progress">
          <div className="meter-head"><span>{post.progress?.message ?? "Waiting to start"}</span><strong>{percent}%</strong></div>
          <div className="meter-track"><div className="meter-fill" style={{ width: `${Math.max(percent, 3)}%` }} /></div>
        </div>
        <p className="fine-print">You can leave this page; it keeps going in the background.</p>
      </div>
    </article>
  );
}

function Slides({ urls, isReel, postId }: { urls: string[]; isReel: boolean; postId: number }) {
  const [index, setIndex] = useState(0);
  const [media, setMedia] = useState<{ url: string; isVideo: boolean } | null>(null);
  // A reel's media is [video, cover]; show only the video.
  const shown = isReel ? urls.slice(0, 1) : urls;

  useEffect(() => {
    if (!shown.length) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    setMedia(null);
    fetchMedia(shown[index]).then((result) => {
      objectUrl = result.url;
      if (!cancelled) setMedia(result);
    }).catch(() => setMedia(null));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [shown.join("|"), index]);

  if (!shown.length) return <div className="slides empty">No media rendered yet</div>;
  return (
    <div className={isReel ? "slides reel" : "slides"}>
      {media ? (media.isVideo
        ? <video src={media.url} controls playsInline loop />
        : <img src={media.url} alt={`Slide ${index + 1} of ${shown.length}`} />)
        : <div className="slides-loading">Loading…</div>}
      {media && <a className="slides-download" href={media.url} download={`post-${postId}-${index + 1}.${media.isVideo ? "mp4" : "jpg"}`}>Download</a>}
      {shown.length > 1 && (
        <div className="slides-nav">
          <button aria-label="Previous slide" onClick={() => setIndex((index - 1 + shown.length) % shown.length)}>‹</button>
          <span>{index + 1} / {shown.length}</span>
          <button aria-label="Next slide" onClick={() => setIndex((index + 1) % shown.length)}>›</button>
        </div>
      )}
    </div>
  );
}

function Published({ onError }: { onError: (e: unknown) => void }) {
  const [media, setMedia] = useState<IgMedia[] | null>(null);

  useEffect(() => {
    api<IgMedia[]>("/api/v1/dashboard/content").then(setMedia).catch(onError);
  }, [onError]);

  if (!media) return <div className="dash-loading">Loading Instagram posts…</div>;
  if (!media.length) return <p className="library-empty">Nothing published yet.</p>;

  const columns: { key: keyof NonNullable<IgMedia["metrics"]>; label: string }[] = [
    { key: "reach", label: "Reach" },
    { key: "views", label: "Views" },
    { key: "likes", label: "Likes" },
    { key: "comments", label: "Comments" },
    { key: "saves", label: "Saves" },
    { key: "shares", label: "Shares" },
  ];

  return (
    <section className="dash-card">
      <header className="chart-head"><div><h3>Published posts</h3><p>Latest synced numbers. Use "Sync insights" on Overview to refresh.</p></div></header>
      <div className="table-wrap">
        <table className="data-table media-table">
          <thead><tr><th>Post</th><th>Date</th>{columns.map((c) => <th key={c.key} className="num">{c.label}</th>)}<th /></tr></thead>
          <tbody>
            {media.map((m) => (
              <tr key={m.id}>
                <td className="media-cell">
                  {(m.thumbnail_url || m.media_url) && <img src={m.thumbnail_url || m.media_url} alt="" />}
                  <span>{(m.caption ?? "").split("\n")[0].slice(0, 70) || m.media_type}{m.post_id ? <em> · bot #{m.post_id}</em> : null}</span>
                </td>
                <td>{new Date(m.timestamp).toLocaleDateString()}</td>
                {columns.map((c) => (
                  <td key={c.key} className="num">{formatCount(m.metrics?.[c.key] as number | null | undefined ?? (c.key === "likes" ? m.like_count : c.key === "comments" ? m.comments_count : null))}</td>
                ))}
                <td><a className="text-button" href={m.permalink} target="_blank" rel="noreferrer">Open ↗</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
