import os
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import activities.activity.crud as activities_crud
import activities.activity.utils as activities_utils
import core.config as core_config
import core.logger as core_logger
from core.database import SessionLocal
import websocket.schema as websocket_schema

from polar import crud as polar_crud
from polar import utils as polar_utils


async def process_exercise_notification(
    polar_user_id: int,
    exercise_id: str,
    exercise_url: str | None = None,
):
    db: Session | None = None
    try:
        db = SessionLocal()
        account = polar_crud.get_account_by_polar_user_id(polar_user_id, db)
        if account is None:
            core_logger.print_to_log(
                f"Skipping Polar webhook for unknown user_id {polar_user_id}",
                "warning",
            )
            return

        if activities_crud.get_activity_by_polar_id_from_user_id(
            exercise_id, account.user_id, db
        ):
            core_logger.print_to_log(
                f"Polar exercise {exercise_id} already stored for user {account.user_id}",
                "info",
            )
            return

        access_token = polar_utils.get_access_token(account)
        metadata = None
        if exercise_url:
            try:
                metadata = polar_utils.fetch_json_with_token(access_token, exercise_url)
            except HTTPException as err:
                core_logger.print_to_log(
                    f"Unable to fetch exercise metadata for {exercise_id}: {err.detail}",
                    "warning",
                )

        gpx_bytes = polar_utils.download_gpx(access_token, exercise_id)

        os.makedirs(core_config.FILES_DIR, exist_ok=True)
        timestamp_suffix = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        file_name = f"polar_{account.user_id}_{exercise_id}_{timestamp_suffix}.gpx"
        file_path = os.path.join(core_config.FILES_DIR, file_name)
        with open(file_path, "wb") as gpx_file:
            gpx_file.write(gpx_bytes)

        websocket_manager = websocket_schema.get_websocket_manager()
        import_info = {
            "source": "polar",
            "exercise_id": exercise_id,
        }
        if exercise_url:
            import_info["metadata_url"] = exercise_url
        if metadata:
            import_info["metadata"] = metadata

        overrides = {
            "polar_exercise_id": exercise_id,
            "import_info": import_info,
        }
        await activities_utils.parse_and_store_activity_from_file(
            account.user_id,
            file_path,
            websocket_manager,
            db,
            activity_overrides=overrides,
        )
        core_logger.print_to_log(
            f"Stored Polar exercise {exercise_id} for user {account.user_id}"
        )
    except HTTPException as err:
        raise err
    except Exception as err:
        core_logger.print_to_log(
            f"Error processing Polar exercise {exercise_id}: {err}",
            "error",
            exc=err,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Polar exercise",
        ) from err
    finally:
        if db is not None:
            db.close()
