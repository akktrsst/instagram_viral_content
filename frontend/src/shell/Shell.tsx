import { useCallback, useEffect, useState } from "react";
import { sendEmailVerification, signOut, type User } from "firebase/auth";
import { ApiError } from "../api";
import { getFirebaseServices } from "../firebase";
import { Icon, Logo, type IconName } from "../icons";
import { Link, match, navigate, usePath } from "../router";
import Home from "../dashboard/Home";
import Overview from "../dashboard/Overview";
import Audience from "../dashboard/Audience";
import Skills from "../dashboard/Skills";
import CaptionLab from "../studio/CaptionLab";
import Create from "../app/Create";
import Library from "../app/Library";
import PostDetail from "../app/PostDetail";
import Published from "../app/Performance";

type Page = { path: string; label: string; icon: IconName; title: string; blurb: string; mobile?: boolean };

const PAGES: Page[] = [
  { path: "/app", label: "Dashboard", icon: "home", title: "Dashboard", blurb: "Your Instagram at a glance.", mobile: true },
  { path: "/app/create", label: "Create", icon: "plus", title: "Create", blurb: "Pick what to make, describe it, and we'll do the rest.", mobile: true },
  { path: "/app/library", label: "Library", icon: "layers", title: "Library", blurb: "Everything you've made: watch, edit and post.", mobile: true },
  { path: "/app/analytics", label: "Analytics", icon: "chart", title: "Analytics", blurb: "Followers, reach and how each post performed.", mobile: true },
  { path: "/app/audience", label: "Audience", icon: "users", title: "Audience", blurb: "Who follows you and where they are." },
  { path: "/app/skills", label: "Skills", icon: "sparkles", title: "Skills", blurb: "Reusable recipes for every kind of post, including your own.", mobile: true },
  { path: "/app/captions", label: "Caption lab", icon: "pen", title: "Caption lab", blurb: "Brainstorm captions and get feedback before you post." },
];

type Theme = "light" | "dark" | "system";

function readTheme(): Theme {
  try {
    const saved = localStorage.getItem("theme");
    return saved === "light" || saved === "dark" ? saved : "system";
  } catch {
    return "system";
  }
}

export default function Shell({ user }: { user: User }) {
  const path = usePath();
  const [theme, setTheme] = useState<Theme>(readTheme);
  const [access, setAccess] = useState<"ok" | "denied" | "unverified">("ok");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

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

  useEffect(() => setError(""), [path]);

  const onError = useCallback((cause: unknown) => {
    if (cause instanceof ApiError && cause.status === 403) {
      setAccess(cause.message === "EMAIL_NOT_VERIFIED" ? "unverified" : "denied");
      return;
    }
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

  const postMatch = match("/app/posts/:id", path);
  const page = postMatch
    ? { path, label: "Post", icon: "image" as IconName, title: "Post", blurb: "Watch, edit and publish." }
    : PAGES.find((p) => p.path === path) ?? PAGES[0];
  const isDark = theme === "dark" || (theme === "system" && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
  const initial = (user.email ?? "?")[0].toUpperCase();
  const skillParam = new URLSearchParams(window.location.search).get("skill") ?? undefined;

  function content() {
    if (postMatch) return <PostDetail id={Number(postMatch.id)} onError={onError} />;
    switch (page.path) {
      case "/app/create": return <Create onError={onError} skillParam={skillParam} />;
      case "/app/library": return <Library onError={onError} />;
      case "/app/analytics": return <><Overview onError={onError} onOpenContent={() => navigate("/app/library")} /><Published onError={onError} /></>;
      case "/app/audience": return <Audience onError={onError} />;
      case "/app/skills": return <Skills onError={onError} onUse={(skill) => navigate(`/app/create?skill=${skill.id}`)} />;
      case "/app/captions": return <CaptionLab />;
      default: return <Home onError={onError} />;
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/app" aria-label="Dashboard"><Logo subtitle="Instagram studio" /></Link>
        <Link to="/app/create" className="btn btn-primary sidebar-create"><Icon name="plus" /> New creation</Link>
        <div className="nav-label">Studio</div>
        {PAGES.map((item) => (
          <Link key={item.path} to={item.path} className={page.path === item.path ? "nav-item active" : "nav-item"} aria-current={page.path === item.path ? "page" : undefined}>
            <Icon name={item.icon} /> {item.label}
          </Link>
        ))}
        <div className="sidebar-promo">
          <strong>Make a movie</strong>
          <p>Characters who talk on camera, in your language.</p>
          <Link to="/app/create" className="btn"><Icon name="video" /> Start</Link>
        </div>
        <div className="account">
          <span className="avatar">{initial}</span>
          <div className="account-text"><strong>{user.email}</strong><small>{user.emailVerified ? "Verified" : "Not verified"}</small></div>
          <button className="icon-btn" onClick={() => setTheme(isDark ? "light" : "dark")} aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}><Icon name={isDark ? "sun" : "moon"} /></button>
          <button className="icon-btn" onClick={() => void signOut(getFirebaseServices().auth).then(() => navigate("/"))} aria-label="Sign out"><Icon name="logout" /></button>
        </div>
      </aside>

      <main className="main">
        <div className="mobile-header">
          <Link to="/app" aria-label="Dashboard"><Logo /></Link>
          <div className="topbar-actions">
            <button className="icon-btn" onClick={() => setTheme(isDark ? "light" : "dark")} aria-label="Toggle theme"><Icon name={isDark ? "sun" : "moon"} /></button>
            <button className="icon-btn" onClick={() => void signOut(getFirebaseServices().auth).then(() => navigate("/"))} aria-label="Sign out"><Icon name="logout" /></button>
          </div>
        </div>

        {!postMatch && (
          <header className="topbar">
            <div><h1>{page.title}</h1><p>{page.blurb}</p></div>
            {page.path !== "/app/create" && (
              <div className="topbar-actions"><Link to="/app/create" className="btn btn-primary"><Icon name="plus" /><span className="btn-label">New creation</span></Link></div>
            )}
          </header>
        )}

        {(access !== "ok" || error || notice) && (
          <div className="dash" style={{ marginBottom: 20, marginTop: postMatch ? 20 : 0 }}>
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
        )}

        {(access === "ok" || page.path === "/app/captions") && <div className={postMatch ? "page-pad" : ""}>{content()}</div>}
      </main>

      <nav className="bottom-nav" aria-label="Sections">
        {PAGES.filter((p) => p.mobile).map((item) => (
          <Link key={item.path} to={item.path} className={page.path === item.path ? "active" : ""}>
            <Icon name={item.icon} />{item.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
