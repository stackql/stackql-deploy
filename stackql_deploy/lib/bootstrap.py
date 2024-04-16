import logging
from pystackql import StackQL

# Set up logging at the root level
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("stackql-deploy")

# Create a StackQL instance
stackql = StackQL(download_dir="/mnt/c/LocalGitRepos/stackql/stackql-deploy")
