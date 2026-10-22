# Viral Content Studio

An Instagram content studio MVP: generate post ideas, captions, and hashtag
sets with Vertex AI, get Pro-tier feedback, and save private drafts with
Firebase SQL Connect.

## Requirements

- Python 3.11+
- Node.js 20+ and npm
- Firebase CLI
- Google Cloud Application Default Credentials with Vertex AI access to
  `instagram-viral-content-a8eba`

## Firebase setup and local run

1. Copy `.env.example` to `.env`. Add the public Firebase web app settings from
   Firebase Console > Project settings > Your apps. `.env` is ignored by git.
2. Install the Firebase CLI if needed (`npm install -g firebase-tools`), then
   authenticate with `firebase login`.
3. In the Firebase Console, enable Email/Password under Authentication. This
   app is already configured for project `instagram-viral-content-a8eba`.
4. Run `firebase init dataconnect` from the repository root and select the
   configured project and `viral-content` service. If prompted to create a
   service or database, follow the Firebase CLI workflow. To retain no-cost
   trial eligibility, accept the default database configuration; resizing the
   instance or enabling private IP can end the trial.
5. Generate the typed client SDK and install frontend dependencies:

   ```sh
   firebase dataconnect:sdk:generate
   cd frontend
   npm install
   ```

6. Start the local Firebase Auth and SQL Connect emulators from the repository
   root:

   ```sh
   firebase emulators:start --only auth,dataconnect
   ```

7. In another terminal, start the API:

   ```sh
   cd backend
   python -m venv .venv
   . .venv/bin/activate
   pip install -e '.[dev]'
   gcloud auth application-default login
   FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 uvicorn app.main:app --reload
   ```

8. In another terminal run `cd frontend && npm run dev`, then open
   <http://localhost:5173>. Sign up with the local Auth emulator. The API docs
   are at <http://localhost:8000/docs>.

The browser talks to SQL Connect through generated, authenticated operations;
each draft query and mutation is scoped to the signed-in user. The FastAPI
generation endpoints verify Firebase ID tokens and use Google ADC for Vertex
AI. No service-account key or database password belongs in `.env`.

## Content bot (Phase 1)

The `bot` package in `backend/` turns a topic into a finished post: Gemini
writes structured JSON for the chosen format (carousel, single image, or reel
script), and Playwright renders 1080x1350 PNGs from the HTML templates in
`backend/bot/media/templates/`. Every post is saved as a `draft` in the bot
database, ready for the review queue in Phase 3.

- `config/settings.yaml`: niche, audience, posting times, trend sources, and
  scoring weights. The niche is a placeholder; change it to your own.
- `config/brand_kit.yaml`: colours, fonts, logo, voice, CTAs, banned words,
  default hashtags and collaborators, and the AI disclosure line.

```sh
cd backend
. .venv/bin/activate
pip install -e '.[dev]'
python -m playwright install chromium
python -m bot make "5 free AI tools that save students hours" -f carousel
python -m bot make "Notion vs Obsidian" -f image
python -m bot make "Automate your inbox in 60 seconds" -f reel   # script + cover; video in Phase 2
python -m bot list
```

Output goes to `output/post-<id>-<slug>/` (`slide_XX.png`, `caption.txt`,
`script.json`). Use `--tier pro` to write with `GEMINI_MODEL_PRO`.

The bot uses local SQLite (`output/bot.db`) unless `CLOUDSQL_INSTANCE` is set,
in which case it connects to Cloud SQL Postgres through the Cloud SQL Python
Connector using ADC. The instance `viral-content-postgres` (db-f1-micro,
PostgreSQL 15, us-central1) is the same one named in `dataconnect.yaml`. The
`bot` user's password is stored in Secret Manager as `cloudsql-bot-password`.
On Postgres the bot's tables live in the `bot` schema. The `public` schema
belongs to SQL Connect (its `draft` table), whose strict migrations drop any
table they don't know, so never put bot tables in `public`.

To read the password:

```sh
gcloud secrets versions access latest --secret=cloudsql-bot-password \
  --project=instagram-viral-content-a8eba
```

If the connector fails with `CERTIFICATE_VERIFY_FAILED` on macOS, run
`/Applications/Python\ 3.13/Install\ Certificates.command` once.

## Publishing to Instagram (Phase 3)

Publishing uses the Instagram API with Instagram Login (`graph.instagram.com`)
and needs a professional (Creator or Business) account. Put `IG_USER_ID` and
`IG_ACCESS_TOKEN` from the Meta app dashboard in `.env`, then:

```sh
python -m bot ig-check                        # verify the token and daily quota
python -m bot approve 2 --collab some_user    # only listed usernames get collab invites
python -m bot publish 2
python -m bot reject 1
```

