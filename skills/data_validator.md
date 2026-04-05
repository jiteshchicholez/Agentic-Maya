# Data Validator Skill

## Overview
The Data Validator Skill provides comprehensive validation capabilities for ensuring data quality, consistency, and compliance with defined schemas and business rules. It includes anomaly detection and generates detailed validation reports.

## Validation Capabilities
- **Schema Validation**: JSON Schema, Avro, custom schema definitions
- **Type Checking**: Data type enforcement and coercion
- **Constraint Validation**: Range, length, regex, uniqueness checks
- **Anomaly Detection**: Statistical anomaly identification
- **Relationship Validation**: Cross-field and referential integrity

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `data_set` | object | Data collection to validate |
| `schema_definition` | string | Schema definition (JSON Schema, Avro, etc) |
| `validation_rules` | array | Custom business validation rules |
| `strict_mode` | boolean | Fail on first error (true) or collect all (false) |

## Outputs
| Key | Type | Description |
|-----|------|-------------|
| `validation_results` | object | Per-record validation status |
| `error_report` | array | Detailed error listing with locations |
| `anomaly_detection` | array | Detected anomalous records with scores |

## Validation Rules
### Type Constraints
- String, Integer, Float, Boolean, Array, Object
- Custom type definitions
- Nullable vs. required fields

### Value Constraints
- Min/max values
- String length and pattern matching
- Enum validation
- Regex pattern enforcement

### Relationship Validation
- Foreign key constraints
- Referential integrity
- Cross-field dependencies
- Uniqueness constraints

## Governance
- **Level**: MEDIUM
- **Audit Trail**: All validation operations logged
- **Error Handling**: Comprehensive error documentation

## Permissions Required
- **Memory**: Read/write for storing results
- **Audit**: Query permissions for audit trail
- **Tool Calls**: `myna.memory_read`, `myna.memory_write`, `myna.audit_query`

## Error Categories
- `SCHEMA_MISMATCH` - Field missing or type incorrect
- `CONSTRAINT_VIOLATION` - Value outside allowed range
- `ANOMALY_DETECTED` - Statistical outlier
- `REFERENCE_ERROR` - Foreign key violation
- `CUSTOM_RULE_FAILURE` - Business rule violation

## Performance
- **Latency SLO**: 45 seconds
- **Scalability**: Processes datasets with 10K+ records
- **Error Detail**: Line-level error reporting

## Related Skills
- `agentic.file_summarizer` - Data inspection
- Data enrichment and transformation workflows
