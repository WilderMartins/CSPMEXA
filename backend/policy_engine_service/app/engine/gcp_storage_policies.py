from typing import List, Optional
from app.schemas.input_data_schema import GCPStorageBucketDataInput # Alterado para Input
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

class GCPStoragePolicy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, bucket: GCPStorageBucketDataInput, project_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Definições de Políticas para GCP Storage ---

class GCPStorageBucketPublicIAMPolicy(GCPStoragePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Storage_Bucket_Public_IAM",
            title="Bucket do Cloud Storage com Acesso Público via IAM",
            description="A política IAM do bucket concede acesso a 'allUsers' ou 'allAuthenticatedUsers', tornando os objetos potencialmente públicos.",
            severity="Critical",
            recommendation="Revise as políticas IAM do bucket. Remova 'allUsers' e 'allAuthenticatedUsers' das bindings, a menos que o acesso público seja explicitamente necessário. Use o Acesso Uniforme a Nível de Bucket e evite ACLs legadas."
        )

    def check(self, bucket: GCPStorageBucketDataInput, project_id: Optional[str]) -> Optional[Alert]:
        if bucket.is_public_by_iam: # Este campo é preenchido pelo collector
            details = {
                "bucket_name": bucket.name,
                "project_id": project_id or bucket.project_number or "N/A", # project_number pode não ser o ID do projeto
                "location": bucket.location,
                "public_iam_details": bucket.public_iam_details,
                "iam_policy_bindings": [b.model_dump(exclude_none=True) for b in bucket.iam_policy.bindings] if bucket.iam_policy else []
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name, # Ou bucket.id
                resource_type="GCPStorageBucket",
                account_id=project_id or bucket.project_number or "N/A", # Usar project_id passado
                region=bucket.location,
                provider="gcp",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(bucket.public_iam_details)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class GCPStorageBucketVersioningDisabledPolicy(GCPStoragePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Storage_Bucket_Versioning_Disabled",
            title="Versionamento desabilitado em Bucket do Cloud Storage",
            description="O versionamento de objetos não está habilitado para o bucket. O versionamento protege contra exclusões ou sobrescritas acidentais.",
            severity="Medium",
            recommendation="Habilite o versionamento de objetos nas configurações do bucket para proteger os dados contra perda acidental e facilitar a recuperação."
        )

    def check(self, bucket: GCPStorageBucketDataInput, project_id: Optional[str]) -> Optional[Alert]:
        if bucket.versioning is None or not bucket.versioning.enabled:
            status = "Desabilitado" if bucket.versioning else "Não Configurado"
            details = {
                "bucket_name": bucket.name,
                "project_id": project_id or bucket.project_number or "N/A",
                "location": bucket.location,
                "versioning_status": status
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="GCPStorageBucket",
                account_id=project_id or bucket.project_number or "N/A",
                region=bucket.location,
                provider="gcp",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Status atual: {status}.",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

class GCPStorageBucketLoggingDisabledPolicy(GCPStoragePolicy):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Storage_Bucket_Logging_Disabled",
            title="Logging de Acesso desabilitado para Bucket do Cloud Storage",
            description="O logging de uso (acesso) do bucket não está habilitado ou configurado. Os logs de uso são importantes para auditoria e análise de segurança.",
            severity="Medium",
            recommendation="Configure o logging de uso para o bucket, especificando um bucket de destino para os logs de acesso e, opcionalmente, para os logs de armazenamento."
        )

    def check(self, bucket: GCPStorageBucketDataInput, project_id: Optional[str]) -> Optional[Alert]:
        # Logging em GCP é habilitado se log_bucket estiver definido.
        if bucket.logging is None or not bucket.logging.log_bucket:
            status = "Desabilitado" if bucket.logging else "Não Configurado"
            details = {
                "bucket_name": bucket.name,
                "project_id": project_id or bucket.project_number or "N/A",
                "location": bucket.location,
                "logging_status": status
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="GCPStorageBucket",
                account_id=project_id or bucket.project_number or "N/A",
                region=bucket.location,
                provider="gcp",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None


# Lista de todas as políticas GCP Storage a serem avaliadas
gcp_storage_policies_to_evaluate: List[GCPStoragePolicy] = [
    GCPStorageBucketPublicIAMPolicy(),
    GCPStorageBucketVersioningDisabledPolicy(),
    GCPStorageBucketLoggingDisabledPolicy(),
]


def evaluate_gcp_storage_policies(
    gcp_buckets_data: List[GCPStorageBucketDataInput],
    project_id: Optional[str] # project_id do request de análise
) -> List[Alert]:
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(gcp_buckets_data)} buckets GCP Storage para o projeto {project_id or 'N/A'}.")

    for bucket in gcp_buckets_data:
        if bucket.error_details:
            logger.warning(f"Skipping GCP bucket {bucket.name} due to previous collection error: {bucket.error_details}")
            continue

        # O project_id passado para evaluate_gcp_storage_policies é o ID do projeto da requisição de análise.
        # O bucket.project_number (se disponível) é o número do projeto do bucket.
        # Usar o project_id da requisição para o campo account_id do alerta.
        effective_project_id_for_alert = project_id or bucket.project_number # Fallback se project_id não for passado

        for policy in gcp_storage_policies_to_evaluate:
            try:
                alert = policy.check(bucket, effective_project_id_for_alert)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for GCP bucket {bucket.name}: {e}", exc_info=True)
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()),
                    resource_id=bucket.name,
                    resource_type="GCPStorageBucket",
                    account_id=effective_project_id_for_alert or "N/A",
                    region=bucket.location,
                    provider="gcp",
                    severity="Medium",
                    title=f"Erro ao Avaliar Política GCP {policy.policy_id}",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para o bucket GCP {bucket.name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR_GCP",
                    details={"failed_policy_id": policy.policy_id, "bucket_data": bucket.model_dump(exclude_none=True, by_alias=True)},
                    recommendation="Verifique os logs do Policy Engine para mais detalhes."
                ))

    logger.info(f"Avaliação de GCP Storage concluída para o projeto {project_id or 'N/A'}. {len(all_alerts)} alertas gerados.")
    return all_alerts