Images are rendered as JPEG (Instagram rejects PNG), uploaded to the public
bucket `gs://instagram-viral-content-a8eba-media` (objects auto-delete after
30 days), and published as a single image or carousel. A post is published
only from `approved`, and never twice: `ig_media_id` is checked first. Reels
need Phase 2 video rendering. Long-lived tokens expire after 60 days.

## Movie mode

Story videos have two styles (`--style` on the CLI, or the first step of the
website's Create flow):

- **cinematic** (default): moving stills, character voices, real-video clips for
  the hook and climax. About $0.03 per second of video.
- **movie**: every shot is a generated clip with its own sound
  (`MOVIE_VIDEO_MODEL`, default Veo 3.1 Fast). Dialogue shots have the character
  speak their lines on camera with lip-sync, in a voice described once per
  character for consistency; narration shots get natural ambience with the
  narrator's voice over it. The writer keeps each shot to one clip (4-8 s, at
  most ~16 words) and frames speakers facing the camera. A clip that fails
  (for example under service load, which is retried) falls back to a moving
  still with the recorded voices. About $0.12 per second, roughly $14 for 2
  minutes; the website shows an estimate before creating.

Measured lip-sync (Gemini review of a Hindi line): side profile on Veo Lite
2/10, front-facing close-up on Veo Fast 5/10. Words were transcribed exactly in
both. Expect better results in English than in other languages.

## Website structure

Public pages: `/` (home), `/features`, `/showcase`, `/how-it-works`, `/faq`,
`/login`. Signed-in app: `/app` (dashboard), `/app/create` (choose, describe,
create, with a cost and time estimate), `/app/library`, `/app/posts/:id` (player,
live progress, script with who-says-what, caption, publish), `/app/analytics`,
`/app/audience`, `/app/skills`, `/app/captions`. Showcase videos live in
`frontend/public/showcase/`.

## Story videos (20 seconds to 2 minutes)

`-f story` (or "Story video" on the website) runs a small agent:

1. **Plan**: title, logline, genre, narration language, visual style, setting,
   up to 4 characters with fixed looks, and beats sized to the chosen length.
2. **Shot list**: one shot about every 4.5 seconds; each pairs a narration
   line with the exact picture shown while it is spoken.
3. **Editor review** (Pro model): scores the script against the brief and
   length; below 8/10 the writer revises once with the feedback, and the length
   is corrected if the narration is far off target.
4. **Render**: a character reference sheet keeps faces and clothes consistent
   across shots; key moments (the hook, and the climax for longer videos) become
   real image-to-video clips (`VIDEO_MODEL`, default Veo 3.1 Lite, 1080p);
   every other shot gets a camera move. Narration uses a voice in the story's
   language. Any clip that fails falls back to a moving still.
5. **Dialogue**: characters speak their own lines; each is cast a distinct
   voice from their gender and age (a lighter, quicker voice for children, a
   deeper, slower one for elders), the narrator links scenes, and captions show
   the speaker's name while they talk. Real-video clips are not lip-synced.

Creation runs in the background with progress shown on the website; pictures,
voiceovers and clips are reused if a run is interrupted, so "Try again" only
redoes what is missing. Rough cost of a 2-minute story: about 26 pictures
(~$1.75) plus about 16 seconds of video (~$1.30). Google lists the Veo 3.1
models as retiring on 2026-10-22; set `VIDEO_MODEL` to its successor, or leave
it empty for stills only.

```sh
python -m bot make "A street dog waiting for a girl at a railway station" -f story --seconds 60
python -m bot make "The ghost of the old library" -f story --skill horror-story --seconds 90
```

## Skills

A skill is a reusable recipe for one kind of post: structure, pacing, tone and
look. Built-in skills are YAML files in `config/skills/` (story, motivational,
horror, kids' moral story, love, mystery, funny, real-life style, mythology,
facts countdown, recipe, mini documentary); edit them freely. Describe a new
skill on the website's Skills page or with
`python -m bot skills create "60-second travel diaries of hidden places"` and it
is designed and saved for reuse. `python -m bot skills list` shows them all.

## Reels and AI photos

- **Reel** (`-f reel`): Gemini writes 3-6 scenes; `IMAGE_MODEL` draws a vertical
  image per scene; Google Cloud Text-to-Speech (`voiceover.voice` in
  `brand_kit.yaml`) reads each line; ffmpeg (bundled via `imageio-ffmpeg`) adds a
  slow zoom and word-timed captions and outputs a 1080x1920 H.264/AAC
  `video.mp4` plus `cover.jpg`. Drop royalty-free `.mp3` files in `assets/music/`
  to mix in background music at low volume.
- **Explainer reel** (`-f explainer`): Gemini models the topic as a flow diagram
  (3-9 boxes and arrows) and a 3-6 step narration; each step reveals and
  highlights its boxes on an auto-laid-out, top-to-bottom diagram, with the same
  voiceover and captions as reels. No image model is used, so it is unaffected
  by image quotas.
