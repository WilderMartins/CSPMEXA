import boto3
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.schemas.ec2 import Ec2InstanceData, SecurityGroup, InstanceState # Adicionar outros schemas se necessário
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Cache de clientes EC2 por região
ec2_clients_cache = {}

def get_ec2_client(region_name: str):
    if region_name not in ec2_clients_cache:
        try:
            ec2_clients_cache[region_name] = boto3.client("ec2", region_name=region_name)
        except (NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"AWS credentials not found or incomplete for EC2 in region {region_name}: {e}")
            raise HTTPException(status_code=500, detail=f"AWS credentials not configured for EC2 in {region_name}.") from e
        except Exception as e:
            logger.error(f"Error creating EC2 client for region {region_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating EC2 client for {region_name}: {str(e)}") from e
    return ec2_clients_cache[region_name]

async def get_all_regions() -> List[str]:
    """Obtém todas as regiões AWS disponíveis e habilitadas para a conta."""
    try:
        # Um cliente EC2 de qualquer região (ou o default) pode chamar describe_regions
        # Usar a região padrão definida nas configurações.
        client = get_ec2_client(settings.AWS_REGION_NAME)
        response = client.describe_regions(AllRegions=False) # AllRegions=False para apenas as habilitadas
        return [region["RegionName"] for region in response["Regions"]]
    except (NoCredentialsError, PartialCredentialsError):
        logger.error("AWS credentials not found or incomplete when describing regions.")
        raise HTTPException(status_code=500, detail="AWS credentials not configured for describe_regions.")
    except ClientError as e:
        logger.error(f"ClientError describing regions: {e.response['Error']['Message']}")
        raise HTTPException(status_code=500, detail=f"ClientError describing regions: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Unexpected error describing regions: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while describing regions: {str(e)}")


async def describe_ec2_instances(region_name: str) -> List[Ec2InstanceData]:
    """
    Descreve todas as instâncias EC2 em uma região específica.
    """
    ec2_client = get_ec2_client(region_name)
    instances_data: List[Ec2InstanceData] = []

    try:
        paginator = ec2_client.get_paginator('describe_instances')
        for page in paginator.paginate(Filters=[{'Name': 'instance-state-name', 'Values': ['pending', 'running', 'shutting-down', 'stopping', 'stopped']}]):
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    try:
                        iam_profile_arn = instance.get("IamInstanceProfile", {}).get("Arn")

                        # Processar security groups para extrair IDs e nomes
                        sg_simple = []
                        if instance.get("SecurityGroups"):
                            for sg in instance["SecurityGroups"]:
                                sg_simple.append({"GroupId": sg.get("GroupId"), "GroupName": sg.get("GroupName")})

                        instance_obj = Ec2InstanceData(
                            instance_id=instance["InstanceId"],
                            instance_type=instance.get("InstanceType"),
                            image_id=instance.get("ImageId"),
                            launch_time=instance.get("LaunchTime"),
                            platform=instance.get("PlatformDetails"), # PlatformDetails é mais informativo
                            private_dns_name=instance.get("PrivateDnsName"),
                            private_ip_address=instance.get("PrivateIpAddress"),
                            public_dns_name=instance.get("PublicDnsName"),
                            public_ip_address=instance.get("PublicIpAddress"),
                            state=InstanceState(**instance.get("State", {})),
                            subnet_id=instance.get("SubnetId"),
                            vpc_id=instance.get("VpcId"),
                            architecture=instance.get("Architecture"),
                            iam_instance_profile_arn=iam_profile_arn,
                            security_groups=sg_simple,
                            tags=instance.get("Tags", []),
                            region=region_name
                        )
                        instances_data.append(instance_obj)
                    except Exception as e_inst: # Erro ao processar uma instância individual
                        logger.error(f"Error processing instance {instance.get('InstanceId')} in region {region_name}: {e_inst}")
                        instances_data.append(Ec2InstanceData(
                            instance_id=instance.get("InstanceId", "UNKNOWN"),
                            region=region_name,
                            error_details=f"Failed to process instance details: {str(e_inst)}"
                        ))

    except ClientError as e:
        logger.error(f"ClientError describing EC2 instances in region {region_name}: {e.response['Error']['Message']}")
        # Retorna uma lista com um item de erro para esta região específica
        return [Ec2InstanceData(instance_id="ERROR_REGION", region=region_name, error_details=f"ClientError: {e.response['Error']['Message']}")]
    except Exception as e_region: # Outras exceções ao descrever instâncias na região
        logger.error(f"Unexpected error describing EC2 instances in region {region_name}: {e_region}")
        return [Ec2InstanceData(instance_id="ERROR_REGION", region=region_name, error_details=f"Unexpected error: {str(e_region)}")]

    return instances_data

