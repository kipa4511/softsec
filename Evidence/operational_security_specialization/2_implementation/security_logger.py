import logging
import os
from datetime import datetime
from flask import request

class SecurityLogger:
    def __init__(self):
        # Create logs directory
        log_dir = '/app/logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Setup logging
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)

        # File handler
        fh = logging.FileHandler('/app/logs/security.log')
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def log_event(self, event_type, user_info, details, success=True):
        """Enhanced logging with structured data"""
        status = "SUCCESS" if success else "FAILED"
        ip = getattr(request, 'remote_addr', 'unknown')

        message = f"{event_type} | User:{user_info} | IP:{ip} | {details} | Status:{status}"

        if not success:
            self.logger.warning(f"SECURITY_ALERT - {message}")
        else:
            self.logger.info(message)

# Global instance
security_logger = SecurityLogger()

# Explicit functions
def log_success(message):
    security_logger.log_event("SUCCESS", "system", message, True)

def log_failure(message):
    security_logger.log_event("FAILURE", "system", message, False)

def log_event(message):
    # Simple auto-detection as fallback
    if any(word in message.upper() for word in [' FAILED', ' ERROR', ' UNAUTHORIZED']):
        log_failure(message)
    else:
        log_success(message)
