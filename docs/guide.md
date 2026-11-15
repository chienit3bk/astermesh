# Astermesh User Guide

Astermesh turns a source repository into an in-memory code knowledge graph using static AST parsing (`tree-sitter`) and graph algorithms (`networkx`, `igraph`, `leidenalg`). The graph is exposed in three ways:

| Interface | Audience | Purpose |
| :--- | :--- | :--- |
| `astermesh build` | LLM / human | Export snapshot artifacts (`#ACN2` wire, Markdown report, HTML map) |
| `astermesh query` | Human | Look up symbols and communities from the terminal |
| `astermesh serve` | AI assistant | Long-running MCP server with live incremental updates |

No embeddings and no LLM calls are used during indexing.

---

## 1. Installation

Requirements: Python 3.10+.

```bash
git clone https://github.com/ddthang2611/astermesh.git
cd astermesh
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify:

```bash
astermesh --help
# or, without relying on the console script
python -m astermesh --help
```

---

## 2. Core Concepts

### 2.1 Supported languages and files

| Category / Extension | Extracted entities | Extracted relations |
| :--- | :--- | :--- |
| `.py` | classes, functions, methods, module-level variables | imports, inheritance, calls, variable references |
| `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.mts`, `.cts` | classes, functions, methods, arrow functions, React components, hooks, Angular/NestJS `@Injectable` services and `@Module`/`@Component` modules | ES/CJS imports, barrel re-exports, inheritance, calls, JSX `<Component />` renders, constructor DI injections, module providers, asset imports |
| `.vue`, `.svelte` | SFC components, script functions/variables, template custom-tag references | imports, calls, template component renders (`RENDERS`), asset imports |
| `.toml`, `.json`, `.yaml`, `.yml`, `.md`, `.ini`, `.cfg`, `.rst`, `Dockerfile`, `Makefile` | satellite configuration sections/keys (`config`) and documentation headings (`doc`) | `DEFINES`, `REFERENCES` |
| `.svg`, `.png`, `.jpg`, `.webp`, `.css`, `.scss`, `.woff2`, ... | isolated static asset nodes (`asset`) when imported by code | incoming `IMPORTS`, `REFERENCES`, `RENDERS` |

Other file types and lockfiles (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`) are ignored.

### 2.2 Ignored directories

The following directories are skipped during scanning and watching, together with every directory whose name starts with `.`:

`.git`, `.venv`, `venv`, `__pycache__`, `node_modules`, `.agents`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist`, `build`, `coverage`, `.next`, `.nuxt`, `xml-graph`, `astermesh-graph`, `generated`, `__generated__`

### 2.3 Node identifiers

Every node in the graph has a stable string ID:

| Node type | ID format | Example |
| :--- | :--- | :--- |
| `folder` | path relative to the workspace root (`.` for root) | `src/astermesh/graph` |
| `file`, `asset` | path relative to the workspace root | `src/astermesh/graph/builder.py` |
| `class`, `function`, `variable`, `component`, `hook`, `service`, `module` | fully qualified name derived from the file path | `src.astermesh.graph.builder.GraphBuilder.build_full` |
| `config`, `doc` | `<module_fqn>.<section_or_heading>` | `pyproject.project.name` |

FQN rules: the file extension is dropped, `/` becomes `.`, and `__init__` segments are removed. FQNs are therefore relative to the directory you index: indexing the repository root yields `src.astermesh...`, indexing `src/` yields `astermesh...`.

### 2.4 Edge types

| Edge | Weight | Meaning |
| :--- | :--- | :--- |
| `DEFINES` | `3.0` | file or class defines an entity |
| `INHERITS` | `2.5` | class inherits from / implements another class |
| `INJECTS` | `2.5` | class or service injects a dependency via constructor / decorator |
| `RENDERS` | `2.0` | UI component (React JSX, Vue, Svelte, Angular) renders another component or asset |
| `CALLS` | `1.5` | entity invokes another callable |
| `PROVIDES` | `1.0` | module or component registers a provider/import/export |
| `IMPORTS` | `1.0` | file imports a module, symbol, or static asset |
| `CONTAINS` | `1.0` | folder contains folder or file |
| `REFERENCES` | `0.8` | entity reads a module-level variable or config/asset |

Call and import targets are resolved statically in this order: lexical scope and `tsconfig.json`/`jsconfig.json` path aliases, imported symbol or barrel re-export (`export * from ...`, `export { X } from ...`), same-module symbol, exact FQN, unique dot-path suffix, then a unique exported short name across the project.

### 2.5 Communities

Logic entities (`class`, `function`, `variable`, `component`, `hook`, `service`, `module`) are clustered with the weighted Leiden algorithm (`modularity` or `cpm` objective, deterministic `seed=0`). Static assets, folders, files, configs, and docs are excluded from clustering so shared assets never distort architectural boundaries. Each community is named after its **God Node**, the member with the highest intra-community weighted degree, and receives an ID `C1`, `C2`, ... ordered by size.

---

## 3. CLI Reference

### 3.1 `astermesh build`

Index a repository and write snapshot artifacts.

```bash
astermesh build [PATH] [-o OUTPUT] [--format acn|xml|all] [--max-tokens N] [--include-xml-legacy] [--html HTML_PATH] [--no-html]
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `PATH` | `.` | Workspace root to index |
| `-o`, `--output`, `--output-dir` | `astermesh-graph` | Output directory, or an explicit `.acn` or `.xml` file path. Relative paths are resolved against `PATH` |
| `--format` | `acn` | Context format: `acn` (`#ACN2` wire), `xml` (deprecated legacy), or `all` |
| `--max-tokens` | none | Optional token budget triggering `L0` -> `L1` -> `L2` compression |
| `--include-xml-legacy` | off | Also export deprecated `context_graph.xml` |
| `--html` | `<output>/astermesh_view.html` | Custom path for the HTML map |
| `--no-html` | off | Skip HTML generation |

