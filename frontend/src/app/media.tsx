import { useEffect, useState } from "react";
import { fetchMedia, formatSeconds, VIDEO_FORMATS, type BotPost, type PostFormat, type PostStatus } from "../api";
import { Icon, type IconName } from "../icons";

export const FORMAT_INFO: Record<PostFormat, { label: string; icon: IconName }> = {
  story: { label: "Story video", icon: "video" },
  reel: { label: "Short reel", icon: "video" },
  explainer: { label: "Explainer", icon: "layers" },
  carousel: { label: "Carousel", icon: "grid" },
  photo: { label: "AI photo", icon: "image" },
  image: { label: "Quote image", icon: "quote" },
};

export const STATUS_LABELS: Record<PostStatus, string> = {
  generating: "Creating",
  draft: "Draft",
  approved: "Approved",
  publishing: "Posting",
  published: "Published",
  failed: "Needs attention",
  rejected: "Rejected",
};

export const LANGUAGE_NAMES: Record<string, string> = {
  "en-IN": "English", "en-US": "English (US)", hi: "Hindi", hinglish: "Hinglish", bho: "Bhojpuri", bn: "Bengali",
  mr: "Marathi", ta: "Tamil", te: "Telugu", gu: "Gujarati", kn: "Kannada", ml: "Malayalam", pa: "Punjabi", ur: "Urdu",
};

export function postKind(post: BotPost): string {
  if (post.format === "story" && post.style === "movie") return "Movie";
  return FORMAT_INFO[post.format]?.label ?? post.format;
}

export function postTitle(post: BotPost): string {
  const title = (post.script as { title?: string; hook?: string; headline?: string } | undefined);
  return title?.title || title?.headline || post.topic;
}

export function postMeta(post: BotPost): string {
  return [
    postKind(post),
    post.target_seconds ? formatSeconds(post.target_seconds) : null,
    post.language ? LANGUAGE_NAMES[post.language] ?? post.language : null,
  ].filter(Boolean).join(" · ");
}

export function StatusChip({ status }: { status: PostStatus }) {
  return <span className={`status status-${status}`}>{STATUS_LABELS[status] ?? status}</span>;
}

/** Fetch a private media file once and keep a blob URL for it. */
export function useMedia(path: string | undefined) {
  const [media, setMedia] = useState<{ url: string; isVideo: boolean } | null>(null);
  useEffect(() => {
    if (!path) { setMedia(null); return; }
    let objectUrl: string | null = null;
    let cancelled = false;
    setMedia(null);
    fetchMedia(path).then((result) => {
      objectUrl = result.url;
      if (cancelled) URL.revokeObjectURL(result.url);
      else setMedia(result);
    }).catch(() => setMedia(null));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);
  return media;
}

/** Cover image for a post card (a video's media is [video, cover]). */
export function PostThumb({ post, className = "post-thumb" }: { post: BotPost; className?: string }) {
  const isVideo = VIDEO_FORMATS.includes(post.format);
  const media = useMedia(isVideo ? post.media_urls[1] : post.media_urls[0]);
  if (post.status === "generating") {
    return (
      <div className={`${className} thumb-generating`}>
        <span className="spinner" />
        <small>{post.progress?.percent ?? 0}%</small>
      </div>
    );
  }
  if (!media) return <div className={`${className} thumb-empty`}><Icon name={FORMAT_INFO[post.format]?.icon ?? "image"} /></div>;
  return (
    <div className={className}>
      <img src={media.url} alt="" />
      {isVideo && <span className="thumb-play"><Icon name="video" /></span>}
    </div>
  );
}

/** Player: a video for video posts, a swipeable slideshow for images. */
export function MediaPlayer({ post }: { post: BotPost }) {
  const isVideo = VIDEO_FORMATS.includes(post.format);
  const urls = isVideo ? post.media_urls.slice(0, 1) : post.media_urls;
  const [index, setIndex] = useState(0);
  const media = useMedia(urls[index]);

  if (post.status === "generating") {
    return (
      <div className={isVideo ? "player reel player-generating" : "player player-generating"}>
        <div className="player-glow" />
        <span className="spinner" />
        <strong>{post.progress?.message ?? "Getting started"}</strong>
        <div className="meter-track"><div className="meter-fill" style={{ width: `${Math.max(post.progress?.percent ?? 0, 3)}%` }} /></div>
        <small>{post.progress?.percent ?? 0}% · keeps going even if you leave this page</small>
      </div>
    );
  }
  if (!urls.length) return <div className={isVideo ? "player reel player-empty" : "player player-empty"}><Icon name={FORMAT_INFO[post.format].icon} /><span>No media yet</span></div>;

  return (
    <div className={isVideo ? "player reel" : "player"}>
      {media ? (media.isVideo
        ? <video src={media.url} controls playsInline autoPlay muted loop />
        : <img src={media.url} alt={`Slide ${index + 1} of ${urls.length}`} />)
        : <div className="player-loading"><span className="spinner" /></div>}
      {media && (
        <a className="player-download" href={media.url} download={`post-${post.id}-${index + 1}.${media.isVideo ? "mp4" : "jpg"}`}>
          <Icon name="arrowRight" className="icon rot90" /> Download
        </a>
      )}
      {urls.length > 1 && (
        <div className="slides-nav">
          <button aria-label="Previous slide" onClick={() => setIndex((index - 1 + urls.length) % urls.length)}>‹</button>
          <span>{index + 1} / {urls.length}</span>
          <button aria-label="Next slide" onClick={() => setIndex((index + 1) % urls.length)}>›</button>
        </div>
      )}
    </div>
  );
}
