import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """
    Configura o logging estruturado em JSON para a aplicação.
    """
    log_level_str = "INFO"
    try:
        log_level = getattr(logging, log_level_str.upper())
    except AttributeError:
        log_level = logging.INFO

    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remover handlers existentes para evitar duplicação de logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Adicionar um handler para logar em JSON no stdout
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(service)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
    )
    logHandler.setFormatter(formatter)

    # Adicionar um filtro para injetar o nome do serviço
    class ServiceNameFilter(logging.Filter):
        def filter(self, record):
            record.service = "collector_service"
            return True

    logger.addFilter(ServiceNameFilter())
    logger.addHandler(logHandler)

    logging.info("Logging configurado para formato JSON.")
