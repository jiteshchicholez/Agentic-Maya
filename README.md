# Agentic Maya

![Python](https://img.shields.io/badge/Python-3.12+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen)


**Agentic Maya** — Governed multi-agent orchestration with YAML pipelines, policies, and skills for enterprise-grade AI workflows.

website: [Agentic Maya](https://agentic-maya.vercel.app/)

## What It Does

Agentic Maya provides a secure, auditable framework for running multi-agent AI pipelines with built-in governance, memory management, and human oversight. It's designed for production use cases requiring compliance, traceability, and safety.

### Key Features

- **YAML-Driven Pipelines**: Define complex workflows with steps, checkpoints, and fallback models
- **Policy Enforcement**: Six-layer governance system (Intent, Auth, Budget, PII, External Gate, Escalation)
- **Skill Registry**: Reusable, versioned agent capabilities with audit trails
- **Memory Tiers**: Session, episodic, long-term, and audit memory for safe persistence
- **CLI Tools**: Full lifecycle management with status, audit, checkpoint, and rollback commands
- **HITL Integration**: Human-in-the-loop approvals for critical decisions
- **Audit Logging**: Immutable, hash-chained logs for compliance

## Quick Start

### Installation

```bash
pip install agentic-maya
# or for development
pip install -e .
```

### First Pipeline

```bash
# Run a sample pipeline
myna run ./pipelines/document_review.yml

# Check execution status
myna status <session_id>

# View detailed audit trail
myna audit <session_id>
```

### CLI Commands

- `myna run <pipeline.yml>` - Execute a pipeline
- `myna status <session_id>` - Check pipeline status
- `myna audit <session_id>` - View audit logs
- `myna checkpoint <session_id> --label <name>` - Create checkpoint
- `myna rollback <session_id> --to <checkpoint>` - Rollback to checkpoint
- `myna approve <session_id> --request-id <id>` - Approve pending requests
- `myna pause <session_id>` - Pause execution
- `myna terminate <session_id>` - Stop pipeline

## Architecture

### Governance Layers

1. **Intent Verification** - Validate task intent against policies
2. **Model Authorization** - Check model access permissions
3. **Budget Control** - Enforce token and cost limits
4. **PII Detection** - Block sensitive data leaks
5. **External Gate** - Control API/tool usage
6. **Escalation** - Human approval for critical actions

### Memory Tiers

- **Session Memory**: Current execution state
- **Episodic Memory**: Step checkpoints and resumes
- **Long-Term Memory**: Persistent knowledge and preferences
- **Audit Memory**: Compliance event history

### Agent Roles

- **Orchestrator**: Controls pipeline execution
- **Specialist**: Executes domain tasks
- **Subagent**: Scoped helper agents
- **Critic**: Validates outputs and compliance
- **Memory Manager**: Handles all memory operations
- **Tool Executor**: Runs external tools/APIs
- **Audit Agent**: Enforces governance and logging

## Documentation

📖 **[Full Documentation](https://agentic-maya.vercel.app/)** - Complete guides and API reference

- [Core Concepts](https://agentic-maya.vercel.app/docs)
- [Pipeline Guide](https://agentic-maya.vercel.app/pipelines)
- [Policy Reference](https://agentic-maya.vercel.app/policies)
- [Skills Registry](https://agentic-maya.vercel.app/skills)

## Project Structure

```
agentic-myna/
├── main.py                 # CLI entry point
├── pyproject.toml          # Project configuration
├── myna.toml              # Runtime defaults
├── src/myna/              # Core package
│   ├── cli.py            # Command-line interface
│   ├── runtime.py        # Pipeline execution engine
│   ├── governance.py     # Policy enforcement
│   ├── memory.py         # Memory management
│   └── schemas.py        # Data validation
├── pipelines/             # YAML pipeline definitions
├── policies/              # YAML governance policies
├── skills/                # YAML skill definitions
├── tests/                 # Test suite
│   ├── test_*.py         # Unit tests
│   └── scenarios/        # Integration tests
├── docs/                  # Markdown documentation
└── website/               # Static website
    ├── index.html        # Homepage
    └── docs/             # HTML documentation
```

## Development

### Setup

```bash
git clone <repository-url>
cd agentic-myna
pip install -e .[dev]
```

### Testing

```bash
# Run all tests
python -m pytest

# Run specific test
python -m pytest tests/test_governance.py -v

# Run with coverage
python -m pytest --cov=src/myna
```

### Building Documentation

```bash
# Generate HTML docs from Markdown
python scripts/build_docs.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`python -m pytest`)
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Guidelines

- Follow PEP 8 style guidelines
- Add type hints for new functions
- Update documentation for API changes
- Ensure backward compatibility

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: adlitoxit@gmail.com
- 🐛 GitHub: [GitHub](https://github.com/jiteshchicholez/Agentic-Maya)

---

*Agentic Maya - Safe, Auditable, Multi-Agent AI Orchestration*
