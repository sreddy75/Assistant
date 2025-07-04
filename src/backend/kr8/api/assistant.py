from os import getenv
from typing import Union, Dict, List

from httpx import Response

from src.backend.kr8.api.api import api, invalid_response
from src.backend.kr8.api.routes import ApiRoutes
from src.backend.kr8.api.schemas.assistant import (
    AssistantEventCreate,
    AssistantRunCreate,
)
from src.backend.kr8.constants import PHI_API_KEY_ENV_VAR, PHI_WS_KEY_ENV_VAR
from src.backend.kr8.cli.settings import phi_cli_settings
from src.backend.kr8.utils.log import logger


def create_assistant_run(run: AssistantRunCreate) -> bool:
    if not phi_cli_settings.api_enabled:
        return True

    logger.debug("--o-o-- Creating Assistant Run")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.ASSISTANT_RUN_CREATE,
                headers={
                    "Authorization": f"Bearer {getenv(PHI_API_KEY_ENV_VAR)}",
                    "PHI-WORKSPACE": f"{getenv(PHI_WS_KEY_ENV_VAR)}",
                },
                json={
                    "run": run.model_dump(exclude_none=True),
                    # "workspace": assistant_workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create assistant run: {e}")
    return False


def create_assistant_event(event: AssistantEventCreate) -> bool:
    if not phi_cli_settings.api_enabled:
        return True

    logger.debug("--o-o-- Creating Assistant Event")
    with api.AuthenticatedClient() as api_client:
        try:
            r: Response = api_client.post(
                ApiRoutes.ASSISTANT_EVENT_CREATE,
                headers={
                    "Authorization": f"Bearer {getenv(PHI_API_KEY_ENV_VAR)}",
                    "PHI-WORKSPACE": f"{getenv(PHI_WS_KEY_ENV_VAR)}",
                },
                json={
                    "event": event.model_dump(exclude_none=True),
                    # "workspace": assistant_workspace.model_dump(exclude_none=True),
                },
            )
            if invalid_response(r):
                return False

            response_json: Union[Dict, List] = r.json()
            if response_json is None:
                return False

            logger.debug(f"Response: {response_json}")
            return True
        except Exception as e:
            logger.debug(f"Could not create assistant event: {e}")
    return False
