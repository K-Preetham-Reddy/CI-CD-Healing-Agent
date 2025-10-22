import logging
from settings import settings

def logging_data():
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/app.log",mode='a')
        ]
    )
    logging.info("Logging is configured successfully.")