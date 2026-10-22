import { useCallback, useEffect, useMemo, useState } from "react";
import { api, type BotPost, type PostStatus } from "../api";
import { Icon } from "../icons";
import { Link } from "../router";
import { postMeta, PostThumb, postTitle, StatusChip } from "./media";

const TABS: { key: string; label: string; statuses: PostStatus[] | null }[] = [
  { key: "all", label: "All", statuses: null },
  { key: "creating", label: "Creating", statuses: ["generating"] },
  { key: "review", label: "To review", statuses: ["draft", "failed"] },
  { key: "approved", label: "Approved", statuses: ["approved", "publishing"] },
  { key: "published", label: "Published", statuses: ["published"] },
  { key: "rejected", label: "Rejected", statuses: ["rejected"] },
];
const POLL_MS = 5000;

export default function Library({ onError }: { onError: (e: unknown) => void }) {
  const [posts, setPosts] = useState<BotPost[] | null>(null);
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");

  const load = useCallback(() => {
    api<BotPost[]>("/api/v1/dashboard/posts").then(setPosts).catch(onError);
  }, [onError]);
  useEffect(() => { load(); }, [load]);

  const creating = posts?.some((p) => p.status === "generating") ?? false;
  useEffect(() => {
    if (!creating) return;
    const timer = window.setInterval(load, POLL_MS);
    return () => window.clearInterval(timer);
  }, [creating, load]);

  const counts = useMemo(() => Object.fromEntries(
    TABS.map((t) => [t.key, (posts ?? []).filter((p) => !t.statuses || t.statuses.includes(p.status)).length]),
  ), [posts]);

  const shown = useMemo(() => {
    const statuses = TABS.find((t) => t.key === tab)?.statuses;
    const q = query.trim().toLowerCase();
    return (posts ?? []).filter((p) =>
      (!statuses || statuses.includes(p.status)) &&
      (!q || p.topic.toLowerCase().includes(q) || postTitle(p).toLowerCase().includes(q)));
  }, [posts, tab, query]);

  return (
    <div className="dash">
      <div className="library-bar">
        <div className="tabs" role="tablist">
          {TABS.map((t) => (
            <button key={t.key} role="tab" aria-selected={tab === t.key} className={tab === t.key ? "tab active" : "tab"} onClick={() => setTab(t.key)}>
              {t.label} <span className="count">{counts[t.key] ?? 0}</span>
            </button>
          ))}
        </div>
        <label className="search">
          <span className="sr-only">Search</span>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search your posts" />
        </label>
      </div>

      {posts === null && <div className="library-grid">{Array.from({ length: 8 }, (_, i) => <div key={i} className="post-card skeleton" />)}</div>}
      {posts && shown.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon"><Icon name="layers" /></span>
          <h3>{posts.length ? "Nothing here yet" : "Your library is empty"}</h3>
          <p>{posts.length ? "Try another tab or search." : "Create your first movie, story or post. It will show up here."}</p>
          <Link to="/app/create" className="btn btn-primary"><Icon name="plus" /> Create something</Link>
        </div>
      )}
      {shown.length > 0 && (
        <div className="library-grid">
          {shown.map((post) => (
            <Link key={post.id} to={`/app/posts/${post.id}`} className="post-card">
              <PostThumb post={post} />
              <div className="post-card-body">
                <div className="post-card-top"><StatusChip status={post.status} /><small>#{post.id}</small></div>
                <strong>{postTitle(post)}</strong>
                <small>{postMeta(post)}</small>
                {post.status === "generating" && (
                  <div className="meter-track mini"><div className="meter-fill" style={{ width: `${Math.max(post.progress?.percent ?? 0, 3)}%` }} /></div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
