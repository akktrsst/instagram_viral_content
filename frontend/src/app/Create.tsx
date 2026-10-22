import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, formatSeconds, languageLabel, savedLanguage, saveLanguage, type BotPost, type Language, type PostFormat, type Skill } from "../api";
import { Icon, type IconName } from "../icons";
import { navigate } from "../router";

type Choice = { id: string; format: PostFormat; style?: "cinematic" | "movie"; title: string; blurb: string; icon: IconName; badge?: string; tone: string };

const CHOICES: Choice[] = [
  { id: "movie", format: "story", style: "movie", title: "Movie", blurb: "Every scene is real video. Characters talk on camera with lip-sync and natural sound.", icon: "video", badge: "New", tone: "tone-violet" },
  { id: "story", format: "story", style: "cinematic", title: "Story video", blurb: "A narrated story with characters' voices, matching pictures and moving camera. Fast and affordable.", icon: "sparkles", tone: "tone-pink" },
  { id: "reel", format: "reel", title: "Short reel", blurb: "A punchy 20–40 second reel with voiceover and captions.", icon: "bolt", tone: "tone-amber" },
  { id: "explainer", format: "explainer", title: "Explainer", blurb: "An animated diagram that builds step by step as the voice explains.", icon: "layers", tone: "tone-teal" },
  { id: "carousel", format: "carousel", title: "Carousel", blurb: "Swipeable slides: tips, steps, lists or myth vs fact.", icon: "grid", tone: "tone-blue" },
  { id: "photo", format: "photo", title: "AI photo", blurb: "One striking picture with an optional headline.", icon: "image", tone: "tone-green" },
  { id: "image", format: "image", title: "Quote image", blurb: "A clean text graphic: quote, greeting or announcement.", icon: "quote", tone: "tone-slate" },
];

const EXAMPLES: Record<string, string[]> = {
  movie: ["A shy boy and a talking parrot become best friends in a busy Mumbai market", "Two old friends meet again at the railway station after 30 years", "A grandmother's secret recipe saves the family restaurant"],
  story: ["A street dog who waits every evening at a railway station for a little girl", "The ghost who lives in the old school library", "How a tea seller's daughter became a pilot"],
  reel: ["5 habits that make mornings easier", "Why you feel tired after lunch", "3 budget travel tricks for students"],
  explainer: ["How a seed grows into a tree", "How UPI payments work", "How the heart pumps blood"],
  carousel: ["7 study tips for exam season", "Myths vs facts about drinking water", "The best street foods of Delhi"],
  photo: ["Diwali greetings for my bakery customers", "Monsoon morning in the mountains", "A cosy reading corner on a rainy day"],
  image: ["A motivational quote for Monday", "Happy Holi wishes from our team", "We are open this Sunday"],
};

