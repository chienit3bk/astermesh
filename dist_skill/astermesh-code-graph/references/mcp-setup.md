# Astermesh MCP Setup & Client Integration Guide

## 1. Installation

Astermesh requires **Python >= 3.10**. Install directly from the official repository:

### Option A: Install directly via pip (Recommended)
```bash
pip install git+https://github.com/ddthang2611/astermesh.git
```

### Option B: Clone and install in a virtual environment
```bash
git clone https://github.com/ddthang2611/astermesh.git
cd astermesh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify that the CLI is accessible:
```bash
astermesh --help
```

---

## 2. Register MCP Server in Your AI Coding Agent

Astermesh communicates over standard input/output (`stdio`) or streamable HTTP/SSE.

### A. Cursor Configuration
Add to `.cursor/mcp.json` in your workspace or global settings:

```json
{
  "mcpServers": {
    "astermesh": {
      "command": "astermesh",
      "args": ["serve", ".", "--transport", "stdio"]
    }
  }
}
```

*Note: Replace `"."` with `${workspaceFolder}` or an absolute repository path if running outside the project root.*

---

### B. Claude Code CLI
Add the server using the `claude mcp` CLI command:

```bash
claude mcp add astermesh -- astermesh serve /path/to/your/project --transport stdio
```

---

### C. Claude Desktop
Add to your Claude Desktop configuration file (`claude_desktop_config.json`):

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "astermesh": {
      "command": "astermesh",
      "args": ["serve", "/absolute/path/to/your/codebase", "--transport", "stdio"]
    }
  }
}
```

---

### D. Google Antigravity / Gemini CLI
Add to `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "astermesh": {
      "command": "astermesh",
      "args": ["serve", ".", "--transport", "stdio"]
    }
  }
}
```

---

## 3. Standalone CLI Commands

You can also run Astermesh independently from the terminal:

### Build Graph Artifacts
Export Semantic `#ACN2` wire format, Markdown report, and interactive 2D HTML map:
```bash
astermesh build .
```
Outputs are written to `astermesh-graph/` by default.

### Query Symbols and Architecture Directly
```bash
# Locate symbol definition and exact lines
astermesh query "GraphBuilder"

# Overview statistics
astermesh query --overview

# List detected Leiden communities
astermesh query --list-communities
```

### Run Token Benchmark
Measure token reduction on your repository:
```bash
astermesh benchmark . --report benchmark_report.md
```

---

## 4. Troubleshooting & Support

- **Repository**: [https://github.com/ddthang2611/astermesh](https://github.com/ddthang2611/astermesh)
- **Issue Tracker**: [https://github.com/ddthang2611/astermesh/issues](https://github.com/ddthang2611/astermesh/issues)
