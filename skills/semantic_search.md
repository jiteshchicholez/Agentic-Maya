# Semantic Search Skill

## Overview
The Semantic Search Skill provides intelligent content discovery using embeddings and vector similarity matching. Rather than keyword matching, it understands meaning and context to find relevant information.

## Core Capabilities
- **Semantic Matching**: Context-aware relevance beyond keywords
- **Vector Similarity**: Embedding-based similarity calculation
- **Multi-Source Search**: Files, memory, and code repositories
- **Relevance Ranking**: Scored results ordered by similarity
- **Context Extraction**: Snippets showing matching context

## Supported Scopes
| Scope | Coverage | Use Case |
|-------|----------|----------|
| documents | Markdown, text files | Documentation search |
| code | Python, configuration files | Code discovery |
| memory | Episodic and persistent | Execution history |
| workspace | All file types | Full project search |

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `query_text` | string | Natural language search query |
| `search_scope` | enum | Where to search: documents, code, memory, workspace |
| `similarity_threshold` | float | Min relevance score (0.0-1.0, default 0.5) |
| `max_results` | integer | Maximum results to return (1-100) |

## Outputs
| Key | Type | Description |
|-----|------|-------------|
| `search_results` | array | Matching documents/items found |
| `relevance_scores` | array | Similarity scores for each result |
| `context_snippets` | array | Extracted excerpts with matches highlighted |

## Search Examples

### Documentation Search
```
Query: "How to configure agent budgets?"
Results: Links to configuration docs with scoring
Useful for: User onboarding, self-service support
```

### Code Discovery
```
Query: "Memory persistence implementation"
Results: Relevant source files and code sections
Useful for: Development, code review, refactoring
```

### Execution History
```
Query: "Pipeline cost overrun incidents"
Results: Past executions matching query
Useful for: Troubleshooting, pattern analysis
```

## Embedding Model
- **Model**: Text-embedding-3-small
- **Dimensions**: 1536
- **Optimization**: Fast similarity computation
- **Quality**: High semantic accuracy

## Govern
- **Level**: MEDIUM
- **Audit Trail**: All searches logged
- **Permissions**: File and memory reading

## Permissions Required
- **File Access**: Read workspace files  
- **Memory**: Read episodic and persistent memory
- **Tool Calls**: `maya.file_read`, `maya.memory_read`, `maya.summarize`

## Performance
- **Latency SLO**: 25 seconds
- **Index Building**: On-demand (cached)
- **Scalability**: Searches across 10K+ documents
- **Accuracy**: Semantic understanding over keyword matching

## Similarity Scoring
- **1.0** - Perfect semantic match
- **0.7-0.9** - Highly relevant
- **0.5-0.7** - Related content
- **<0.5** - Weak relevance (filtered out)

## Best Practices
1. Use natural language queries
2. Set appropriate threshold for precision
3. Combine with keyword search when needed
4. Iterate on queries for refinement
5. Leverage context snippets for verification

## Related Skills
- `agentic.file_summarizer` - Content preparation
- `agentic.report_writer` - Result documentation
