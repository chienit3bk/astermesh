from pathlib import Path

from astermesh.graph.builder import GraphBuilder
from astermesh.graph.clustering import CommunityClusterer
from astermesh.graph.model import EdgeType
from astermesh.graph.query import GraphQuery
from astermesh.serializers.compact_wire import render_compact_wire


# kiem thu 5 bat bien co lap khong gian asset
def test_five_invariants_of_isolated_asset_space(tmp_path: Path):
    (tmp_path / "src/assets").mkdir(parents=True)
    (tmp_path / "src/assets/logo.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "src/assets/unused.png").write_text("PNG", encoding="utf-8")
    (tmp_path / "src/btn.module.css").write_text(".btn {}", encoding="utf-8")
    (tmp_path / "src/global.css").write_text("body {}", encoding="utf-8")

    (tmp_path / "src/PrimaryButton.tsx").write_text(
        """import LogoIcon from './assets/logo.svg?react';
import styles from './btn.module.css';
import './global.css';

export function PrimaryButton() {
    return <button className={styles.btn}><LogoIcon /></button>;
}

export function SecondaryText() {
    return <span>ok</span>;
}
""",
        encoding="utf-8",
    )

    builder = GraphBuilder(tmp_path)
    g = builder.build_full()

    # invariant 5: lazy asset creation
    assert g.has_node("src/assets/logo.svg")
    assert g.has_node("src/btn.module.css")
    assert g.has_node("src/global.css")
    assert not g.has_node("src/assets/unused.png")

    # invariant 4: two-step function-level edge mapping
    btn_edges = [
        (v, d["type"]) for _, v, d in g.out_edges("src.PrimaryButton.PrimaryButton", data=True)
    ]
    assert ("src/assets/logo.svg", EdgeType.RENDERS.value) in btn_edges
    assert ("src/btn.module.css", EdgeType.REFERENCES.value) in btn_edges

    # side-effect import stays at file level
    file_edges = [(v, d["type"]) for _, v, d in g.out_edges("src/PrimaryButton.tsx", data=True)]
    assert ("src/global.css", EdgeType.IMPORTS.value) in file_edges

    # reverse impact_radius from asset reaches consuming component
    q = GraphQuery(g)
    impact = q.impact_radius("src/assets/logo.svg", max_depth=2)
    affected_ids = [item["id"] for item in impact["impact_by_depth"].get(1, [])]
    assert "src.PrimaryButton.PrimaryButton" in affected_ids
    assert "src.PrimaryButton.SecondaryText" not in affected_ids

    # invariant 1: asset isolation from leiden clustering
    clusterer = CommunityClusterer(seed=0, partition_mode="cpm", resolution_parameter=0.05)
    communities = clusterer.cluster(g)
    for c in communities:
        assert "src/assets/logo.svg" not in c.members
        assert "src/btn.module.css" not in c.members
    assert g.nodes["src/assets/logo.svg"]["community_id"] is None

    # acn2 excludes isolated assets from @F and registers them in @A
    acn_out = render_compact_wire(g, communities, "app")
    acn_lines = acn_out.splitlines()
    assert acn_lines[0].startswith("#ACN2 ")
    assert "mode:L0" in acn_lines[0]
    file_table_line = next(ln for ln in acn_lines if ln.startswith("@F "))
    asset_table_line = next(ln for ln in acn_lines if ln.startswith("@A "))
    assert "logo.svg" not in file_table_line
    assert "PrimaryButton.tsx" in file_table_line
    assert "logo.svg" in asset_table_line
