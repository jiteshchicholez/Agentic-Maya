# Agentic Maya - Artifacts Index

Complete catalog of all governance, pipeline, policy, and skill artifacts.

---

## Pipelines

| ID | Type | Version | Governance | Status |
|---|---|---|---|---|
| document_review | Pipeline | 1.0.0 | MEDIUM | ACTIVE |
| code_audit | Pipeline | 1.0.0 | MEDIUM | ACTIVE |
| data_enrichment | Pipeline | 1.0.0 | MEDIUM | ACTIVE |

### Pipeline Details

#### document_review
- **Description**: Multi-stage document analysis pipeline with content extraction, relevance assessment, and compliance verification
- **Agents**: 3 (review_orchestrator, content_specialist, policy_reviewer)
- **Flow Steps**: 4
- **Global Budget**: $1.50 USD, 32,768 tokens
- **Global Policies**: myna.audit_all_actions, myna.budget_ceiling, myna.no_external_without_permission, org.pii_block, org.external_call_gate, org.critical_escalation
- **File**: [pipelines/document_review.yml](../pipelines/document_review.yml)

#### code_audit
- **Description**: Automated code quality and security audit pipeline with architecture analysis, vulnerability scanning, and best practices evaluation
- **Agents**: 4 (audit_orchestrator, architecture_analyst, security_reviewer, quality_evaluator)
- **Flow Steps**: 5
- **Global Budget**: $2.50 USD, 65,536 tokens
- **Global Policies**: myna.audit_all_actions, myna.budget_ceiling, myna.require_critic_for_high_risk, org.pii_block, org.external_call_gate, org.critical_escalation
- **File**: [pipelines/code_audit.yml](../pipelines/code_audit.yml)

#### data_enrichment
- **Description**: Intelligent data processing pipeline with validation, transformation, and enrichment from external sources
- **Agents**: 4 (enrichment_orchestrator, validation_specialist, enrichment_specialist, qa_agent)
- **Flow Steps**: 5
- **Global Budget**: $1.25 USD, 32,768 tokens
- **Global Policies**: myna.audit_all_actions, myna.budget_ceiling, myna.no_external_without_permission, org.pii_block, org.external_call_gate, org.critical_escalation
- **File**: [pipelines/data_enrichment.yml](../pipelines/data_enrichment.yml)

---

## Policies

| ID | Type | Version | Governance | Status |
|---|---|---|---|---|
| policy.budget_guard | Policy | 1.0.0 | MEDIUM | ACTIVE |
| policy.pii_block | Policy | 1.0.0 | HIGH | ACTIVE |
| policy.external_call_gate | Policy | 1.0.0 | HIGH | ACTIVE |
| policy.critical_escalation | Policy | 1.0.0 | CRITICAL | ACTIVE |

### Policy Details

#### policy.budget_guard
- **Description**: Budget monitoring with cost threshold warnings
- **Scope**: AGENT
- **Action**: WARN
- **Trigger**: Budget check when cost exceeds $0.50 USD
- **Audit on Trigger**: Yes
- **Escalation Target**: HUMAN
- **Cooldown**: 0 seconds
- **File**: [policies/budget_guard.yml](../policies/budget_guard.yml)

#### policy.pii_block
- **Description**: Blocks PII in memory operations (GDPR/CCPA/HIPAA compliant)
- **Scope**: AGENT
- **Action**: DENY
- **Trigger**: Memory write with PII detected
- **Audit on Trigger**: Yes
- **Escalation Target**: HUMAN
- **Cooldown**: 0 seconds
- **Compliance**: GDPR, CCPA, HIPAA
- **File**: [policies/pii_block.yml](../policies/pii_block.yml)

#### policy.external_call_gate
- **Description**: Enforces authorization for external API calls
- **Scope**: AGENT
- **Action**: DENY
- **Trigger**: External call without approval
- **Audit on Trigger**: Yes
- **Escalation Target**: HUMAN
- **Cooldown**: 0 seconds
- **Risk Level**: HIGH
- **File**: [policies/external_call_gate.yml](../policies/external_call_gate.yml)

#### policy.critical_escalation
- **Description**: Auto-escalates on critical conditions, server errors, or cost overruns
- **Scope**: PIPELINE
- **Action**: ESCALATE
- **Trigger**: CRITICAL severity, 5xx errors, cost > $2.00
- **Audit on Trigger**: Yes
- **Escalation Target**: BOTH
- **Cooldown**: 0 seconds
- **File**: [policies/critical_escalation.yml](../policies/critical_escalation.yml)

---

## Skills

