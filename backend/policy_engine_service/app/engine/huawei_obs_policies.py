from typing import List, Optional
from app.schemas.input_data_schema import HuaweiOBSBucketDataInput
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

class HuaweiOBSPolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, bucket: HuaweiOBSBucketDataInput, account_id: Optional[str]) -> Optional[Alert]: # account_id aqui seria project_id ou domain_id
        raise NotImplementedError

# --- Definições de Políticas para Huawei OBS ---

class HuaweiOBSBucketPublicAccessPolicy(HuaweiOBSPolicy):
    def __init__(self):
        super().__init__(
            policy_id="HUAWEI_OBS_Bucket_Public_Access",
            title="Bucket OBS com Acesso Público (via Política ou ACL)",
            description="O bucket OBS permite acesso público através de sua política de bucket ou ACLs. Isso pode expor dados sensíveis.",
            severity="Critical", # Acesso público a buckets é geralmente crítico
            recommendation="Revise as políticas e ACLs do bucket. Remova permissões para 'Everyone' ou equivalentes (ex: Principal Huawei: '*') se o acesso público não for necessário. Utilize o controle de acesso mais granular possível."
        )

    def check(self, bucket: HuaweiOBSBucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        is_public = False
        public_details_combined = []

        if bucket.is_public_by_policy and bucket.public_policy_details:
            is_public = True
            public_details_combined.extend([f"Policy: {d}" for d in bucket.public_policy_details])

        if bucket.is_public_by_acl and bucket.public_acl_details:
            is_public = True
            public_details_combined.extend([f"ACL: {d}" for d in bucket.public_acl_details])

        if is_public:
            details = {
                "bucket_name": bucket.name,
                "account_id": account_id or "N/A", # Pode ser project_id ou domain_id
                "location": bucket.location or "N/A",
                "public_access_details": public_details_combined,
                "bucket_policy": bucket.bucket_policy.model_dump(exclude_none=True, by_alias=True) if bucket.bucket_policy else None,
                "acl": bucket.acl.model_dump(exclude_none=True, by_alias=True) if bucket.acl else None
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="HuaweiOBSBucket",
                account_id=account_id or "N/A",
                region=bucket.location or "N/A",
                provider="huawei",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(public_details_combined)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class HuaweiOBSBucketVersioningDisabledPolicy(HuaweiOBSPolicy):
    def __init__(self):
        super().__init__(
            policy_id="HUAWEI_OBS_Bucket_Versioning_Disabled",
            title="Versionamento desabilitado em Bucket OBS",
            description="O versionamento de objetos não está habilitado ou está suspenso para o bucket OBS. O versionamento protege contra exclusões ou sobrescritas acidentais.",
            severity="Medium",
            recommendation="Habilite o versionamento no bucket OBS para proteger os dados contra perda acidental e facilitar a recuperação."
        )

    def check(self, bucket: HuaweiOBSBucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if bucket.versioning is None or bucket.versioning.status != "Enabled": # Huawei usa "Enabled" ou "Suspended"
            status = "Não Configurado"
            if bucket.versioning and bucket.versioning.status:
                status = bucket.versioning.status

            details = {
                "bucket_name": bucket.name,
                "account_id": account_id or "N/A",
                "location": bucket.location or "N/A",
                "versioning_status": status
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="HuaweiOBSBucket",
                account_id=account_id or "N/A",
                region=bucket.location or "N/A",
                provider="huawei",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Status atual: {status}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class HuaweiOBSBucketLoggingDisabledPolicy(HuaweiOBSPolicy):
    def __init__(self):
        super().__init__(
            policy_id="HUAWEI_OBS_Bucket_Logging_Disabled",
            title="Logging de Acesso desabilitado para Bucket OBS",
            description="O logging de acesso ao servidor não está habilitado para o bucket OBS. Os logs de acesso fornecem detalhes sobre as requisições feitas ao bucket, úteis para auditoria de segurança.",
            severity="Medium",
            recommendation="Habilite o logging de acesso ao servidor para o bucket OBS, especificando um bucket de destino para os logs."
        )

    def check(self, bucket: HuaweiOBSBucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if bucket.logging is None or not bucket.logging.enabled:
            status = "Desabilitado" if bucket.logging else "Não Configurado"
            details = {
                "bucket_name": bucket.name,
                "account_id": account_id or "N/A",
                "location": bucket.location or "N/A",
                "logging_status": status
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="HuaweiOBSBucket",
                account_id=account_id or "N/A",
                region=bucket.location or "N/A",
                provider="huawei",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

# Lista de todas as políticas Huawei OBS a serem avaliadas
huawei_obs_policies_to_evaluate: List[HuaweiOBSPolicy] = [
    HuaweiOBSBucketPublicAccessPolicy(),
    HuaweiOBSBucketVersioningDisabledPolicy(),
    HuaweiOBSBucketLoggingDisabledPolicy(),
]

def evaluate_huawei_obs_policies(
    huawei_buckets_data: List[HuaweiOBSBucketDataInput],
    account_id: Optional[str] # Pode ser project_id ou domain_id dependendo do contexto
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(huawei_buckets_data)} buckets Huawei OBS para a conta/projeto {account_id or 'N/A'}.")

    for bucket in huawei_buckets_data:
        if bucket.error_details:
            logger.warning(f"Skipping Huawei OBS bucket {bucket.name} due to collection error: {bucket.error_details}")
            continue

        for policy_def in huawei_obs_policies_to_evaluate:
            try:
                alert = policy_def.check(bucket, account_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy_def.policy_id} for Huawei OBS bucket {bucket.name}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()), resource_id=bucket.name, resource_type="HuaweiOBSBucket",
                    account_id=account_id or "N/A", region=bucket.location or "N/A", provider="huawei",
                    severity="Medium", title=f"Erro ao Avaliar Política Huawei OBS {policy_def.policy_id}",
                    description=f"Ocorreu um erro interno: {str(e)}", policy_id="POLICY_ENGINE_ERROR_HUAWEI_OBS",
                    details={"failed_policy_id": policy_def.policy_id, "bucket_name": bucket.name},
                    recommendation="Verifique os logs do Policy Engine."
                ))

    logger.info(f"Avaliação de Huawei OBS concluída para {account_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts
