import { FormEvent, useCallback, useEffect, useState } from "react";
import { createDraft, deleteDraft as removeDraft, listDrafts } from "@dataconnect/generated";
import { api, ApiError } from "../api";
import { Icon } from "../icons";

type Draft = { id: string; title: string; topic: string; platform: string; tone: string; caption: string; hashtags: string[]; updatedAt: string };
type Generated = { title: string; caption: string; hashtags: string[]; topic: string; tone: string };
type Review = { score: number; summary: string; strengths: string[]; improvements: string[] };
type Tier = "auto" | "lite" | "standard" | "pro";
type Mode = "ideas" | "caption";

const TONES = ["Warm & witty", "Bold & confident", "Calm & thoughtful", "Playful & curious", "Expert & clear"];

export default function CaptionLab() {
  const [topic, setTopic] = useState("");
  const [tone, setTone] = useState(TONES[0]);
  const [tier, setTier] = useState<Tier>("auto");
  const [mode, setMode] = useState<Mode>("caption");
  const [generated, setGenerated] = useState<Generated | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [busy, setBusy] = useState<"generate" | "review" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadDrafts = useCallback(async () => {
    try {
      const response = await listDrafts();
      setDrafts(response.data.drafts.map((d) => ({ ...d, updatedAt: String(d.updatedAt) })));
    } catch (cause) {
      console.error(cause);
      setError("Your saved captions couldn't be loaded right now.");
    }
  }, []);

  useEffect(() => { void loadDrafts(); }, [loadDrafts]);

  const modelTier = tier === "auto" ? null : tier;

  async function generate(event: FormEvent) {
    event.preventDefault();
    setBusy("generate"); setError(""); setNotice("");
    try {
      const result = await api<Omit<Generated, "topic" | "tone">>(`/api/v1/content/generate?task=${mode}`, {
        method: "POST", body: JSON.stringify({ topic, tone, platform: "Instagram", model_tier: modelTier }),
      });
      setGenerated({ ...result, topic, tone });
      setReview(null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "We couldn't write this. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  async function runReview() {
    if (!generated) return;
    setBusy("review"); setError("");
    try {
      setReview(await api<Review>("/api/v1/content/review", {
        method: "POST",
        body: JSON.stringify({ topic: generated.topic, tone: generated.tone, platform: "Instagram", caption: generated.caption, hashtags: generated.hashtags, model_tier: modelTier }),
      }));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "We couldn't review this. Please try again.");
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    if (!generated) return;
    setError(""); setNotice("");
    try {
      await createDraft({ title: generated.title, topic: generated.topic, platform: "Instagram", tone: generated.tone, caption: generated.caption, hashtags: generated.hashtags });
      await loadDrafts();
      setNotice("Saved to your caption library.");
    } catch (cause) {
      console.error(cause);
      setError("We couldn't save this caption. Please try again.");
    }
  }

  async function remove(id: string) {
    try {
      await removeDraft({ id });
      setDrafts((current) => current.filter((d) => d.id !== id));
    } catch (cause) {
      console.error(cause);
      setError("We couldn't delete this caption. Please try again.");
    }
  }

  return (
    <div className="dash">
      {error && <div role="alert" className="message error">{error}</div>}
      {notice && <div role="status" className="message success">{notice}</div>}

      <div className="lab-grid">
        <form className="dash-card lab-form" onSubmit={generate}>
          <header className="chart-head"><div><h3>Brief</h3><p>What's the post about?</p></div></header>
          <div>
            <label htmlFor="lab-topic">Topic</label>
            <textarea id="lab-topic" rows={4} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. The tiny morning ritual that changed my whole workday" minLength={3} maxLength={1000} required />
          </div>
          <div className="field-row">
            <div>
              <label htmlFor="lab-tone">Tone</label>
              <select id="lab-tone" value={tone} onChange={(e) => setTone(e.target.value)}>{TONES.map((t) => <option key={t}>{t}</option>)}</select>
            </div>
            <div>
              <label htmlFor="lab-tier">Quality</label>
              <select id="lab-tier" value={tier} onChange={(e) => setTier(e.target.value as Tier)}>
                <option value="auto">Recommended</option>
                <option value="lite">Quick</option>
                <option value="standard">Balanced</option>
                <option value="pro">Best</option>
              </select>
            </div>
          </div>
          <div>
            <label>I need</label>
            <div className="segmented" role="radiogroup" aria-label="Output">
              <button type="button" role="radio" aria-checked={mode === "ideas"} className={mode === "ideas" ? "active" : ""} onClick={() => setMode("ideas")}>Post ideas</button>
              <button type="button" role="radio" aria-checked={mode === "caption"} className={mode === "caption" ? "active" : ""} onClick={() => setMode("caption")}>A caption</button>
            </div>
          </div>
          <button className="btn btn-primary btn-lg" type="submit" disabled={!!busy || topic.trim().length < 3}>
            {busy === "generate" ? <><span className="spinner" /> Writing…</> : <><Icon name="sparkles" /> Generate</>}
          </button>
        </form>

        <section className="dash-card">
          <header className="chart-head">
            <div><h3>Preview</h3><p>How it reads in the feed</p></div>
            {generated && <button className="btn btn-ghost" onClick={() => void navigator.clipboard.writeText(`${generated.caption}\n\n${generated.hashtags.join(" ")}`)}>Copy</button>}
          </header>
          {generated ? (
            <div className="dash" style={{ gap: 14 }}>
              <div className="ig-preview">
                <div className="ig-head"><span className="avatar">S</span><strong>your.brand</strong></div>
                <div className="ig-art">{generated.title}</div>
                <div className="ig-body">
                  <p>{generated.caption}</p>
                  <p className="tags">{generated.hashtags.join(" ")}</p>
                </div>
              </div>
              {review && (
                <div className="review">
                  <div className="review-score">{review.score}<small>/100</small></div>
                  <div>
                    <p>{review.summary}</p>
                    <ul>{review.strengths.map((s, i) => <li key={`s${i}`}>✓ {s}</li>)}{review.improvements.map((s, i) => <li key={`i${i}`}>→ {s}</li>)}</ul>
                  </div>
                </div>
              )}
              <div className="queue-actions" style={{ marginTop: 0 }}>
                <button className="btn btn-ghost" onClick={() => void runReview()} disabled={!!busy}>{busy === "review" ? "Reviewing…" : "Get AI feedback"}</button>
                <button className="btn btn-primary" onClick={() => void save()}><Icon name="bookmark" /> Save</button>
              </div>
            </div>
          ) : <div className="chart-empty">Your caption will appear here.</div>}
        </section>
      </div>

      <section className="dash-card">
        <header className="chart-head"><div><h3>Caption library</h3><p>{drafts.length} saved</p></div></header>
        {drafts.length ? (
          <div className="draft-grid">
            {drafts.map((d) => (
              <article className="draft-card" key={d.id}>
                <div className="row"><span>{new Date(d.updatedAt).toLocaleDateString()}</span>
                  <button className="icon-btn" style={{ height: 28, width: 28 }} aria-label={`Delete ${d.title}`} onClick={() => void remove(d.id)}><Icon name="x" /></button></div>
                <strong>{d.title}</strong>
                <p>{d.caption}</p>
              </article>
            ))}
          </div>
        ) : <p className="library-empty">Captions you save will live here.</p>}
      </section>
    </div>
  );
}
