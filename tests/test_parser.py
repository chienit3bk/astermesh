from pathlib import Path

from astermesh.parser.engine import ASTEngine
from astermesh.parser.extractors.sfc import _kebab_to_pascal, extract_template_tags


# kiem thu danh sach phan mo rong ho tro
def test_parser_supported_extensions():
    engine = ASTEngine()
    exts = engine.supported_extensions

    assert {".py", ".js", ".ts", ".tsx", ".vue", ".svelte"}.issubset(exts)
    assert engine.supports(".PY")
    assert engine.supports(".vue")
    assert not engine.supports(".cpp")


# kiem thu phan tich python, relative import va decorator
def test_parse_python_file_and_relative_imports(tmp_path: Path):
    pkg = tmp_path / "pkg" / "sub"
    pkg.mkdir(parents=True)
    init_file = pkg / "__init__.py"
    init_file.write_text("DEFAULT_TIMEOUT = 30\n", encoding="utf-8")

    code = """import os as operating_sys
from . import sibling
from ..core import BaseRunner as Runner

GLOBAL_LIMIT = 100

def deco(fn):
    return fn

@deco
class Calculator(Runner):
    def add(self, a: int, b: int = 1, c=2):
        return a + b + c

    @deco
    async def compute(self, val):
        return self.add(val, GLOBAL_LIMIT)
"""
    fpath = pkg / "math_mod.py"
    fpath.write_text(code, encoding="utf-8")
    engine = ASTEngine()

    init_res = engine.parse_file(init_file, tmp_path)
    assert init_res is not None
    assert init_res.module_fqn == "pkg.sub"

    result = engine.parse_file(fpath, tmp_path)
    assert result is not None
    assert result.module_fqn == "pkg.sub.math_mod"
    assert result.imports["operating_sys"] == "os"
    assert result.imports["sibling"] == "pkg.sub.sibling"
    assert result.imports["Runner"] == "pkg.core.BaseRunner"

    by_name = {e.name: e for e in result.entities}
    assert by_name["Calculator"].bases == ["Runner"]
    assert by_name["add"].parameters == ["self", "a", "b", "c"]
    assert by_name["compute"].is_async is True
    assert by_name["compute"].is_method is True
    assert "GLOBAL_LIMIT" in by_name["compute"].references


# kiem thu thu thap bien cuc bo ts_scope va the sfc
def test_ts_scope_destructuring_locals_and_sfc_tags(tmp_path: Path):
    code = """export function process(
    { id, meta: { tag = 'v1' } }: any,
    [first, ...rest]: number[],
    fallback = 10
) {
    const [localA, { nestedB }] = rest as any;
    function innerHelper(paramX: string) { return paramX; }
    class LocalBox {}
    const arrow = item => item;
    for (const loopVar of rest) {
        try { innerHelper(String(loopVar)); } catch (errObj) {}
    }
    return [id, tag, first, fallback, localA, nestedB];
}
"""
    fpath = tmp_path / "scope.ts"
    fpath.write_text(code, encoding="utf-8")
    res = ASTEngine().parse_file(fpath, tmp_path)
    assert res is not None
    proc = next(e for e in res.entities if e.name == "process")

    expected_locals = {
        "id",
        "tag",
        "first",
        "rest",
        "fallback",
        "localA",
        "nestedB",
        "innerHelper",
        "paramX",
        "LocalBox",
        "arrow",
        "item",
        "loopVar",
        "errObj",
    }
    assert expected_locals.issubset(proc.local_names)

    assert _kebab_to_pascal("user-profile-card") == "UserProfileCard"
    tags = extract_template_tags("<div><user-card /><ModalDialog /><router-view /></div>")
    assert tags == ["UserCard", "ModalDialog"]
