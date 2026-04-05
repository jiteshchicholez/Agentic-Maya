# External Call Gate Policy

## Overview
The External Call Gate Policy enforces strict authorization requirements for all external API calls and communications. This policy prevents unauthorized information leakage and ensures controlled integration with external systems.

## Purpose
- Control external network communications
- Prevent unauthorized data exfiltration
- Enforce zero-trust network access
- Maintain network security boundaries
- Audit external dependencies

## Trigger Conditions
- Action Type: External API call
- Approval Status: Not explicitly authorized

## Approved External Endpoints
External calls are permitted only to:
1. Explicitly whitelisted API endpoints
2. Services with active approval tokens
3. Connections including required authentication
4. Endpoints matching organizational security policies

## Action
- **Type**: DENY
- **Effect**: External call is blocked
- **Logging**: WARN level
- **Human Alert**: Required - notify security ops
- **Message**: Authorization requirement notification

## Scope
- **Level**: AGENT
- **Application**: All external communications
- **Enforcement**: Pre-execution blocking

## Authorization Process
To call external endpoints:
1. Submit API endpoint for security review
2. Provide business justification
3. Document data sensitivity level
4. Obtain approval from security officer
5. Receive authorization token and credentials
6. Update agent permissions configuration

## Suppported Categories
- **Approved**: OAuth-protected SaaS platforms, vendor APIs with signed agreements
- **Conditional**: Internal services with VPN/mTLS, monitoring systems
- **Blocked**: Unverified endpoints, proxy services, personal cloud accounts

## Integration Examples
✓ GitHub API (approved for CI/CD)
✓ Slack API (approved for notifications)
✓ OpenAI API (approved for LLM calls)
✗ Arbitrary HTTP endpoints
✗ Third-party logging services without review

## Related Policies
- `myna.no_external_without_permission` - Global external call restriction
- `myna.audit_all_actions` - Complete audit trail
