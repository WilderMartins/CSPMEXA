from typing import List, Dict, Any, Optional
from app.schemas.aws.rds_input_schema import RDSInstanceDataInput
from app.schemas.alert_schema import AlertSeverityEnum # Para usar o enum de severidade

def evaluate_rds_policies(
    rds_instances_data: List[RDSInstanceDataInput],
    account_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Avalia todas as políticas RDS para uma lista de instâncias RDS.
    Retorna uma lista de dicionários, cada um representando dados para AlertCreate.
    """
    alerts_data: List[Dict[str, Any]] = []

    for instance in rds_instances_data:
        alerts_data.extend(check_rds_instance_publicly_accessible(instance, account_id))
        alerts_data.extend(check_rds_instance_storage_not_encrypted(instance, account_id))
        alerts_data.extend(check_rds_instance_backup_disabled_or_low_retention(instance, account_id))
        # alerts_data.extend(check_rds_instance_multi_az_disabled(instance, account_id)) # Opcional
        # Adicionar chamadas para outras políticas RDS aqui

    return alerts_data

def check_rds_instance_publicly_accessible(
    instance: RDSInstanceDataInput,
    account_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Verifica se uma instância RDS está publicamente acessível.
    Policy ID: RDS_Instance_Publicly_Accessible
    """
    alerts_data: List[Dict[str, Any]] = []
    if instance.PubliclyAccessible:
        alerts_data.append({
            "resource_id": instance.DBInstanceIdentifier,
            "resource_type": "AWS::RDS::DBInstance",
            "provider": "aws",
            "severity": AlertSeverityEnum.CRITICAL,
            "title": "RDS Instance is Publicly Accessible",
            "description": f"RDS instance '{instance.DBInstanceIdentifier}' in account '{account_id or 'N/A'}' region '{instance.region}' is publicly accessible. This can expose the database to unauthorized access from the internet.",
            "policy_id": "RDS_Instance_Publicly_Accessible",
            "account_id": account_id,
            "region": instance.region,
            "details": {
                "DBInstanceIdentifier": instance.DBInstanceIdentifier,
                "DBInstanceArn": instance.DBInstanceArn,
                "Engine": instance.Engine,
                "EndpointAddress": instance.Endpoint.Address if instance.Endpoint else "N/A",
                "PubliclyAccessible": instance.PubliclyAccessible,
            },
            "recommendation": "Review the need for public accessibility. If not required, set 'PubliclyAccessible' to false. Ensure that VPC security groups and network ACLs restrict access to only authorized sources."
        })
    return alerts_data

def check_rds_instance_storage_not_encrypted(
    instance: RDSInstanceDataInput,
    account_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    Verifica se o armazenamento de uma instância RDS não está criptografado.
    Policy ID: RDS_Instance_Storage_Not_Encrypted
    """
    alerts_data: List[Dict[str, Any]] = []
    if not instance.StorageEncrypted:
        alerts_data.append({
            "resource_id": instance.DBInstanceIdentifier,
            "resource_type": "AWS::RDS::DBInstance",
            "provider": "aws",
            "severity": AlertSeverityEnum.HIGH,
            "title": "RDS Instance Storage Not Encrypted",
            "description": f"RDS instance '{instance.DBInstanceIdentifier}' in account '{account_id or 'N/A'}' region '{instance.region}' does not have storage encryption enabled. This can expose data at rest if underlying storage is compromised.",
            "policy_id": "RDS_Instance_Storage_Not_Encrypted",
            "account_id": account_id,
            "region": instance.region,
            "details": {
                "DBInstanceIdentifier": instance.DBInstanceIdentifier,
                "DBInstanceArn": instance.DBInstanceArn,
                "StorageEncrypted": instance.StorageEncrypted,
                "KmsKeyId": instance.KmsKeyId
            },
            "recommendation": "Enable storage encryption for the RDS instance. For existing instances, this typically involves creating a snapshot, copying the snapshot with encryption enabled, and then restoring a new instance from the encrypted snapshot."
        })
    return alerts_data

def check_rds_instance_backup_disabled_or_low_retention(
    instance: RDSInstanceDataInput,
    account_id: Optional[str],
    min_retention_days: int = 7 # Limite mínimo de retenção aceitável
) -> List[Dict[str, Any]]:
    """
    Verifica se os backups automáticos de uma instância RDS estão desabilitados ou têm um período de retenção baixo.
    Policy ID: RDS_Instance_Backup_Disabled_Or_Low_Retention
    """
    alerts_data: List[Dict[str, Any]] = []
    if instance.BackupRetentionPeriod == 0:
        alerts_data.append({
            "resource_id": instance.DBInstanceIdentifier,
            "resource_type": "AWS::RDS::DBInstance",
            "provider": "aws",
            "severity": AlertSeverityEnum.HIGH,
            "title": "RDS Instance Automated Backups Disabled",
            "description": f"Automated backups are disabled for RDS instance '{instance.DBInstanceIdentifier}' (BackupRetentionPeriod is 0) in account '{account_id or 'N/A'}' region '{instance.region}'. This increases the risk of data loss.",
            "policy_id": "RDS_Instance_Backup_Disabled", # Sub-ID específico
            "account_id": account_id,
            "region": instance.region,
            "details": {
                "DBInstanceIdentifier": instance.DBInstanceIdentifier,
                "BackupRetentionPeriod": instance.BackupRetentionPeriod
            },
            "recommendation": f"Enable automated backups for the RDS instance by setting a BackupRetentionPeriod greater than 0 (e.g., at least {min_retention_days} days)."
        })
    elif instance.BackupRetentionPeriod < min_retention_days:
        alerts_data.append({
            "resource_id": instance.DBInstanceIdentifier,
            "resource_type": "AWS::RDS::DBInstance",
            "provider": "aws",
            "severity": AlertSeverityEnum.MEDIUM,
            "title": "RDS Instance Low Backup Retention Period",
            "description": f"Automated backup retention period for RDS instance '{instance.DBInstanceIdentifier}' is {instance.BackupRetentionPeriod} days, which is less than the recommended minimum of {min_retention_days} days, in account '{account_id or 'N/A'}' region '{instance.region}'.",
            "policy_id": "RDS_Instance_Low_Backup_Retention", # Sub-ID específico
            "account_id": account_id,
            "region": instance.region,
            "details": {
                "DBInstanceIdentifier": instance.DBInstanceIdentifier,
                "BackupRetentionPeriod": instance.BackupRetentionPeriod,
                "RecommendedMinRetention": min_retention_days
            },
            "recommendation": f"Increase the automated backup retention period for the RDS instance to at least {min_retention_days} days."
        })
    return alerts_data

def check_rds_instance_multi_az_disabled(
    instance: RDSInstanceDataInput,
    account_id: Optional[str]
) -> List[Dict[str, Any]]:
    """
    (Opcional) Verifica se Multi-AZ está desabilitado para uma instância RDS.
    Policy ID: RDS_Instance_Multi_AZ_Disabled
    """
    alerts_data: List[Dict[str, Any]] = []
    # Considerar apenas instâncias que não sejam réplicas de leitura, pois MultiAZ para réplicas é diferente.
    if not instance.ReadReplicaSourceDBInstanceIdentifier and not instance.MultiAZ:
        alerts_data.append({
            "resource_id": instance.DBInstanceIdentifier,
            "resource_type": "AWS::RDS::DBInstance",
            "provider": "aws",
            "severity": AlertSeverityEnum.MEDIUM, # Ou Low, dependendo dos requisitos de HA
            "title": "RDS Instance Multi-AZ Disabled",
            "description": f"Multi-AZ is disabled for the primary RDS instance '{instance.DBInstanceIdentifier}' in account '{account_id or 'N/A'}' region '{instance.region}'. This reduces high availability and resilience to AZ failures.",
            "policy_id": "RDS_Instance_Multi_AZ_Disabled",
            "account_id": account_id,
            "region": instance.region,
            "details": {
                "DBInstanceIdentifier": instance.DBInstanceIdentifier,
                "MultiAZ": instance.MultiAZ
            },
            "recommendation": "Enable Multi-AZ for the RDS instance to improve availability and data durability during AZ outages or maintenance."
        })
    return alerts_data

# Adicionar mais funções de política RDS aqui conforme necessário.
# Exemplo:
# - Verificar versões de engine desatualizadas (RDS_Instance_Outdated_Engine_Version)
# - Verificar se exclusão acidental está desabilitada (RDS_Instance_Deletion_Protection_Disabled)
# - Verificar se IAM Database Authentication está desabilitada (RDS_Instance_IAM_Auth_Disabled)
# - Verificar se Performance Insights está desabilitado (RDS_Instance_Performance_Insights_Disabled)
# - Verificar se logs específicos não estão sendo exportados para CloudWatch (RDS_Instance_Log_Exports_Disabled)
# - Verificar se o CA Certificate está desatualizado (RDS_Instance_Outdated_CA_Certificate)
# - Verificar se Auto Minor Version Upgrade está desabilitado (RDS_Instance_Auto_Minor_Upgrade_Disabled)
#   (Pode ser intencional, então a severidade deve ser baixa ou informativa)
```
