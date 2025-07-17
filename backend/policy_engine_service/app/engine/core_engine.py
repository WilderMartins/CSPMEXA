import logging
from typing import List, Dict, Any
from app.schemas.input_data_schema import AnalysisRequest
from app.engine.policy_loader import loaded_policies
from app.engine.generic_policy_evaluator import evaluate_policy

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self):
        self.policies = loaded_policies
        logger.info(f"Motor de Políticas inicializado com {len(self.policies)} políticas carregadas.")

    async def analyze(self, request_data: AnalysisRequest) -> List[Dict[str, Any]]:
        generated_alerts: List[Dict[str, Any]] = []

        provider = request_data.provider.lower()
        service = request_data.service.lower()
        data = request_data.data
        account_id = request_data.account_id

        if not data:
            logger.info(f"Nenhum dado fornecido para {provider}/{service}. Análise pulada.")
            return []

        relevant_policies = [
            p for p in self.policies
            if p.get('provider', '').lower() == provider and p.get('service', '').lower() == service
        ]

        if not relevant_policies:
            logger.warning(f"Nenhuma política encontrada para {provider}/{service}. Análise pulada.")
            return []

        logger.info(f"Analisando dados de {provider}/{service} contra {len(relevant_policies)} políticas.")

        for policy in relevant_policies:
            try:
                alerts_from_policy = evaluate_policy(policy=policy, data=data, account_id=account_id)
                if alerts_from_policy:
                    generated_alerts.extend(alerts_from_policy)
            except Exception as e:
                logger.error(f"Erro crítico ao avaliar a política '{policy.get('id')}': {e}", exc_info=True)

        logger.info(f"Análise para {provider}/{service} concluída. {len(generated_alerts)} alertas gerados.")
        return generated_alerts

policy_engine = PolicyEngine()
