from collections import OrderedDict
from typing import Dict, List, Type, Union

from src.backend.kr8.docker.resource.network import DockerNetwork
from src.backend.kr8.docker.resource.image import DockerImage
from src.backend.kr8.docker.resource.container import DockerContainer
from src.backend.kr8.docker.resource.volume import DockerVolume
from src.backend.kr8.docker.resource.base import DockerResource

# Use this as a type for an object that can hold any DockerResource
DockerResourceType = Union[
    DockerNetwork,
    DockerImage,
    DockerVolume,
    DockerContainer,
]

# Use this as an ordered list to iterate over all DockerResource Classes
# This list is the order in which resources are installed as well.
DockerResourceTypeList: List[Type[DockerResource]] = [
    DockerNetwork,
    DockerImage,
    DockerVolume,
    DockerContainer,
]

# Maps each DockerResource to an Install weight
# lower weight DockerResource(s) get installed first
# i.e. Networks are installed first, Images, then Volumes ... and so on
DockerResourceInstallOrder: Dict[str, int] = OrderedDict(
    {resource_type.__name__: idx for idx, resource_type in enumerate(DockerResourceTypeList, start=1)}
)
