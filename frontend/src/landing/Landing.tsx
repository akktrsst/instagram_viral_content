import { FormEvent, useEffect, useState } from "react";
import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from "firebase/auth";
import { getFirebaseServices } from "../firebase";
import { Icon, Logo, type IconName } from "../icons";

const FEATURES: { icon: IconName; title: string; body: string }[] = [
  { icon: "video", title: "AI reels with voiceover", body: "Type a topic and get a 9:16 reel: AI scene images, a natural voiceover, word-timed captions and a cover, ready to publish." },
  { icon: "grid", title: "Carousels & AI photos", body: "Swipeable carousels and striking AI photos rendered in your brand colours, fonts and handle at Instagram's ideal size." },
  { icon: "send", title: "Review, then one-tap publish", body: "Every draft waits for you. Edit the caption, invite collaborators, and post straight to Instagram with one tap." },
  { icon: "chart", title: "Analytics that build up daily", body: "Followers, reach, views and profile visits tracked over time, plus per-post saves, shares and comments." },
  { icon: "users", title: "Know your audience", body: "Age, gender, top countries and cities from Instagram's own insights once your account reaches 100 followers." },
  { icon: "shield", title: "Safe for your account", body: "Instagram-approved publishing only: no bots, no auto-follows, no scraping. AI content is labelled and nothing posts without you." },
];

const STEPS = [
  { title: "Drop in a topic", body: "One line is enough: a tip, a trend, a question your audience asks." },
  { title: "AI writes & renders", body: "Script, caption, hashtags, visuals and voiceover in about a minute." },
  { title: "You review", body: "Preview the reel or slides, tweak the words, choose collaborators." },
  { title: "Publish & learn", body: "Post to Instagram and watch reach, saves and followers in one place." },
];

