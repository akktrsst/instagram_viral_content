import { FormEvent, useEffect, useState } from "react";
import { api, formatSeconds, type PostFormat, type Skill } from "../api";
import { Icon, type IconName } from "../icons";

const KIND_LABELS: Record<PostFormat, { label: string; icon: IconName }> = {
  story: { label: "Story video", icon: "video" },
  reel: { label: "Short reel", icon: "video" },
  explainer: { label: "Explainer", icon: "layers" },
  carousel: { label: "Carousel", icon: "grid" },
  photo: { label: "AI photo", icon: "image" },
  image: { label: "Text image", icon: "quote" },
};

export default function Skills({ onError, onUse }: { onError: (e: unknown) => void; onUse: (skill: Skill) => void }) {
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [open, setOpen] = useState<Skill | null>(null);
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api<Skill[]>("/api/v1/dashboard/skills").then(setSkills).catch(onError);
  }, [onError]);

  async function show(skill: Skill) {
    if (open?.id === skill.id) return setOpen(null);
    try {
      setOpen(await api<Skill>(`/api/v1/dashboard/skills/${skill.id}`));
    } catch (cause) {
      onError(cause);
    }
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    try {
      const skill = await api<Skill>("/api/v1/dashboard/skills", { method: "POST", body: JSON.stringify({ description }) });
      setSkills((current) => [...(current ?? []), skill]);
      setOpen(skill);
      setDescription("");
    } catch (cause) {
      onError(cause);
    } finally {
      setCreating(false);
    }
  }

  async function remove(skill: Skill) {
    if (!window.confirm(`Delete the skill "${skill.name}"?`)) return;
    try {
      await api(`/api/v1/dashboard/skills/${skill.id}`, { method: "DELETE" });
      setSkills((current) => current?.filter((s) => s.id !== skill.id) ?? null);
      if (open?.id === skill.id) setOpen(null);
    } catch (cause) {
      onError(cause);
    }
  }

  const groups = [
    { title: "Story & long videos", items: skills?.filter((s) => s.kind === "story") ?? [] },
    { title: "Other formats", items: skills?.filter((s) => s.kind !== "story") ?? [] },
  ].filter((g) => g.items.length);

  return (
    <div className="dash">
      <form className="dash-card skill-create" onSubmit={create}>
        <div className="chart-head"><div><h3>Create a skill</h3><p>Describe a kind of post you want to make again and again. We'll turn it into a reusable recipe.</p></div></div>
        <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} aria-label="Describe the skill"
          placeholder="e.g. 60-second true-crime style mystery stories with a twist ending, or 'travel diary reels for hidden places in India'" minLength={10} maxLength={1000} required />
        <div className="create-foot">
          <span className="fine-print">Takes a few seconds. You can use it right away from Create & queue.</span>
          <button className="save-button" type="submit" disabled={creating || description.trim().length < 10}>
            {creating ? <><span className="spinner" /> Creating…</> : <><Icon name="sparkles" /> Create skill</>}
          </button>
        </div>
      </form>

      {skills === null && <div className="dash-loading">Loading skills…</div>}
      {groups.map((group) => (
        <section key={group.title}>
          <h3 className="section-title">{group.title}</h3>
          <div className="skill-grid">
            {group.items.map((skill) => (
              <article key={skill.id} className={open?.id === skill.id ? "dash-card skill-card open" : "dash-card skill-card"}>
                <div className="skill-top">
                  <span className="stat-ico"><Icon name={KIND_LABELS[skill.kind].icon} /></span>
                  <span className="skill-badges">
                    <span className="status status-draft">{KIND_LABELS[skill.kind].label}</span>
                    {!skill.builtin && <span className="status status-approved">Yours</span>}
                  </span>
                </div>
                <h4>{skill.name}</h4>
                <p>{skill.description}</p>
                {skill.kind === "story" && <small className="fine-print">Default length {formatSeconds(skill.default_seconds)}</small>}
                {open?.id === skill.id && open.instructions && (
                  <div className="skill-detail">
                    <strong>How it writes</strong>
                    <p>{open.instructions}</p>
                    {open.visual_guidance && <><strong>How it looks</strong><p>{open.visual_guidance}</p></>}
                  </div>
                )}
                <div className="skill-actions">
                  <button className="btn btn-primary" onClick={() => onUse(skill)}>Use</button>
                  <button className="btn btn-ghost" onClick={() => void show(skill)}>{open?.id === skill.id ? "Hide" : "Details"}</button>
                  {!skill.builtin && <button className="btn btn-ghost btn-danger" onClick={() => void remove(skill)} aria-label={`Delete ${skill.name}`}><Icon name="x" /></button>}
                </div>
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
