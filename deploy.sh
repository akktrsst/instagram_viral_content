#!/usr/bin/env bash
# Deploy the studio to Google Cloud: image -> Cloud Run API + generation job + daily insights
# sync -> Firebase Hosting website. Settings come from .env; secrets come from Secret Manager.
#
#   ./deploy.sh            build a new image and deploy everything
#   ./deploy.sh web        rebuild and deploy only the website
#   IMAGE_TAG=... ./deploy.sh skip-build   deploy an image that's already built
set -euo pipefail

PROJECT=instagram-viral-content-a8eba
REGION=us-central1
SERVICE=studio-api
GENERATE_JOB=studio-generate
SYNC_JOB=studio-sync
SA="studio-runtime@${PROJECT}.iam.gserviceaccount.com"
REPO="${REGION}-docker.pkg.dev/${PROJECT}/studio/studio"
SITE="https://${PROJECT}.web.app,https://${PROJECT}.firebaseapp.com"
cd "$(dirname "$0")"
mode="${1:-all}"

env_file() {
  # Runtime settings from .env, minus secrets, website-only and local-only values.
  local out
  out="$(mktemp -t studio-env).yaml"
  python3 - "$out" "$SITE" <<'PY'
import sys
skip_prefixes = ("VITE_",)
skip = {"DB_PASSWORD", "IG_ACCESS_TOKEN", "DATABASE_URL", "FRONTEND_ORIGIN", "APP_ENV",
        "MEDIA_STORE", "JOB_RUNNER"}
values = {}
for raw in open(".env"):
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key in skip or key.startswith(skip_prefixes) or not value:
        continue
    values[key] = value
values.update(APP_ENV="production", MEDIA_STORE="gcs", JOB_RUNNER="cloudrun",
              FRONTEND_ORIGIN=sys.argv[2])
with open(sys.argv[1], "w") as f:
    for key, value in values.items():
        f.write(f"{key}: {value!r}\n".replace("'", '"'))
PY
  echo "$out"
}

deploy_backend() {
  local image="$1" envs secrets
  envs="$(env_file)"
  secrets="DB_PASSWORD=cloudsql-bot-password:latest,IG_ACCESS_TOKEN=instagram-access-token:latest"

  gcloud run deploy "$SERVICE" --project="$PROJECT" --region="$REGION" --image="$image" \
    --service-account="$SA" --env-vars-file="$envs" --set-secrets="$secrets" \
    --cpu=1 --memory=1Gi --concurrency=20 --timeout=900 --min-instances=0 --max-instances=3 \
    --execution-environment=gen2 --allow-unauthenticated --quiet

  for job in "$GENERATE_JOB" "$SYNC_JOB"; do
    local cmd_args="-m,bot,run-job,0"
    [[ "$job" == "$SYNC_JOB" ]] && cmd_args="-m,bot,sync-insights"
    local verb=create
    gcloud run jobs describe "$job" --project="$PROJECT" --region="$REGION" >/dev/null 2>&1 && verb=update
    gcloud run jobs "$verb" "$job" --project="$PROJECT" --region="$REGION" --image="$image" \
      --service-account="$SA" --env-vars-file="$envs" --set-secrets="$secrets" \
      --command=python --args="$cmd_args" --cpu=2 --memory=4Gi --task-timeout=3600 \
      --max-retries=0 --execution-environment=gen2 --quiet
  done
  rm -f "$envs"

  # The API starts generation jobs (with per-post arguments) as the runtime account.
  gcloud run jobs add-iam-policy-binding "$GENERATE_JOB" --project="$PROJECT" --region="$REGION" \
    --member="serviceAccount:${SA}" --role=roles/run.developer --quiet >/dev/null
  gcloud iam service-accounts add-iam-policy-binding "$SA" --project="$PROJECT" \
    --member="serviceAccount:${SA}" --role=roles/iam.serviceAccountUser --quiet >/dev/null

  # Daily insights snapshot at 09:00 India time, so the charts build up on their own.
  gcloud run jobs add-iam-policy-binding "$SYNC_JOB" --project="$PROJECT" --region="$REGION" \
    --member="serviceAccount:${SA}" --role=roles/run.invoker --quiet >/dev/null
  local uri="https://run.googleapis.com/v2/projects/${PROJECT}/locations/${REGION}/jobs/${SYNC_JOB}:run"
  if gcloud scheduler jobs describe studio-daily-sync --project="$PROJECT" --location="$REGION" >/dev/null 2>&1; then
    gcloud scheduler jobs update http studio-daily-sync --project="$PROJECT" --location="$REGION" \
      --schedule="0 9 * * *" --time-zone="Asia/Kolkata" --uri="$uri" --http-method=POST \
      --oauth-service-account-email="$SA" --quiet >/dev/null
  else
    gcloud scheduler jobs create http studio-daily-sync --project="$PROJECT" --location="$REGION" \
      --schedule="0 9 * * *" --time-zone="Asia/Kolkata" --uri="$uri" --http-method=POST \
      --oauth-service-account-email="$SA" --quiet >/dev/null
  fi
}

deploy_web() {
  local api_url
  api_url="$(gcloud run services describe "$SERVICE" --project="$PROJECT" --region="$REGION" --format='value(status.url)')"
  (cd frontend && VITE_API_BASE_URL="$api_url" VITE_USE_FIREBASE_EMULATORS=false npm run build)
  firebase deploy --only hosting --project "$PROJECT" --non-interactive
}

case "$mode" in
  web) deploy_web ;;
  skip-build) deploy_backend "${REPO}:${IMAGE_TAG:?set IMAGE_TAG}"; deploy_web ;;
  all)
    tag="$(date +%Y%m%d-%H%M)"
    gcloud builds submit --project="$PROJECT" --region="$REGION" --tag="${REPO}:${tag}" --timeout=1800 .
    deploy_backend "${REPO}:${tag}"
    deploy_web
    ;;
  *) echo "usage: $0 [all|web|skip-build]" >&2; exit 1 ;;
esac
echo "Deployed: https://${PROJECT}.web.app"
