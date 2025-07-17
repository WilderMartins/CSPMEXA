import pytest
from app.engine.aws_iam_policies import check_root_mfa_enabled
from app.engine.aws_cloudtrail_policies import check_cloudtrail_multi_region, check_cloudtrail_log_file_validation

# --- Testes para a política CIS-AWS-1.1 (MFA do Root) ---

def test_check_root_mfa_enabled_fail():
    """Testa o caso em que o MFA do root está desabilitado."""
    # Simula os dados do get_account_summary
    summary_data = {"AccountMFAEnabled": 0}
    # A política espera uma lista de usuários, onde o primeiro contém o sumário
    iam_data = [{"account_summary": summary_data}]

    alerts = check_root_mfa_enabled(iam_data)

    assert len(alerts) == 1
    assert alerts[0]["status"] == "FAIL"
    assert "MFA não está habilitado para o usuário root" in alerts[0]["details"]

def test_check_root_mfa_enabled_pass():
    """Testa o caso em que o MFA do root está habilitado."""
    summary_data = {"AccountMFAEnabled": 1}
    iam_data = [{"account_summary": summary_data}]

    alerts = check_root_mfa_enabled(iam_data)

    assert len(alerts) == 0

# --- Testes para a política CIS-AWS-2.2 (CloudTrail Multi-Região) ---

def test_check_cloudtrail_multi_region_fail():
    """Testa o caso em que não há trails multi-região."""
    cloudtrail_data = [
        {"trail_info": {"is_multi_region_trail": False}},
        {"trail_info": {"is_multi_region_trail": False}},
    ]
    alerts = check_cloudtrail_multi_region(cloudtrail_data)

    assert len(alerts) == 1
    assert "Nenhum trail do CloudTrail multi-região foi encontrado" in alerts[0]["details"]

def test_check_cloudtrail_multi_region_pass():
    """Testa o caso em que há pelo menos um trail multi-região."""
    cloudtrail_data = [
        {"trail_info": {"is_multi_region_trail": False}},
        {"trail_info": {"is_multi_region_trail": True}},
    ]
    alerts = check_cloudtrail_multi_region(cloudtrail_data)

    assert len(alerts) == 0

# --- Testes para a política CIS-AWS-2.3 (Validação de Log do CloudTrail) ---

def test_check_cloudtrail_log_file_validation_fail():
    """Testa o caso em que um trail não tem a validação de log habilitada."""
    cloudtrail_data = [
        {"trail_info": {"name": "Trail-1", "log_file_validation_enabled": True}},
        {"trail_info": {"name": "Trail-2", "log_file_validation_enabled": False}},
    ]
    alerts = check_cloudtrail_log_file_validation(cloudtrail_data)

    assert len(alerts) == 1
    assert alerts[0]["resource_id"] == "Trail-2"
    assert "não está habilitada para o trail 'Trail-2'" in alerts[0]["details"]

def test_check_cloudtrail_log_file_validation_pass():
    """Testa o caso em que todos os trails têm a validação de log habilitada."""
    cloudtrail_data = [
        {"trail_info": {"name": "Trail-1", "log_file_validation_enabled": True}},
        {"trail_info": {"name": "Trail-2", "log_file_validation_enabled": True}},
    ]
    alerts = check_cloudtrail_log_file_validation(cloudtrail_data)

    assert len(alerts) == 0
