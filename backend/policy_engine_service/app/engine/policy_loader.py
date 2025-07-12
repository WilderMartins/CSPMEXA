import os
import yaml
from typing import List, Dict, Any
from functools import lru_cache

# Caminho para o diretório onde as políticas YAML estão armazenadas.
POLICIES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'policies')

@lru_cache()
def load_policies() -> List[Dict[str, Any]]:
    """
    Carrega todas as políticas de arquivos .yml do diretório de políticas.

    Percorre o diretório POLICIES_DIR, lê cada arquivo .yml,
    faz o parsing do seu conteúdo e retorna uma lista de políticas.

    Returns:
        Uma lista de dicionários, onde cada dicionário representa uma política.
    """
    if not os.path.exists(POLICIES_DIR):
        print(f"AVISO: Diretório de políticas '{POLICIES_DIR}' não encontrado.")
        return []

    all_policies = []
    print(f"Carregando políticas de: {POLICIES_DIR}")

    for filename in os.listdir(POLICIES_DIR):
        if filename.endswith(('.yml', '.yaml')):
            filepath = os.path.join(POLICIES_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    policy_data = yaml.safe_load(f)
                    if policy_data and 'id' in policy_data:
                        # Adiciona o nome do arquivo de origem para referência, se necessário
                        policy_data['source_file'] = filename
                        all_policies.append(policy_data)
                        print(f"  - Política '{policy_data['id']}' carregada de '{filename}'")
                    else:
                        print(f"AVISO: Arquivo de política inválido ou sem 'id': {filename}")
            except yaml.YAMLError as e:
                print(f"ERRO: Falha ao fazer o parsing do arquivo YAML '{filename}': {e}")
            except Exception as e:
                print(f"ERRO: Falha ao ler o arquivo de política '{filename}': {e}")

    print(f"Total de {len(all_policies)} políticas carregadas.")
    return all_policies

# Para permitir o acesso fácil às políticas carregadas em toda a aplicação
loaded_policies = load_policies()