async def describe_security_groups(region_name: str) -> List[SecurityGroup]:
    """
    Descreve todos os Security Groups em uma região específica.
    """
    ec2_client = get_ec2_client(region_name)
    sg_data: List[SecurityGroup] = []

    try:
        paginator = ec2_client.get_paginator('describe_security_groups')
        for page in paginator.paginate():
            for sg in page.get("SecurityGroups", []):
                try:
                    # O schema SecurityGroup usa populate_by_name=True, então podemos passar o dict diretamente
                    # No entanto, IpPermissions e IpPermissionsEgress podem precisar de tratamento se não existirem
                    sg_obj = SecurityGroup(
                        GroupId=sg["GroupId"],
                        GroupName=sg.get("GroupName"),
                        Description=sg.get("Description"),
                        VpcId=sg.get("VpcId"),
                        OwnerId=sg.get("OwnerId"),
                        IpPermissions=sg.get("IpPermissions", []),
                        IpPermissionsEgress=sg.get("IpPermissionsEgress", []),
                        Tags=sg.get("Tags", []),
                        region=region_name # Adicionando a região ao objeto SG
                    )
                    sg_data.append(sg_obj)
                except Exception as e_sg: # Erro ao processar um SG individual
                    logger.error(f"Error processing security group {sg.get('GroupId')} in region {region_name}: {e_sg}")
                    # Adicionar um placeholder ou log, dependendo da estratégia de erro
                    # Por simplicidade, vamos pular SGs com erro de parsing, mas logar.
    except ClientError as e:
        logger.error(f"ClientError describing Security Groups in region {region_name}: {e.response['Error']['Message']}")
        # Levantar exceção para ser tratada no endpoint, ou retornar uma lista com erro
        raise HTTPException(status_code=500, detail=f"ClientError in {region_name} for Security Groups: {e.response['Error']['Message']}") from e
    except Exception as e_region:
        logger.error(f"Unexpected error describing Security Groups in region {region_name}: {e_region}")
        raise HTTPException(status_code=500, detail=f"Unexpected error in {region_name} for Security Groups: {str(e_region)}") from e

    return sg_data


async def get_ec2_instance_data_all_regions() -> List[Ec2InstanceData]:
    """Coleta dados de instâncias EC2 de todas as regiões habilitadas."""
    all_instances: List[Ec2InstanceData] = []
    regions = await get_all_regions() # Pode levantar HTTPException

    for region in regions:
        logger.info(f"Fetching EC2 instance data for region: {region}...")
        instances_in_region = await describe_ec2_instances(region)
        all_instances.extend(instances_in_region)
    return all_instances

async def get_security_group_data_all_regions() -> List[SecurityGroup]:
    """Coleta dados de Security Groups de todas as regiões habilitadas."""
    all_sgs: List[SecurityGroup] = []
    regions = await get_all_regions() # Pode levantar HTTPException

    for region in regions:
        logger.info(f"Fetching EC2 Security Group data for region: {region}...")
        try:
            sgs_in_region = await describe_security_groups(region) # Pode levantar HTTPException
            all_sgs.extend(sgs_in_region)
        except HTTPException as e:
            # Se uma região falhar, podemos decidir continuar e coletar de outras,
            # ou falhar tudo. Por enquanto, vamos logar e continuar,
            # mas o erro já foi logado em describe_security_groups.
            # Poderíamos adicionar um objeto de erro à lista all_sgs aqui se quiséssemos
            # notificar o chamador sobre falhas parciais de forma estruturada.
            logger.error(f"Failed to get Security Groups from region {region}: {e.detail}")
            # Exemplo de como adicionar um erro:
            # all_sgs.append(SecurityGroup(GroupId=f"ERROR_{region}", ErrorDetails=e.detail))
            # Mas o schema SecurityGroup não tem ErrorDetails. Ajustar se necessário.
            # Por ora, a falha em uma região (se não for credencial) não impede outras.
            pass # A exceção já foi loggada.
    return all_sgs
