from typing import List, Optional
from app.schemas.input_data_schema import S3BucketDataInput
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

# Estrutura base para uma definição de política (pode ser mais elaborada no futuro)
class S3Policy:
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, bucket: S3BucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        """
        Verifica o bucket S3 contra esta política.
        Retorna um Alert se a política for violada, None caso contrário.
        """
        raise NotImplementedError


# --- Definições de Políticas S3 ---

class S3PublicReadACLPolicy(S3Policy):
    def __init__(self):
        super().__init__(
            policy_id="S3_Public_Read_ACL",
            title="S3 Bucket com ACL de Leitura Pública",
            description="O bucket S3 permite leitura pública através de suas Listas de Controle de Acesso (ACLs) para 'AllUsers' ou 'AuthenticatedUsers'. Isso pode expor dados sensíveis.",
            severity="High",
            recommendation="Revise as ACLs do bucket. Se o acesso público não for necessário, remova as permissões para 'AllUsers' e 'AuthenticatedUsers'. Considere usar Políticas de Bucket e Bloqueio de Acesso Público para um controle mais granular e seguro."
        )

    def check(self, bucket: S3BucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if bucket.acl and bucket.acl.is_public:
            # Detalhes específicos da violação
            violation_details = {
                "acl_public_details": bucket.acl.public_details,
                "bucket_name": bucket.name,
                "region": bucket.region
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="S3Bucket",
                account_id=account_id or "N/A",
                region=bucket.region,
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(bucket.acl.public_details)}.",
                policy_id=self.policy_id,
                details=violation_details,
                recommendation=self.recommendation,
            )
        return None

class S3PublicPolicyPolicy(S3Policy): # Nome da classe ligeiramente redundante
    def __init__(self):
        super().__init__(
            policy_id="S3_Public_Policy",
            title="S3 Bucket com Política de Acesso Público",
            description="A política do bucket S3 permite acesso público (ex: Principal AWS: '*'). Isso pode expor dados sensíveis a qualquer pessoa na internet.",
            severity="Critical", # Geralmente mais crítico que ACL pública
            recommendation="Revise a política do bucket. Se o acesso público não for intencional, restrinja o Principal ou as ações permitidas. Utilize o Bloqueio de Acesso Público S3 para evitar configurações públicas acidentais."
        )

    def check(self, bucket: S3BucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if bucket.policy_is_public: # Este campo é preenchido pelo collector
            violation_details = {
                "bucket_name": bucket.name,
                "region": bucket.region,
                "policy_document": bucket.policy # Inclui a política para referência
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="S3Bucket",
                account_id=account_id or "N/A",
                region=bucket.region,
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=violation_details,
                recommendation=self.recommendation,
            )
        return None

class S3VersioningDisabledPolicy(S3Policy):
    def __init__(self):
        super().__init__(
            policy_id="S3_Versioning_Disabled",
            title="Versionamento desabilitado ou suspenso em Bucket S3",
            description="O versionamento não está habilitado ou está suspenso para o bucket S3. O versionamento protege contra exclusões ou sobrescritas acidentais de objetos.",
            severity="Medium",
            recommendation="Habilite o versionamento no bucket S3 para proteger os dados contra perda acidental e facilitar a recuperação."
        )

    def check(self, bucket: S3BucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if bucket.versioning is None or bucket.versioning.status != "Enabled":
            status = "Não Configurado"
            if bucket.versioning and bucket.versioning.status:
                status = bucket.versioning.status

            violation_details = {
                "bucket_name": bucket.name,
                "region": bucket.region,
                "versioning_status": status
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="S3Bucket",
                account_id=account_id or "N/A",
                region=bucket.region,
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=f"{self.description} Status atual: {status}.",
                policy_id=self.policy_id,
                details=violation_details,
                recommendation=self.recommendation,
            )
        return None

class S3LoggingDisabledPolicy(S3Policy):
    def __init__(self):
        super().__init__(
            policy_id="S3_Logging_Disabled",
            title="Logging de Acesso ao Servidor desabilitado para Bucket S3",
            description="O logging de acesso ao servidor não está habilitado para o bucket S3. Os logs de acesso fornecem detalhes sobre as requisições feitas ao bucket, úteis para auditoria de segurança e análise de acesso.",
            severity="Medium",
            recommendation="Habilite o logging de acesso ao servidor para o bucket S3, especificando um bucket de destino para os logs."
        )

    def check(self, bucket: S3BucketDataInput, account_id: Optional[str]) -> Optional[Alert]:
        if bucket.logging is None or not bucket.logging.enabled:
            violation_details = {
                "bucket_name": bucket.name,
                "region": bucket.region,
                "logging_status": "Desabilitado" if bucket.logging else "Não Configurado"
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=bucket.name,
                resource_type="S3Bucket",
                account_id=account_id or "N/A",
                region=bucket.region,
                provider="aws",
                severity=self.severity,
                title=self.title,
                description=self.description,
                policy_id=self.policy_id,
                details=violation_details,
                recommendation=self.recommendation,
            )
        return None

# Lista de todas as políticas S3 a serem avaliadas
s3_policies_to_evaluate: List[S3Policy] = [
    S3PublicReadACLPolicy(),
    S3PublicPolicyPolicy(),
    S3VersioningDisabledPolicy(),
    S3LoggingDisabledPolicy(),
]


def evaluate_s3_policies(s3_buckets_data: List[S3BucketDataInput], account_id: Optional[str]) -> List[Alert]:
    """
    Avalia uma lista de buckets S3 em relação a todas as políticas S3 definidas.
    """
    all_alerts: List[Alert] = []
    logger.info(f"Avaliando {len(s3_buckets_data)} buckets S3 para a conta {account_id or 'N/A'}.")

    for bucket in s3_buckets_data:
        if bucket.error_details:
            logger.warning(f"Skipping bucket {bucket.name} due to previous collection error: {bucket.error_details}")
            continue

        for policy in s3_policies_to_evaluate:
            try:
                alert = policy.check(bucket, account_id)
                if alert:
                    all_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error evaluating policy {policy.policy_id} for bucket {bucket.name}: {e}", exc_info=True)
                # Opcional: criar um alerta sobre a falha da avaliação da política
                all_alerts.append(Alert(
                    id=str(uuid.uuid4()),
                    resource_id=bucket.name,
                    resource_type="S3Bucket",
                    account_id=account_id or "N/A",
                    region=bucket.region,
                    provider="aws",
                    severity="Medium", # Ou outra severidade apropriada para erro de engine
                    title=f"Erro ao Avaliar Política {policy.policy_id}",
                    description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy.title}' para o bucket {bucket.name}. Detalhe: {str(e)}",
                    policy_id="POLICY_ENGINE_ERROR",
                    details={"failed_policy_id": policy.policy_id, "bucket_data": bucket.model_dump_json(exclude_none=True)},
                    recommendation="Verifique os logs do Policy Engine para mais detalhes."
                ))

    logger.info(f"Avaliação de S3 concluída. {len(all_alerts)} alertas gerados.")
    return all_alerts
