# PII Block Policy

## Overview
The PII Block Policy prevents accidental exposure of personally identifiable information (PII) by blocking memory write operations that contain sensitive personal data. This policy is critical for regulatory compliance and data protection.

## Purpose
- Prevent PII data exposure in system memory
- Maintain GDPR, CCPA, and HIPAA compliance
- Protect individual privacy rights
- Block unauthorized data collection

## Trigger Conditions
- Action Type: Memory write operation
- Content Assessment: PII detected

## PII Categories Detected
- Names and email addresses
- Social Security Numbers and tax IDs
- Financial account information
- Health records and medical information
- Biometric data
- Location history
- Phone numbers and addresses
- Government-issued identifiers

## Action
- **Type**: DENY
- **Effect**: Operation is blocked and rejected
- **Logging**: ERROR level, detailed logging
- **Human Alert**: Required - notify security team
- **Message**: Explicit PII detection with operation rejection

## Scope
- **Level**: AGENT
- **Application**: All memory write operations
- **Enforcement**: Pre-execution validation

## Compliance Standards
- **GDPR**: Article 4 - Personal Data protection
- **CCPA**: Consumer Privacy Rights
- **HIPAA**: Protected Health Information (PHI)

## Implementation
The policy uses pattern matching and content analysis to detect PII in write operations. Detection occurs before data is persisted to prevent exposure.

## Exception Handling
PII handling requires:
1. Explicit authorization from compliance officer
2. Data minimization practices
3. Anonymization techniques
4. Encryption of PII fields
5. Audit trail documentation

## Related Policies
- `maya.audit_all_actions` - Data handling audit trail
- Security incident response procedures
