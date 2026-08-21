"""Interactive Textual UI for browsing a plan and applying it."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from fileshelf.apply import apply_plan
from fileshelf.config import Config, load_config
from fileshelf.format import human_size
from fileshelf.models import MoveAction, Plan, ScanResult
from fileshelf.planner import LAYOUTS, plan_from_scan
from fileshelf.scanner import scan as scan_dir

_CSS = """
Screen {
    background: #10161e;
    color: #d6dde6;
}

Header {
    background: #1a2332;
    color: #e8b86d;
    text-style: bold;
}

Footer {
    background: #1a2332;
}

#body {
    height: 1fr;
}

#sidebar {
    width: 32;
    min-width: 24;
    border: tall #3d4f63;
    background: #182230;
}

#sidebar-title {
    padding: 1 1 0 1;
    color: #7eb8c9;
    text-style: bold;
}

#categories {
    height: 1fr;
    padding: 0 0 1 0;
    background: #182230;
}

#main {
    border: tall #3d4f63;
    background: #141b24;
}

#files {
    height: 1fr;
}

#summary {
    height: 3;
    padding: 0 1;
    background: #1a2332;
    color: #a8b4c4;
    border-top: solid #3d4f63;
}

DataTable {
    background: #141b24;
}

DataTable > .datatable--header {
    color: #e8b86d;
    text-style: bold;
    background: #1a2332;
}

DataTable > .datatable--cursor {
    background: #2a4158;
    color: #f4efe6;
    text-style: bold;
}

OptionList {
    background: #182230;
}

OptionList > .option-list--option-highlighted {
    background: #2a4158;
    color: #e8b86d;
}

ConfirmScreen {
    align: center middle;
    background: #10161e 60%;
}

#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: auto auto;
    padding: 1 2;
    width: 64;
    height: auto;
    border: tall #e8b86d;
    background: #1a2332;
}

#question {
    column-span: 2;
    content-align: center middle;
    padding: 1 0;
    color: #d6dde6;
}

