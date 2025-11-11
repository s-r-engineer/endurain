import json
from typing import Annotated, Callable

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Security,
    status,
)
from sqlalchemy.orm import Session

import activities.activity.crud as activities_crud
import core.database as core_database
import core.logger as core_logger
import polar.activity_utils as polar_activity_utils
import polar.crud as polar_crud
import polar.schema as polar_schema
import polar.utils as polar_utils
import session.security as session_security

router = APIRouter()


@router.put("/client")
async def polar_set_user_client(
    client: polar_schema.PolarClient,
    validate_access_token: Annotated[
        Callable,
        Depends(session_security.validate_access_token),
    ],
    check_scopes: Annotated[
        Callable, Security(session_security.check_scopes, scopes=["profile"])
    ],
    token_user_id: Annotated[
        int,
        Depends(session_security.get_user_id_from_access_token),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
):
    polar_crud.set_client_credentials(
        token_user_id, client.client_id, client.client_secret, db
    )
    return {"detail": f"Polar client saved for user {token_user_id}"}


@router.put("/state/{state}")
async def polar_set_user_state(
    state: str | None,
    validate_access_token: Annotated[
        Callable,
        Depends(session_security.validate_access_token),
    ],
    check_scopes: Annotated[
        Callable, Security(session_security.check_scopes, scopes=["profile"])
    ],
    token_user_id: Annotated[
        int,
        Depends(session_security.get_user_id_from_access_token),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
):
    polar_crud.set_state(token_user_id, state, db)
    return {"detail": f"Polar state updated for user {token_user_id}"}


@router.put("/link")
async def polar_link(
    state: str,
    code: str,
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
):
    account = polar_crud.get_account_by_state(state, db)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Polar state not found",
        )

    try:
        tokens = polar_utils.exchange_code_for_token(account, code)
        scope = tokens.get("scope") or "accesslink.read_all"
        polar_crud.store_token_payload(account, tokens, scope, db)

        access_token = polar_utils.get_access_token(account)
        member_id = f"endurain-{account.user_id}"
        registration = polar_utils.register_user(access_token, member_id)
        polar_crud.store_registration_details(account, registration, db)

        return {
            "detail": f"Polar linked successfully for user {account.user_id}",
        }
    except HTTPException as err:
        polar_crud.unlink_account(account.user_id, db)
        raise err
    except Exception as err:
        core_logger.print_to_log(
            f"Unexpected error linking Polar account: {err}", "error", exc=err
        )
        polar_crud.unlink_account(account.user_id, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to complete Polar linking flow",
        ) from err


@router.delete("/unlink")
async def polar_unlink(
    validate_access_token: Annotated[
        Callable,
        Depends(session_security.validate_access_token),
    ],
    check_scopes: Annotated[
        Callable, Security(session_security.check_scopes, scopes=["profile"])
    ],
    token_user_id: Annotated[
        int,
        Depends(session_security.get_user_id_from_access_token),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
):
    account = polar_crud.get_account_by_user_id(token_user_id, db)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Polar account not found",
        )

    try:
        try:
            access_token = polar_utils.get_access_token(account)
            polar_utils.delete_remote_user(access_token, account.polar_user_id)
        except HTTPException as err:
            core_logger.print_to_log(
                f"Unable to notify Polar while unlinking user {token_user_id}: {err.detail}",
                "warning",
            )

        activities_crud.delete_all_polar_activities_for_user(token_user_id, db)
        polar_crud.unlink_account(token_user_id, db)
    except HTTPException as err:
        raise err
    except Exception as err:
        core_logger.print_to_log(
            f"Error unlinking Polar for user {token_user_id}: {err}",
            "error",
            exc=err,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to unlink Polar account",
        ) from err

    return {"detail": f"Polar unlinked for user {token_user_id}"}


@router.post("/webhook")
async def polar_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    raw_body = await request.body()
    signature = request.headers.get("Polar-Webhook-Signature")
    event_type = request.headers.get("Polar-Webhook-Event")

    if not polar_utils.verify_webhook_signature(signature, raw_body):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )

    try:
        payload_dict = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {err.msg}",
        ) from err

    data = polar_schema.PolarWebhookPayload(**payload_dict)
    effective_event = event_type or data.event
    if effective_event == "PING":
        return {"detail": "pong"}

    if effective_event != "EXERCISE":
        core_logger.print_to_log(
            f"Received unsupported Polar webhook event {effective_event}", "info"
        )
        return {"detail": "ignored"}

    if data.user_id is None or data.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing user_id or entity_id in Polar webhook payload",
        )

    background_tasks.add_task(
        polar_activity_utils.process_exercise_notification,
        data.user_id,
        data.entity_id,
        data.url,
    )

    return {"detail": "accepted"}
