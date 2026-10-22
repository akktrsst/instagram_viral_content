import { useEffect, useState } from "react";
import { api, formatCount, type IgMedia } from "../api";

/** Published Instagram posts with their latest synced numbers. */
export default function Published({ onError }: { onError: (e: unknown) => void }) {
  const [media, setMedia] = useState<IgMedia[] | null>(null);

  useEffect(() => {
    api<IgMedia[]>("/api/v1/dashboard/content").then(setMedia).catch(onError);
  }, [onError]);

  if (!media) return <div className="dash-loading">Loading Instagram posts…</div>;
  if (!media.length) return <p className="library-empty">Nothing published yet.</p>;

  const columns: { key: keyof NonNullable<IgMedia["metrics"]>; label: string }[] = [
    { key: "reach", label: "Reach" },
    { key: "views", label: "Views" },
    { key: "likes", label: "Likes" },
    { key: "comments", label: "Comments" },
    { key: "saves", label: "Saves" },
    { key: "shares", label: "Shares" },
  ];

  return (
    <section className="dash-card">
      <header className="chart-head"><div><h3>Published posts</h3><p>Latest synced numbers. Use "Sync insights" on Overview to refresh.</p></div></header>
      <div className="table-wrap">
        <table className="data-table media-table">
          <thead><tr><th>Post</th><th>Date</th>{columns.map((c) => <th key={c.key} className="num">{c.label}</th>)}<th /></tr></thead>
          <tbody>
            {media.map((m) => (
              <tr key={m.id}>
                <td className="media-cell">
                  {(m.thumbnail_url || m.media_url) && <img src={m.thumbnail_url || m.media_url} alt="" />}
                  <span>{(m.caption ?? "").split("\n")[0].slice(0, 70) || m.media_type}{m.post_id ? <em> · bot #{m.post_id}</em> : null}</span>
                </td>
                <td>{new Date(m.timestamp).toLocaleDateString()}</td>
                {columns.map((c) => (
                  <td key={c.key} className="num">{formatCount(m.metrics?.[c.key] as number | null | undefined ?? (c.key === "likes" ? m.like_count : c.key === "comments" ? m.comments_count : null))}</td>
                ))}
                <td><a className="text-button" href={m.permalink} target="_blank" rel="noreferrer">Open ↗</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
