import { useEffect, useState, type ReactNode } from "react";
import { Icon, Logo } from "../icons";
import { Link, usePath } from "../router";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/features", label: "Features" },
  { to: "/showcase", label: "Showcase" },
  { to: "/how-it-works", label: "How it works" },
  { to: "/faq", label: "FAQ" },
];

export default function SiteLayout({ children, signedIn }: { children: ReactNode; signedIn: boolean }) {
  const path = usePath();
  const [scrolled, setScrolled] = useState(false);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => setMenu(false), [path]);

  return (
    <div className="landing">
      <nav className={scrolled ? "l-nav scrolled" : "l-nav"}>
        <div className="l-container l-nav-inner">
          <Link to="/" aria-label="Home"><Logo /></Link>
          <div className={menu ? "l-links open" : "l-links"}>
            {NAV.map((item) => (
              <Link key={item.to} to={item.to} className={path === item.to ? "active" : ""}>{item.label}</Link>
            ))}
          </div>
          <div className="l-nav-cta">
            {signedIn
              ? <Link to="/app" className="btn btn-primary">Open studio <Icon name="arrowRight" /></Link>
              : <>
                  <Link to="/login" className="btn btn-ghost">Sign in</Link>
                  <Link to="/login?new=1" className="btn btn-primary">Get started</Link>
                </>}
            <button className="icon-btn menu-btn" onClick={() => setMenu(!menu)} aria-label="Menu" aria-expanded={menu}><Icon name={menu ? "x" : "grid"} /></button>
          </div>
        </div>
      </nav>
      <main>{children}</main>
      <footer className="l-footer">
        <div className="l-container footer-grid">
          <div>
            <Logo />
            <p>Create movies, stories, reels and posts for Instagram in any language, then publish and track them in one place.</p>
          </div>
          <div>
            <strong>Product</strong>
            <Link to="/features">Features</Link>
            <Link to="/showcase">Showcase</Link>
            <Link to="/how-it-works">How it works</Link>
          </div>
          <div>
            <strong>Help</strong>
            <Link to="/faq">FAQ</Link>
            <Link to="/login">Sign in</Link>
          </div>
        </div>
        <div className="l-container footer-bottom">Not affiliated with or endorsed by Instagram.</div>
      </footer>
    </div>
  );
}