Button {
    width: 1fr;
}
"""


class ConfirmScreen(ModalScreen[bool]):
    CSS = _CSS

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(self.message, id="question"),
            Button("Cancel", variant="default", id="no"),
            Button("Apply", variant="warning", id="yes"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class ShelfApp(App[None]):
    CSS = _CSS
    TITLE = "fileshelf"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_row", "Toggle"),
        Binding("a", "apply", "Apply"),
        Binding("r", "reload", "Rescan"),
        Binding("l", "cycle_layout", "Layout"),
        Binding("d", "toggle_dupes", "Skip dupes"),
        Binding("tab", "focus_next", "Focus", show=False),
    ]

    def __init__(
        self,
        root: Path,
        dest: Path | None,
        layout: str,
        cfg: Config,
        force_home: bool = False,
    ) -> None:
        super().__init__()
        self.root = root
        self.dest = dest
        self.layout = layout
        self.cfg = cfg
        self.force_home = force_home
        self.skip_duplicates = cfg.skip_duplicates
        self.scan_result: ScanResult | None = None
        self.plan: Plan | None = None
        self.actions: list[MoveAction] = []
        self.excluded: set[str] = set()
        self.category = "All"
        self._loading = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Static("Categories", id="sidebar-title")
                yield OptionList(id="categories")
            with Vertical(id="main"):
                yield DataTable(id="files", cursor_type="row", zebra_stripes=True)
        yield Static("Scanning…", id="summary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#files", DataTable)
        table.add_column("On", key="on", width=4)
        table.add_column("Size", key="size", width=10)
        table.add_column("File", key="file")
        table.add_column("Shelf", key="shelf")
        self._reload()

    def _reload(self) -> None:
        if self._loading:
            return
        self._loading = True
        self.query_one("#summary", Static).update("Scanning…")
        self.run_worker(self._scan_worker, exclusive=True, thread=True)

    def _scan_worker(self) -> None:
        result = scan_dir(
            self.root,
            recursive=self.cfg.recursive,
            include_hidden=self.cfg.include_hidden,
            extra_skip_dirs=set(self.cfg.skip_directories),
            rules=self.cfg.rules,
        )
        organized = plan_from_scan(
            result,
            dest=self.dest,
            layout=self.layout,
            skip_duplicates=self.skip_duplicates,
        )
        self.call_from_thread(self._ingest, result, organized)

    def _ingest(self, result: ScanResult, organized: Plan) -> None:
        self._loading = False
        self.scan_result = result
        self.plan = organized
        self.actions = list(organized.actions)
        still = {str(a.source) for a in self.actions}
        self.excluded &= still
        self.sub_title = f"{self.root}  ·  {self.layout}"
        self._fill_categories()
        self._fill_table()
        self._fill_summary()

    def _fill_categories(self) -> None:
        options: list[Option] = []
        counts: dict[str, int] = {}
        sizes: dict[str, int] = {}
        for action in self.actions:
            counts[action.category] = counts.get(action.category, 0) + 1
            sizes[action.category] = sizes.get(action.category, 0) + action.size_bytes
        options.append(Option(f"All  ({len(self.actions)})", id="All"))
        for cat in sorted(counts, key=lambda c: (-counts[c], c)):
            options.append(
                Option(
                    f"{cat}  ({counts[cat]} · {human_size(sizes[cat])})",
                    id=cat,
                )
            )
        listing = self.query_one("#categories", OptionList)
        listing.clear_options()
        listing.add_options(options)
        try:
            listing.highlighted = listing.get_option_index(self.category)
        except Exception:
            self.category = "All"
            listing.highlighted = 0

    def _visible(self) -> list[MoveAction]:
        if self.category == "All":
            return self.actions
        return [a for a in self.actions if a.category == self.category]

    def _rel(self, path: Path, base: Path) -> str:
        try:
            return str(path.relative_to(base))
        except ValueError:
            return str(path)

    def _fill_table(self) -> None:
        table = self.query_one("#files", DataTable)
        table.clear()
        dest_root = self.plan.destination_root if self.plan else self.root
        for action in self._visible():
            key = str(action.source)
            included = key not in self.excluded
            table.add_row(
                "●" if included else "○",
                human_size(action.size_bytes),
                self._rel(action.source, self.root),
                self._rel(action.destination, dest_root),
                key=key,
            )

    def _fill_summary(self) -> None:
        included = [a for a in self.actions if str(a.source) not in self.excluded]
        skipped = len(self.plan.skipped) if self.plan else 0
        dupes = "on" if self.skip_duplicates else "off"
        text = (
            f"{len(included)} selected of {len(self.actions)} moves  ·  "
            f"{human_size(sum(a.size_bytes for a in included))}  ·  "
            f"{skipped} skipped  ·  skip-dupes {dupes}  ·  "
            "space toggle  ·  a apply  ·  l layout  ·  r rescan"
        )
        self.query_one("#summary", Static).update(text)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id != "categories":
            return
        new_cat = event.option.id or "All"
        if new_cat == self.category:
            return
        self.category = new_cat
        self._fill_table()

    def action_toggle_row(self) -> None:
        table = self.query_one("#files", DataTable)
        if table.row_count == 0:
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        if row_key is None or row_key.value is None:
            return
        key = str(row_key.value)
        if key in self.excluded:
            self.excluded.remove(key)
            mark = "●"
        else:
            self.excluded.add(key)
            mark = "○"
        table.update_cell(row_key, "on", mark)
        self._fill_summary()

    def action_cycle_layout(self) -> None:
        idx = LAYOUTS.index(self.layout) if self.layout in LAYOUTS else 0
        self.layout = LAYOUTS[(idx + 1) % len(LAYOUTS)]
        self.notify(f"Layout: {self.layout}")
        self._reload()

    def action_toggle_dupes(self) -> None:
        self.skip_duplicates = not self.skip_duplicates
        self.notify(f"Skip duplicates: {'on' if self.skip_duplicates else 'off'}")
        self._reload()

    def action_reload(self) -> None:
        self._reload()

    def action_apply(self) -> None:
        included = [a for a in self.actions if str(a.source) not in self.excluded]
        if not included:
            self.notify("Nothing selected.", severity="warning")
            return
        size = human_size(sum(a.size_bytes for a in included))
        message = f"Move {len(included)} files ({size}) with layout '{self.layout}'?"

        def _done(confirmed: bool | None) -> None:
            if confirmed:
                self._do_apply(included)

        self.push_screen(ConfirmScreen(message), _done)

    def _do_apply(self, included: list[MoveAction]) -> None:
        if not self.plan:
            return
        subset = Plan(
            root=self.plan.root,
            destination_root=self.plan.destination_root,
            layout=self.plan.layout,
            actions=included,
            skipped=self.plan.skipped,
        )
        extra = (Path.home() / "Library", *self.cfg.protect_paths)
        result = apply_plan(
            subset,
            dry_run=False,
            conflict=self.cfg.conflict,
            extra_deny=extra,
            force_home=self.force_home,
        )
        if result.errors and not result.moved:
            self.notify(result.errors[0], severity="error")
            return
        self.notify(
            f"Moved {len(result.moved)} files · session {result.session_id}",
            severity="information",
        )
        self._reload()


def run_tui(
    root: Path,
    dest: Path | None = None,
    layout: str = "smart",
    *,
    force_home: bool = False,
) -> None:
    cfg = load_config()
    ShelfApp(root=root, dest=dest, layout=layout, cfg=cfg, force_home=force_home).run()
