import logging
from typing import List, Dict, Any
from app.schemas.input_data_schema import AnalysisRequest
from app.engine.policy_loader import loaded_policies
from app.engine.generic_policy_evaluator import evaluate_resource

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self):
        """
        Inicializa o motor de políticas.
        As políticas já são carregadas na memória pelo módulo policy_loader.
        """
        self.policies = loaded_policies
        logger.info(f"Motor de Políticas inicializado com {len(self.policies)} políticas carregadas.")

    async def analyze(self, request_data: AnalysisRequest) -> List[Dict[str, Any]]:
        """
        Ponto de entrada principal para analisar os dados de recursos da nuvem de forma genérica.
        Filtra as políticas relevantes e avalia cada recurso contra elas.
        """
        generated_alerts: List[Dict[str, Any]] = []

        provider = request_data.provider.lower()
        # O 'service' na requisição agora mapeia para 'resource_type' nas políticas.
        # Ex: service 's3' -> resource_type 'bucket'
        # Precisamos de um mapeamento ou convenção. Por enquanto, vamos assumir que o 'service'
        # da requisição pode ser usado para encontrar o 'resource_type' relevante.
        # Vamos simplificar e usar 'service' para filtrar.
        service = request_data.service.lower()
        data = request_data.data
        account_id = request_data.account_id

        if not data:
            logger.info(f"Nenhum dado fornecido para {provider}/{service}. Análise pulada.")
            return []

        # Filtra as políticas que se aplicam ao provedor e serviço da requisição.
        # Esta lógica pode ser aprimorada para mapear 'service' para 'resource_type'.
        relevant_policies = [
            p for p in self.policies
            if p.get('provider', '').lower() == provider and p.get('service', '').lower() == service
        ]

        if not relevant_policies:
            logger.warning(f"Nenhuma política encontrada para {provider}/{service}. Análise pulada.")
            return []

        logger.info(f"Analisando {len(data)} recursos de {provider}/{service} contra {len(relevant_policies)} políticas.")

        # Itera sobre cada recurso enviado nos dados da requisição
        for resource_item in data:
            if not isinstance(resource_item, dict):
                try:
                    # Tenta converter objetos Pydantic para dicts
                    resource_dict = resource_item.model_dump(exclude_none=True)
                except AttributeError:
                    logger.error(f"Item de dado não é um dicionário e não pôde ser convertido: {resource_item}")
                    continue
            else:
                resource_dict = resource_item

            # Adiciona o account_id ao recurso para que o avaliador possa usá-lo.
            resource_dict['account_id'] = account_id

            # Para cada recurso, avalia contra todas as políticas relevantes
            for policy in relevant_policies:
                try:
                    alert_data = evaluate_resource(resource=resource_dict, policy=policy)
                    if alert_data:
                        generated_alerts.append(alert_data)
                except Exception as e:
                    logger.error(f"Erro crítico ao avaliar a política '{policy.get('id')}' para o recurso '{resource_dict.get('id')}': {e}", exc_info=True)

        logger.info(f"Análise para {provider}/{service} concluída. {len(generated_alerts)} alertas gerados.")
        return generated_alerts

# Instância global do motor
policy_engine = PolicyEngine()
