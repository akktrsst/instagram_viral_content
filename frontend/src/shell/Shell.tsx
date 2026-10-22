import { useCallback, useEffect, useState } from "react";
import { sendEmailVerification, signOut, type User } from "firebase/auth";
import { ApiError } from "../api";
import { getFirebaseServices } from "../firebase";
import { Icon, Logo, type IconName } from "../icons";
import Home from "../dashboard/Home";
import Content from "../dashboard/Content";
import Overview from "../dashboard/Overview";
import Audience from "../dashboard/Audience";
import CaptionLab from "../studio/CaptionLab";
import Skills from "../dashboard/Skills";
import type { ContentPreset } from "../dashboard/Content";

export const VIEWS = [
  { key: "home", label: "Home", icon: "home", title: "Home", blurb: "Your Instagram at a glance." },
  { key: "content", label: "Create & queue", short: "Create", icon: "layers", title: "Create & queue", blurb: "Create story videos, reels, carousels and photos, review them, and post to Instagram." },
  { key: "skills", label: "Skills", icon: "sparkles", title: "Skills", blurb: "Reusable recipes for every kind of post: story genres, recipes, countdowns and your own." },
  { key: "analytics", label: "Analytics", icon: "chart", title: "Analytics", blurb: "Followers, reach and engagement over time." },
  { key: "audience", label: "Audience", icon: "users", title: "Audience", blurb: "Who follows you and where they are." },
  { key: "lab", label: "Caption lab", short: "Captions", icon: "pen", title: "Caption lab", blurb: "Brainstorm ideas and captions, and get AI feedback before you post." },
] as const satisfies readonly { key: string; label: string; icon: IconName; title: string; blurb: string; short?: string }[];

export type View = (typeof VIEWS)[number]["key"];
type Theme = "light" | "dark" | "system";

function readHash(): View {
  const hash = window.location.hash.slice(1);
  return VIEWS.some((v) => v.key === hash) ? (hash as View) : "home";
}

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

export default function Shell({ user }: { user: User }) {
  const [view, setViewState] = useState<View>(readHash);
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [access, setAccess] = useState<"ok" | "denied" | "unverified">("ok");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preset, setPreset] = useState<ContentPreset | undefined>();

  useEffect(() => {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
    try {
      if (theme === "system") localStorage.removeItem("theme");
      else localStorage.setItem("theme", theme);
    } catch {
      /* storage unavailable: theme just won't persist */
    }
  }, [theme]);

  useEffect(() => {
    const onHash = () => setViewState(readHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const setView = useCallback((next: View) => {
    setViewState(next);
    setError("");
    window.history.replaceState(null, "", `#${next}`);
    window.scrollTo({ top: 0 });
  }, []);

  const onError = useCallback((cause: unknown) => {
    if (cause instanceof ApiError && cause.status === 403) {
      setAccess(cause.message === "EMAIL_NOT_VERIFIED" ? "unverified" : "denied");
      return;
    }
    // Server messages are written for people; anything else (e.g. a dropped connection) is not.
    setError(cause instanceof ApiError ? cause.message : "Something went wrong. Check your connection and try again.");
  }, []);

  async function verifyEmail() {
    try {
      await sendEmailVerification(user);
      setNotice(`Verification email sent to ${user.email}. Click the link, then press "I've verified".`);
    } catch (cause) {
      console.error(cause);
      setError("We couldn't send the verification email. Please try again in a minute.");
    }
  }

  async function recheck() {
    await user.reload();
    await user.getIdToken(true);
    setNotice("");
    setAccess("ok");
  }

  const isDark = theme === "dark" || (theme === "system" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  const current = VIEWS.find((v) => v.key === view)!;
  const initial = (user.email ?? "?")[0].toUpperCase();

  return (
    <div className="shell">
      <aside className="sidebar">
        <Logo subtitle="Instagram manager" />
        <div className="nav-label">Workspace</div>
        {VIEWS.map((item) => (
          <button key={item.key} className={view === item.key ? "nav-item active" : "nav-item"} onClick={() => setView(item.key)} aria-current={view === item.key ? "page" : undefined}>
            <Icon name={item.icon} /> {item.label}
          </button>
        ))}
        <div className="sidebar-promo">
          <strong>Tell a story</strong>
          <p>Story videos from 20 seconds to 2 minutes, with narration and real motion.</p>
          <button className="btn" onClick={() => { setPreset({ skillId: "story", format: "story" }); setView("content"); }}><Icon name="video" /> New story</button>
        </div>
        <div className="account">
          <span className="avatar">{initial}</span>
          <div className="account-text"><strong>{user.email}</strong><small>{user.emailVerified ? "Verified" : "Not verified"}</small></div>
          <button className="icon-btn" onClick={() => setTheme(isDark ? "light" : "dark")} aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}><Icon name={isDark ? "sun" : "moon"} /></button>
          <button className="icon-btn" onClick={() => void signOut(getFirebaseServices().auth)} aria-label="Sign out"><Icon name="logout" /></button>
        </div>
      </aside>

      <main className="main">
        <div className="mobile-header">
          <Logo />
          <div className="topbar-actions">
            <button className="icon-btn" onClick={() => setTheme(isDark ? "light" : "dark")} aria-label="Toggle theme"><Icon name={isDark ? "sun" : "moon"} /></button>
            <button className="icon-btn" onClick={() => void signOut(getFirebaseServices().auth)} aria-label="Sign out"><Icon name="logout" /></button>
          </div>
        </div>

        <header className="topbar">
          <div>
            <h1>{current.title}</h1>
            <p>{current.blurb}</p>
          </div>
          {view !== "content" && (
            <div className="topbar-actions">
              <button className="btn btn-primary" onClick={() => setView("content")}><Icon name="plus" /><span className="btn-label">New post</span></button>
            </div>
          )}
        </header>

        <div className="dash" style={{ marginBottom: access === "ok" && !error && !notice ? 0 : 20 }}>
          {access === "denied" && <div role="alert" className="message error">{user.email} doesn't have access to this workspace yet. Ask the workspace owner to add you.</div>}
          {access === "unverified" && (
            <div role="alert" className="message warn verify-box">
              <span>Verify {user.email} before managing Instagram, so nobody else can claim your address.</span>
              <button className="btn btn-ghost" onClick={() => void verifyEmail()}>Send verification email</button>
              <button className="btn btn-ghost" onClick={() => void recheck()}>I've verified</button>
            </div>
          )}
          {notice && <div role="status" className="message success">{notice}</div>}
          {error && <div role="alert" className="message error">{error}</div>}
        </div>

        {(access === "ok" || view === "lab") && (
          <>
            {view === "home" && access === "ok" && <Home onError={onError} onNavigate={setView} />}
            {view === "content" && <Content onError={onError} preset={preset} />}
            {view === "skills" && <Skills onError={onError} onUse={(skill) => { setPreset({ skillId: skill.id, format: skill.kind }); setView("content"); }} />}
            {view === "analytics" && <Overview onError={onError} onOpenContent={() => setView("content")} />}
            {view === "audience" && <Audience onError={onError} />}
            {view === "lab" && <CaptionLab />}
          </>
        )}
      </main>

      <nav className="bottom-nav" aria-label="Sections">
        {VIEWS.map((item) => (
          <button key={item.key} className={view === item.key ? "active" : ""} onClick={() => setView(item.key)}>
            <Icon name={item.icon} />{"short" in item ? item.short : item.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
