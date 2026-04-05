# Report Writer Skill

## Overview
The Report Writer Skill enables professional document generation from structured data and analysis results. It creates formatted reports with tables, charts, executive summaries, and detailed sections.

## Supported Output Formats
- **Markdown** (`.md`) - Version-controllable, Git-friendly
- **JSON** (`.json`) - Structured, programmatic consumption
- **HTML** (`.html`) - Formatted web display
- **PDF** (`.pdf`) - Professional distribution format

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `report_data` | object | Analysis results and metrics to include |
| `report_template` | string | Template identifier: "executive", "technical", "audit" |
| `formatting_style` | string | Visual style: "professional", "detailed", "summary" |
| `output_format` | enum | Desired output format (md, json, html, pdf) |

## Outputs
| Key | Type | Description |
|-----|------|-------------|
| `report_document` | string | Formatted report content |
| `visualization_data` | array | Chart and table specifications |
| `metadata` | object | Report metadata and statistics |

## Report Templates

### Executive Template
- High-level overview
- Key findings and recommendations
- Budget summary
- Status indicators
- **Use Cases**: Management presentations, stakeholder updates

### Technical Template
- Detailed methodology
- Complete findings with evidence
- Technical recommendations
- Appendices with raw data
- **Use Cases**: Engineering reviews, audit reports

### Audit Template
- Compliance assessment
- Risk categorization
- Remediation requirements
- Timeline and ownership
- **Use Cases**: Governance, compliance reporting

## Report Sections
1. **Title Page** - Report identification and metadata
2. **Executive Summary** - High-level overview
3. **Table of Contents** - Navigation aids
4. **Findings** - Detailed results and analysis
5. **Recommendations** - Actionable improvements
6. **Appendices** - Supporting documentation

## Formatting Features
✓ Dynamic table generation
✓ Chart and visualization embedding
✓ Styled headers and sections
✓ Cross-references and TOC
✓ Page breaks and layout control
✓ Metadata timestamps

## Governance
- **Level**: LOW (data output focused)
- **Audit Trail**: Report generation logged
- **Permissions**: File write, data access

## Permissions Required
- **File Access**: Write to workspace
- **Memory**: Read data and analysis results
- **Tool Calls**: `myna.file_write`, `myna.memory_read`, `myna.summarize`

## Performance
- **Latency SLO**: 60 seconds
- **File Size**: Handles reports up to 50MB
- **Concurrency**: Supports parallel report generation

## Best Practices
1. Use appropriate template for audience
2. Include data-driven evidence
3. Provide actionable recommendations
4. Add clear formatting for readability
5. Verify data accuracy before publishing

## Related Skills
- `agentic.file_summarizer` - Content preparation
- `agentic.data_validator` - Data quality verification
