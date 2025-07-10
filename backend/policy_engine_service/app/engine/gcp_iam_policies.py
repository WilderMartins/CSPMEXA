from typing import List, Optional, Dict, Any
from app.schemas.input_data_schema import GCPProjectIAMPolicyDataInput # Alterado para Input
from app.schemas.alert_schema import Alert
import logging
import uuid

logger = logging.getLogger(__name__)

# --- Estrutura Base para Políticas GCP IAM ---
class GCPIAMPolicyDefinition: # Renomeado para evitar conflito com schema
    def __init__(self, policy_id: str, title: str, description: str, severity: str, recommendation: str):
        self.policy_id = policy_id
        self.title = title
        self.description = description
        self.severity = severity
        self.recommendation = recommendation

    def check(self, policy_data: GCPProjectIAMPolicyDataInput, project_id: Optional[str]) -> Optional[Alert]:
        raise NotImplementedError

# --- Definições de Políticas para GCP Project IAM ---

class GCPProjectIAMExternalPrimitiveRolesPolicy(GCPIAMPolicyDefinition):
    def __init__(self):
        super().__init__(
            policy_id="GCP_Project_IAM_External_Primitive_Roles",
            title="Projeto GCP com Membros Externos em Papéis Primitivos",
            description="A política IAM do projeto concede papéis primitivos (Owner, Editor, Viewer) a membros externos como 'allUsers' ou 'allAuthenticatedUsers'. Isso pode conceder acesso excessivo e amplo aos recursos do projeto.",
            severity="Critical", # Para Owner/Editor, High para Viewer
            recommendation="Revise as políticas IAM do projeto. Remova 'allUsers' e 'allAuthenticatedUsers' de papéis primitivos. Conceda permissões granulares a identidades específicas e use o princípio do menor privilégio."
        )

    def check(self, policy_data: GCPProjectIAMPolicyDataInput, project_id_param: Optional[str]) -> Optional[Alert]:
        # O collector já preenche has_external_members_with_primitive_roles e external_primitive_role_details
        project_id_to_report = project_id_param or policy_data.project_id

        if policy_data.has_external_members_with_primitive_roles:
            # Determinar a severidade com base nos detalhes
            # (Poderia ser mais granular se soubéssemos qual papel primitivo foi concedido)
            current_severity = self.severity
            if policy_data.external_primitive_role_details:
                is_viewer_only = True
                for detail_str in policy_data.external_primitive_role_details:
                    if "roles/owner" in detail_str.lower() or "roles/editor" in detail_str.lower():
                        is_viewer_only = False
                        break
                if is_viewer_only and "roles/viewer" in " ".join(policy_data.external_primitive_role_details).lower():
                    current_severity = "High" # Rebaixar para High se for apenas Viewer externo

            details = {
                "project_id": project_id_to_report,
                "problematic_bindings": policy_data.external_primitive_role_details,
                "full_iam_policy_bindings": [b.model_dump(exclude_none=True) for b in policy_data.iam_policy.bindings]
            }
            return Alert(
                id=str(uuid.uuid4()),
                resource_id=project_id_to_report, # O recurso é o próprio projeto
                resource_type="GCPProject",
                account_id=project_id_to_report,
                region="global", # IAM de projeto é global
                provider="gcp",
                severity=current_severity,
                title=self.title,
                description=f"{self.description} Detalhes: {'; '.join(policy_data.external_primitive_role_details)}",
                policy_id=self.policy_id,
                details=details,
                recommendation=self.recommendation,
            )
        return None

# Adicionar mais políticas IAM aqui, por exemplo:
# - Service Account com privilégios de administrador de projeto
# - Uso excessivo de chaves de Service Account em vez de impersonation
# - Políticas de Senha da Organização (se coletadas)

# --- Lista de Políticas ---
gcp_project_iam_policies_to_evaluate: List[GCPIAMPolicyDefinition] = [
    GCPProjectIAMExternalPrimitiveRolesPolicy(),
]

# --- Funções de Avaliação ---
def evaluate_gcp_project_iam_policies(
    project_iam_data: Optional[GCPProjectIAMPolicyDataInput], # Pode ser None se a coleta falhar
    project_id: Optional[str] # ID do projeto da requisição de análise
) -> List[Alert]:
    all_alerts: List[Alert] = []

    if not project_iam_data:
        logger.info(f"Nenhum dado de política IAM de projeto fornecido para o projeto {project_id or 'N/A'}. Nenhuma avaliação será feita.")
        return all_alerts

    # Usar o project_id da requisição de análise como o ID da conta principal para o alerta.
    # O project_iam_data.project_id deve corresponder, mas o da requisição é a fonte de verdade.
    effective_project_id_for_alert = project_id or project_iam_data.project_id

    logger.info(f"Avaliando política IAM do projeto GCP: {effective_project_id_for_alert}.")

    if project_iam_data.error_details:
        logger.warning(f"Skipping GCP Project IAM policy evaluation for project {effective_project_id_for_alert} due to collection error: {project_iam_data.error_details}")
        # Poderia gerar um alerta sobre a falha na coleta, se desejado
        return all_alerts

    for policy_def in gcp_project_iam_policies_to_evaluate:
        try:
            alert = policy_def.check(project_iam_data, effective_project_id_for_alert)
            if alert:
                all_alerts.append(alert)
        except Exception as e:
            logger.error(f"Error evaluating policy {policy_def.policy_id} for GCP project IAM {effective_project_id_for_alert}: {e}", exc_info=True)
            all_alerts.append(Alert(
                id=str(uuid.uuid4()),
                resource_id=effective_project_id_for_alert,
                resource_type="GCPProjectIAMPolicy", # Tipo de recurso específico para a política
                account_id=effective_project_id_for_alert,
                region="global",
                provider="gcp",
                severity="Medium",
                title=f"Erro ao Avaliar Política GCP IAM {policy_def.policy_id}",
                description=f"Ocorreu um erro interno ao tentar avaliar a política '{policy_def.title}' para a política IAM do projeto {effective_project_id_for_alert}. Detalhe: {str(e)}",
                policy_id="POLICY_ENGINE_ERROR_GCP_IAM",
                details={"failed_policy_id": policy_def.policy_id, "project_id": effective_project_id_for_alert},
                recommendation="Verifique os logs do Policy Engine para mais detalhes."
            ))

    logger.info(f"Avaliação da política IAM do projeto GCP {effective_project_id_for_alert} concluída. {len(all_alerts)} alertas gerados.")
    return all_alerts