| ID | Type | Version | Governance | Status |
|---|---|---|---|---|
| agentic.file_summarizer | Skill | 1.0.0 | MEDIUM | ACTIVE |
| agentic.data_validator | Skill | 1.0.0 | LOW | ACTIVE |
| agentic.report_writer | Skill | 1.0.0 | HIGH | ACTIVE |
| agentic.semantic_search | Skill | 1.0.0 | MEDIUM | ACTIVE |

### Skill Details

#### agentic.file_summarizer
- **Description**: Intelligent file content summarization extracting key insights
- **Governance**: MEDIUM
- **Audit Required**: Yes
- **Supported Formats**: md, txt, json, yaml, py
- **Performance SLO**: 30 seconds
- **Tools**: myna.file_read, myna.summarize, myna.memory_write
- **File**: [skills/file_summarizer.yml](../skills/file_summarizer.yml)

#### agentic.data_validator
- **Description**: Comprehensive data validation with schema compliance and anomaly detection
- **Governance**: LOW
- **Audit Required**: Yes
- **Supported Schemas**: json-schema, avro, custom
- **Performance SLO**: 45 seconds
- **Tools**: myna.memory_read, myna.memory_write, myna.audit_query
- **File**: [skills/data_validator.yml](../skills/data_validator.yml)

#### agentic.report_writer
- **Description**: Professional report generation with formatting and visualization
- **Governance**: HIGH
- **Audit Required**: Yes
- **Output Formats**: markdown, json, html, pdf
- **Performance SLO**: 60 seconds
- **Tools**: myna.file_write, myna.memory_read, myna.summarize
- **File**: [skills/report_writer.yml](../skills/report_writer.yml)

#### agentic.semantic_search
- **Description**: Intelligent content discovery using embeddings and vector similarity
- **Governance**: MEDIUM
- **Audit Required**: Yes
- **Embedding Model**: text-embedding-3-small
- **Performance SLO**: 25 seconds
- **Search Scopes**: documents, code, memory, workspace
- **Tools**: myna.file_read, myna.memory_read, myna.summarize
- **File**: [skills/semantic_search.yml](../skills/semantic_search.yml)

---

## Summary Statistics

| Category | Count | Total Files |
|----------|-------|-------------|
| Pipelines | 3 | 6 (YAML + MD) |
| Policies | 4 | 8 (YAML + MD) |
| Skills | 4 | 8 (YAML + MD) |
| **Total** | **11** | **22** |

---

## File Organization

```
agenticmyna/
├── artifacts/
│   └── index.md                    (This file)
├── pipelines/
│   ├── document_review.yml
│   ├── document_review.md
│   ├── code_audit.yml
│   ├── code_audit.md
│   ├── data_enrichment.yml
│   └── data_enrichment.md
├── policies/
│   ├── budget_guard.yml
│   ├── budget_guard.md
│   ├── pii_block.yml
│   ├── pii_block.md
│   ├── external_call_gate.yml
│   ├── external_call_gate.md
│   ├── critical_escalation.yml
│   └── critical_escalation.md
├── skills/
│   ├── file_summarizer.yml
│   ├── file_summarizer.md
│   ├── data_validator.yml
│   ├── data_validator.md
│   ├── report_writer.yml
│   ├── report_writer.md
│   ├── semantic_search.yml
│   └── semantic_search.md
└── src/
    └── myna/
        ├── __init__.py
        ├── cli.py
        ├── config.py
        ├── governance.py
        ├── loader.py
        ├── memory.py
        ├── model_client.py
        ├── persistence.py
        ├── policy.py
        ├── runtime.py
        ├── schemas.py
        └── utils.py
```

---

## Governance Framework

### Policy Enforcement

All pipelines include the following mandatory governance policies:
- **myna.audit_all_actions** - Complete audit trail of all actions
- **myna.budget_ceiling** - Global budget enforcement
- **org.pii_block** - PII protection (GDPR/CCPA/HIPAA)
- **org.external_call_gate** - External communication control
- **org.critical_escalation** - Automatic incident escalation

### Risk Levels

| Level | Agent Governance | Examples |
|-------|---|---|
| LOW | Basic monitoring | data_validator |
| MEDIUM | Audit + budget control | file_summarizer, semantic_search |
| HIGH | Enhanced oversight | report_writer |
| CRITICAL | Max controls | Not assigned to skills |

### Audit Trail

All artifacts support comprehensive auditing:
- Action logging with timestamps
- Cost tracking per agent
- Memory access controls
- External call authorization
- Policy violation detection

---

## Status Legend

- **ACTIVE** - Ready for use in production pipelines
- **DEPRECATED** - Scheduled for removal
- **BETA** - Testing/validation phase
- **ARCHIVED** - Historical reference only

All current artifacts are **ACTIVE**.

---

*Last Updated: April 5, 2026*
