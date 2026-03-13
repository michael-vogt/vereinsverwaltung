"""
Vereinsverwaltung – Terminal User Interface
Erfordert: pip install textual httpx

Starten:  python tui.py
          python tui.py --api http://localhost:8000
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from typing import Any

import httpx
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button, ContentSwitcher, DataTable, Footer, Header,
    Input, Label, Select,
)

DEFAULT_API = "http://localhost:8000"

# ── Hilfsfunktionen ────────────────────────────────────────────────────────────

def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        y, m, d = iso[:10].split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return iso or "—"

def fmt_betrag(val: Any) -> str:
    try:
        return f"{float(val):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(val)

def today() -> str:
    return date.today().isoformat()

def clean_select(v: Any) -> str | None:
    """Wandelt Select-Werte sicher in str|None um. Filtert Select.BLANK heraus."""
    if v is None or v is Select.BLANK:
        return None
    s = str(v)
    return None if (s == "" or not s.lstrip("-").isdigit()) else s

# ── API-Client ─────────────────────────────────────────────────────────────────

class ApiClient:
    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def _c(self):
        return httpx.Client(base_url=self.base, timeout=10)

    def get(self, path, **params):
        with self._c() as c:
            r = c.get(path, params={k: v for k, v in params.items() if v is not None})
            r.raise_for_status()
            return r.json()

    def post(self, path, data):
        with self._c() as c:
            r = c.post(path, json=data)
            r.raise_for_status()
            return r.json()

    def put(self, path, data):
        with self._c() as c:
            r = c.put(path, json=data)
            r.raise_for_status()
            return r.json()

    def delete(self, path):
        with self._c() as c:
            r = c.delete(path)
            r.raise_for_status()

# ── Modals ─────────────────────────────────────────────────────────────────────

class ConfirmModal(ModalScreen):
    BINDINGS = [("escape", "no"), ("enter", "yes")]

    def __init__(self, msg: str):
        super().__init__()
        self.msg = msg

    def compose(self) -> ComposeResult:
        with Container(id="mb"):
            yield Label("Bestätigung", id="mt")
            yield Label(self.msg, id="mb2")
            with Horizontal(id="mbtns"):
                yield Button("Ja  [Enter]", variant="error",   id="by")
                yield Button("Nein [Esc]",  variant="default", id="bn")

    def action_yes(self): self.dismiss(True)
    def action_no(self):  self.dismiss(False)

    @on(Button.Pressed, "#by")
    def _y(self): self.dismiss(True)

    @on(Button.Pressed, "#bn")
    def _n(self): self.dismiss(False)


class MitgliedModal(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    def __init__(self, prefill: dict | None = None):
        super().__init__()
        self._p    = prefill or {}
        self._edit = bool(prefill)

    def compose(self) -> ComposeResult:
        titel   = "Mitglied bearbeiten" if self._edit else "Mitglied anlegen"
        btn_lbl = "Speichern" if self._edit else "Anlegen"
        with Container(id="mb"):
            yield Label(titel, id="mt")
            yield Label("Name")
            yield Input(value=self._p.get("name", ""), placeholder="Name", id="fn")
            yield Label("Status")
            yield Select(
                [("Aktiv", "aktiv"), ("Passiv", "passiv"),
                 ("Gast", "gast"), ("Ausgetreten", "ausgetreten")],
                value=self._p.get("status", "aktiv"), id="fs",
            )
            yield Label("Eintrittsdatum")
            yield Input(value=self._p.get("gueltig_von", today()), id="fd")
            with Horizontal(id="mbtns"):
                yield Button(f"{btn_lbl} [F5]",   variant="primary", id="bs")
                yield Button("Abbrechen [Esc]", variant="default", id="bc")

    def action_cancel(self): self.dismiss(None)

    @on(Button.Pressed, "#bc")
    def _c(self): self.dismiss(None)

    @on(Button.Pressed, "#bs")
    def _s(self):
        n = self.query_one("#fn", Input).value.strip()
        if not n:
            self.app.notify("Name fehlt", severity="error")
            return
        self.dismiss({
            "name":        n,
            "status":      self.query_one("#fs", Select).value,
            "gueltig_von": self.query_one("#fd", Input).value.strip(),
        })


class StatusModal(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    def __init__(self, name: str):
        super().__init__()
        self._name = name

    def compose(self) -> ComposeResult:
        with Container(id="mb"):
            yield Label("Statuswechsel", id="mt")
            yield Label(f"Mitglied: {self._name}", id="mh")
            yield Label("Neuer Status")
            yield Select(
                [("Aktiv", "aktiv"), ("Passiv", "passiv"),
                 ("Gast", "gast"), ("Ausgetreten", "ausgetreten")],
                value="aktiv", id="fs",
            )
            yield Label("Gültig ab")
            yield Input(value=today(), id="fd")
            with Horizontal(id="mbtns"):
                yield Button("Speichern [F5]",  variant="primary", id="bs")
                yield Button("Abbrechen [Esc]", variant="default", id="bc")

    def action_cancel(self): self.dismiss(None)

    @on(Button.Pressed, "#bc")
    def _c(self): self.dismiss(None)

    @on(Button.Pressed, "#bs")
    def _s(self):
        d = self.query_one("#fd", Input).value.strip()
        if not d:
            self.app.notify("Datum fehlt", severity="error")
            return
        self.dismiss({
            "neuer_status": self.query_one("#fs", Select).value,
            "gueltig_ab":   d,
        })


class KontoModal(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    def __init__(self, prefill: dict | None = None):
        super().__init__()
        self._p    = prefill or {}
        self._edit = bool(prefill)

    def compose(self) -> ComposeResult:
        titel   = "Konto bearbeiten" if self._edit else "Konto anlegen"
        btn_lbl = "Speichern" if self._edit else "Anlegen"
        with Container(id="mb"):
            yield Label(titel, id="mt")
            yield Label("Kontonummer")
            yield Input(value=self._p.get("kontonummer", ""), placeholder="1000", id="fn")
            yield Label("Kontoname")
            yield Input(value=self._p.get("kontoname",   ""), placeholder="Kasse", id="fk")
            with Horizontal(id="mbtns"):
                yield Button(f"{btn_lbl} [F5]",   variant="primary", id="bs")
                yield Button("Abbrechen [Esc]", variant="default", id="bc")

    def action_cancel(self): self.dismiss(None)

    @on(Button.Pressed, "#bc")
    def _c(self): self.dismiss(None)

    @on(Button.Pressed, "#bs")
    def _s(self):
        n = self.query_one("#fn", Input).value.strip()
        k = self.query_one("#fk", Input).value.strip()
        if not n or not k:
            self.app.notify("Alle Felder ausfüllen", severity="error")
            return
        self.dismiss({"kontonummer": n, "kontoname": k})


class BuchungModal(ModalScreen):
    BINDINGS = [("escape", "cancel")]

    def __init__(self, konten: list, mitglieder: list,
                 prefill: dict | None = None, storno_id: int | None = None):
        super().__init__()
        self._k  = konten
        self._m  = mitglieder
        self._p  = prefill or {}
        self._si = storno_id

    def compose(self) -> ComposeResult:
        titel      = f"Storno #{self._si} & Neu" if self._si else "Buchung erfassen"
        konto_opts = [(f"{k['kontonummer']} {k['kontoname']}", str(k['id'])) for k in self._k]
        mitgl_opts = [("— kein Mitglied —", Select.BLANK)] + \
                     [(m['name'], str(m['id'])) for m in self._m]
        mitgl_val  = str(self._p.get("mitglied_id") or "")
        mitgl_val  = Select.BLANK if mitgl_val in ("", "None") else mitgl_val

        with Container(id="mb", classes="mw"):
            yield Label(titel, id="mt")
            if self._si:
                yield Label(f"↩ Buchung #{self._si} wird storniert.", id="mh")
            yield Label("Sollkonto")
            yield Select(konto_opts, value=str(self._p.get("sollkonto_id", "")), id="fso")
            yield Label("Habenkonto")
            yield Select(konto_opts, value=str(self._p.get("habenkonto_id", "")), id="fha")
            yield Label("Betrag (€)")
            yield Input(value=str(self._p.get("betrag", "")), placeholder="0.00", id="fb")
            yield Label("Datum")
            yield Input(value=self._p.get("buchungsdatum", today()), id="fd")
            yield Label("Text")
            yield Input(value=self._p.get("buchungstext", ""), placeholder="optional", id="ft")
            yield Label("Mitglied")
            yield Select(mitgl_opts, value=mitgl_val, allow_blank=True, id="fm")
            with Horizontal(id="mbtns"):
                yield Button("Buchen [F5]",     variant="primary", id="bs")
                yield Button("Abbrechen [Esc]", variant="default", id="bc")

    def action_cancel(self): self.dismiss(None)

    @on(Button.Pressed, "#bc")
    def _c(self): self.dismiss(None)

    @on(Button.Pressed, "#bs")
    def _s(self):
        so = self.query_one("#fso", Select).value
        ha = self.query_one("#fha", Select).value
        be = self.query_one("#fb",  Input).value.strip()
        da = self.query_one("#fd",  Input).value.strip()
        te = self.query_one("#ft",  Input).value.strip() or None
        mi = self.query_one("#fm",  Select).value

        if not so or not ha:
            self.app.notify("Konten wählen", severity="error"); return
        if so == ha:
            self.app.notify("Soll ≠ Haben",  severity="error"); return
        try:
            b = float(be.replace(",", ".")); assert b > 0
        except Exception:
            self.app.notify("Ungültiger Betrag", severity="error"); return
        if not da:
            self.app.notify("Datum fehlt", severity="error"); return

        self.dismiss({
            "sollkonto_id":  int(so),
            "habenkonto_id": int(ha),
            "betrag":        f"{b:.2f}",
            "buchungsdatum": da,
            "buchungstext":  te,
            "mitglied_id":   int(mi) if mi and mi is not Select.BLANK else None,
        })

# ── Haupt-App ──────────────────────────────────────────────────────────────────

class VereinsApp(App):
    TITLE = "Vereinsverwaltung"

    BINDINGS = [
        Binding("f1", "show('mitglieder')", "Mitglieder"),
        Binding("f2", "show('konten')",     "Konten"),
        Binding("f3", "show('buchungen')",  "Buchungen"),
        Binding("f4", "show('tkonten')",    "T-Konten"),
        Binding("q",  "quit",               "Beenden"),
    ]

    CSS = """
    Screen { background: #1a1c22; layout: vertical; }
    Header { background: #1a1c22; color: #c8cdd6; border-bottom: solid #2a2d35; }
    Footer { background: #1a1c22; color: #6b7280; border-top: solid #2a2d35; }

    /* ── Navigationsleiste ── */
    #nav-bar       { height: 3; background: #13151a; padding: 0 1;
                     border-bottom: solid #2a2d35; align: left middle; }
    .nav-btn       { background: #13151a; color: #6b7280; border: none;
                     height: 1; margin-right: 1; min-width: 16; padding: 0 2; }
    .nav-btn:hover { background: #1e2028; color: #c8cdd6; }
    .nav-active    { color: #00c97a !important; }

    /* ── Inhaltsbereich ── */
    ContentSwitcher { height: 1fr; }
    #view-mitglieder, #view-konten, #view-buchungen {
        layout: vertical; height: 1fr; padding: 1 2;
    }

    /* ── Toolbar & Filterleiste ── */
    #tb, #fb { height: 3; align: left middle; margin-bottom: 1; }
    .fi { width: 16; }
    .fs { width: 24; }
    #fb Label { margin: 0 1; color: #6b7280; }

    /* ── Buttons ── */
    Button          { margin-right: 1; height: 1; min-width: 14;
                      background: #2a2d35; color: #c8cdd6; border: none; }
    Button:hover    { background: #3a3d47; }
    Button.-primary { background: #00c97a; color: #000000; }
    Button.-error   { background: #e05263; color: #ffffff; }

    /* ── Tabellen ── */
    DataTable                      { height: 1fr; background: #1e2028; border: solid #2a2d35; }
    DataTable > .datatable--header { background: #13151a; color: #6b7280; }
    DataTable > .datatable--cursor { background: #003d25; }

    /* ── T-Konten ── */
    #view-tkonten #tb  { height: 3; align: left middle; margin-bottom: 1; }
    .tk-sel            { width: 40; }
    #tk-body           { height: 1fr; }
    #tk-soll-col, #tk-haben-col { width: 1fr; layout: vertical; }
    #tk-soll-hdr       { height: 1; text-style: bold; color: #00c97a; margin-bottom: 0; }
    #tk-haben-hdr      { height: 1; text-style: bold; color: #00c97a; margin-bottom: 0; text-align: right; }
    #tk-soll, #tk-haben { height: 1fr; background: #1e2028; border: solid #2a2d35; }
    #tk-soll           { border-right: solid #3a3d47; }
    #tk-footer         { height: 1; }
    #tk-saldo-soll     { width: 1fr; color: #6b7280; padding: 0 1; }
    #tk-saldo-haben    { width: 1fr; color: #6b7280; padding: 0 1; text-align: right; }

    /* ── Modaldialoge ── */
    ConfirmModal, MitgliedModal, StatusModal, KontoModal, BuchungModal {
        align: center middle;
    }
    #mb    { background: #1e2028; border: solid #3a3d47; padding: 2 3; width: 54; }
    .mw    { width: 70; }
    #mt    { text-style: bold; color: #00c97a; margin-bottom: 1; }
    #mh    { color: #4a9eff; margin-bottom: 1; }
    #mb2   { color: #c8cdd6; margin-bottom: 1; }
    #mbtns { align: right middle; margin-top: 1; height: 3; }
    Label  { color: #6b7280; height: 1; margin-top: 1; }
    Input  { margin-bottom: 0; }
    Select { margin-bottom: 0; }
    """

    def __init__(self, api_url: str):
        super().__init__()
        self._api        = ApiClient(api_url)
        self._active_tab = "mitglieder"
        self._m_data:    list = []
        self._k_data:    list = []
        self._b_data:    list = []
        self._konten:    list = []
        self._mitgl:     list = []
        self._grouped:   bool = False
        self._tk_data:   list = []

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="nav-bar"):
            yield Button("Mitglieder", id="nav-mitglieder", classes="nav-btn nav-active")
            yield Button("Konten",     id="nav-konten",     classes="nav-btn")
            yield Button("Buchungen",  id="nav-buchungen",  classes="nav-btn")
            yield Button("T-Konten",   id="nav-tkonten",    classes="nav-btn")

        with ContentSwitcher(initial="view-mitglieder"):

            # ── Mitglieder ──────────────────────────────────────────────────
            with Vertical(id="view-mitglieder"):
                with Horizontal(id="tb"):
                    yield Button("F5 Neu",          id="m-add")
                    yield Button("F6 Bearbeiten",   id="m-edit")
                    yield Button("F7 Status",       id="m-status")
                    yield Button("F8 Löschen",      id="m-del")
                    yield Button("r Aktualisieren", id="m-reload")
                    yield Label("  Filter: ")
                    yield Select(
                        [("Alle", ""), ("Aktiv", "aktiv"), ("Passiv", "passiv"),
                         ("Gast", "gast"), ("Ausgetreten", "ausgetreten")],
                        value="", allow_blank=False, id="m-filter",
                    )
                yield DataTable(id="m-table", cursor_type="row")

            # ── Konten ──────────────────────────────────────────────────────
            with Vertical(id="view-konten"):
                with Horizontal(id="tb"):
                    yield Button("F5 Neu",          id="k-add")
                    yield Button("F6 Bearbeiten",   id="k-edit")
                    yield Button("F8 Löschen",      id="k-del")
                    yield Button("r Aktualisieren", id="k-reload")
                yield DataTable(id="k-table", cursor_type="row")

            # ── Buchungen ───────────────────────────────────────────────────
            with Vertical(id="view-buchungen"):
                with Horizontal(id="tb"):
                    yield Button("F5 Neu",          id="b-add")
                    yield Button("F6 Bearbeiten",   id="b-edit")
                    yield Button("F7 Kopieren",     id="b-copy")
                    yield Button("F8 Löschen",      id="b-del")
                    yield Button("g Gruppieren",    id="b-grp")
                    yield Button("r Aktualisieren", id="b-reload")
                with Horizontal(id="fb"):
                    yield Label("Von:")
                    yield Input(placeholder="YYYY-MM-DD", id="b-von", classes="fi")
                    yield Label("Bis:")
                    yield Input(placeholder="YYYY-MM-DD", id="b-bis", classes="fi")
                    yield Label("Konto:")
                    yield Select([("Alle", Select.BLANK)], value=Select.BLANK,
                                 allow_blank=True, id="b-konto", classes="fs")
                    yield Label("Mitglied:")
                    yield Select([("Alle", Select.BLANK)], value=Select.BLANK,
                                 allow_blank=True, id="b-mitglied", classes="fs")
                    yield Button("Suchen", id="b-search")
                    yield Button("✕",     id="b-clear")
                yield DataTable(id="b-table", cursor_type="row")

            # ── T-Konten ────────────────────────────────────────────────────
            with Vertical(id="view-tkonten"):
                with Horizontal(id="tb"):
                    yield Label("Konto:")
                    yield Select([("— bitte wählen —", Select.BLANK)], value=Select.BLANK,
                                 allow_blank=True, id="tk-konto", classes="tk-sel")
                    yield Button("r Aktualisieren", id="tk-reload")
                with Horizontal(id="tk-body"):
                    with Vertical(id="tk-soll-col"):
                        yield Label("◄ SOLL", id="tk-soll-hdr")
                        yield DataTable(id="tk-soll", cursor_type="row")
                    with Vertical(id="tk-haben-col"):
                        yield Label("HABEN ►", id="tk-haben-hdr")
                        yield DataTable(id="tk-haben", cursor_type="row")
                with Horizontal(id="tk-footer"):
                    yield Label("", id="tk-saldo-soll")
                    yield Label("", id="tk-saldo-haben")

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#m-table", DataTable).add_columns("ID", "Name", "Status", "Seit", "Bis")
        self.query_one("#k-table", DataTable).add_columns("ID", "Nummer", "Name")
        self.query_one("#b-table", DataTable).add_columns(
            "ID", "Datum", "Soll", "Haben", "Betrag", "Text", "Mitglied"
        )
        self.query_one("#tk-soll",  DataTable).add_columns("Datum", "Gegenkonto", "Betrag", "Text")
        self.query_one("#tk-haben", DataTable).add_columns("Datum", "Gegenkonto", "Betrag", "Text")
        self._load_all()
        self.call_after_refresh(lambda: self.query_one("#m-table").focus())

    @work(thread=True)
    def _load_all(self):
        self.app.call_from_thread(self._reload_mitglieder)
        self.app.call_from_thread(self._reload_konten)
        self.app.call_from_thread(self._load_refs)

    # ── Navigation ────────────────────────────────────────────────────────────

    _NAV_LABELS = {
        "mitglieder": "Mitglieder",
        "konten":     "Konten",
        "buchungen":  "Buchungen",
        "tkonten":    "T-Konten",
    }

    def action_show(self, tab: str) -> None:
        self.query_one(ContentSwitcher).current = f"view-{tab}"
        self._active_tab = tab
        for t, label in self._NAV_LABELS.items():
            btn = self.query_one(f"#nav-{t}", Button)
            btn.label = label
            if t == tab:
                btn.add_class("nav-active")
            else:
                btn.remove_class("nav-active")
        focus_map = {
            "mitglieder": "#m-table",
            "konten":     "#k-table",
            "buchungen":  "#b-table",
            "tkonten":    "#tk-konto",
        }
        self.call_after_refresh(lambda: self.query_one(focus_map[tab]).focus())
        if tab == "buchungen":
            self.call_after_refresh(self._reload_buchungen)

    @on(Button.Pressed, "#nav-mitglieder")
    def _nav_m(self): self.action_show("mitglieder")

    @on(Button.Pressed, "#nav-konten")
    def _nav_k(self): self.action_show("konten")

    @on(Button.Pressed, "#nav-buchungen")
    def _nav_b(self): self.action_show("buchungen")

    @on(Button.Pressed, "#nav-tkonten")
    def _nav_tk(self): self.action_show("tkonten")

    def on_key(self, event) -> None:
        cur = self.query_one(ContentSwitcher).current
        k   = event.key
        if cur == "view-mitglieder":
            {"f5": self.m_add, "f6": self.m_edit, "f7": self.m_status,
             "f8": self.m_del, "r": self._reload_mitglieder}.get(k, lambda: None)()
        elif cur == "view-konten":
            {"f5": self.k_add, "f6": self.k_edit, "f8": self.k_del,
             "r": self._reload_konten}.get(k, lambda: None)()
        elif cur == "view-buchungen":
            {"f5": self.b_add, "f6": self.b_edit, "f7": self.b_copy,
             "f8": self.b_del, "g": self.b_grp, "r": self._reload_buchungen}.get(k, lambda: None)()
        elif cur == "view-tkonten":
            {"r": self._reload_tkonten}.get(k, lambda: None)()

    # ══════════════════════════════════════════════════════════════════════════
    # MITGLIEDER
    # ══════════════════════════════════════════════════════════════════════════

    def _reload_mitglieder(self) -> None:
        sel = self.query_one("#m-filter", Select).value
        self._fetch_mitglieder(sel if sel else None)

    @work(thread=True)
    def _fetch_mitglieder(self, status_filter: str | None) -> None:
        try:
            d = self._api.get("/members/", nur_aktuell=False, mitglied_status=status_filter)
            self._m_data = d
            self.call_from_thread(self._fill_mitglieder, d)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    def _fill_mitglieder(self, data: list) -> None:
        t = self.query_one("#m-table", DataTable)
        t.clear()
        for m in data:
            t.add_row(str(m["id"]), m["name"], m["status"],
                      fmt_date(m.get("gueltig_von")),
                      fmt_date(m.get("gueltig_bis")) or "—",
                      key=str(m["id"]))

    def _m_cur(self) -> dict | None:
        t = self.query_one("#m-table", DataTable)
        if t.cursor_row < 0 or not self._m_data: return None
        row_id = t.get_row_at(t.cursor_row)[0]
        return next((m for m in self._m_data if str(m["id"]) == row_id), None)

    @on(Button.Pressed, "#m-add")
    def m_add(self): self.push_screen(MitgliedModal(), self._do_m_add)

    @work(thread=True)
    def _do_m_add(self, res: dict | None) -> None:
        if not res: return
        try:
            self._api.post("/members/", res)
            self.call_from_thread(self.notify, "Mitglied angelegt")
            self.call_from_thread(self._reload_mitglieder)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#m-edit")
    def m_edit(self) -> None:
        m = self._m_cur()
        if not m: return
        self.push_screen(
            MitgliedModal(prefill={"name": m["name"], "status": m["status"],
                                   "gueltig_von": m.get("gueltig_von", today())}),
            lambda r: self._do_m_edit(r, m["id"])
        )

    @work(thread=True)
    def _do_m_edit(self, res: dict | None, mid: int) -> None:
        if not res: return
        try:
            self._api.put(f"/members/{mid}", res)
            self.call_from_thread(self.notify, "Gespeichert")
            self.call_from_thread(self._reload_mitglieder)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#m-status")
    def m_status(self) -> None:
        m = self._m_cur()
        if not m: return
        if m.get("gueltig_bis"):
            self.notify("Nur aktuelle Einträge", severity="warning"); return
        self.push_screen(StatusModal(m["name"]), lambda r: self._do_m_status(r, m["id"]))

    @work(thread=True)
    def _do_m_status(self, res: dict | None, mid: int) -> None:
        if not res: return
        try:
            self._api.put(f"/members/{mid}/status", res)
            self.call_from_thread(self.notify, "Status geändert")
            self.call_from_thread(self._reload_mitglieder)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#m-del")
    def m_del(self) -> None:
        m = self._m_cur()
        if not m: return
        self.push_screen(
            ConfirmModal(f"#{m['id']} '{m['name']}' löschen?"),
            lambda ok: self._do_m_del(ok, m["id"])
        )

    @work(thread=True)
    def _do_m_del(self, ok: bool, mid: int) -> None:
        if not ok: return
        try:
            self._api.delete(f"/members/{mid}")
            self.call_from_thread(self.notify, "Gelöscht")
            self.call_from_thread(self._reload_mitglieder)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#m-reload")
    def _m_reload_btn(self): self._reload_mitglieder()

    @on(Select.Changed, "#m-filter")
    def _m_filter_changed(self, _): self._reload_mitglieder()

    # ══════════════════════════════════════════════════════════════════════════
    # KONTEN
    # ══════════════════════════════════════════════════════════════════════════

    def _reload_konten(self) -> None:
        self._fetch_konten()

    @work(thread=True)
    def _fetch_konten(self) -> None:
        try:
            d = self._api.get("/konten/")
            self._k_data = d
            self.call_from_thread(self._fill_konten, d)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    def _fill_konten(self, data: list) -> None:
        t = self.query_one("#k-table", DataTable)
        t.clear()
        for k in data:
            t.add_row(str(k["id"]), k["kontonummer"], k["kontoname"], key=str(k["id"]))

    def _k_cur(self) -> dict | None:
        t = self.query_one("#k-table", DataTable)
        if t.cursor_row < 0 or not self._k_data: return None
        row_id = t.get_row_at(t.cursor_row)[0]
        return next((k for k in self._k_data if str(k["id"]) == row_id), None)

    @on(Button.Pressed, "#k-add")
    def k_add(self): self.push_screen(KontoModal(), self._do_k_add)

    @work(thread=True)
    def _do_k_add(self, res: dict | None) -> None:
        if not res: return
        try:
            self._api.post("/konten/", res)
            self.call_from_thread(self.notify, "Konto angelegt")
            self.call_from_thread(self._reload_konten)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#k-edit")
    def k_edit(self) -> None:
        k = self._k_cur()
        if not k: return
        self.push_screen(
            KontoModal(prefill={"kontonummer": k["kontonummer"], "kontoname": k["kontoname"]}),
            lambda r: self._do_k_edit(r, k["id"])
        )

    @work(thread=True)
    def _do_k_edit(self, res: dict | None, kid: int) -> None:
        if not res: return
        try:
            self._api.put(f"/konten/{kid}", res)
            self.call_from_thread(self.notify, "Gespeichert")
            self.call_from_thread(self._reload_konten)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#k-del")
    def k_del(self) -> None:
        k = self._k_cur()
        if not k: return
        self.push_screen(
            ConfirmModal(f"Konto '{k['kontoname']}' löschen?"),
            lambda ok: self._do_k_del(ok, k["id"])
        )

    @work(thread=True)
    def _do_k_del(self, ok: bool, kid: int) -> None:
        if not ok: return
        try:
            self._api.delete(f"/konten/{kid}")
            self.call_from_thread(self.notify, "Gelöscht")
            self.call_from_thread(self._reload_konten)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#k-reload")
    def _k_reload_btn(self): self._reload_konten()

    # ══════════════════════════════════════════════════════════════════════════
    # BUCHUNGEN
    # ══════════════════════════════════════════════════════════════════════════

    @work(thread=True)
    def _load_refs(self) -> None:
        try:
            self._konten = self._api.get("/konten/")
            self._mitgl  = self._api.get("/members/", nur_aktuell=True)
            self.call_from_thread(self._populate_b_selects)
        except Exception:
            pass

    def _populate_b_selects(self) -> None:
        konto_opts = [(f"{k['kontonummer']} {k['kontoname']}", str(k["id"]))
                      for k in self._konten]
        ks = self.query_one("#b-konto", Select)
        ks.set_options(konto_opts)
        ks.clear()
        ms = self.query_one("#b-mitglied", Select)
        ms.set_options([(m["name"], str(m["id"])) for m in self._mitgl])
        ms.clear()
        # T-Konten Select mitbefüllen – gleiche Quelle, gleicher Zeitpunkt
        tk = self.query_one("#tk-konto", Select)
        tk.set_options(konto_opts)
        tk.clear()

    def _reload_buchungen(self) -> None:
        self._fetch_buchungen()

    @work(thread=True)
    def _fetch_buchungen(self) -> None:
        von = self.query_one("#b-von",      Input).value.strip() or None
        bis = self.query_one("#b-bis",      Input).value.strip() or None
        k   = clean_select(self.query_one("#b-konto",    Select).value)
        m   = clean_select(self.query_one("#b-mitglied", Select).value)
        try:
            d = self._api.get("/buchungen/", von=von, bis=bis, konto_id=k, mitglied_id=m)
            self._b_data = d
            self.call_from_thread(self._render_buchungen)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    def _render_buchungen(self) -> None:
        if self._grouped:
            self._fill_b_grouped(self._b_data)
        else:
            self._fill_b(self._b_data)

    def _fill_b(self, data: list) -> None:
        t = self.query_one("#b-table", DataTable)
        t.clear()
        for b in data:
            t.add_row(
                str(b["id"]),
                fmt_date(b["buchungsdatum"]),
                f"{b['sollkonto']['kontonummer']} {b['sollkonto']['kontoname']}",
                f"{b['habenkonto']['kontonummer']} {b['habenkonto']['kontoname']}",
                fmt_betrag(b["betrag"]),
                b.get("buchungstext") or "—",
                b["mitglied"]["name"] if b.get("mitglied") else "—",
                key=str(b["id"]),
            )

    def _fill_b_grouped(self, data: list) -> None:
        t = self.query_one("#b-table", DataTable)
        t.clear()
        g: dict = defaultdict(list)
        for b in data:
            key = (b["sollkonto"]["id"], b["habenkonto"]["id"],
                   b["buchungsdatum"], b.get("buchungstext") or "")
            g[key].append(b)
        for (_, _, datum, text), bs in g.items():
            ids = ",".join(str(b["id"]) for b in bs)
            t.add_row(
                ids,
                fmt_date(datum),
                f"{bs[0]['sollkonto']['kontonummer']} {bs[0]['sollkonto']['kontoname']}",
                f"{bs[0]['habenkonto']['kontonummer']} {bs[0]['habenkonto']['kontoname']}",
                fmt_betrag(sum(float(b["betrag"]) for b in bs)),
                f"[{len(bs)}×] {text}" if text else f"[{len(bs)}×]",
                "—",
                key=ids,
            )

    def _b_cur(self) -> dict | None:
        t = self.query_one("#b-table", DataTable)
        if t.cursor_row < 0 or not self._b_data: return None
        first_id = str(t.get_row_at(t.cursor_row)[0]).split(",")[0]
        return next((b for b in self._b_data if str(b["id"]) == first_id), None)

    @on(Button.Pressed, "#b-grp")
    def b_grp(self) -> None:
        self._grouped = not self._grouped
        self.query_one("#b-grp", Button).label = \
            "g ⊟ Aufheben" if self._grouped else "g Gruppieren"
        self._render_buchungen()

    @on(Button.Pressed, "#b-search")
    def _b_search(self): self._reload_buchungen()

    @on(Button.Pressed, "#b-reload")
    def _b_reload_btn(self): self._reload_buchungen()

    @on(Button.Pressed, "#b-clear")
    def _b_clear(self) -> None:
        self.query_one("#b-von",      Input).value = ""
        self.query_one("#b-bis",      Input).value = ""
        self.query_one("#b-konto",    Select).clear()
        self.query_one("#b-mitglied", Select).clear()
        self._reload_buchungen()

    @on(Button.Pressed, "#b-add")
    def b_add(self): self.push_screen(BuchungModal(self._konten, self._mitgl), self._do_b_add)

    @work(thread=True)
    def _do_b_add(self, res: dict | None) -> None:
        if not res: return
        try:
            self._api.post("/buchungen/", res)
            self.call_from_thread(self.notify, "Buchung erfasst")
            self.call_from_thread(self._reload_buchungen)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#b-edit")
    def b_edit(self) -> None:
        b = self._b_cur()
        if not b: return
        pre = {
            "sollkonto_id":  b["sollkonto"]["id"],
            "habenkonto_id": b["habenkonto"]["id"],
            "betrag":        b["betrag"],
            "buchungsdatum": b["buchungsdatum"],
            "buchungstext":  b.get("buchungstext", ""),
            "mitglied_id":   b["mitglied"]["id"] if b.get("mitglied") else None,
        }
        self.push_screen(
            BuchungModal(self._konten, self._mitgl, prefill=pre, storno_id=b["id"]),
            lambda r: self._do_b_storno(r, b)
        )

    @work(thread=True)
    def _do_b_storno(self, res: dict | None, orig: dict) -> None:
        if not res: return
        try:
            storno_text = f"Storno #{orig['id']}"
            if orig.get("buchungstext"):
                storno_text += f" – {orig['buchungstext']}"
            self._api.post("/buchungen/", {
                "sollkonto_id":  orig["habenkonto"]["id"],
                "habenkonto_id": orig["sollkonto"]["id"],
                "betrag":        orig["betrag"],
                "buchungsdatum": today(),
                "buchungstext":  storno_text,
                "mitglied_id":   orig["mitglied"]["id"] if orig.get("mitglied") else None,
            })
            self._api.post("/buchungen/", res)
            self.call_from_thread(self.notify, f"#{orig['id']} storniert & neu erfasst")
            self.call_from_thread(self._reload_buchungen)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    @on(Button.Pressed, "#b-copy")
    def b_copy(self) -> None:
        b = self._b_cur()
        if not b: return
        pre = {
            "sollkonto_id":  b["sollkonto"]["id"],
            "habenkonto_id": b["habenkonto"]["id"],
            "betrag":        b["betrag"],
            "buchungsdatum": today(),
            "buchungstext":  b.get("buchungstext", ""),
            "mitglied_id":   b["mitglied"]["id"] if b.get("mitglied") else None,
        }
        self.push_screen(BuchungModal(self._konten, self._mitgl, prefill=pre), self._do_b_add)

    @on(Button.Pressed, "#b-del")
    def b_del(self) -> None:
        b = self._b_cur()
        if not b: return
        self.push_screen(
            ConfirmModal(f"Buchung #{b['id']} löschen?"),
            lambda ok: self._do_b_del(ok, b["id"])
        )

    @work(thread=True)
    def _do_b_del(self, ok: bool, bid: int) -> None:
        if not ok: return
        try:
            self._api.delete(f"/buchungen/{bid}")
            self.call_from_thread(self.notify, "Gelöscht")
            self.call_from_thread(self._reload_buchungen)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    # ══════════════════════════════════════════════════════════════════════════
    # T-KONTEN
    # ══════════════════════════════════════════════════════════════════════════

    @on(Select.Changed, "#tk-konto")
    def _tk_konto_changed(self, _) -> None:
        self._reload_tkonten()

    @on(Button.Pressed, "#tk-reload")
    def _tk_reload_btn(self): self._reload_tkonten()

    def _reload_tkonten(self) -> None:
        kid = clean_select(self.query_one("#tk-konto", Select).value)
        if not kid:
            return
        self._fetch_tkonten(int(kid))

    @work(thread=True)
    def _fetch_tkonten(self, konto_id: int) -> None:
        try:
            buchungen = self._api.get("/buchungen/", konto_id=konto_id)
            self._tk_data = buchungen
            konto = next((k for k in self._konten if k["id"] == konto_id), None)
            self.call_from_thread(self._fill_tkonten, buchungen, konto)
        except Exception as e:
            self.call_from_thread(self.notify, str(e), severity="error")

    def _fill_tkonten(self, buchungen: list, konto: dict | None) -> None:
        soll_t  = self.query_one("#tk-soll",  DataTable)
        haben_t = self.query_one("#tk-haben", DataTable)
        soll_t.clear()
        haben_t.clear()

        konto_id   = konto["id"] if konto else None
        soll_summe = 0.0
        hab_summe  = 0.0

        for b in buchungen:
            datum   = fmt_date(b["buchungsdatum"])
            betrag  = float(b["betrag"])
            text    = b.get("buchungstext") or "—"
            if b["sollkonto"]["id"] == konto_id:
                gegen = f"{b['habenkonto']['kontonummer']} {b['habenkonto']['kontoname']}"
                soll_t.add_row(datum, gegen, fmt_betrag(betrag), text, key=str(b["id"]))
                soll_summe += betrag
            else:
                gegen = f"{b['sollkonto']['kontonummer']} {b['sollkonto']['kontoname']}"
                haben_t.add_row(datum, gegen, fmt_betrag(betrag), text, key=str(b["id"]))
                hab_summe += betrag

        saldo = soll_summe - hab_summe

        # Saldo-Ausgleichszeile auf der kleineren Seite
        if saldo > 0:
            haben_t.add_row("—", "Saldo", fmt_betrag(saldo), "", key="saldo")
        elif saldo < 0:
            soll_t.add_row("—", "Saldo", fmt_betrag(abs(saldo)), "", key="saldo")

        gesamt = soll_summe + max(0.0, saldo) if saldo > 0 else hab_summe + max(0.0, -saldo)
        self.query_one("#tk-saldo-soll",  Label).update(f"Summe Soll:  {fmt_betrag(gesamt)}")
        self.query_one("#tk-saldo-haben", Label).update(f"Summe Haben:  {fmt_betrag(gesamt)}")

        name = f"{konto['kontonummer']} {konto['kontoname']}" if konto else "T-Konto"
        self.query_one("#tk-soll-hdr",  Label).update(f"◄ SOLL  |  {name}")
        self.query_one("#tk-haben-hdr", Label).update(f"{name}  |  HABEN ►")


# ── Einstieg ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Vereinsverwaltung TUI")
    p.add_argument("--api", default=DEFAULT_API, help=f"API-URL (Standard: {DEFAULT_API})")
    VereinsApp(api_url=p.parse_args().api).run()
