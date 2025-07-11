# Este arquivo reexporta os schemas para facilitar os imports no data_router.py

from . import collector_s3_schemas
from . import collector_ec2_schemas
from . import collector_iam_schemas
from . import collector_rds_schemas

from . import collector_gcp_storage_schemas
from . import collector_gcp_compute_schemas
from . import collector_gcp_iam_schemas
from . import collector_gke_schemas # Adicionado GKE

from . import collector_huawei_obs_schemas
from . import collector_huawei_ecs_schemas
from . import collector_huawei_iam_schemas

from . import collector_azure_schemas

from . import collector_google_workspace_schemas # Para Google Workspace (Usuários e Drive)

from . import policy_engine_alert_schema

__all__ = [
    "collector_s3_schemas",
    "collector_ec2_schemas",
    "collector_iam_schemas",
    "collector_rds_schemas",
    "collector_gcp_storage_schemas",
    "collector_gcp_compute_schemas",
    "collector_gcp_iam_schemas",
    "collector_gke_schemas", # Adicionado GKE
    "collector_huawei_obs_schemas",
    "collector_huawei_ecs_schemas",
    "collector_huawei_iam_schemas",
    "collector_azure_schemas",
    "collector_google_workspace_schemas", # Exporta todos os schemas de GWS
    "policy_engine_alert_schema"
]