export default function Create({ onError, skillParam }: { onError: (e: unknown) => void; skillParam?: string }) {
  const [step, setStep] = useState<1 | 2>(skillParam ? 2 : 1);
  const [choice, setChoice] = useState<Choice>(CHOICES[0]);
  const [topic, setTopic] = useState("");
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillId, setSkillId] = useState(skillParam ?? "story");
  const [languages, setLanguages] = useState<Language[]>([]);
  const [language, setLanguage] = useState(savedLanguage);
  const [seconds, setSeconds] = useState(60);
  const [estimate, setEstimate] = useState<{ usd: number; minutes: number; shots: number } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Skill[]>("/api/v1/dashboard/skills").then((all) => {
      setSkills(all);
      const chosen = skillParam ? all.find((s) => s.id === skillParam) : undefined;
      if (chosen) {
        setChoice(CHOICES.find((c) => c.format === chosen.kind && c.style !== "movie") ?? CHOICES[1]);
        setSkillId(chosen.id);
        setSeconds(chosen.default_seconds);
      }
    }).catch(() => setSkills([]));
    api<Language[]>("/api/v1/dashboard/languages").then(setLanguages).catch(() => setLanguages([]));
  }, []);

  const isStory = choice.format === "story";
  useEffect(() => {
    if (!isStory) { setEstimate(null); return; }
    const timer = window.setTimeout(() => {
      api<{ usd: number; minutes: number; shots: number }>(`/api/v1/dashboard/estimate?style=${choice.style ?? "cinematic"}&seconds=${seconds}`)
        .then(setEstimate).catch(() => setEstimate(null));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [isStory, choice.style, seconds]);

  const genreSkills = useMemo(() => skills.filter((s) => s.kind === choice.format), [skills, choice.format]);

  function pick(next: Choice) {
    setChoice(next);
    setSkillId(next.format === "story" ? "story" : "");
    setStep(2);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const post = await api<BotPost>("/api/v1/dashboard/posts", {
        method: "POST",
        body: JSON.stringify({
          topic,
          format: choice.format,
          style: isStory ? choice.style ?? "cinematic" : null,
          skill_id: skillId || null,
          target_seconds: isStory ? seconds : null,
          language: language || null,
        }),
      });
      navigate(`/app/posts/${post.id}`);
    } catch (cause) {
      onError(cause);
      setBusy(false);
    }
  }

  if (step === 1) {
    return (
      <div className="dash">
        <div className="wizard-steps"><span className="active">1 · Choose</span><span>2 · Describe</span><span>3 · Create</span></div>
        <div className="choice-grid">
          {CHOICES.map((c) => (
            <button key={c.id} className={`choice-card ${c.tone}`} onClick={() => pick(c)}>
              <span className="choice-icon"><Icon name={c.icon} /></span>
              {c.badge && <span className="choice-badge">{c.badge}</span>}
              <strong>{c.title}</strong>
              <span>{c.blurb}</span>
              <span className="choice-go">Start <Icon name="arrowRight" /></span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <form className="dash create-wizard" onSubmit={submit}>
      <div className="wizard-steps"><button type="button" onClick={() => setStep(1)}>1 · Choose</button><span className="active">2 · Describe</span><span>3 · Create</span></div>

      <div className="create-layout">
        <section className="dash-card create-main">
          <div className={`create-kind ${choice.tone}`}>
            <span className="choice-icon"><Icon name={choice.icon} /></span>
            <div><strong>{choice.title}</strong><small>{choice.blurb}</small></div>
            <button type="button" className="btn btn-ghost" onClick={() => setStep(1)}>Change</button>
          </div>

          <label htmlFor="brief">{isStory ? "What's the story?" : "What's it about?"}</label>
          <textarea id="brief" className="brief" rows={4} value={topic} onChange={(e) => setTopic(e.target.value)} minLength={3} maxLength={1000} required
            placeholder={isStory ? "Describe the story in your own words: who it's about, what happens, the mood…" : "Describe your post in your own words: topic, audience, mood…"} />
          <div className="examples">
            <span>Try:</span>
            {(EXAMPLES[choice.id] ?? []).map((ex) => <button type="button" key={ex} className="example-chip" onClick={() => setTopic(ex)}>{ex}</button>)}
          </div>

          {genreSkills.length > 0 && (
            <>
              <label>{isStory ? "Genre" : "Style"}</label>
              <div className="genre-chips">
                {!isStory && <button type="button" className={skillId === "" ? "genre active" : "genre"} onClick={() => setSkillId("")}>General</button>}
                {genreSkills.map((s) => (
                  <button type="button" key={s.id} className={skillId === s.id ? "genre active" : "genre"} onClick={() => { setSkillId(s.id); if (isStory) setSeconds(s.default_seconds); }} title={s.description}>{s.name}</button>
                ))}
              </div>
            </>
          )}

          <div className="create-row">
            <div>
              <label htmlFor="language">Language</label>
              <select id="language" value={language} onChange={(e) => { setLanguage(e.target.value); saveLanguage(e.target.value); }}>
                <option value="">Same as my description</option>
                {languages.map((l) => <option key={l.code} value={l.code}>{languageLabel(l)}</option>)}
              </select>
            </div>
            {isStory && (
              <div className="length-field">
                <label htmlFor="length">Length <strong>{formatSeconds(seconds)}</strong></label>
                <input id="length" type="range" min={20} max={120} step={5} value={seconds} onChange={(e) => setSeconds(Number(e.target.value))} />
                <div className="range-marks"><span>20s</span><span>1 min</span><span>2 min</span></div>
              </div>
            )}
          </div>
        </section>

        <aside className="dash-card create-summary">
          <span className="wizard-steps-inline">3 · Create</span>
          <h3>Ready to create</h3>
          <ul className="summary-list">
            <li><span>Type</span><strong>{choice.title}</strong></li>
            {genreSkills.find((s) => s.id === skillId) && <li><span>{isStory ? "Genre" : "Style"}</span><strong>{genreSkills.find((s) => s.id === skillId)?.name}</strong></li>}
            <li><span>Language</span><strong>{languages.find((l) => l.code === language)?.name ?? "Auto"}</strong></li>
            {isStory && <li><span>Length</span><strong>{formatSeconds(seconds)}</strong></li>}
            {estimate && <li><span>Scenes</span><strong>about {estimate.shots}</strong></li>}
            {estimate && <li><span>Time to create</span><strong>about {estimate.minutes} min</strong></li>}
            {estimate && <li><span>Estimated cost</span><strong>${estimate.usd.toFixed(2)}</strong></li>}
          </ul>
          {choice.style === "movie" && (
            <p className="fine-print">Movie mode films every scene as real video with lip-synced dialogue. It costs more and takes longer than a story video. Lip-sync is good on faces turned to the camera, and less precise in some languages.</p>
          )}
          <button className="btn btn-primary btn-lg" type="submit" disabled={busy || topic.trim().length < 3}>
            {busy ? <><span className="spinner" /> Starting…</> : <><Icon name="sparkles" /> Create {choice.title.toLowerCase()}</>}
          </button>
          <small className="fine-print">It's made in the background. You'll see live progress, and nothing is posted until you approve it.</small>
        </aside>
      </div>
    </form>
  );
}
