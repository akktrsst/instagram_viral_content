import { useEffect, useState } from "react";
import { onAuthStateChanged, type User } from "firebase/auth";
import { getFirebaseServices } from "./firebase";
import { Logo } from "./icons";
import Landing from "./landing/Landing";
import Shell from "./shell/Shell";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [configError, setConfigError] = useState("");

  useEffect(() => {
    try {
      return onAuthStateChanged(getFirebaseServices().auth, (current) => {
        setUser(current);
        setReady(true);
      });
    } catch (cause) {
      console.error(cause);
      setConfigError("setup");
      setReady(true);
    }
  }, []);

  if (!ready) {
    return <div className="center-screen"><div className="center-card"><Logo /><p style={{ marginTop: 16 }}>Loading your workspace…</p></div></div>;
  }
  if (configError) {
    return (
      <div className="center-screen"><div className="center-card">
        <Logo />
        <h1>We're getting things ready</h1>
        <p>The workspace isn't available right now. Please try again in a little while.</p>
      </div></div>
    );
  }
  return user ? <Shell user={user} /> : <Landing />;
}
