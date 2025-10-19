# Attack Evidence Documentation

## Detected Security Incidents

### Incident 1: Sustained Brute Force Attack
- **Time Period**: 16:28:19 - 16:56:09 (28-minute campaign)
- **Attacker IP**: 172.18.0.1
- **Total Failed Logins**: 9 attempts
- **Targeted Accounts**: 
  - test2@test.com (4 attempts)
  - victim1@test.com through victim6@test.com (6 sequential attempts)
- **Pattern**: Systematic credential guessing across multiple accounts

### Incident 2: User Enumeration via Registration
- **Time**: Multiple attempts at 16:28:25, 16:50:42, 16:56:14
- **IP**: 172.18.0.1
- **Technique**: Repeated registration attempts for test2@test.com
- **Purpose**: Confirm existence of valid user accounts
- **Detection**: Multiple "Duplicate registration" errors

## Attack Timeline Analysis

### Phase 1: Initial Reconnaissance (16:28-16:51)
- Tested credentials for test2@test.com account
- Attempted user enumeration via registration
- Established attack pattern from consistent IP

### Phase 2: Expanded Targeting (16:56:03-16:56:09)
- Rapid sequential attacks on 6 new victim accounts
- 6 failed login attempts in 6 seconds
- Systematic username pattern (victim1 through victim6)

### Phase 3: Continued Enumeration (16:56:14)
- Final registration attempt to confirm user existence
- Consistent attack methodology throughout

## Security System Performance Metrics

### Detection Effectiveness
- ✅ 100% of attack attempts logged
- ✅ Real-time monitoring detected 9 failed logins
- ✅ IP address consistently tracked (172.18.0.1)
- ✅ Attack patterns correctly identified

### Forensic Capability
- ✅ Complete timeline reconstruction
- ✅ Detailed account targeting information
- ✅ Success/failure status accurately recorded
- ✅ Comprehensive audit trail maintained

## Impact Assessment
- **Systems Affected**: Authentication system only
- **Data Compromised**: None
- **Service Availability**: 100% maintained
- **User Accounts**: No successful compromises
- **Attack Success Rate**: 0% (all attacks blocked)

## Attack Sophistication Analysis
- **Skill Level**: Intermediate (systematic approach)
- **Persistence**: High (28-minute campaign)
- **Stealth**: Low (no attempt to hide source IP)
- **Success**: None (completely thwarted by security controls)
