import { useState } from "react";
import { Icon, type IconName } from "../icons";
import { Link } from "../router";

const SHOWCASE = [
  { src: "/showcase/movie-lipsync", title: "Dadi's advice", kind: "Movie · lip-sync", text: "A character speaking Hindi on camera, with her voice and lips generated together." },
  { src: "/showcase/station-dog", title: "Platform Three", kind: "Story video · 30s", text: "A street dog waits for the girl who shared her lunch. Same dog, same girl, every scene." },
  { src: "/showcase/dadi-roti", title: "Gol roti aur sabr", kind: "Story with dialogue · Hindi", text: "A grandmother and granddaughter talk in their own voices, with name tags on the captions." },
  { src: "/showcase/transformer-explainer", title: "How transformers work", kind: "Explainer · animated diagram", text: "A diagram that builds step by step while the voice explains." },
];

const MAKE: { icon: IconName; title: string; text: string; tone: string }[] = [
  { icon: "video", title: "Movies", text: "Every scene is real video. Characters speak on camera with lip-sync and natural sound.", tone: "tone-violet" },
  { icon: "sparkles", title: "Story videos", text: "Any genre, 20 seconds to 2 minutes, with narration, character voices and matching pictures.", tone: "tone-pink" },
  { icon: "bolt", title: "Short reels", text: "Punchy 20–40 second reels with voiceover and bold captions.", tone: "tone-amber" },
  { icon: "layers", title: "Explainers", text: "Animated diagrams for processes, recipes, systems and how-tos.", tone: "tone-teal" },
  { icon: "grid", title: "Carousels", text: "Swipeable slides in your brand colours: tips, steps, lists.", tone: "tone-blue" },
  { icon: "image", title: "Photos & quotes", text: "Striking AI photos and clean text graphics for greetings and announcements.", tone: "tone-green" },
];

const LANGS = ["English", "हिन्दी", "Hinglish", "भोजपुरी", "বাংলা", "मराठी", "தமிழ்", "తెలుగు", "ગુજરાતી", "ಕನ್ನಡ", "മലയാളം", "ਪੰਜਾਬੀ", "اردو"];

const STEPS = [
  { title: "Describe it", text: "Type your idea in your own words. Pick the type, genre, language and length." },
  { title: "AI writes and directs", text: "It plans the story, casts the characters, writes the dialogue, and an editor checks the script." },
  { title: "Scenes are made", text: "Characters keep the same look and voice in every scene. Key moments are filmed as real video." },
  { title: "Review and post", text: "Watch it, tweak the caption, and post to Instagram with one tap. Then track how it does." },
];

const FAQS = [
  { q: "What can I make?", a: "Movies with talking characters, narrated story videos, short reels, animated explainers, carousels, AI photos and quote images." },
  { q: "How long can videos be?", a: "Story videos and movies can be anywhere from 20 seconds to 2 minutes. You choose the length before you create." },
  { q: "Which languages are supported?", a: "English, Hindi, Hinglish, Bhojpuri, Bengali, Marathi, Tamil, Telugu, Gujarati, Kannada, Malayalam, Punjabi and Urdu. Each one is read by a natural voice; Bhojpuri uses the Hindi voice." },
  { q: "Do characters really talk?", a: "Yes. In story videos each character speaks in their own voice. In movie mode they speak on camera with lip-sync. Lip-sync looks best when the face is turned toward the camera, and is less precise in some languages." },
  { q: "Does anything post without me?", a: "No. Everything waits in your library until you approve it. Posting uses Instagram's own approved connection, never bots or scraping." },
  { q: "How long does it take?", a: "Photos and carousels take under a minute. A one-minute story takes a few minutes, and a two-minute movie can take 15 minutes or more. It runs in the background, so you can leave the page." },
  { q: "Can I reuse a style?", a: "Yes. Skills are reusable recipes such as horror story, recipe video or mini documentary. You can also describe a new one and it's created for you." },
];

function ShowVideo({ src, className = "" }: { src: string; className?: string }) {
  return <video className={className} src={`${src}.mp4`} poster={`${src}.jpg`} autoPlay muted loop playsInline preload="metadata" />;
}

