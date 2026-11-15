from pathlib import Path

import networkx as nx
import pytest

from astermesh.graph.model import CommunityInfo, EdgeType, NodeType
from astermesh.serializers.compact_wire import export_compact_wire
from astermesh.serializers.html_visual import export_html_visual
from astermesh.serializers.markdown_report import export_markdown_report, render_markdown_report
from astermesh.serializers.xml_context import export_semantic_xml, render_semantic_xml


def _build_sample_graph():
    g = nx.MultiDiGraph()
    g.add_node("file_a.py", type=NodeType.FILE.value, file_path="file_a.py")
    g.add_node("file_b.py", type=NodeType.FILE.value, file_path="file_b.py")
    g.add_node(
        "file_a.Hero",
        type=NodeType.CLASS.value,
        name="Hero",
        file_path="file_a.py",
        line_start=1,
        line_end=20,
    )
    g.add_node(
        "file_b.villain",
        type=NodeType.FUNCTION.value,
        name="villain",
        file_path="file_b.py",
        line_start=1,
        line_end=10,
    )

    g.add_edge("file_a.Hero", "file_b.villain", type=EdgeType.CALLS.value)
    g.add_edge("file_a.py", "file_b.villain", type=EdgeType.IMPORTS.value)
    return g


# kiem thu canh bao ngung ho tro xml legacy
def test_render_and_export_semantic_xml(tmp_path: Path):
    g = _build_sample_graph()
    comms = [
        CommunityInfo(
            id="C0",
            name="battle",
            size=2,
            god_node="file_a.Hero",
            members=["file_a.Hero", "file_b.villain"],
        )
    ]

    with pytest.warns(DeprecationWarning):
        xml_str = render_semantic_xml(g, comms, "my_repo", compact=True)
    assert "<c_graph" in xml_str
    assert "<files>" in xml_str

    with pytest.warns(DeprecationWarning):
        verbose_xml = render_semantic_xml(g, comms, "my_repo", compact=False)
    assert "<codebase_knowledge_graph" in verbose_xml

    out_file = tmp_path / "graph.xml"
    with pytest.warns(DeprecationWarning):
        export_semantic_xml(g, comms, "my_repo", out_file, compact=True)
    assert out_file.read_text(encoding="utf-8") == xml_str


# kiem thu xuat bao cao kien truc markdown
def test_render_and_export_markdown_report(tmp_path: Path):
    g = _build_sample_graph()
    comms = [
        CommunityInfo(
            id="C0",
            name="battle",
            size=2,
            god_node="file_a.Hero",
            members=["file_a.Hero", "file_b.villain"],
        )
    ]

    report_str = render_markdown_report(g, comms, "my_repo")
    assert "# Architecture Snapshot: `my_repo`" in report_str
    assert "## 1. Macro Statistics" in report_str
    assert "## 2. Functional Communities" in report_str

    out_file = tmp_path / "report.md"
    export_markdown_report(g, comms, "my_repo", out_file)
    assert out_file.read_text(encoding="utf-8") == report_str


# kiem thu xuat acn2 wire fe va html visual
def test_serializers_acn2_and_html_visual(tmp_path: Path):
    g = nx.MultiDiGraph()
    g.add_node("src/App.tsx", type=NodeType.FILE.value, file_path="src/App.tsx")
    g.add_node(
        "src/assets/icon.svg",
        type=NodeType.ASSET.value,
        name="icon.svg",
        file_path="src/assets/icon.svg",
    )
    g.add_node(
        "src.App.App",
        type=NodeType.COMPONENT.value,
        name="App",
        file_path="src/App.tsx",
        line_start=1,
        line_end=10,
    )
    g.add_node(
        "src.App.useAuth",
        type=NodeType.HOOK.value,
        name="useAuth",
        file_path="src/App.tsx",
        line_start=12,
        line_end=15,
    )
    g.add_edge("src.App.App", "src.App.useAuth", type=EdgeType.CALLS.value)
    g.add_edge("src.App.App", "src/assets/icon.svg", type=EdgeType.RENDERS.value)

    comms = [
        CommunityInfo(
            id="C1",
            name="App",
            size=2,
            god_node="src.App.App",
            members=["src.App.App", "src.App.useAuth"],
        )
    ]

    acn_path = tmp_path / "graph.acn"
    acn_text = export_compact_wire(g, comms, "fe_app", acn_path)
    assert acn_path.exists()
    assert "#ACN2 " in acn_text
    assert "@A a1:src/assets/icon.svg" in acn_text
    assert "App*:u@1-10" in acn_text
    assert "~a1" in acn_text
    assert ">useAuth" in acn_text

    html_path = tmp_path / "view.html"
    export_html_visual(g, html_path)
    assert html_path.exists()
    html_content = html_path.read_text(encoding="utf-8")
    assert "src.App.App" in html_content
    assert "#ec4899" in html_content
