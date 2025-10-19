#!/usr/bin/env python3
import time
import subprocess
from datetime import datetime, timedelta

def detailed_security_monitor():
    """Security monitor that shows both counts and details"""
    
    print("Starting Tatou Security Monitor - Detailed Mode...")
    
    while True:
        try:
            current_time = datetime.now()
            print(f"\n=== Security Check at {current_time.strftime('%H:%M:%S')} ===")
            
            # Check for failed logins with details
            check_failed_logins()
            
            # Check for unauthorized access with details
            check_unauthorized_access()
            
            # Check log file size
            check_log_health()
            
            print(f"[{current_time.strftime('%H:%M:%S')}] Monitoring check completed")
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(30)

def check_failed_logins():
    """Check for brute force attempts with details"""
    try:
        # Count failed logins
        result = subprocess.run(
            "grep 'LOGIN FAILED' /app/logs/security.log | tail -20 | wc -l",
            shell=True, capture_output=True, text=True
        )
        failed_count = int(result.stdout.strip())
        
        # Get details of recent failed logins
        result_details = subprocess.run(
            "grep 'LOGIN FAILED' /app/logs/security.log | tail -5",
            shell=True, capture_output=True, text=True
        )
        failed_details = result_details.stdout.strip().split('\n')
        
        if failed_count >= 3:
            print(f"⚠️  SECURITY ALERT: {failed_count} failed logins detected")
            if failed_details and failed_details[0]:
                print("Recent failed logins:")
                for i, detail in enumerate(failed_details[-3:], 1):
                    if detail:
                        # Extract just the important part
                        clean_detail = detail.split('LOGIN FAILED - ')[-1] if 'LOGIN FAILED - ' in detail else detail
                        print(f"  {i}. {clean_detail}")
            
    except Exception as e:
        print(f"Error checking failed logins: {e}")

def check_unauthorized_access():
    """Check for unauthorized access attempts with details"""
    try:
        result = subprocess.run(
            "grep 'UNAUTHORIZED' /app/logs/security.log | tail -10 | wc -l",
            shell=True, capture_output=True, text=True
        )
        unauthorized_count = int(result.stdout.strip())
        
        # Get details of unauthorized access
        result_details = subprocess.run(
            "grep 'UNAUTHORIZED' /app/logs/security.log | tail -3",
            shell=True, capture_output=True, text=True
        )
        unauthorized_details = result_details.stdout.strip().split('\n')
        
        if unauthorized_count > 0:
            print(f"🚨 UNAUTHORIZED ACCESS: {unauthorized_count} attempts detected")
            if unauthorized_details and unauthorized_details[0]:
                print("Recent unauthorized access:")
                for i, detail in enumerate(unauthorized_details, 1):
                    if detail:
                        clean_detail = detail.split('UNAUTHORIZED - ')[-1] if 'UNAUTHORIZED - ' in detail else detail
                        print(f"  {i}. {clean_detail}")
            
    except Exception as e:
        print(f"Error checking unauthorized access: {e}")

def check_log_health():
    """Ensure logging is working"""
    try:
        result = subprocess.run(
            "ls -la /app/logs/security.log | awk '{print $5}'",
            shell=True, capture_output=True, text=True
        )
        file_size = int(result.stdout.strip())
        
        if file_size == 0:
            print("❌ LOGGING ERROR: Security log file is empty")
            
    except Exception as e:
        print(f"Error checking log health: {e}")

if __name__ == "__main__":
    detailed_security_monitor()
