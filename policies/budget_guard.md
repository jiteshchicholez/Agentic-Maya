# Budget Guard Policy

## Overview
The Budget Guard Policy monitors agent-level cost consumption and provides warnings when spending patterns exceed safe thresholds. This policy helps maintain cost predictability and prevent runaway expenses.

## Purpose
- Prevent unexpected cost overruns
- Alert on elevated spending patterns
- Enable proactive budget management
- Maintain cost visibility across agents

## Trigger Conditions
- Action Type: Budget check
- Cost Threshold: $0.50 USD per agent

## Action
- **Type**: WARN
- **Notification**: Logged as WARNING level
- **Human Alert**: Not required
- **Message**: Escalation indicator with optimization guidance

## Scope
- **Level**: AGENT
- **Application**: Per-agent cost monitoring
- **Enforcement**: Real-time during execution

## Implementation
This policy integrates with the agent execution runtime to track cumulative costs. When an individual agent's cost consumption reaches the $0.50 USD threshold, a warning is generated and logged.

## Best Practices
1. Monitor cost warnings in audit logs
2. Review agent token usage patterns
3. Optimize system prompts for efficiency
4. Consider model downgrades for cost reduction
5. Implement token-efficient techniques

## Related Policies
- `myna.budget_ceiling` - Global pipeline cost limit
- `myna.audit_all_actions` - Cost tracking and audit
