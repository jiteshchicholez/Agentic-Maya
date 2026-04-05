# File Summarizer Skill

## Overview
The File Summarizer Skill provides intelligent content extraction and summarization capabilities. It analyzes various file types to identify key information, main points, and actionable insights.

## Supported File Formats
- Markdown (`.md`)
- Plain Text (`.txt`)
- JSON (`.json`)
- YAML (`.yaml`, `.yml`)
- Python (`.py`)

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | string | Absolute path to file for summarization |
| `summary_style` | enum | Format: "bullet_points", "narrative", "executive" |
| `max_length` | integer | Maximum tokens in summary (100-500) |

## Outputs
| Key | Type | Description |
|-----|------|-------------|
| `summary_text` | string | Condensed summary of file content |
| `key_points` | array | List of main points extracted |
| `metadata` | object | File stats and processing metadata |

## Governance
- **Level**: MEDIUM
- **Audit Trail**: Full logging of all summarizations
- **Tool Requirements**: File reading, content summarization, memory operations

## Permissions Required
- **File Access**: Read permission for workspace files
- **Memory**: Write access for storing summaries
- **Tool Calls**: `maya.file_read`, `maya.summarize`, `maya.memory_write`

## Key Features
✓ Multi-format file support
✓ Context-aware summarization
✓ Key point extraction
✓ Configurable summary length
✓ Performance SLO: 30 seconds max

## Usage Per Agent
- **Permissions Setting**:
  ```yaml
  permissions:
    tools:
      - maya.file_read
      - maya.summarize
      - maya.memory_write
    memory: write
    file_access:
      - workspace
  ```

## Performance
- **Latency SLO**: 30 seconds maximum
- **Error Handling**: Graceful fallback for unsupported formats
- **Scalability**: Supports files up to 10MB

## Related Skills
- `agentic.semantic_search` - Content discovery
- `agentic.report_writer` - Report generation