Generated files (default layout):

```text
<PATH>/astermesh-graph/
├── context_graph.acn     # dense #ACN2 wire notation for LLM context
├── GRAPH_REPORT.md       # macro architecture summary
└── astermesh_view.html   # interactive 2D map for humans
```

Examples:

```bash
astermesh build .
astermesh build /path/to/repo --no-html
astermesh build . --max-tokens 6000
astermesh build . -o artifacts/graph.acn
```

> The HTML map loads `vis-network` from a CDN, so it needs internet access to render.

### 3.2 `astermesh query`

Look up symbols or inspect the graph without starting a server.

```bash
astermesh query [SYMBOL] [-p PATH] [--overview] [--list-communities]
```

| Option | Description |
| :--- | :--- |
| `SYMBOL` | Case-insensitive. Matches any node whose ID contains `SYMBOL`, or whose short name equals `SYMBOL` |
| `-p`, `--path` | Workspace root (default `.`) |
| `--overview` | Print node, edge and community counts |
| `--list-communities` | Print every community with its God Node and size |

Output format for symbol lookup:

```text
[class] src.astermesh.graph.builder.GraphBuilder -> src/astermesh/graph/builder.py:24-259
```

Line numbers are 1-based and inclusive.

### 3.3 `astermesh serve`

Start the MCP server. The graph is built once at startup and then kept in sync by a file watcher.

```bash
astermesh serve [PATH] [--transport stdio|sse|streamable-http] [--host HOST] [--port PORT] [--no-watch] [--context-max-tokens N]
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `PATH` | `.` | Workspace root |
| `--transport` | `stdio` | MCP transport |
| `--host`, `--port` | `127.0.0.1`, `8000` | Bind address, used by the `sse` transport |
| `--no-watch` | off | Disable incremental updates |
| `--context-max-tokens` | none | Optional token budget applied to `codebase://context` |

### 3.4 `astermesh benchmark`

Compare the token size of raw source code against `#ACN2`, `#ACN1`, and optional legacy XML.

```bash
astermesh benchmark [PATH] [-r REPORT_PATH] [--max-tokens N] [--include-xml-legacy]
```

Tokens are counted with `tiktoken` (`cl100k_base`); if it is unavailable, the count falls back to `characters / 4`. Cost estimates assume USD 3.00 per 1M input tokens. See [BENCHMARK.md](BENCHMARK.md) for methodology.

---

## 4. Using Astermesh with an AI Assistant (MCP)

### 4.1 Client configuration

Add the server to your client's `mcpServers` configuration (Cursor, Claude Desktop, Antigravity, ...):

```json
{
  "mcpServers": {
    "astermesh": {
      "command": "astermesh",
      "args": ["serve", "/absolute/path/to/your/project", "--transport", "stdio"]
    }
  }
}
```

If `astermesh` is not on the client's `PATH`, point `command` to the virtual environment binary, for example `/path/to/astermesh/.venv/bin/astermesh`.

### 4.2 Tools

| Tool | Arguments | Returns |
| :--- | :--- | :--- |
| `locate_symbol` | `name` | Up to 25 matching nodes with `file_path`, `line_start`, `line_end` |
| `get_file_outline` | `file_path` | All entities of a file, sorted by line |
| `get_neighbors` | `symbol`, `direction` = `in` / `out` / `both` | 1-hop incoming and outgoing relations with locations |
| `get_impact_radius` | `symbol`, `max_depth` = 2 | Transitive incoming dependents per depth, affected files, and a risk level (`LOW` < 3, `MEDIUM` < 10, `HIGH` >= 10 dependents) |
| `trace_path` | `source`, `target` (exact node IDs) | Shortest path between two nodes, ignoring edge direction |
| `get_community` | `name` (community name or ID) | All members of a Leiden community |
| `get_community_wire` | `name`, `max_tokens` (optional) | Standalone `#ACN2` wire slice for one community |
| `read_file_snippet` | `file_path`, `start_line`, `end_line` | Targeted physical line slice inside workspace |
| `rebuild_graph` | none | Full rescan; returns node, edge and community counts |

