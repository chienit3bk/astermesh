import threading
from pathlib import Path

from watchdog.events import (
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
)

from astermesh.graph.builder import GraphBuilder
from astermesh.graph.watcher import GraphEventHandler


def test_watcher_event_handler(tmp_path: Path):
    # arrange
    builder = GraphBuilder(tmp_path)
    builder.build_full()
    callback_fired = False

    def on_update():
        nonlocal callback_fired
        callback_fired = True

    handler = GraphEventHandler(builder, on_updated=on_update, debounce_sec=0.01)

    # act: simulate creating a file
    fpath = tmp_path / "mod.py"
    fpath.write_text("def worker(): pass\n", encoding="utf-8")
    event_created = FileCreatedEvent(str(fpath))
    handler.on_any_event(event_created)

    # assert: builder updated
    assert builder.graph.has_node("mod.worker")

    # act: simulate deleting the file
    fpath.unlink()
    event_deleted = FileDeletedEvent(str(fpath))
    handler.on_any_event(event_deleted)

    # assert: builder removed
    assert not builder.graph.has_node("mod.worker")


# kiem thu su kien moved, reload tsconfig, ignore node_modules va debounce
def test_watcher_moved_tsconfig_ignore_and_debounce(tmp_path: Path):
    (tmp_path / "src").mkdir()
    old_f = tmp_path / "src/OldComp.tsx"
    old_f.write_text("export const OldComp = () => <div />;", encoding="utf-8")

    builder = GraphBuilder(tmp_path)
    builder.build_full()
    assert builder.graph.has_node("src.OldComp.OldComp")

    fired = threading.Event()
    handler = GraphEventHandler(builder, on_updated=fired.set, debounce_sec=0.02)

    new_f = tmp_path / "src/NewComp.tsx"
    old_f.rename(new_f)
    new_f.write_text("export const NewComp = () => <span />;", encoding="utf-8")
    handler.on_any_event(FileMovedEvent(str(old_f), str(new_f)))

    assert not builder.graph.has_node("src.OldComp.OldComp")
    assert builder.graph.has_node("src.NewComp.NewComp")
    assert fired.wait(timeout=1.0)

    nm_dir = tmp_path / "node_modules/pkg"
    nm_dir.mkdir(parents=True)
    nm_file = nm_dir / "index.js"
    nm_file.write_text("function skip() {}", encoding="utf-8")
    handler.on_any_event(FileCreatedEvent(str(nm_file)))
    assert not builder.graph.has_node("node_modules.pkg.index.skip")

    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {"paths": {"@/*": ["src/*"]}}}', encoding="utf-8")
    handler.on_any_event(FileModifiedEvent(str(tsconfig)))
    assert builder.resolver._has_aliases is True


# watcher readonly filter and config lock
def test_watcher_ignores_readonly_events_and_locks_reload(tmp_path: Path):
    src_file = tmp_path / "app.py"
    src_file.write_text("def hello(): pass\n", encoding="utf-8")
    tsconfig = tmp_path / "tsconfig.json"
    tsconfig.write_text('{"compilerOptions": {}}', encoding="utf-8")

    builder = GraphBuilder(tmp_path)
    builder.build_full()

    updates: list[str] = []
    handler = GraphEventHandler(builder, on_updated=lambda: updates.append("ok"), debounce_sec=0.01)

    src_file.write_text("def changed(): pass\n", encoding="utf-8")
    for etype in ("opened", "closed_no_write", "accessed", "closed"):
        ev = FileSystemEvent(str(src_file))
        ev.event_type = etype
        handler.on_any_event(ev)

    assert not builder.graph.has_node("app.changed")
    assert handler._timer is None
    assert updates == []

    lock_busy = False
    orig_reload = builder.resolver.reload_config

    def tracked_reload() -> None:
        nonlocal lock_busy

        def probe() -> None:
            nonlocal lock_busy
            acquired = builder.lock.acquire(blocking=False)
            if acquired:
                builder.lock.release()
            else:
                lock_busy = True

        t = threading.Thread(target=probe)
        t.start()
        t.join(timeout=1.0)
        orig_reload()

    builder.resolver.reload_config = tracked_reload  # type: ignore[method-assign]
    tsconfig.write_text('{"compilerOptions": {"paths": {"@/*": ["src/*"]}}}', encoding="utf-8")
    handler.on_any_event(FileModifiedEvent(str(tsconfig)))

    assert lock_busy is True
    assert builder.resolver._has_aliases is True
