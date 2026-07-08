import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.config.settings import get_settings

security = HTTPBasic(auto_error=False)


def get_current_user(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> str:
    settings = get_settings()
    if not settings.auth_enabled:
        return "anonymous"

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )

    correct_username = secrets.compare_digest(credentials.username, settings.api_username)
    correct_password = secrets.compare_digest(credentials.password, settings.api_password)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
