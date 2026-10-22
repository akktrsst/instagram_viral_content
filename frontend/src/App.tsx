import { useEffect, useState } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { getFirebaseServices } from "./firebase";
import { Logo } from "./icons";
import { navigate, usePath } from "./router";
import Shell from "./shell/Shell";
import SiteLayout from "./site/Layout";
import LoginPage from "./site/Login";
import { FaqPage, FeaturesPage, HomePage, HowPage, ShowcasePage } from "./site/pages";

const SITE_PAGES: Record<string, () => JSX.Element> = {
  "/": HomePage,
  "/features": FeaturesPage,
  "/showcase": ShowcasePage,
  "/how-it-works": HowPage,
  "/faq": FaqPage,
};

export default function App() {
  const path = usePath();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [configError, setConfigError] = useState(false);

  useEffect(() => {
    try {
      return onAuthStateChanged(getFirebaseServices().auth, (current) => {
        setUser(current);
        setReady(true);
      });
    } catch (cause) {
      console.error(cause);
      setConfigError(true);
      setReady(true);
    }
  }, []);

  const inApp = path === "/app" || path.startsWith("/app/");
  useEffect(() => {
    if (!ready) return;
    if (inApp && !user) navigate("/login", { replace: true });
    if (path === "/login" && user) navigate("/app", { replace: true });
  }, [ready, inApp, path, user]);

  if (configError) {
    return (
      <div className="center-screen"><div className="center-card">
        <Logo />
        <h1>We're getting things ready</h1>
        <p>The studio isn't available right now. Please try again in a little while.</p>
      </div></div>
    );
  }
  if (!ready && (inApp || path === "/login")) {
    return <div className="center-screen"><div className="center-card"><Logo /><p style={{ marginTop: 16 }}>Loading your studio…</p></div></div>;
  }
  if (inApp) return user ? <Shell user={user} /> : null;
  if (path === "/login") return user ? null : <LoginPage />;

  const Page = SITE_PAGES[path] ?? HomePage;
  return <SiteLayout signedIn={!!user}><Page /></SiteLayout>;
}
