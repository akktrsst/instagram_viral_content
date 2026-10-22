import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GRAPH_HOST = "https://graph.instagram.com"
MAX_CAROUSEL_ITEMS = 10
MAX_COLLABORATORS = 3


class InstagramError(Exception):
    pass


class InstagramClient:
    """Instagram API with Instagram Login: container -> (wait) -> media_publish."""

    def __init__(
        self,
        user_id: str | None = None,
        access_token: str | None = None,
        version: str | None = None,
        http: httpx.Client | None = None,
        poll_interval: float = 5.0,
        poll_timeout: float = 300.0,
    ):
        self.user_id = user_id or settings.ig_user_id
        self.access_token = access_token or settings.ig_access_token
        if not self.user_id or not self.access_token:
            raise InstagramError("Instagram isn't connected yet.")
        self.base_url = f"{GRAPH_HOST}/{version or settings.ig_graph_version}"
        self.http = http or httpx.Client(timeout=60)
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout

    def account(self) -> dict:
        return self._request("GET", "/me", fields="user_id,username,account_type")

    def publishing_limit(self) -> dict:
        data = self._request(
            "GET", f"/{self.user_id}/content_publishing_limit", fields="config,quota_usage"
        )
        return (data.get("data") or [{}])[0]

    def publish_images(
        self, image_urls: list[str], caption: str, collaborators: list[str] | None = None
    ) -> str:
        if not image_urls:
            raise InstagramError("This post has no images yet.")
        if len(image_urls) > MAX_CAROUSEL_ITEMS:
            raise InstagramError(f"A carousel can have at most {MAX_CAROUSEL_ITEMS} slides.")

        extra = _collaborator_params(collaborators)
        if len(image_urls) == 1:
            container = self._create(image_url=image_urls[0], caption=caption, **extra)
        else:
            children = [self._create(image_url=url, is_carousel_item="true") for url in image_urls]
            for child in children:
                self._wait_until_ready(child)
            container = self._create(
                media_type="CAROUSEL", children=",".join(children), caption=caption, **extra
            )
        self._wait_until_ready(container)
        return self._publish(container)

    def publish_reel(
        self,
        video_url: str,
        caption: str,
        cover_url: str | None = None,
        collaborators: list[str] | None = None,
    ) -> str:
        params = {"media_type": "REELS", "video_url": video_url, "caption": caption}
        if cover_url:
            params["cover_url"] = cover_url
        container = self._create(**params, **_collaborator_params(collaborators))
        self._wait_until_ready(container)
        return self._publish(container)

    def _create(self, **params) -> str:
        return self._request("POST", f"/{self.user_id}/media", **params)["id"]

    def _publish(self, container_id: str) -> str:
        return self._request("POST", f"/{self.user_id}/media_publish", creation_id=container_id)[
            "id"
        ]

    def _wait_until_ready(self, container_id: str) -> None:
        deadline = time.monotonic() + self.poll_timeout
        while True:
            status = self._request("GET", f"/{container_id}", fields="status_code").get(
                "status_code"
            )
            if status in ("FINISHED", "PUBLISHED"):
                return
            if status in ("ERROR", "EXPIRED"):
                logger.error("Media container %s ended with %s", container_id, status)
                raise InstagramError("Instagram couldn't process this media. Please try again.")
            if time.monotonic() > deadline:
                logger.error("Media container %s was not ready in time", container_id)
                raise InstagramError(
                    "Instagram is still processing this video. Nothing was posted; please try "
                    "again in a few minutes."
                )
            time.sleep(self.poll_interval)

    def _request(self, method: str, path: str, **params) -> dict:
        params["access_token"] = self.access_token
        if method == "GET":
            response = self.http.get(self.base_url + path, params=params)
        else:
            response = self.http.post(self.base_url + path, data=params)
        data = response.json() if response.content else {}
        if response.is_error or "error" in data:
            error = data.get("error", {})
            logger.error(
                "Instagram request %s %s failed (%s): %s",
                method,
                path,
                response.status_code,
                error or response.text[:500],
            )
            # Instagram's user-facing message is plain language; its developer message is not.
            friendly = error.get("error_user_msg") or {
                190: "Instagram connection needs to be renewed.",
                200: "Instagram has paused access for this app. Open the Meta app dashboard to see "
                "why and what to do.",
            }.get(
                error.get("code"),
                "Instagram couldn't complete this request. Please try again in a few minutes.",
            )
            raise InstagramError(friendly)
        return data


def _collaborator_params(collaborators: list[str] | None) -> dict:
    usernames = [c.lstrip("@") for c in (collaborators or [])][:MAX_COLLABORATORS]
    return {"collaborators": json.dumps(usernames)} if usernames else {}
