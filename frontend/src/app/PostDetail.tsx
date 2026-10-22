import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type BotPost } from "../api";
import { Icon } from "../icons";
import { Link, navigate } from "../router";
import { MediaPlayer, postMeta, postTitle, StatusChip } from "./media";

type Line = { speaker: string; text: string };
type Shot = { lines?: Line[]; narration?: string; scene?: string; on_screen_text?: string };
type Slide = { heading: string; body: string };
type Scene = { voiceover: string; on_screen_text: string };

const POLL_MS = 4000;

export default function PostDetail({ id, onError }: { id: number; onError: (e: unknown) => void }) {
  const [post, setPost] = useState<BotPost | null>(null);
  const [missing, setMissing] = useState(false);
  const [tab, setTab] = useState<"caption" | "script">("caption");

  const load = useCallback(async () => {
    try {
      const all = await api<BotPost[]>("/api/v1/dashboard/posts");
      const found = all.find((p) => p.id === id) ?? null;
      setPost(found);
      setMissing(!found);
    } catch (cause) {
      onError(cause);
    }
  }, [id, onError]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (post?.status !== "generating") return;
    const timer = window.setInterval(() => void load(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [post?.status, load]);

  if (missing) {
    return (
      <div className="empty-state">
        <h3>Post not found</h3>
        <p>It may have been removed.</p>
        <Link to="/app/library" className="btn btn-primary">Back to library</Link>
      </div>
    );
  }
  if (!post) return <div className="detail-layout"><div className="player skeleton" /><div className="dash-card skeleton" style={{ minHeight: 420 }} /></div>;

  return (
    <div className="dash">
      <Link to="/app/library" className="back-link"><Icon name="arrowRight" className="icon flip" /> Library</Link>
      <div className="detail-layout">
        <div className="detail-media"><MediaPlayer key={`${post.id}-${post.media_urls.join()}`} post={post} /></div>
        <section className="dash-card detail-panel">
          <div className="queue-meta"><StatusChip status={post.status} /><span>#{post.id} · {postMeta(post)}</span></div>
          <h2 className="detail-title">{postTitle(post)}</h2>
          {postTitle(post) !== post.topic && <p className="detail-brief">“{post.topic}”</p>}

          {post.status === "generating" ? (
            <div className="generating-steps">
              <p>We're making this now. You can leave this page; it keeps going.</p>
              <ol>
                {["Writing", "Recording voices", "Creating pictures", "Filming / animating", "Editing"].map((label, i) => {
                  const percent = post.progress?.percent ?? 0;
                  const state = percent >= [30, 40, 60, 88, 100][i] ? "done" : percent >= [0, 30, 40, 58, 88][i] ? "now" : "";
                  return <li key={label} className={state}>{label}</li>;
                })}
              </ol>
            </div>
          ) : (
            <>
              <div className="tabs" role="tablist">
                <button role="tab" aria-selected={tab === "caption"} className={tab === "caption" ? "tab active" : "tab"} onClick={() => setTab("caption")}>Caption & publish</button>
                <button role="tab" aria-selected={tab === "script"} className={tab === "script" ? "tab active" : "tab"} onClick={() => setTab("script")}>Script</button>
              </div>
              {tab === "caption"
                ? <CaptionEditor key={`${post.id}-${post.status}`} post={post} onChange={setPost} onError={onError} />
                : <Script post={post} />}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function CaptionEditor({ post, onChange, onError }: { post: BotPost; onChange: (p: BotPost) => void; onError: (e: unknown) => void }) {
  const [caption, setCaption] = useState(post.caption);
  const [hashtags, setHashtags] = useState(post.hashtags.join(" "));
  const [collabs, setCollabs] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const editable = post.status === "draft" || post.status === "failed";
  const dirty = caption !== post.caption || hashtags !== post.hashtags.join(" ");
  const hasMedia = post.media_urls.length > 0;

  async function act(name: string, path: string, body?: object, method = "POST") {
    setBusy(name);
    try {
      const updated = await api<BotPost>(`/api/v1/dashboard/posts/${post.id}${path}`, { method, body: body ? JSON.stringify(body) : undefined });
      onChange(updated);
      return updated;
    } catch (cause) {
      onError(cause);
      return null;
    } finally {
      setBusy(null);
    }
  }
  const save = () => act("save", "", { caption, hashtags: hashtags.split(/[\s,]+/).filter(Boolean) }, "PATCH");
  const collaborators = () => collabs.split(/[\s,]+/).filter(Boolean);

  async function postNow() {
    if (!window.confirm("Post this to Instagram now? It goes live publicly.")) return;
    if (dirty && !(await save())) return;
    setBusy("publish");
    try {
      if (post.status !== "approved") await api(`/api/v1/dashboard/posts/${post.id}/approve`, { method: "POST", body: JSON.stringify({ collaborators: collaborators() }) });
      onChange(await api<BotPost>(`/api/v1/dashboard/posts/${post.id}/publish`, { method: "POST" }));
    } catch (cause) {
      onError(cause);
      if (!(cause instanceof ApiError && cause.status === 403)) {
        api<BotPost[]>("/api/v1/dashboard/posts").then((all) => { const fresh = all.find((p) => p.id === post.id); if (fresh) onChange(fresh); }).catch(() => undefined);
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="caption-editor">
      {post.error && (
        <div className="message warn verify-box">
          <span>{post.error}</span>
          {(editable || post.status === "approved") && <button className="btn btn-ghost" onClick={() => void act("render", "/render")} disabled={!!busy}>Try again</button>}
        </div>
      )}
      {post.status === "published" && <div className="message success">This post is live on Instagram.</div>}
      {post.manual_post && <div className="message warn">Needs a trending sound: download it and post from the Instagram app.</div>}

      <label htmlFor="caption">Caption</label>
      <textarea id="caption" rows={8} value={caption} onChange={(e) => setCaption(e.target.value)} disabled={!editable} maxLength={2000} />
      <label htmlFor="tags">Hashtags</label>
      <input id="tags" value={hashtags} onChange={(e) => setHashtags(e.target.value)} disabled={!editable} />
      {editable && (
        <>
          <label htmlFor="collabs">Invite collaborators (optional, up to 3)</label>
          <input id="collabs" value={collabs} onChange={(e) => setCollabs(e.target.value)} placeholder={post.collaborators.length ? `Suggested: ${post.collaborators.join(", ")}` : "username1, username2"} />
        </>
      )}

      <div className="detail-actions">
        {editable && !hasMedia && !post.error && <button className="btn btn-primary" onClick={() => void act("render", "/render")} disabled={!!busy}>Create media</button>}
        {(editable || post.status === "approved") && !post.manual_post && (
          <button className="btn btn-primary btn-lg" onClick={() => void postNow()} disabled={!!busy || !hasMedia}>
            {busy === "publish" ? <><span className="spinner" /> Posting…</> : <><Icon name="instagram" /> Post to Instagram</>}
          </button>
        )}
        <div className="detail-secondary">
          {editable && <button className="btn btn-ghost" onClick={() => void save()} disabled={!dirty || !!busy}>{busy === "save" ? "Saving…" : "Save edits"}</button>}
          {editable && <button className="btn btn-ghost" onClick={() => void act("approve", "/approve", { collaborators: collaborators() })} disabled={!!busy}>Approve for later</button>}
          {!["rejected", "publishing", "published"].includes(post.status) && (
            <button className="btn btn-ghost btn-danger" onClick={async () => { if (await act("reject", "/reject")) navigate("/app/library"); }} disabled={!!busy}>Reject</button>
          )}
        </div>
      </div>
    </div>
  );
}

function Script({ post }: { post: BotPost }) {
  const script = post.script as { shots?: Shot[]; slides?: Slide[]; scenes?: Scene[]; logline?: string; characters?: { name: string; look: string }[] };
  if (script.shots) {
    return (
      <div className="script">
        {script.logline && <p className="detail-brief">{script.logline}</p>}
        {script.characters && script.characters.length > 0 && (
          <div className="cast">{script.characters.map((c) => <span key={c.name} className="cast-chip" title={c.look}>{c.name}</span>)}</div>
        )}
        <ol className="shot-list">
          {script.shots.map((shot, i) => (
            <li key={i}>
              <span className="shot-num">{i + 1}</span>
              <div>
                {(shot.lines ?? [{ speaker: "Narrator", text: shot.narration ?? "" }]).map((line, j) => (
                  <p key={j} className={line.speaker === "Narrator" ? "line narrator" : "line"}>
                    <b>{line.speaker}</b> {line.text}
                  </p>
                ))}
                {shot.scene && <small className="shot-scene">{shot.scene}</small>}
              </div>
            </li>
          ))}
        </ol>
      </div>
    );
  }
  if (script.slides) return <ol className="shot-list">{script.slides.map((s, i) => <li key={i}><span className="shot-num">{i + 1}</span><div><p className="line"><b>{s.heading}</b></p><small>{s.body}</small></div></li>)}</ol>;
  if (script.scenes) return <ol className="shot-list">{script.scenes.map((s, i) => <li key={i}><span className="shot-num">{i + 1}</span><div><p className="line">{s.voiceover}</p><small>{s.on_screen_text}</small></div></li>)}</ol>;
  return <p className="library-empty">No script for this post.</p>;
}
