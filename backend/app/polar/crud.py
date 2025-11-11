from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import core.cryptography as core_cryptography
import core.logger as core_logger

from polar import models as polar_models


def _get_account_query(user_id: int, db: Session):
    return (
        db.query(polar_models.PolarAccount)
        .filter(polar_models.PolarAccount.user_id == user_id)
        .first()
    )


def get_or_create_account(user_id: int, db: Session) -> polar_models.PolarAccount:
    account = _get_account_query(user_id, db)
    if account is None:
        account = polar_models.PolarAccount(user_id=user_id, is_linked=False)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def get_account_by_user_id(
    user_id: int, db: Session
) -> polar_models.PolarAccount | None:
    return _get_account_query(user_id, db)


def get_account_by_state(state: str, db: Session) -> polar_models.PolarAccount | None:
    if state is None:
        return None
    return (
        db.query(polar_models.PolarAccount)
        .filter(polar_models.PolarAccount.state == state)
        .first()
    )


def get_account_by_polar_user_id(
    polar_user_id: int, db: Session
) -> polar_models.PolarAccount | None:
    if polar_user_id is None:
        return None
    return (
        db.query(polar_models.PolarAccount)
        .filter(polar_models.PolarAccount.polar_user_id == polar_user_id)
        .first()
    )


def set_state(user_id: int, state: str | None, db: Session):
    account = get_or_create_account(user_id, db)
    account.state = None if state in (None, "null") else state
    db.commit()


def set_client_credentials(user_id: int, client_id: str, client_secret: str, db: Session):
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client ID and secret are required",
        )
    account = get_or_create_account(user_id, db)
    try:
        account.client_id = core_cryptography.encrypt_token_fernet(client_id)
        account.client_secret = core_cryptography.encrypt_token_fernet(client_secret)
        db.commit()
    except Exception as err:
        db.rollback()
        core_logger.print_to_log(
            f"Error saving Polar client credentials: {err}",
            "error",
            exc=err,
            context={"user_id": user_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store Polar client credentials",
        ) from err


def store_token_payload(
    account: polar_models.PolarAccount,
    token_payload: dict,
    scope: str | None,
    db: Session,
):
    try:
        account.access_token = core_cryptography.encrypt_token_fernet(
            token_payload["access_token"]
        )
        account.token_type = token_payload.get("token_type")
        account.token_scope = scope
        account.token_issued_at = datetime.now(timezone.utc)
        expires_in = token_payload.get("expires_in")
        if expires_in:
            account.token_expires_at = account.token_issued_at + timedelta(
                seconds=int(expires_in)
            )
        else:
            account.token_expires_at = None
        account.x_user_id = token_payload.get("x_user_id")
        account.is_linked = True
        account.state = None
        db.commit()
    except Exception as err:
        db.rollback()
        core_logger.print_to_log(
            f"Error storing Polar token payload: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store Polar token information",
        ) from err


def store_registration_details(
    account: polar_models.PolarAccount, registration_payload: dict, db: Session
):
    try:
        account.polar_user_id = registration_payload.get("polar-user-id")
        account.member_id = registration_payload.get("member-id")
        registration_date = registration_payload.get("registration-date")
        if registration_date:
            account.registration_date = datetime.fromisoformat(
                registration_date.replace("Z", "+00:00")
            )
        db.commit()
    except Exception as err:
        db.rollback()
        core_logger.print_to_log(
            f"Error storing Polar registration details: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store Polar registration data",
        ) from err


def unlink_account(user_id: int, db: Session):
    account = get_account_by_user_id(user_id, db)
    if account is None:
        return
    try:
        account.access_token = None
        account.token_type = None
        account.token_scope = None
        account.token_issued_at = None
        account.token_expires_at = None
        account.x_user_id = None
        account.polar_user_id = None
        account.member_id = None
        account.registration_date = None
        account.is_linked = False
        account.state = None
        db.commit()
    except Exception as err:
        db.rollback()
        core_logger.print_to_log(
            f"Error unlinking Polar account: {err}", "error", exc=err
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to unlink Polar account",
        ) from err