export function HomePage() {
  return (
    <>
      <header className="hero">
        <div className="l-container hero-grid">
          <div>
            <span className="pill"><b>New</b> Movie mode: characters talk with lip-sync</span>
            <h1>Turn ideas into <span className="grad-text">movies, stories and reels</span> for Instagram.</h1>
            <p className="hero-sub">Describe it in your own words, in your own language. Get finished videos with characters, voices and real motion, then post with one tap.</p>
            <div className="hero-ctas">
              <Link to="/login?new=1" className="btn btn-primary btn-lg">Start creating <Icon name="arrowRight" /></Link>
              <Link to="/showcase" className="btn btn-ghost btn-lg">See examples</Link>
            </div>
            <div className="hero-proof">
              <span><Icon name="check" /> 20 seconds to 2 minutes</span>
              <span><Icon name="check" /> 13 languages</span>
              <span><Icon name="check" /> Nothing posts without you</span>
            </div>
          </div>
          <div className="phone-stage">
            <div className="phone phone-video"><ShowVideo src="/showcase/station-dog" /></div>
            <div className="phone phone-video phone-back"><ShowVideo src="/showcase/dadi-roti" /></div>
            <div className="float-card float-1">
              <span className="badge-icon" style={{ background: "var(--good-soft)", color: "var(--good)" }}><Icon name="check" /></span>
              <div><strong>Same characters</strong><small>in every scene</small></div>
            </div>
            <div className="float-card float-3">
              <span className="badge-icon" style={{ background: "var(--primary-soft)", color: "var(--primary)" }}><Icon name="mic" /></span>
              <div><strong>Their own voices</strong><small>in your language</small></div>
            </div>
          </div>
        </div>
      </header>

      <section className="l-section alt">
        <div className="l-container">
          <div className="section-head"><span className="eyebrow">One studio</span><h2>Everything you post, made for you</h2><p>Pick what you want and describe it. The studio writes, designs, voices and edits it.</p></div>
          <div className="feature-grid">
            {MAKE.map((m) => (
              <article key={m.title} className={`feature ${m.tone}`}>
                <span className="feature-icon"><Icon name={m.icon} /></span>
                <h3>{m.title}</h3>
                <p>{m.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="l-section">
        <div className="l-container split">
          <div className="split-media"><div className="phone phone-video"><ShowVideo src="/showcase/movie-lipsync" /></div></div>
          <div>
            <span className="eyebrow">Movie mode</span>
            <h2 className="split-title">Characters who actually talk</h2>
            <p className="split-text">Every scene is filmed as real video. When a character speaks, their voice, lips and expression are generated together, with natural sound around them, and the narrator ties it all together.</p>
            <ul className="tick-list">
              <li><Icon name="check" /> Consistent faces and outfits from scene to scene</li>
              <li><Icon name="check" /> A distinct voice for every character</li>
              <li><Icon name="check" /> Speaker name tags on the captions</li>
            </ul>
            <Link to="/login?new=1" className="btn btn-primary">Make a movie <Icon name="arrowRight" /></Link>
          </div>
        </div>
      </section>

      <section className="l-section alt">
        <div className="l-container">
          <div className="section-head"><span className="eyebrow">Your language</span><h2>Speak to your audience in theirs</h2><p>Write, caption and narrate in 13 languages, each with natural voices.</p></div>
          <div className="lang-cloud">{LANGS.map((l) => <span key={l}>{l}</span>)}</div>
        </div>
      </section>

      <section className="l-section">
        <div className="l-container">
          <div className="section-head"><span className="eyebrow">Showcase</span><h2>Made with the studio</h2></div>
          <div className="showcase-grid">
            {SHOWCASE.slice(0, 3).map((s) => (
              <figure key={s.src} className="show-card">
                <ShowVideo src={s.src} />
                <figcaption><small>{s.kind}</small><strong>{s.title}</strong></figcaption>
              </figure>
            ))}
          </div>
          <div className="center-cta"><Link to="/showcase" className="btn btn-ghost">See all examples <Icon name="arrowRight" /></Link></div>
        </div>
      </section>

      <HowSection />
      <CtaBand />
    </>
  );
}

function HowSection() {
  return (
    <section className="l-section alt" id="how">
      <div className="l-container">
        <div className="section-head"><span className="eyebrow">How it works</span><h2>From idea to posted in four steps</h2></div>
        <div className="steps">
          {STEPS.map((s, i) => (
            <div className="step" key={s.title}><span className="step-num">{i + 1}</span><h3>{s.title}</h3><p>{s.text}</p></div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CtaBand() {
  return (
    <section className="l-section">
      <div className="l-container">
        <div className="cta-band">
          <h2>Your next story is one idea away</h2>
          <p>Describe it in a sentence. We'll turn it into something worth watching.</p>
          <Link to="/login?new=1" className="btn btn-white btn-lg">Get started <Icon name="arrowRight" /></Link>
        </div>
      </div>
    </section>
  );
}

function PageHead({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <header className="page-head">
      <div className="l-container">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
    </header>
  );
}

const FEATURE_GROUPS: { title: string; items: { icon: IconName; title: string; text: string }[] }[] = [
  { title: "Create", items: [
    { icon: "video", title: "Movie mode", text: "Real video for every scene, with lip-synced dialogue and natural sound." },
    { icon: "sparkles", title: "Story videos", text: "20 seconds to 2 minutes. An AI editor reviews every script before it's made." },
    { icon: "users", title: "Characters that stay the same", text: "A reference sheet keeps faces, hair and clothes consistent across scenes." },
    { icon: "mic", title: "Voices for everyone", text: "A narrator plus a distinct voice for each character, by age and gender." },
    { icon: "layers", title: "Explainers", text: "Animated diagrams that build up step by step." },
    { icon: "grid", title: "Carousels, photos, quotes", text: "On-brand slides, AI photos and text graphics." },
  ]},
  { title: "Make it yours", items: [
    { icon: "pen", title: "Skills", text: "Reusable recipes: horror, love, kids' moral stories, recipes, countdowns, documentaries, and your own." },
    { icon: "trending", title: "Any topic", text: "Food, comedy, fitness, festivals, offers, news: the post follows your idea." },
    { icon: "comment", title: "13 languages", text: "Hindi, Bhojpuri, Hinglish, Tamil, Bengali and more, written and voiced natively." },
  ]},
  { title: "Publish and grow", items: [
    { icon: "check", title: "Review before posting", text: "Edit captions and hashtags, invite collaborators, then post with one tap." },
    { icon: "chart", title: "Analytics", text: "Followers, reach, views and per-post saves, shares and comments, updated daily." },
    { icon: "shield", title: "Safe for your account", text: "Instagram's approved connection only. No bots, no scraping, AI content labelled." },
  ]},
];

export function FeaturesPage() {
  return (
    <>
      <PageHead eyebrow="Features" title="A full studio for Instagram" text="Everything from the first idea to the posted video and the numbers afterwards." />
      {FEATURE_GROUPS.map((group, i) => (
        <section key={group.title} className={i % 2 ? "l-section alt" : "l-section"}>
          <div className="l-container">
            <h2 className="group-title">{group.title}</h2>
            <div className="feature-grid">
              {group.items.map((f) => (
                <article key={f.title} className="feature">
                  <span className="feature-icon"><Icon name={f.icon} /></span>
                  <h3>{f.title}</h3>
                  <p>{f.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      ))}
      <CtaBand />
    </>
  );
}

export function ShowcasePage() {
  return (
    <>
      <PageHead eyebrow="Showcase" title="See what it makes" text="Real examples created with the studio, each from a one-line idea." />
      <section className="l-section">
        <div className="l-container showcase-grid wide">
          {SHOWCASE.map((s) => (
            <figure key={s.src} className="show-card">
              <video src={`${s.src}.mp4`} poster={`${s.src}.jpg`} controls playsInline preload="metadata" />
              <figcaption><small>{s.kind}</small><strong>{s.title}</strong><span>{s.text}</span></figcaption>
            </figure>
          ))}
        </div>
      </section>
      <CtaBand />
    </>
  );
}

export function HowPage() {
  return (
    <>
      <PageHead eyebrow="How it works" title="Like having a film crew in your pocket" text="Behind every video is a small team of AI helpers, each doing one job well." />
      <section className="l-section">
        <div className="l-container timeline">
          {[
            ["Planner", "Reads your idea and decides the title, genre, setting, characters (with their looks and voices) and the story beats for your chosen length."],
            ["Writer", "Writes the scenes: what each character says, what the narrator says, and exactly what the camera shows at that moment."],
            ["Editor", "Scores the script out of 10 for hook, story, dialogue, pacing and accuracy, and sends it back for a rewrite if it isn't ready."],
            ["Casting", "Draws a reference sheet so every character looks the same in every scene, and gives each a fitting voice."],
            ["Camera", "Creates each scene. Key moments, or every scene in movie mode, are filmed as real video with sound."],
            ["Editor's cut", "Adds voices, captions with speaker names, camera moves and a cover, and joins everything into one video."],
            ["You", "Watch it, edit the caption, and post when you're happy. The analytics show how it did."],
          ].map(([title, text], i) => (
            <div key={title} className="timeline-item">
              <span className="step-num">{i + 1}</span>
              <div><h3>{title}</h3><p>{text}</p></div>
            </div>
          ))}
        </div>
      </section>
      <CtaBand />
    </>
  );
}

export function FaqPage() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <>
      <PageHead eyebrow="FAQ" title="Questions, answered" text="Everything you might want to know before you start." />
      <section className="l-section">
        <div className="l-container faq">
          {FAQS.map((f, i) => (
            <div key={f.q} className={open === i ? "faq-item open" : "faq-item"}>
              <button onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}>
                {f.q}<Icon name={open === i ? "x" : "plus"} />
              </button>
              {open === i && <p>{f.a}</p>}
            </div>
          ))}
        </div>
      </section>
      <CtaBand />
    </>
  );
}
