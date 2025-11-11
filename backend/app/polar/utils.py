import hashlib
import hmac
from datetime import datetime

import requests
from fastapi import HTTPException, status

import core.config as core_config
import core.cryptography as core_cryptography
import core.logger as core_logger

from polar import models as polar_models

POLAR_TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
POLAR_API_BASE = "https://www.polaraccesslink.com/v3"

_webhook_secret_warning_logged = False


def _require_host() -> str:
    if not core_config.ENDURAIN_HOST:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ENDURAIN_HOST environment variable is not configured",
        )
    return core_config.ENDURAIN_HOST.rstrip("/")


def get_redirect_uri() -> str:
    return f"{_require_host()}/polar/callback"


def _decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    return core_cryptography.decrypt_token_fernet(value)


def get_client_credentials(
    account: polar_models.PolarAccount,
) -> tuple[str, str]:
    client_id = _decrypt(account.client_id)
    client_secret = _decrypt(account.client_secret)
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Polar client ID and secret must be configured before linking",
        )
    return client_id, client_secret


def get_access_token(account: polar_models.PolarAccount) -> str:
    access_token = _decrypt(account.access_token)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail="Polar access token is missing. Please relink your account.",
        )
    return access_token


def exchange_code_for_token(
    account: polar_models.PolarAccount, code: str
) -> dict:
    client_id, client_secret = get_client_credentials(account)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_redirect_uri(),
    }
    headers = {
        "Accept": "application/json;charset=UTF-8",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        response = requests.post(
            POLAR_TOKEN_URL,
            headers=headers,
            data=data,
            auth=(client_id, client_secret),
            timeout=30,
        )
    except requests.RequestException as err:
        core_logger.print_to_log(
            f"Error exchanging Polar authorization code: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Polar token endpoint",
        ) from err

    if response.status_code != status.HTTP_200_OK:
        core_logger.print_to_log(
            f"Polar token endpoint returned {response.status_code}: {response.text}",
            "error",
        )
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail="Polar token exchange failed",
        )
    return response.json()


def register_user(access_token: str, member_id: str) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {"member-id": member_id}
    try:
        response = requests.post(
            f"{POLAR_API_BASE}/users", json=payload, headers=headers, timeout=30
        )
    except requests.RequestException as err:
        core_logger.print_to_log(
            f"Error registering Polar user: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to register Polar user",
        ) from err

    if response.status_code == status.HTTP_200_OK:
        return response.json()

    if response.status_code == status.HTTP_409_CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Polar user already registered for these client credentials. Please unlink in Polar Flow or use a different member-id.",
        )

    core_logger.print_to_log(
        f"Unexpected Polar register response {response.status_code}: {response.text}",
        "error",
    )
    raise HTTPException(
        status_code=status.HTTP_424_FAILED_DEPENDENCY,
        detail="Polar registration failed",
    )


def delete_remote_user(access_token: str, polar_user_id: int):
    if not polar_user_id:
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    try:
        response = requests.delete(
            f"{POLAR_API_BASE}/users/{polar_user_id}", headers=headers, timeout=30
        )
    except requests.RequestException as err:
        core_logger.print_to_log(
            f"Error deregistering Polar user {polar_user_id}: {err}",
            "error",
            exc=err,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to contact Polar to unlink the user",
        ) from err

    if response.status_code not in (
        status.HTTP_200_OK,
        status.HTTP_204_NO_CONTENT,
    ):
        core_logger.print_to_log(
            f"Unexpected response while deleting Polar user {polar_user_id}: {response.status_code} {response.text}",
            "warning",
        )


def fetch_json_with_token(access_token: str, url: str) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as err:
        resp = err.response
        status_code = resp.status_code if resp is not None else "unknown"
        body = resp.text if resp is not None else "no-body"
        core_logger.print_to_log(
            f"Polar API responded with {status_code} for {url}: {body}",
            "error",
        )
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail="Polar API call failed",
        ) from err
    except requests.RequestException as err:
        core_logger.print_to_log(
            f"Error calling Polar API {url}: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach Polar API",
        ) from err


def download_gpx(access_token: str, exercise_id: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/gpx+xml",
    }
    try:
        response = requests.get(
            f"{POLAR_API_BASE}/exercises/{exercise_id}/gpx", headers=headers, timeout=60
        )
    except requests.RequestException as err:
        core_logger.print_to_log(
            f"Error downloading Polar GPX {exercise_id}: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to download Polar exercise GPX",
        ) from err

    if response.status_code != status.HTTP_200_OK:
        core_logger.print_to_log(
            f"Polar GPX download failed ({response.status_code}) for exercise {exercise_id}",
            "error",
        )
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail="Polar exercise download failed",
        )
    return response.content


def verify_webhook_signature(signature: str | None, payload: bytes) -> bool:
    global _webhook_secret_warning_logged
    secret = core_config.POLAR_WEBHOOK_SECRET
    if not secret:
        if not _webhook_secret_warning_logged:
            core_logger.print_to_log_and_console(
                "POLAR_WEBHOOK_SECRET is not configured; webhook signatures will not be verified.",
                "warning",
            )
            _webhook_secret_warning_logged = True
        return True

    if not signature:
        return False

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
