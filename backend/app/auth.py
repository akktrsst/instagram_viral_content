import os
from typing import Annotated

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def require_firebase_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> dict[str, object]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        try:
            app = firebase_admin.get_app()
        except ValueError:
            app = firebase_admin.initialize_app(
                options={"projectId": settings.google_cloud_project}
            )
        return auth.verify_id_token(credentials.credentials, app=app)
    except (ValueError, firebase_admin.exceptions.FirebaseError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your sign-in has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_admin(
    user: Annotated[dict[str, object], Depends(require_firebase_user)],
) -> dict[str, object]:
    allowed = {e.strip().lower() for e in settings.admin_emails.split(",") if e.strip()}
    email = str(user.get("email", "")).lower()
    if not email or email not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account doesn't have access to this workspace.",
        )
    # An unverified address could have been registered by someone else.
    if not user.get("email_verified") and not os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED",
        )
    return user
