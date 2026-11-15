import asyncio
import json
from pathlib import Path

from astermesh.server import create_mcp_server


# kiem thu toan dien cong cu va tai nguyen mcp server
def test_server_tools_resources_and_community_wire(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'test'\nlicense = 'MIT'\n",
        encoding="utf-8",
    )
    (tmp_path / "service.py").write_text(
        """class UserService:
    def get_user(self, user_id):
        return {"id": user_id}

def main():
    srv = UserService()
    return srv.get_user(1)
""",
        encoding="utf-8",
    )

    async def _run():
        server = create_mcp_server(tmp_path, watch=False, context_max_tokens=300)

        tools = await server.list_tools()
        assert len(tools) == 9
        for t in tools:
            assert t.description and len(t.description.strip()) > 15

        resources = await server.list_resources()
        uris = {str(r.uri) for r in resources}
        assert {"codebase://context", "codebase://report", "codebase://communities"}.issubset(uris)

        ctx = await server.read_resource("codebase://context")
        assert "#ACN2" in str(ctx)
        assert "Architecture Snapshot" in str(await server.read_resource("codebase://report"))
        assert "Discovered Architectural Communities" in str(
            await server.read_resource("codebase://communities")
        )

        locate_res = await server.call_tool("locate_symbol", {"name": "UserService"})
        assert locate_res is not None and len(locate_res.content) > 0

        outline_res = await server.call_tool("get_file_outline", {"file_path": "service.py"})
        assert outline_res is not None and len(outline_res.content) > 0

        comm_ok = await server.call_tool("get_community", {"name": "C1"})
        assert json.loads(comm_ok.content[0].text)["id"] == "C1"

        comm_err = await server.call_tool("get_community", {"name": "Missing"})
        assert "error" in json.loads(comm_err.content[0].text)

        wire_ok = await server.call_tool("get_community_wire", {"name": "C1", "max_tokens": 200})
        assert "#ACN2 " in wire_ok.content[0].text
        assert "@C1 " in wire_ok.content[0].text

        wire_err = await server.call_tool("get_community_wire", {"name": "Missing"})
        assert "Error:" in wire_err.content[0].text

        snippet = await server.call_tool(
            "read_file_snippet",
            {"file_path": "pyproject.toml", "start_line": 2, "end_line": 3},
        )
        payload = json.loads(snippet.content[0].text)
        assert "2: name = 'test'" in payload["content"]
        assert "3: license = 'MIT'" in payload["content"]

        bad_snippet = await server.call_tool("read_file_snippet", {"file_path": "../../etc/passwd"})
        assert "error" in json.loads(bad_snippet.content[0].text)

        rebuilt = await server.call_tool("rebuild_graph", {})
        assert json.loads(rebuilt.content[0].text)["status"] == "rebuilt"

    asyncio.run(_run())
