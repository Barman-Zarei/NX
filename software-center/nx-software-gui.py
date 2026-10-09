#!/usr/bin/env python3
"""NX Software Center GUI (GTK3). Thin UI over nxsoft.py: search apt, show details + NX compatibility record,
install/remove only after the user confirms the exact command (privileged part runs through pkexec/PolicyKit)."""
import os
import sys
import threading

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nxsoft  # noqa: E402


class SoftwareWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="NX Software Center")
        self.set_default_size(760, 480)
        self.selected = None
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.add(box)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.entry = Gtk.SearchEntry()
        self.entry.connect("activate", lambda e: self.start_search(e.get_text()))
        self.store = Gtk.ListStore(str, str)
        self.view = Gtk.TreeView(model=self.store)
        for i, t in enumerate(("Name", "Summary")):
            self.view.append_column(Gtk.TreeViewColumn(t, Gtk.CellRendererText(), text=i))
        self.view.get_selection().connect("changed", self._on_changed)
        sc = Gtk.ScrolledWindow(); sc.add(self.view); sc.set_size_request(380, -1)
        left.pack_start(self.entry, False, False, 0); left.pack_start(sc, True, True, 0)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.details = Gtk.Label(label="Select an application", xalign=0, yalign=0, wrap=True, selectable=True)
        self.status = Gtk.Label(label="", xalign=0, wrap=True)
        self.btn_install = Gtk.Button(label="Install"); self.btn_remove = Gtk.Button(label="Remove")
        self.btn_install.connect("clicked", lambda b: self.request("install"))
        self.btn_remove.connect("clicked", lambda b: self.request("remove"))
        row = Gtk.Box(spacing=6); row.pack_start(self.btn_install, False, False, 0); row.pack_start(self.btn_remove, False, False, 0)
        right.pack_start(self.details, True, True, 0); right.pack_start(row, False, False, 0); right.pack_start(self.status, False, False, 0)
        box.pack_start(left, False, True, 6); box.pack_start(right, True, True, 6)

    # --- logic (testable without a click) ---
    def populate(self, results):
        self.store.clear()
        for r in results[:200]:
            self.store.append([r["name"], r["summary"]])

    def start_search(self, term):
        def work():
            res = nxsoft.search(term)
            GLib.idle_add(self.populate, res)
        threading.Thread(target=work, daemon=True).start()

    def select_name(self, name):
        self.selected = name
        i = nxsoft.info(name)
        c = nxsoft.compat_report(name)
        if not i:
            self.details.set_text("No package information for %s" % name); return
        self.details.set_text("%s %s (%s)\n\n%s\n\nNX compatibility: %s" % (
            i.get("Package"), i.get("Version"), i.get("Architecture"), i.get("Description", ""), c.get("status", "unknown")))

    def _on_changed(self, sel):
        model, it = sel.get_selected()
        if it:
            self.select_name(model[it][0])

    def request(self, action, confirm=None):
        if not self.selected:
            self.status.set_text("Select an application first"); return "none"
        cmd = nxsoft.plan(action, self.selected)
        if cmd is None:
            self.status.set_text("Invalid request"); return "denied"
        ask = confirm or self._dialog_confirm
        if not ask(" ".join(cmd)):
            self.status.set_text("Cancelled"); return "cancelled"
        st, out = nxsoft.apply(action, self.selected, approved=True)
        self.status.set_text("%s: %s" % (st, out[-300:]))
        return st

    def _dialog_confirm(self, cmdline):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                              buttons=Gtk.ButtonsType.YES_NO, text="Run this command with administrator rights?")
        d.format_secondary_text(cmdline)
        ok = d.run() == Gtk.ResponseType.YES
        d.destroy()
        return ok


def main():
    w = SoftwareWindow(); w.connect("destroy", Gtk.main_quit); w.show_all(); Gtk.main()


if __name__ == "__main__":
    main()
