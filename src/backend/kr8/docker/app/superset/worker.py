from typing import Optional, Union, List

from src.backend.kr8.docker.app.superset.base import SupersetBase


class SupersetWorker(SupersetBase):
    # -*- App Name
    name: str = "superset-worker"

    # Command for the container
    command: Optional[Union[str, List[str]]] = "worker"
