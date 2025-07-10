from typing import List
from app.schemas.input_data_schema import S3BucketData
from app.schemas.alert_schema import Alert
import uuid
# import datetime # Removido, pois não está sendo usado diretamente aqui (está em Alert schema)


def check_s3_bucket_public_acl(bucket_data: S3BucketData) -> List[Alert]:
    """
    Verifica se um bucket S3 é público com base nas informações de ACL fornecidas.
    Gera um alerta se for público.
    """
    alerts: List[Alert] = []

    # A lógica de `is_public_by_acl` já foi determinada pelo collector.
    # O collector pode retornar True, False, "Error", ou "Unknown".
    # Vamos alertar se for explicitamente True.
    if bucket_data.is_public_by_acl is True:
        alert_title = f"S3 Bucket '{bucket_data.name}' is publicly accessible via ACL"
        alert_description = (
            f"The S3 bucket '{bucket_data.name}' in region '{bucket_data.region}' has ACL settings "
            f"that grant public access. Details: {bucket_data.public_acl_details}. "
            "This can lead to unintended data exposure."
        )
        alerts.append(
            Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket_data.name,
                resource_type="S3Bucket",
                region=bucket_data.region,
                severity="Critical",  # Ou High, dependendo da política da empresa
                title=alert_title,
                description=alert_description,
                policy_id="S3_PUBLIC_ACL_DETECTED",  # Um ID de política interno
                details={
                    "bucket_name": bucket_data.name,
                    "region": bucket_data.region,
                    "acl_details": bucket_data.public_acl_details,
                },
                recommendation="Review bucket ACLs and remove public grants (e.g., for 'AllUsers' or 'AuthenticatedUsers'). Prefer using bucket policies for fine-grained access control and disable public ACLs if possible using S3 Block Public Access settings.",
            )
        )
    elif bucket_data.is_public_by_acl == "Error":
        # Opcional: Gerar um alerta informativo ou de baixa severidade se a ACL não pôde ser verificada.
        alerts.append(
            Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket_data.name,
                resource_type="S3Bucket",
                region=bucket_data.region,
                severity="Informational",
                title=f"S3 Bucket '{bucket_data.name}' ACL check resulted in an error",
                description=f"Could not definitively determine the ACL status for bucket '{bucket_data.name}'. Details: {bucket_data.public_acl_details}. Manual review might be needed.",
                policy_id="S3_ACL_CHECK_ERROR",
                details={
                    "bucket_name": bucket_data.name,
                    "region": bucket_data.region,
                    "error_details": bucket_data.public_acl_details,
                },
            )
        )

    # Adicionar mais verificações de políticas S3 aqui no futuro
    # Ex: verificar políticas de bucket, configurações de "Block Public Access", etc.

    return alerts


def analyze_s3_data(s3_data_list: List[S3BucketData]) -> List[Alert]:
    """
    Analisa uma lista de dados de buckets S3 e retorna uma lista de alertas.
    """
    all_alerts: List[Alert] = []
    for bucket_data in s3_data_list:
        all_alerts.extend(check_s3_bucket_public_acl(bucket_data))
    return all_alerts
