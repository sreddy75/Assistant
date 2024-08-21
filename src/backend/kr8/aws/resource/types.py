from collections import OrderedDict
from typing import Dict, List, Type, Union

from src.backend.kr8.aws.resource.base import AwsResource
from src.backend.kr8.aws.resource.acm.certificate import AcmCertificate
from src.backend.kr8.aws.resource.cloudformation.stack import CloudFormationStack
from src.backend.kr8.aws.resource.ec2.volume import EbsVolume
from src.backend.kr8.aws.resource.ec2.subnet import Subnet
from src.backend.kr8.aws.resource.ec2.security_group import SecurityGroup
from src.backend.kr8.aws.resource.ecs.cluster import EcsCluster
from src.backend.kr8.aws.resource.ecs.task_definition import EcsTaskDefinition
from src.backend.kr8.aws.resource.eks.cluster import EksCluster
from src.backend.kr8.aws.resource.ecs.service import EcsService
from src.backend.kr8.aws.resource.eks.fargate_profile import EksFargateProfile
from src.backend.kr8.aws.resource.eks.node_group import EksNodeGroup

from src.backend.kr8.aws.resource.eks.kubeconfig import EksKubeconfig
from src.backend.kr8.aws.resource.elb.load_balancer import LoadBalancer
from src.backend.kr8.aws.resource.elb.target_group import TargetGroup
from src.backend.kr8.aws.resource.elb.listener import Listener
from src.backend.kr8.aws.resource.iam.role import IamRole
from src.backend.kr8.aws.resource.iam.policy import IamPolicy
from src.backend.kr8.aws.resource.glue.crawler import GlueCrawler
from src.backend.kr8.aws.resource.s3.bucket import S3Bucket
from src.backend.kr8.aws.resource.secret.manager import SecretsManager
from src.backend.kr8.aws.resource.emr.cluster import EmrCluster
from src.backend.kr8.aws.resource.rds.db_cluster import DbCluster
from src.backend.kr8.aws.resource.rds.db_instance import DbInstance
from src.backend.kr8.aws.resource.rds.db_subnet_group import DbSubnetGroup
from src.backend.kr8.aws.resource.elasticache.cluster import CacheCluster
from src.backend.kr8.aws.resource.elasticache.subnet_group import CacheSubnetGroup

# Use this as a type for an object which can hold any AwsResource
AwsResourceType = Union[
    AcmCertificate,
    CloudFormationStack,
    EbsVolume,
    EksCluster,
    EksKubeconfig,
    EksFargateProfile,
    EksNodeGroup,
    IamRole,
    IamPolicy,
    GlueCrawler,
    S3Bucket,
    SecretsManager,
    Subnet,
    SecurityGroup,
    DbSubnetGroup,
    DbCluster,
    DbInstance,
    CacheSubnetGroup,
    CacheCluster,
    EmrCluster,
    EcsCluster,
    EcsTaskDefinition,
    EcsService,
    LoadBalancer,
    TargetGroup,
    Listener,
]

# Use this as an ordered list to iterate over all AwsResource Classes
# This list is the order in which resources should be installed as well.
AwsResourceTypeList: List[Type[AwsResource]] = [
    Subnet,
    SecurityGroup,
    IamRole,
    IamPolicy,
    S3Bucket,
    SecretsManager,
    EbsVolume,
    AcmCertificate,
    CloudFormationStack,
    GlueCrawler,
    DbSubnetGroup,
    DbCluster,
    DbInstance,
    CacheSubnetGroup,
    CacheCluster,
    LoadBalancer,
    TargetGroup,
    Listener,
    EcsCluster,
    EcsTaskDefinition,
    EcsService,
    EksCluster,
    EksKubeconfig,
    EksFargateProfile,
    EksNodeGroup,
    EmrCluster,
]

# Map Aws resource alias' to their type
_aws_resource_type_names: Dict[str, Type[AwsResource]] = {
    aws_type.__name__.lower(): aws_type for aws_type in AwsResourceTypeList
}
_aws_resource_type_aliases: Dict[str, Type[AwsResource]] = {
    "s3": S3Bucket,
    "volume": EbsVolume,
}

AwsResourceAliasToTypeMap: Dict[str, Type[AwsResource]] = dict(**_aws_resource_type_names, **_aws_resource_type_aliases)

# Maps each AwsResource to an install weight
# lower weight AwsResource(s) get installed first
AwsResourceInstallOrder: Dict[str, int] = OrderedDict(
    {resource_type.__name__: idx for idx, resource_type in enumerate(AwsResourceTypeList, start=1)}
)
