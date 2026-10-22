import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from bot.db.models import AccountSnapshot, Metric, Post
from bot.publisher.graph_api import InstagramClient, InstagramError

logger = logging.getLogger(__name__)

PROFILE_FIELDS = (
    "username,name,biography,profile_picture_url,followers_count,follows_count,media_count"
)
MEDIA_FIELDS = "id,caption,media_type,media_product_type,permalink,timestamp,like_count,comments_count,thumbnail_url,media_url"
ACCOUNT_DAY_METRICS = [
    "reach",
    "views",
    "profile_views",
    "accounts_engaged",
    "total_interactions",
    "likes",
    "comments",
    "saves",
    "shares",
]
MEDIA_METRICS = {
    "REELS": [
        "reach",
        "views",
        "likes",
        "comments",
        "saved",
        "shares",
        "total_interactions",
        "ig_reels_avg_watch_time",
    ],
    "FEED": ["reach", "views", "likes", "comments", "saved", "shares", "total_interactions"],
}
DEMOGRAPHIC_BREAKDOWNS = ["age", "gender", "country", "city"]


def fetch_profile(client: InstagramClient) -> dict:
    return client._request("GET", f"/{client.user_id}", fields=PROFILE_FIELDS)


def fetch_recent_media(client: InstagramClient, limit: int = 25) -> list[dict]:
    return client._request("GET", f"/{client.user_id}/media", fields=MEDIA_FIELDS, limit=limit).get(
        "data", []
    )


def fetch_account_day_metrics(client: InstagramClient, day: datetime) -> dict[str, int]:
    """Totals for the UTC day starting at `day`."""
    since = int(day.timestamp())
    data = client._request(
        "GET",
        f"/{client.user_id}/insights",
        metric=",".join(ACCOUNT_DAY_METRICS),
        period="day",
        metric_type="total_value",
        since=since,
        until=since + 86400,
    ).get("data", [])
    return {item["name"]: item.get("total_value", {}).get("value", 0) for item in data}


def fetch_media_metrics(client: InstagramClient, media: dict) -> dict[str, int | float]:
    kind = "REELS" if media.get("media_product_type") == "REELS" else "FEED"
    try:
        data = client._request(
            "GET", f"/{media['id']}/insights", metric=",".join(MEDIA_METRICS[kind])
        ).get("data", [])
        values = {item["name"]: (item.get("values") or [{}])[0].get("value") for item in data}
    except InstagramError as exc:
        # Very new or very old media can reject insights; fall back to public counts.
        logger.warning("Insights unavailable for %s: %s", media["id"], exc)
        values = {}
    values.setdefault("likes", media.get("like_count"))
    values.setdefault("comments", media.get("comments_count"))
    return values


def fetch_demographics(client: InstagramClient) -> dict[str, list[dict]]:
    """Follower demographics by breakdown; empty until the account has 100+ followers."""
    result = {}
    for breakdown in DEMOGRAPHIC_BREAKDOWNS:
        data = client._request(
            "GET",
            f"/{client.user_id}/insights",
            metric="follower_demographics",
            period="lifetime",
            metric_type="total_value",
            breakdown=breakdown,
        ).get("data", [])
        rows = []
        for item in data:
            for group in item.get("total_value", {}).get("breakdowns", []):
                for row in group.get("results", []):
                    rows.append(
                        {"label": ", ".join(row["dimension_values"]), "value": row["value"]}
                    )
        result[breakdown] = sorted(rows, key=lambda r: r["value"], reverse=True)
    return result


def sync_insights(session: Session, client: InstagramClient | None = None) -> dict:
    """Store today's account snapshot and a metrics reading for each recent media."""
    client = client or InstagramClient()
    profile = fetch_profile(client)
    yesterday = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
        days=1
    )
    try:
        day_metrics = fetch_account_day_metrics(client, yesterday)
    except InstagramError as exc:
        logger.warning("Account insights unavailable: %s", exc)
        day_metrics = {}

    session.add(
        AccountSnapshot(
            followers=profile.get("followers_count", 0),
            follows=profile.get("follows_count", 0),
            media_count=profile.get("media_count", 0),
            day_metrics=day_metrics,
        )
    )

    post_ids = dict(
        session.execute(
            select(Post.ig_media_id, Post.id).where(Post.ig_media_id.is_not(None))
        ).all()
    )
    media_items = fetch_recent_media(client)
    for media in media_items:
        values = fetch_media_metrics(client, media)
        session.add(
            Metric(
                ig_media_id=media["id"],
                post_id=post_ids.get(media["id"]),
                reach=values.get("reach"),
                views=values.get("views"),
                likes=values.get("likes"),
                comments=values.get("comments"),
                saves=values.get("saved"),
                shares=values.get("shares"),
                total_interactions=values.get("total_interactions"),
                avg_watch_time=values.get("ig_reels_avg_watch_time"),
            )
        )
    session.commit()
    return {"followers": profile.get("followers_count", 0), "media_synced": len(media_items)}
