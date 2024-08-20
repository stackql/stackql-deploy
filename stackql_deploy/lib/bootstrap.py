import logging

# Set up logging at the root level
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("stackql-deploy")