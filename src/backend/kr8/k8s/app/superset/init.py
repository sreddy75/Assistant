from typing import Optional, Union, List

from src.backend.kr8.k8s.app.superset.base import SupersetBase


class SupersetInit(SupersetBase):
    # -*- App Name
    name: str = "superset-init"

    # Command for the container
    entrypoint: Optional[Union[str, List]] = "/scripts/init-superset.sh"
