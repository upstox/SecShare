import logging

# Configure logging 
logging.basicConfig(
    level=logging.INFO,  # Change this to INFO or ERROR in production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Create a global logger
logger = logging.getLogger('secshare')
logger.debug('Logger initialized in utils/logger.py')
