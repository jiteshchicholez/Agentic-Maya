# Code Audit Pipeline

## Overview
The Code Audit Pipeline provides comprehensive analysis of codebases, combining architectural assessment, security vulnerability scanning, and quality metrics evaluation. It delivers actionable intelligence for code improvement and risk mitigation.

## Purpose
- **Architectural Analysis**: Evaluate design patterns, modularity, and scalability
- **Security Assessment**: Identify vulnerabilities and security risks
- **Quality Evaluation**: Assess maintainability, testing, documentation, and standards
- **Risk Mitigation**: Provide prioritized recommendations for improvement

## Workflow
1. **Session Initialization** - Establish audit context and baseline
2. **Parallel Analysis** - Three concurrent specialist evaluations
3. **Findings Synthesis** - Consolidated audit report generation

## Agents

### Audit Orchestrator
- **Role**: Workflow coordination and result synthesis
- **Responsibilities**: Task delegation, findings aggregation, report generation
- **Model**: GPT-4 (fallback: GPT-4-turbo)
- **Tool Access**: File system with workspace scope

### Architecture Analyst
- **Role**: Structural and design pattern evaluation
- **Responsibilities**: Pattern analysis, modularity review, scalability assessment
- **Model**: GPT-4 (fallback: Claude-3-Sonnet)

### Security Reviewer
- **Role**: Vulnerability and risk assessment
- **Responsibilities**: OWASP analysis, vulnerability identification, CVSS scoring
- **Model**: GPT-4 (fallback: Claude-3-Opus)

### Quality Evaluator
- **Role**: Standards and best practices assessment
- **Responsibilities**: Readability, maintainability, test coverage, documentation
- **Model**: GPT-4 (fallback: GPT-4-turbo)

## Budget Allocation
- **Global Budget**: $2.50 USD, 65,536 tokens, 900 seconds wall time
- **Orchestrator**: $0.40 USD, 8,192 tokens, 180 seconds
- **Specialists**: $0.20-0.35 USD each, 6,144-8,192 tokens
- **Tool Calls**: Max 60 per pipeline execution

## Governance
- Enforces complete audit trail via `maya.audit_all_actions`
- Maintains cost controls via `maya.budget_ceiling`
- Requires critic approval for high-risk findings

## Output
Comprehensive audit report with:
- Architectural assessment with recommendations
- Vulnerability list with CVSS scores
- Quality metrics with improvement actions
- Executive summary and prioritized action plan