- **AI photo** (`-f photo`): one generated image with an optional headline,
  rendered at 1080x1350.

Both publish from the dashboard's **Post to Instagram** button (reels can take a
few minutes while Instagram processes the video). A reel marked as needing a
trending sound is never auto-published; download it and post it from the app.
Rough cost per reel is a few cents of Vertex AI credit (one image per scene);
TTS stays within the free tier at this volume. If `GEMINI_MODEL` is overloaded,
`GEMINI_FALLBACK_MODELS` are tried in order.

## Instagram dashboard

The web app has **Overview** (followers, daily reach, views, profile visits,
content pipeline, publishing limit), **Content** (create drafts, preview
slides, edit captions, approve, publish, and per-post reach, views, likes,
comments, saves and shares) and **Audience** (age, gender, country and city;
Instagram only provides these from 100 followers). The **Create** studio is
unchanged.

Only emails in `ADMIN_EMAILS` (in `.env`) with a verified address can use it.
Sign up in the app, then use "Send verification email" when prompted.

```sh
cd backend && .venv/bin/uvicorn app.main:app --port 8000   # API
cd frontend && npm run dev                                  # http://localhost:5173
python -m bot sync-insights                                 # daily snapshot (also a button)
```

Follower and reach charts build up from daily snapshots, so run
`sync-insights` once a day (the scheduler will automate this). Keep the
machine awake while the servers run: a sleeping laptop drops the Cloud SQL
connections.

## Deployment (Google Cloud)

Live site: https://instagram-viral-content-a8eba.web.app

| Piece | Where |
|---|---|
| Website | Firebase Hosting (`frontend/dist`) |
| API | Cloud Run service `studio-api` (scales to zero) |
| Post/video generation | Cloud Run Job `studio-generate`, one execution per post (2 vCPU, 4 GiB, 60 min) |
| Daily insights | Cloud Run Job `studio-sync`, run by Cloud Scheduler `studio-daily-sync` at 09:00 IST |
| Drafts' media + resume cache | private bucket `gs://instagram-viral-content-a8eba-studio` |
| Published media | public bucket `gs://instagram-viral-content-a8eba-media` |
| Secrets | Secret Manager: `cloudsql-bot-password`, `instagram-access-token` |
| Runtime identity | service account `studio-runtime` (AI, Cloud SQL client, its buckets and secrets, run its jobs) |

`./deploy.sh` builds the image with Cloud Build and deploys everything; `./deploy.sh web`
redeploys only the website. Runtime settings come from `.env` (secrets excluded); in the cloud
`MEDIA_STORE=gcs` and `JOB_RUNNER=cloudrun`. When the Instagram token is renewed, add a new
version of the `instagram-access-token` secret and redeploy.

The local servers share the same database: while cloud jobs are running, don't start the local
API (it would mark in-progress posts as interrupted on startup).

## SQL Connect billing and trial

The SQL Connect service and its Cloud SQL PostgreSQL instance have separate
billing components. Google's current [SQL Connect pricing and trial terms](https://firebase.google.com/docs/sql-connect/pricing)
describe a limited 90-day Spark-plan trial or a three-month Cloud SQL trial for
eligible Blaze-plan projects using the default configuration. Trial limits
apply; after a trial ends, paid rates apply unless the resource is removed.
Vertex AI usage is separately billed and may consume the project's $300 credit.
Create a billing budget and alerts in Cloud Billing; alerts do not cap spend.
Billing account `01E8BC-7EAEF3-6AB18B` is linked to the project, with a
budget alert at INR 4,000/month (50%, 90%, 100%). The Cloud SQL instance runs
continuously (about $9-12/month from the credit); stop it with
`gcloud sql instances patch viral-content-postgres --activation-policy=NEVER`
when you are not using it.

## Model routing

The API routes ideas through `GEMINI_MODEL_LITE`, captions through
`GEMINI_MODEL`, and reviews through `GEMINI_MODEL_PRO` by default. The UI also
offers Auto, Lite, Standard, and Pro tiers; explicit choices override the
task-based default. `EMBEDDING_MODEL` is configured for a future
semantic-search feature and is not called by this MVP.

**Model lifecycle (2026-10-20):** the Gemini 2.5 models retire on
2026-10-20, so the defaults are now `gemini-3.5-flash-lite`,
`gemini-3.8-flash`, `gemini-3.1-pro-preview` (a preview model), and
`gemini-embedding-2`. These are served only from the Vertex AI `global`
endpoint, so `GOOGLE_CLOUD_LOCATION=global`. Cloud SQL stays in
`us-central1`. All Vertex usage bills to the project's linked billing account
and its free-trial credit.

Before public launch, configure Firebase App Check, email verification and
account recovery, API rate limits, monitoring, and a managed runtime identity
with least-privilege Vertex AI access. Review Firebase Auth and SQL Connect
production settings in the selected Firebase project before deployment.
