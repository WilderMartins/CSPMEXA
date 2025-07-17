import logging
from typing import List, Dict, Any
from app.schemas.input_data_schema import AnalysisRequest
from app.schemas.asset_schema import AssetCreate
from app.engine.policy_loader import loaded_policies
from app.engine.generic_policy_evaluator import evaluate_policy
from app.crud.crud_asset import asset_crud
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self):
        self.policies = loaded_policies
        logger.info(f"Motor de Políticas inicializado com {len(self.policies)} políticas carregadas.")

    def _save_assets(self, db: Session, request_data: AnalysisRequest):
        logger.info(f"Salvando/Atualizando {len(request_data.data)} ativos para a conta {request_data.account_id}")
        for resource_data in request_data.data:
            # Lida com diferentes campos de ID
            unique_asset_id = resource_data.get("arn") or resource_data.get("asset_id") or resource_data.get("id")
            if not unique_asset_id:
                logger.warning(f"Recurso do tipo '{request_data.service}' sem um ID único. Pulando salvamento no inventário.")
                continue

            asset_in = AssetCreate(
                asset_id=unique_asset_id,
                asset_type=request_data.service,
                name=resource_data.get("name"),
                provider=request_data.provider,
                account_id=request_data.account_id,
                region=resource_data.get("region"),
                configuration=resource_data,
            )
            asset_crud.create_or_update(db, obj_in=asset_in)
        logger.info("Ativos salvos/atualizados com sucesso.")

    async def analyze(self, request_data: AnalysisRequest) -> List[Dict[str, Any]]:
        generated_alerts: List[Dict[str, Any]] = []

        provider = request_data.provider.lower()
        service = request_data.service.lower()
        data = request_data.data
        account_id = request_data.account_id

        if not data:
            return []


        with SessionLocal() as db:
            # 1. Salvar os ativos no inventário
            self._save_assets(db, request_data)

            # 2. Avaliar políticas
            relevant_policies = [p for p in self.policies if p.get('provider', '').lower() == provider and p.get('service', '').lower() == service]
            if relevant_policies:
                for policy in relevant_policies:
                    try:
                        alerts_from_policy = evaluate_policy(policy=policy, data=data, account_id=account_id)
                        if alerts_from_policy:
                            # O ideal é que evaluate_policy também use a sessão do DB para criar os alertas
                            generated_alerts.extend(alerts_from_policy)
                    except Exception as e:
                        logger.error(f"Erro ao avaliar a política '{policy.get('id')}': {e}", exc_info=True)

            # 3. Executar análise de caminhos de ataque
            from app.services.graph_analysis_service import run_attack_path_analysis
            run_attack_path_analysis(db)

        logger.info(f"Análise para {provider}/{service} concluída. {len(generated_alerts)} alertas gerados.")
        return generated_alerts

policy_engine = PolicyEngine()

            try:
                alerts_from_policy = evaluate_policy(policy=policy, data=data, account_id=account_id)
                if alerts_from_policy:
                    generated_alerts.extend(alerts_from_policy)
            except Exception as e:
                logger.error(f"Erro ao avaliar a política '{policy.get('id')}': {e}", exc_info=True)

        logger.info(f"Análise para {provider}/{service} concluída. {len(generated_alerts)} alertas gerados.")
        return generated_alerts

policy_engine = PolicyEngine()