`locate_symbol`, `get_neighbors` and `get_impact_radius` accept either a short name or a full node ID. `trace_path` requires exact IDs; obtain them with `locate_symbol` first.

### 4.3 Resources

| URI | Content |
| :--- | :--- |
| `codebase://context` | Dense `#ACN2` wire representation of the repository graph |
| `codebase://report` | Macro architecture report (same content as `GRAPH_REPORT.md`) |
| `codebase://communities` | List of communities with God Nodes and sizes |

### 4.4 Recommended navigation protocol

To keep the assistant's context small, instruct it to follow a graph-first workflow. A ready-to-use rule file is provided at [`.astermesh/AGENTS.md`](../.astermesh/AGENTS.md):

1. **Orient**: read `codebase://report` or `GRAPH_REPORT.md`, then `get_community` for the relevant subsystem.
2. **Trace**: use `get_neighbors`, `get_impact_radius` and `trace_path` to understand dependencies before editing.
3. **Slice**: use `locate_symbol` and read only the returned `[line_start, line_end]` range.

---

## 5. Reading the `#ACN2` Compact Wire Format

`context_graph.acn` uses a line-oriented `#ACN2` wire format with prefix compression and single-character edge operators to minimize `BPE` tokens:

```text
#ACN2 root:myproject mode:L0 t={c:cls,f:fn,v:var,u:ui,k:hook,s:svc,m:mod,g:cfg,d:doc,a:ast} ops={^:inh,~:ui,+:inj,>:call,&:ref}
@D d1=src/core
@F 1:d1/database.py;2:d1/auth.py
@C1 Authenticator *2:Authenticator|2[Authenticator*:c@3-11;login:f@4-8>1:DBConnection,1:connect&1:DB_TIMEOUT]
```

| Record / operator | Meaning |
| :--- | :--- |
| `#ACN2 root:... mode:L0\|L1\|L2` | Schema header and resolution mode (`L0` lossless, `L1` pruned, `L2` macro skeleton) |
| `@D` | Directory prefix dictionary (`d1=...`) shared by `@F` and `@A` |
| `@F`, `@A` | Indexed file table (`1:...`) and isolated asset table (`a1:...`) |
| `@<cid> <name> *<god_ref>\|...` | Leiden community members grouped by file ID (`<sym>[*]:<t>@<lines><ops>`) |
| `@U` | Bridged satellite/unclustered nodes linked to communities |
| `@E` | Inter-community weighted bridge edges in `L2` skeleton mode |
| `^`, `~`, `+`, `>`, `&` | Inherits, renders, injects, calls, references (`<t_fid>:<target>` when cross-file, `<aid>` for assets) |

Deprecated XML serialization remains available opt-in via `--format xml` or `--include-xml-legacy`.

---

## 6. Python API

The package can be used as a library:

```python
from pathlib import Path

from astermesh import GraphBuilder
from astermesh.graph.clustering import CommunityClusterer
from astermesh.serializers.compact_wire import export_compact_wire

builder = GraphBuilder(Path("."))
graph = builder.build_full()                 # networkx.MultiDiGraph
communities = CommunityClusterer().cluster(graph)

node = graph.nodes["src.astermesh.graph.builder.GraphBuilder"]
print(node["file_path"], node["line_start"], node["line_end"])

export_compact_wire(graph, communities, "astermesh", Path("astermesh-graph/context_graph.acn"))
```

Incremental updates:

```python
builder.update_file(Path("src/astermesh/cli.py"))   # re-parse one file
builder.remove_path("src/astermesh/old_module.py")   # drop a file and its entities
```

All graph mutations are guarded by `builder.lock` (a re-entrant lock); hold it when reading the graph from another thread.

---

## 7. Limitations

- Resolution is static: dynamic dispatch, `getattr`, monkey patching, reflection, and runtime-evaluated imports are not tracked.
- `trace_path` treats the graph as undirected, so a path indicates structural proximity, not necessarily an execution order.
- The HTML map is intended for small and medium repositories; very large graphs render slowly in the browser.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
| :--- | :--- |
| `astermesh: command not found` | Activate the virtual environment, or run `python -m astermesh` |
| Symbol not found | Check that the file extension is supported and the directory is not ignored (Section 2.2). Remember FQNs depend on the indexed root (Section 2.3) |
| MCP client shows no tools | Use an absolute workspace path in `args`, and an absolute `command` path if the client does not inherit your shell `PATH` |
| HTML map is blank | The page needs internet access to load `vis-network` from the CDN |
| Graph is stale while serving | The watcher is disabled (`--no-watch`) or the file is in an ignored directory; call the `rebuild_graph` tool |
