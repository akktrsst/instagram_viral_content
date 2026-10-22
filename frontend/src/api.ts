import { getFirebaseServices } from "./firebase";

export type Metrics = {
  checked_at: string;
  reach: number | null;
  views: number | null;
  likes: number | null;
  comments: number | null;
  saves: number | null;
  shares: number | null;
  total_interactions: number | null;
};

export type PostStatus = "generating" | "draft" | "approved" | "publishing" | "published" | "failed" | "rejected";
export type PostFormat = "carousel" | "image" | "photo" | "reel" | "explainer" | "story";
export const VIDEO_FORMATS: PostFormat[] = ["reel", "explainer", "story"];

export type Skill = {
  id: string;
  name: string;
  description: string;
  kind: PostFormat;
  default_seconds: number;
  builtin: boolean;
  instructions?: string;
  visual_guidance?: string;
};

export type Language = { code: string; name: string; native: string };

export function languageLabel(lang: Language): string {
  return lang.native && lang.native !== lang.name && !lang.name.startsWith(lang.native) ? `${lang.name} · ${lang.native}` : lang.name;
}

const LANGUAGE_KEY = "post-language";
export function savedLanguage(): string {
  try { return localStorage.getItem(LANGUAGE_KEY) ?? ""; } catch { return ""; }
}
export function saveLanguage(code: string) {
  try { if (code) localStorage.setItem(LANGUAGE_KEY, code); else localStorage.removeItem(LANGUAGE_KEY); } catch { /* storage unavailable */ }
}

export function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60), s = seconds % 60;
  return s ? `${m}m ${s}s` : `${m} min`;
}

export type BotPost = {
  id: number;
  topic: string;
  format: PostFormat;
  status: PostStatus;
  caption: string;
  hashtags: string[];
  collaborators: string[];
  alt_text: string;
  manual_post: boolean;
  model: string;
  media_urls: string[];
  ig_media_id: string | null;
  created_at: string;
  published_at: string | null;
  skill_id: string | null;
  target_seconds: number | null;
  language: string | null;
  progress: { step: string; percent: number; message: string } | null;
  error: string | null;
  metrics: Metrics | null;
};

export type Snapshot = {
  taken_at: string;
  followers: number;
  reach?: number;
  views?: number;
  profile_views?: number;
  accounts_engaged?: number;
  total_interactions?: number;
};

export type Overview = {
  profile: {
    username: string;
    name?: string;
    biography?: string;
    profile_picture_url?: string;
    followers_count: number;
    follows_count: number;
    media_count: number;
  } | null;
  instagram_error: string | null;
  quota: { used: number; total: number } | null;
  post_counts: Partial<Record<PostStatus, number>>;
  last_synced_at: string | null;
  snapshots: Snapshot[];
};

export type IgMedia = {
  id: string;
  caption?: string;
  media_type: string;
  media_product_type?: string;
  permalink: string;
  timestamp: string;
  like_count?: number;
  comments_count?: number;
  media_url?: string;
  thumbnail_url?: string;
  post_id: number | null;
  metrics: Metrics | null;
};

export type Audience = {
  followers: number;
  locked: boolean;
  demographics: Partial<Record<"age" | "gender" | "country" | "city", { label: string; value: number }[]>>;
};

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function authHeader(): Promise<Record<string, string>> {
  const token = await getFirebaseServices().auth.currentUser?.getIdToken();
  if (!token) throw new ApiError("Your sign-in has expired. Please sign in again.", 401);
  return { Authorization: `Bearer ${token}` };
}

// Empty in development (Vite proxies /api); the API's own address in production.
const API_BASE: string = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(await authHeader()) };
  if (init.body) headers["Content-Type"] = "application/json";
  const response = await fetch(API_BASE + path, { ...init, headers: { ...headers, ...init.headers } });
  const payload = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new ApiError(typeof detail === "string" ? detail : `Request failed (${response.status}).`, response.status);
  }
  return payload as T;
}

export async function fetchMedia(path: string): Promise<{ url: string; isVideo: boolean }> {
  const response = await fetch(API_BASE + path, { headers: await authHeader() });
  if (!response.ok) throw new ApiError("Could not load media.", response.status);
  const blob = await response.blob();
  return { url: URL.createObjectURL(blob), isVideo: blob.type.startsWith("video/") };
}

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return value < 1000 ? String(value) : compact.format(value);
}
