import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import List, Dict, Any, Optional
from app.schemas.aws.rds_schemas import RDSInstanceData, RDSTag, RDSVpcSecurityGroupMembership, RDSEndpoint
import logging

logger = logging.getLogger(__name__)

def get_rds_instances(region_name: str, account_id: Optional[str] = None) -> List[RDSInstanceData]:
    """
    Collects data for all RDS DB instances in a specific region.
    """
    try:
        # Se account_id for fornecido, pode-se tentar criar uma sessão específica para essa conta (requer configuração de role)
        # Por enquanto, usaremos as credenciais padrão do ambiente.
        session = boto3.Session(region_name=region_name)
        rds_client = session.client("rds")

        paginator = rds_client.get_paginator('describe_db_instances')
        db_instances_data: List[RDSInstanceData] = []

        for page in paginator.paginate():
            for instance_raw in page.get("DBInstances", []):
                try:
                    # Mapeamento e transformação de dados
                    tags = [RDSTag(**tag) for tag in instance_raw.get("TagList", [])]

                    vpc_sgs = []
                    if instance_raw.get("VpcSecurityGroups"):
                        vpc_sgs = [RDSVpcSecurityGroupMembership(**sg) for sg in instance_raw.get("VpcSecurityGroups")]

                    endpoint_data = instance_raw.get("Endpoint")
                    endpoint_obj = RDSEndpoint(**endpoint_data) if endpoint_data else None

                    # Garantir que campos booleanos tenham valores default se ausentes
                    multi_az = instance_raw.get("MultiAZ", False)
                    publicly_accessible = instance_raw.get("PubliclyAccessible", False)
                    storage_encrypted = instance_raw.get("StorageEncrypted", False)
                    iam_db_auth_enabled = instance_raw.get("IAMDatabaseAuthenticationEnabled", False)
                    perf_insights_enabled = instance_raw.get("PerformanceInsightsEnabled", False)
                    copy_tags_to_snapshot = instance_raw.get("CopyTagsToSnapshot", False) # Pode ser None
                    deletion_protection = instance_raw.get("DeletionProtection", False) # Pode ser None

                    instance_data = RDSInstanceData(
                        DBInstanceIdentifier=instance_raw.get("DBInstanceIdentifier"),
                        DBInstanceArn=instance_raw.get("DBInstanceArn"),
                        DBInstanceClass=instance_raw.get("DBInstanceClass"),
                        Engine=instance_raw.get("Engine"),
                        DBInstanceStatus=instance_raw.get("DBInstanceStatus"),
                        MasterUsername=instance_raw.get("MasterUsername"),
                        Endpoint=endpoint_obj,
                        AllocatedStorage=instance_raw.get("AllocatedStorage", 0),
                        InstanceCreateTime=instance_raw.get("InstanceCreateTime"),
                        PreferredBackupWindow=instance_raw.get("PreferredBackupWindow"),
                        BackupRetentionPeriod=instance_raw.get("BackupRetentionPeriod", 0),
                        DBSecurityGroups=[sg.get("DBSecurityGroupName") for sg in instance_raw.get("DBSecurityGroups", []) if sg.get("DBSecurityGroupName")],
                        VpcSecurityGroups=vpc_sgs,
                        DBParameterGroups=[
                            {"DBParameterGroupName": pg.get("DBParameterGroupName"), "ParameterApplyStatus": pg.get("ParameterApplyStatus")}
                            for pg in instance_raw.get("DBParameterGroups", [])
                        ],
                        AvailabilityZone=instance_raw.get("AvailabilityZone"),
                        DBSubnetGroup=instance_raw.get("DBSubnetGroup"), # Pode ser um dict complexo
                        PreferredMaintenanceWindow=instance_raw.get("PreferredMaintenanceWindow"),
                        PendingModifiedValues=instance_raw.get("PendingModifiedValues"), # Dict complexo
                        LatestRestorableTime=instance_raw.get("LatestRestorableTime"),
                        MultiAZ=multi_az,
                        EngineVersion=instance_raw.get("EngineVersion"),
                        AutoMinorVersionUpgrade=instance_raw.get("AutoMinorVersionUpgrade", False),
                        ReadReplicaSourceDBInstanceIdentifier=instance_raw.get("ReadReplicaSourceDBInstanceIdentifier"),
                        ReadReplicaDBInstanceIdentifiers=instance_raw.get("ReadReplicaDBInstanceIdentifiers", []),
                        LicenseModel=instance_raw.get("LicenseModel"),
                        OptionGroupMemberships=instance_raw.get("OptionGroupMemberships", []), # Lista de dicts complexos
                        PubliclyAccessible=publicly_accessible,
                        StorageType=instance_raw.get("StorageType"),
                        DbInstancePort=instance_raw.get("DbInstancePort", 0), # Checar se Endpoint.Port é preferível
                        StorageEncrypted=storage_encrypted,
                        KmsKeyId=instance_raw.get("KmsKeyId"),
                        DbiResourceId=instance_raw.get("DbiResourceId"),
                        CACertificateIdentifier=instance_raw.get("CACertificateIdentifier"),
                        DomainMemberships=instance_raw.get("DomainMemberships", []), # Lista de dicts complexos
                        CopyTagsToSnapshot=copy_tags_to_snapshot, # Pode ser None, Pydantic lidará
                        MonitoringInterval=instance_raw.get("MonitoringInterval"), # Pode ser None
                        MonitoringRoleArn=instance_raw.get("MonitoringRoleArn"), # Pode ser None
                        PromotionTier=instance_raw.get("PromotionTier"), # Pode ser None
                        IAMDatabaseAuthenticationEnabled=iam_db_auth_enabled,
                        PerformanceInsightsEnabled=perf_insights_enabled,
                        PerformanceInsightsKMSKeyId=instance_raw.get("PerformanceInsightsKMSKeyId"), # Pode ser None
                        PerformanceInsightsRetentionPeriod=instance_raw.get("PerformanceInsightsRetentionPeriod"), # Pode ser None
                        EnabledCloudwatchLogsExports=instance_raw.get("EnabledCloudwatchLogsExports", []),
                        DeletionProtection=deletion_protection, # Pode ser None
                        TagList=tags,
                        region=region_name,
                    )
                    db_instances_data.append(instance_data)
                except Exception as e:
                    logger.error(f"Error processing RDS instance {instance_raw.get('DBInstanceIdentifier', 'UNKNOWN')}: {e}", exc_info=True)
                    # Continue to process other instances

        return db_instances_data

    except (NoCredentialsError, PartialCredentialsError):
        logger.error(f"AWS credentials not found or incomplete for region {region_name}.")
        # Re-raise or handle as per application's error handling strategy
        raise HTTPException(status_code=403, detail=f"AWS credentials not found or incomplete for region {region_name}.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'AccessDenied':
            logger.error(f"Access Denied when trying to describe RDS instances in region {region_name}. Check IAM permissions.")
            raise HTTPException(status_code=403, detail=f"Access Denied for RDS in region {region_name}. Check IAM permissions.")
        else:
            logger.error(f"AWS ClientError collecting RDS data in region {region_name}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"AWS ClientError for RDS in region {region_name}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error collecting RDS data in region {region_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error for RDS in region {region_name}: {str(e)}")

# Adicionar HTTPException se não estiver já importado
from fastapi import HTTPException
