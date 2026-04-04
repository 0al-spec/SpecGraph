# PageIndex Search Manual

Complete guide to searching indexed ChatGPT conversations via PageIndex.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Prerequisites](#prerequisites)
4. [Usage](#usage)
5. [Examples](#examples)
6. [Output Formats](#output-formats)
7. [Advanced Options](#advanced-options)
8. [Troubleshooting](#troubleshooting)
9. [API Integration](#api-integration)

---

## Overview

PageIndex Search provides semantic search over 40 indexed ChatGPT conversations covering:

- **Trust Social** — Social network architecture, UI/UX, trust mechanisms
- **Agent Operating System** — Multi-agent systems, orchestration, metrics
- **SpecGraph** — Specification systems, bootstrapping, implementation patterns

The tool uses LLM-driven semantic search (not simple keyword matching) to find relevant conversation sections based on meaning and context.

### Key Features

- **Semantic search** — Find conversations by meaning, not keywords
- **Ranked results** — Results ranked by relevance with reasoning
- **Full text retrieval** — Fetch complete conversation excerpts
- **Multiple output formats** — Human-readable or JSON
- **Fast queries** — Milliseconds to seconds

---

## Quick Start

### 1. Start the PageIndex API Server

```bash
cd ~/Development/GitHub/PageIndexInstance
python3 -m pageindex.local_api --port 8765
```

**Output:**
```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://127.0.0.1:8765
```

Keep this terminal open. The API must be running for searches to work.

### 2. Search in Another Terminal

```bash
cd ~/Development/GitHub/0AL/SpecGraph

# Simple query
python3 tools/search_pageindex.py "agent orchestration"

# Top 10 results with full text
python3 tools/search_pageindex.py "SpecGraph bootstrap" --top-k 10 --context
```

---

## Prerequisites

### System Requirements

- Python 3.9+
- PageIndex indexed (40 conversations)
- PageIndex API running on localhost:8765

### Check Prerequisites

```bash
# Verify PageIndex exists
ls ~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json
# Should return the file path

# Verify Python
python3 --version
# Should be 3.9 or higher
```

### Start PageIndex API

The API must be running before any searches:

```bash
cd ~/Development/GitHub/PageIndexInstance
python3 -m pageindex.local_api --port 8765 &
# or in a separate terminal
```

Check it's running:
```bash
curl http://127.0.0.1:8765/health
# Should return: {"status": "ok", "service": "pageindex-local-api"}
```

---

## Usage

### Command Line Syntax

```bash
python3 tools/search_pageindex.py QUERY [OPTIONS]
```

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `QUERY` | Search term or phrase | `"success criteria"` |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--catalog PATH` | `~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json` | Path to PageIndex catalog |
| `--api-url URL` | `http://localhost:8765` | PageIndex API base URL |
| `--model MODEL` | `gpt-4o-2024-11-20` | LLM model for retrieval |
| `--top-k N` | `7` | Number of results to return (1-20) |
| `--context` | (disabled) | Fetch full text for each result |
| `--json` | (disabled) | Output raw JSON instead of formatted text |

### Basic Examples

```bash
# Simple search (default: top 7 results)
python3 tools/search_pageindex.py "agent operating system"

# More results
python3 tools/search_pageindex.py "metrics" --top-k 15

# With full conversation text
python3 tools/search_pageindex.py "trust mechanisms" --context

# JSON output
python3 tools/search_pageindex.py "specification" --json
```

---

## Examples

### Example 1: Find Architecture Discussions

```bash
$ python3 tools/search_pageindex.py "system architecture"

[1] SpecGraph — 4-Layers in 3D
    Source: Агентная_Операционная_Система_-_SpecGraph_-_4-Layers_in_3D
    Summary: Comprehensive conversation about SpecGraph's layered architecture:
             intent, specification, graph, and code layers. Discusses 3D
             visualization and integration approach.
    Relevance: Directly addresses layered architecture model with detailed
               explanation of four-layer separation of concerns

[2] Agent Operating System — SpecGraph Bootstrap
    Source: Агентная_Операционная_Система_-_SpecGraph_-_Bootstrap_via_OpenSpec
    Summary: Deep dive into bootstrapping SpecGraph from OpenSpec, including
             architecture decisions and implementation strategies.
    Relevance: Discusses architecture decisions and system bootstrap patterns...

[3] SpecGraph — Dogfooding
    Source: Агентная_Операционная_Система_-_SpecGraph_-_Dogfooding
    Summary: Using SpecGraph to build itself; meta-level architecture
             implementation details.
    Relevance: Examines architectural patterns in self-implementing systems...
```

### Example 2: Get Full Context

```bash
$ python3 tools/search_pageindex.py "success criteria" --top-k 3 --context

[1] SpecGraph — Specification Readiness Gate
    Source: Агентная_Операционная_Система_-_SpecGraph_-_Specification_Readiness_Gate
    Summary: Detailed specification about validation gates and success criteria...
    Relevance: Explicitly discusses success criteria framework and validation...
    ---
    USER:
    What are the success criteria for a specification being ready for
    implementation?

    ASSISTANT:
    A specification is ready when it meets these criteria:
    1. All acceptance criteria are defined and measurable
    2. Edge cases are documented with expected behavior
    3. Performance requirements are quantified
    4. Error handling paths are specified
    5. External dependencies are listed and validated
    ...
    ---
```

### Example 3: Filter by Top K

```bash
$ python3 tools/search_pageindex.py "branch orchestration" --top-k 2

[1] Agent Operating System — Branch Orchestration for Codex
    Source: Агентная_Операционная_Система_-_Branch_Оркестрация_для_Codex
    Summary: Strategy for managing conversation branches in multi-agent systems...

[2] Agent Operating System — Orchestration for Codex
    Source: Агентная_Операционная_Система_-_Оркестрация_для_Codex
    Summary: Orchestration patterns for agent coordination and task distribution...
```

### Example 4: Export as JSON

```bash
$ python3 tools/search_pageindex.py "metrics" --json | jq '.[] | {title, document_name}'

{
  "title": "Agent Operating System — SIB Metrics Full",
  "document_name": "Агентная_Операционная_Система_-_SIB_Metrics_Full"
}
{
  "title": "Agent Operating System — Pre-Implementation Balance Metrics",
  "document_name": "Агентная_Операционная_Система_-_Pre-Implementation_Balance_Metrics"
}
{
  "title": "Agent Operating System — Metrics for Analysis",
  "document_name": "Агентная_Операционная_Система_-_SpecGraph_-_Метрики_для_анализа"
}
```

---

## Output Formats

### Human-Readable Format (Default)

```
[1] Conversation Title
    Source: source_document_name
    Summary: Brief summary of the conversation...
    Relevance: Why PageIndex thinks this is relevant...
```

**With `--context` flag:**
```
[1] Conversation Title
    Source: source_document_name
    Summary: Brief summary...
    Relevance: Reasoning...
    ---
    Full conversation text here
    (multiple paragraphs)
    ---
```

### JSON Format (with `--json` flag)

```json
[
  {
    "title": "Conversation Title",
    "document_name": "source_document_name",
    "summary": "Summary text...",
    "reasoning": "Why this is relevant...",
    "text": "Full conversation text (if --context)",
    "record_id": "project:path/to/structure.json",
    "node_id": "0001"
  },
  ...
]
```

---

## Advanced Options

### Custom Catalog Location

```bash
python3 tools/search_pageindex.py "query" \
  --catalog /custom/path/to/catalog.json
```

### Custom API URL

```bash
# If PageIndex API is on a different host/port
python3 tools/search_pageindex.py "query" \
  --api-url http://192.168.1.100:8765
```

### Programmatic Usage (Python)

```python
import subprocess
import json

# Run search
result = subprocess.run([
    "python3", "tools/search_pageindex.py",
    "agent metrics",
    "--top-k", "5",
    "--json"
], capture_output=True, text=True)

# Parse results
nodes = json.loads(result.stdout)
for node in nodes:
    print(f"- {node['title']}")
    print(f"  Summary: {node['summary']}")
```

### Piping Results

```bash
# Get only titles
python3 tools/search_pageindex.py "OpenSpec" --json | \
  jq -r '.[] | .title'

# Get summaries
python3 tools/search_pageindex.py "metrics" --json | \
  jq -r '.[] | "\(.title)\n\(.summary)\n"'

# Count results
python3 tools/search_pageindex.py "architecture" --json | \
  jq 'length'
```

---

## Troubleshooting

### Error: "Cannot reach PageIndex API"

**Symptom:**
```
Cannot reach PageIndex API at http://localhost:8765.
Start it with:
  cd ~/Development/GitHub/PageIndexInstance
  python3 -m pageindex.local_api --port 8765
```

**Solution:**
1. Start the PageIndex API in a separate terminal
2. Wait 2-3 seconds for it to start
3. Verify it's running: `curl http://127.0.0.1:8765/health`

### Error: "Catalog not found"

**Symptom:**
```
Catalog not found: ~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json
```

**Solution:**
1. Verify the catalog exists:
   ```bash
   ls ~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json
   ```
2. If missing, re-index conversations:
   ```bash
   cd ~/Development/GitHub/ChatGPTDialogs
   python3 index_chatgpt_dialogs.py
   ```

### Error: "HTTP 500 from PageIndex API"

**Symptom:**
```
HTTP 500 from PageIndex API:
Internal server error...
```

**Solution:**
1. Check PageIndex API logs
2. Restart the API: `python3 -m pageindex.local_api --port 8765`
3. Verify LM Studio is running (if using local models)
4. Check system resources (RAM, CPU)

### No Results Found

**Symptom:**
Query returns empty results even though relevant conversations exist.

**Solutions:**
1. Try a simpler, more general query: `"agent"` instead of `"agent operating system bootstrap patterns"`
2. Increase `--top-k`: `--top-k 20` (default is 7)
3. Check the catalog has 40 documents:
   ```bash
   jq '.records | length' ~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json
   # Should be 40
   ```

### Slow Queries

**Issue:** Queries taking >10 seconds

**Solutions:**
1. Verify network connectivity to API
2. Check LM Studio is not overloaded
3. Use simpler queries (fewer words)
4. Reduce `--top-k` (fewer results = faster)

---

## API Integration

### Integrating with SpecGraph Tools

```python
# In SpecGraph tools
import subprocess
import json
from pathlib import Path

def search_pageindex(query: str, top_k: int = 7, include_context: bool = False):
    """Search indexed conversations."""
    cmd = [
        "python3",
        "tools/search_pageindex.py",
        query,
        "--json",
        "--top-k", str(top_k)
    ]

    if include_context:
        cmd.append("--context")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )

    if result.returncode != 0:
        raise RuntimeError(f"Search failed: {result.stderr}")

    return json.loads(result.stdout)

# Usage
results = search_pageindex("SpecGraph metrics", top_k=5, include_context=True)
for node in results:
    print(f"Found: {node['title']}")
```

### Chaining with Other Tools

```bash
# Search results can be piped into other tools or `jq`
python3 tools/search_pageindex.py "success criteria" --json | \
  jq -r '.[].title'

# Count conversations about a topic
python3 tools/search_pageindex.py "agent OS" --top-k 20 --json | \
  jq 'group_by(.document_name) | length'
```

---

## Reference

### Indexed Conversation Topics

| Topic | Count | Key Conversations |
|-------|-------|-------------------|
| **Trust Social** | 3 | Landing page, Social network, Bluesky/AT Protocol |
| **Agent OS** | 30+ | Branch orchestration, Codex integration, Metrics |
| **SpecGraph** | 15+ | 4-Layers architecture, Bootstrap, Dogfooding |
| **Metrics** | 5+ | HITL, SIB metrics, Pre-implementation |
| **Other** | 5+ | Swift logic, MasFactory, Implementation speed |

### Environment Variables

```bash
# Optional: Override defaults
export OPENAI_API_KEY=your-key        # For OpenAI models
export OPENAI_BASE_URL=http://...     # For local LM Studio

# These are usually pre-configured in your shell environment
```

### File Locations

| File | Purpose |
|------|---------|
| `tools/search_pageindex.py` | Search tool script |
| `~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json` | Indexed catalog |
| `~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/markdown_src/` | Source Markdown files |

---

## FAQ

**Q: Can I search by conversation date?**
A: No, dates are not indexed. Use the conversation title in your search query.

**Q: Can I update the index with new conversations?**
A: Yes, re-run the ChatGPTDialogs indexing workflow and rebuild the PageIndex catalog.

**Q: What happens if the API is slow?**
A: The search timeout is 120 seconds. If queries timeout, restart the API or check system resources.

**Q: Can I use this from a script?**
A: Yes, see [API Integration](#api-integration) section for Python examples.

**Q: How is relevance ranked?**
A: PageIndex uses LLM reasoning to rank results. Top results are most semantically relevant to your query.

**Q: Can I search multiple catalogs?**
A: Currently only one catalog per search. Use `--catalog` to specify which.

---

## Support

For issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Verify PageIndex API is running: `curl http://127.0.0.1:8765/health`
3. Check catalog exists and is valid: `jq '.records | length' catalog.json`
4. Review PageIndex API logs

---

**Last Updated:** April 4, 2026
**Status:** Production Ready
**Version:** 1.0