export default function Landing() {
  const [auth, setAuth] = useState<"signin" | "signup" | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="landing">
      <nav className={scrolled ? "l-nav scrolled" : "l-nav"}>
        <div className="l-container l-nav-inner">
          <a href="#top" aria-label="Studio home"><Logo /></a>
          <div className="l-links">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#safety">Safety</a>
          </div>
          <div className="l-nav-cta">
            <button className="btn btn-ghost" onClick={() => setAuth("signin")}>Sign in</button>
            <button className="btn btn-primary" onClick={() => setAuth("signup")}>Get started</button>
          </div>
        </div>
      </nav>

      <header className="hero" id="top">
        <div className="l-container hero-grid">
          <div>
            <span className="pill"><b>New</b> AI reels with voiceover, built in</span>
            <h1>Grow on Instagram with <span className="grad-text">content that makes itself.</span></h1>
            <p className="hero-sub">Turn one-line ideas into reels, carousels and photos in your brand style. Review them, post with a tap, and see exactly what's working.</p>
            <div className="hero-ctas">
              <button className="btn btn-primary btn-lg" onClick={() => setAuth("signup")}>Start creating <Icon name="arrowRight" /></button>
              <a className="btn btn-ghost btn-lg" href="#how">See how it works</a>
            </div>
            <div className="hero-proof">
              <span><Icon name="check" /> Instagram-approved publishing</span>
              <span><Icon name="check" /> You approve every post</span>
              <span><Icon name="check" /> Reels in about a minute</span>
            </div>
          </div>

          <div className="phone-stage" aria-hidden="true">
            <div className="phone">
              <div className="phone-screen">
                <div className="phone-top"><span>Reels</span><Icon name="instagram" /></div>
                <div className="phone-chip">3 prompts for app plans</div>
                <div className="phone-caption">Turn your <em>idea</em> into a plan</div>
                <div className="phone-rail">
                  <span><Icon name="heart" />2.4K</span>
                  <span><Icon name="comment" />186</span>
                  <span><Icon name="send" />412</span>
                </div>
                <div className="phone-bottom">@your.brand · Original audio</div>
              </div>
            </div>
            <div className="float-card float-1">
              <span className="badge-icon" style={{ background: "var(--good-soft)", color: "var(--good)" }}><Icon name="check" /></span>
              <div><strong>Published</strong><small>Reel · just now</small></div>
            </div>
            <div className="float-card float-2">
              <span className="badge-icon" style={{ background: "var(--primary-soft)", color: "var(--primary)" }}><Icon name="trending" /></span>
              <div><strong>+38% reach</strong><small>vs last week</small></div>
            </div>
            <div className="float-card float-3">
              <span className="badge-icon" style={{ background: "var(--warn-soft)", color: "var(--warn)" }}><Icon name="bolt" /></span>
              <div><strong>Reel ready</strong><small>Rendered in 58s</small></div>
            </div>
          </div>
        </div>
      </header>

      <section className="l-section alt" id="features">
        <div className="l-container">
          <div className="section-head">
            <span className="eyebrow">Everything in one place</span>
            <h2>Create, publish and track without juggling five apps</h2>
            <p>A single workspace for your Instagram: an AI content studio, a review queue and analytics.</p>
          </div>
          <div className="feature-grid">
            {FEATURES.map((f) => (
              <article className="feature" key={f.title}>
                <span className="feature-icon"><Icon name={f.icon} /></span>
                <h3>{f.title}</h3>
                <p>{f.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="l-section" id="how">
        <div className="l-container">
          <div className="section-head">
            <span className="eyebrow">How it works</span>
            <h2>From idea to posted in four steps</h2>
          </div>
          <div className="steps">
            {STEPS.map((s, i) => (
              <div className="step" key={s.title}>
                <span className="step-num">{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="l-section alt" id="safety">
        <div className="l-container">
          <div className="section-head">
            <span className="eyebrow">Built to Instagram's rules</span>
            <h2>Grow without risking your account</h2>
          </div>
          <div className="stat-band">
            <div><strong>Approved access</strong><span>Posts and insights go through Instagram's own approved connection, never scraping or bots.</span></div>
            <div><strong>Made for Reels</strong><span>Full-screen vertical videos in the exact format Instagram expects, sharp on every phone.</span></div>
            <div><strong>You decide</strong><span>Nothing goes live without your tap. AI-assisted posts are labelled in the caption.</span></div>
          </div>
        </div>
      </section>

      <section className="l-section">
        <div className="l-container">
          <div className="cta-band">
            <h2>Your next 30 posts are one idea away</h2>
            <p>Sign in to your workspace and turn today's idea into tomorrow's best-performing reel.</p>
            <button className="btn btn-white btn-lg" onClick={() => setAuth("signup")}>Get started <Icon name="arrowRight" /></button>
          </div>
        </div>
      </section>

      <footer className="l-footer">
        <div className="l-container l-footer-inner">
          <Logo />
          <span>Not affiliated with or endorsed by Instagram.</span>
        </div>
      </footer>

      {auth && <AuthDialog mode={auth} onMode={setAuth} onClose={() => setAuth(null)} />}
    </div>
  );
}

function AuthDialog({ mode, onMode, onClose }: { mode: "signin" | "signup"; onMode: (m: "signin" | "signup") => void; onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const { auth } = getFirebaseServices();
      if (mode === "signup") await createUserWithEmailAndPassword(auth, email, password);
      else await signInWithEmailAndPassword(auth, email, password);
    } catch (cause) {
      const code = (cause as { code?: string }).code ?? "";
      setError(
        code.includes("invalid-credential") || code.includes("wrong-password") ? "Email or password is incorrect."
          : code.includes("email-already-in-use") ? "An account with this email already exists. Sign in instead."
          : code.includes("weak-password") ? "Use at least 6 characters for your password."
          : code.includes("network") ? "You seem to be offline. Check your connection and try again."
          : code.includes("too-many-requests") ? "Too many attempts. Please wait a moment and try again."
          : "We couldn't sign you in. Please try again.",
      );
      setBusy(false);
    }
  }

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="icon-btn close" onClick={onClose} aria-label="Close"><Icon name="x" /></button>
        <Logo />
        <h2 id="auth-title">{mode === "signin" ? "Welcome back" : "Create your workspace"}</h2>
        <p>{mode === "signin" ? "Sign in to manage your Instagram." : "Start turning ideas into posts in minutes."}</p>
        <form onSubmit={submit}>
          <div>
            <label htmlFor="auth-email">Email</label>
            <input id="auth-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </div>
          <div>
            <label htmlFor="auth-password">Password</label>
            <input id="auth-password" type="password" autoComplete={mode === "signin" ? "current-password" : "new-password"} minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <div role="alert" className="message error">{error}</div>}
          <button className="btn btn-primary btn-lg" type="submit" disabled={busy}>
            {busy ? <span className="spinner" /> : mode === "signin" ? "Sign in" : "Create account"}
          </button>
        </form>
        <button className="switch" onClick={() => { setError(""); onMode(mode === "signin" ? "signup" : "signin"); }}>
          {mode === "signin" ? "New here? Create an account" : "Already have an account? Sign in"}
        </button>
      </div>
    </div>
  );
}
