import networkx as nx
from sqlalchemy.orm import Session
from app.crud.crud_asset import asset_crud
from app.crud.crud_attack_path import attack_path_crud
from app.schemas.attack_path_schema import AttackPathCreate, AttackPathNode
import logging
import json

logger = logging.getLogger(__name__)

class GraphAnalysisService:
    def __init__(self, db: Session):
        self.db = db
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        """Constrói o grafo a partir dos ativos no banco de dados."""
        logger.info("Construindo o grafo de ativos para análise de caminhos de ataque...")
        all_assets = asset_crud.get_multi(self.db, limit=10000) # Limite para segurança

        for asset in all_assets:
            self.graph.add_node(asset.id, data=asset)

        logger.info(f"Grafo construído com {self.graph.number_of_nodes()} nós.")

    def find_public_ec2_to_admin_role_path(self):
        """
        Encontra o caminho de ataque: Instância EC2 pública com uma role de admin.
        """
        logger.info("Iniciando análise: EC2 Pública -> Role de Admin")

        for node_id, node_data in self.graph.nodes(data=True):
            asset = node_data.get('data')
            if not asset or asset.asset_type != 'EC2Instance':
                continue

            config = asset.configuration
            if config.get('public_ip_address'):
                # Instância é pública. Agora, verificar a role.
                iam_profile_arn = config.get('iam_instance_profile_arn')
                if iam_profile_arn:
                    # Precisamos encontrar o nó da role no nosso grafo.
                    # Esta é uma simplificação; uma implementação real usaria relações.
                    # Por agora, vamos assumir que podemos buscar os detalhes da role.
                    # Vamos verificar se a política da role é de admin.
                    # A política da role não está no nó da instância, então esta análise é limitada.
                    # Vamos simular que se o ARN do perfil contiver "admin", é um achado.
                    if "admin" in iam_profile_arn.lower():
                        logger.warning(f"Potencial caminho de ataque encontrado: Instância pública {asset.name} com perfil IAM suspeito: {iam_profile_arn}")

                        nodes = [AttackPathNode(asset_id=asset.id, asset_type=asset.asset_type, name=asset.name or asset.asset_id)]

                        attack_path_in = AttackPathCreate(
                            path_id=f"EC2_PUBLIC_TO_ADMIN_ROLE_{asset.id}",
                            description=f"A instância EC2 pública '{asset.name or asset.asset_id}' está associada a um perfil IAM com nome '{iam_profile_arn}', que pode ter privilégios excessivos.",
                            severity="HIGH",
                            nodes=nodes
                        )
                        # Usar um método create_or_update para não duplicar caminhos
                        attack_path_crud.create(self.db, obj_in=attack_path_in)

def run_attack_path_analysis(db: Session):
    """Função principal para iniciar a análise de caminhos de ataque."""
    try:
        graph_service = GraphAnalysisService(db)
        graph_service.find_public_ec2_to_admin_role_path()
    except Exception as e:
        logger.exception(f"Erro durante a análise de caminhos de ataque: {e}")
