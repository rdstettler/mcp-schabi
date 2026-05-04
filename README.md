# mcp-schabi

An **MCP (Model Context Protocol) Server** that lets AI assistants (e.g. Claude)
retrieve homework, tasks and events from the **Schabi** platform for one or
more children.

Schabi is a popular Swiss/German homework & school communication platform.
This server exposes your children's Schabi accounts as MCP tools so that any
MCP-compatible AI client can answer questions like:

- *"What homework does Emma have today?"*
- *"Are there any events for Lucas this week?"*
- *"Has Emma completed her math assignment?"*

The server supports **multiple children** from a single MCP server instance –
simply configure several username / password / schoolClass combinations.

---

## Features

| MCP Tool          | Description                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| `get_children`    | List all configured child call-names (nothing else – keeps it simple)       |
| `get_homework`    | Return today's (or a specific date's) homework & events for a given child   |

Each homework item contains:
- `day` (YYYY-MM-DD)
- `isEvent` (bool)
- `task` (description)
- `done` (bool for tasks, null for events)

---

## Requirements

- Python 3.11+ **or** a container runtime (Podman / Docker)
- Schabi account(s) for the child(ren)
- The numeric `schoolClass` ID for each child (visible in the Schabi UI or API responses)

---

## Configuration

All configuration is done via **environment variables**:

### Multi-child setup (recommended)

```bash
SCHABI_CHILDREN="Emma,Lucas"
SCHABI_EMMA_USERNAME=emma_card_or_email
SCHABI_EMMA_PASSWORD=secret123
SCHABI_EMMA_SCHOOLCLASS=24088

SCHABI_LUCAS_USERNAME=lucas_card_or_email
SCHABI_LUCAS_PASSWORD=anothersecret
SCHABI_LUCAS_SCHOOLCLASS=24089
```

### Legacy single-child

```bash
SCHABI_USERNAME=...
SCHABI_PASSWORD=...
SCHABI_SCHOOLCLASS=...
```

> **Tip:** Call-names (`Emma`, `Lucas`, …) are free-form strings you choose.
> They are used in the `get_homework` tool call. Use simple alphanumeric names
> for easiest environment variable matching.

---

## Running with Podman (recommended)

### 1. Build the container image

```bash
podman build -t mcp-schabi .
```

### 2. Run the MCP server

```bash
podman run -d --name mcp-schabi -p 8006:8006 --env-file .env mcp-schabi
```

### 3. Add to your MCP client

For **Antigravity** (or any streamable-http client):

```json
{
  "mcpServers": {
    "schabi": {
      "serverUrl": "http://[IP_ADDRESS]:8006/mcp"
    }
  }
}
```

---

## Running without a container

### 1. Install

```bash
pip install .
```

### 2. Set environment variables

```bash
export SCHABI_CHILDREN="Emma,Lucas"
export SCHABI_EMMA_USERNAME=...
export SCHABI_EMMA_PASSWORD=...
export SCHABI_EMMA_SCHOOLCLASS=24088
# ... repeat for other children
```

### 3. Run (stdio transport – for local MCP clients)

```bash
mcp-schabi
```

Or directly:

```bash
python -m mcp_schabi.server
```

For HTTP transport (e.g. testing):

```bash
fastmcp run mcp_schabi.server:mcp --transport streamable-http --host 0.0.0.0 --port 8006
```

---

## License

MIT – see [LICENSE](LICENSE).
