"""Accessible, localizable torrent list control split out of main.py."""

from __future__ import annotations

import wx

from accessible_virtual_list import AccessibleVirtualListMixin
from main_ui_i18n import formatted_status, tr_main
from ui_formatting import (
    clean_status_message,
    fmt_availability,
    fmt_eta,
    fmt_pair,
    fmt_ratio,
    fmt_size,
)

COL_NAME = 0
COL_SIZE = 1
COL_STATUS = 2
COL_TIME_LEFT = 3
COL_SEEDS = 4
COL_LEECHERS = 5
COL_RATIO = 6
COL_AVAILABILITY = 7


def torrent_status_text(row, language=None):
    size = row.get("size", 0)
    done = row.get("done", 0)
    pct = (done / size * 100) if size > 0 else 0
    state = row.get("state", 0)
    hashing = row.get("hashing", 0)
    msg = clean_status_message(row.get("message", ""))

    status = tr_main("Stopped", language)
    if hashing:
        status = tr_main("Checking", language)
    elif state == 1:
        if pct >= 100:
            status = tr_main("Seeding", language)
        else:
            status = formatted_status("Downloaded: {percent:.1f}%", language, percent=pct)
            down_rate = row.get("down_rate", 0)
            if down_rate > 0:
                status += f"; {fmt_size(down_rate)}/s"
    if msg:
        status += f" ({msg})"
    return status


def torrent_eta(row):
    eta = row.get("eta")
    if eta is not None:
        return eta
    try:
        remaining = max(0, int(row.get("size", 0)) - int(row.get("done", 0)))
        down_rate = int(row.get("down_rate", 0) or 0)
        return int(remaining / down_rate) if down_rate > 0 and remaining > 0 else -1
    except (TypeError, ValueError):
        return -1


class TorrentListCtrl(AccessibleVirtualListMixin, wx.ListCtrl):
    def __init__(
        self,
        parent,
        id=wx.ID_ANY,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES | wx.LC_VRULES,
        *,
        language=None,
    ):
        super().__init__(parent, id, pos, size, style)
        self.language = language
        self.data = []
        self.sort_col = -1
        self.sort_asc = True

        for index, heading, width in (
            (COL_NAME, "Name", 300),
            (COL_SIZE, "Size", 100),
            (COL_STATUS, "Status", 220),
            (COL_TIME_LEFT, "Time Left", 110),
            (COL_SEEDS, "Seeds", 120),
            (COL_LEECHERS, "Leechers", 160),
            (COL_RATIO, "Ratio", 80),
            (COL_AVAILABILITY, "Availability", 110),
        ):
            self.InsertColumn(index, tr_main(heading, language), width=width)

        self.SetName(tr_main("Torrent List", language))
        self.init_accessible_virtual_list()
        self.Bind(wx.EVT_LIST_COL_CLICK, self.on_col_click)

    def OnGetItemText(self, item, col):
        if item >= len(self.data):
            return ""
        try:
            row = self.data[item]
            if col == COL_NAME:
                return str(row.get("name", tr_main("Unknown", self.language)))
            if col == COL_SIZE:
                return fmt_size(row.get("size", 0))
            if col == COL_STATUS:
                return torrent_status_text(row, self.language)
            if col == COL_TIME_LEFT:
                return fmt_eta(torrent_eta(row))
            if col == COL_SEEDS:
                return fmt_pair(row.get("seeds_connected", 0), row.get("seeds_total", 0))
            if col == COL_LEECHERS:
                text = fmt_pair(
                    row.get("leechers_connected", 0), row.get("leechers_total", 0)
                )
                up_rate = row.get("up_rate", 0)
                if up_rate > 0:
                    text += f" up: {fmt_size(up_rate)}/s"
                return text
            if col == COL_RATIO:
                return fmt_ratio(row.get("ratio", 0))
            if col == COL_AVAILABILITY:
                return fmt_availability(row.get("availability"))
            return ""
        except Exception:
            return ""

    def _focused_hash(self):
        idx = self.GetFocusedItem()
        if 0 <= idx < len(self.data):
            return self.data[idx].get("hash")
        return None

    def get_focused_hash(self):
        return self._focused_hash()

    def _index_of_hash(self, target_hash):
        if target_hash is None:
            return None
        for idx, row in enumerate(self.data):
            if row.get("hash") == target_hash:
                return idx
        return None

    def update_data(self, new_data):
        selected_hashes = set(self.get_selected_hashes())
        focused_hash = self._focused_hash()
        old_order = [row.get("hash") for row in self.data]

        self.data = new_data
        self._apply_sort()
        new_order = [row.get("hash") for row in self.data]

        if self.GetItemCount() != len(self.data):
            self.SetItemCount(len(self.data))
        self.Refresh()

        if selected_hashes and new_order != old_order:
            for idx, row in enumerate(self.data):
                try:
                    self.Select(idx, row.get("hash") in selected_hashes)
                except Exception:
                    pass

        self._restore_focus_row(len(self.data), self._index_of_hash(focused_hash))

    def on_col_click(self, event):
        selected_hashes = set(self.get_selected_hashes())
        focused_hash = self._focused_hash()
        col = event.GetColumn()
        if col == self.sort_col:
            self.sort_asc = not self.sort_asc
        else:
            self.sort_col = col
            self.sort_asc = True
        self._apply_sort()
        self.Refresh()
        if selected_hashes:
            for idx, row in enumerate(self.data):
                try:
                    self.Select(idx, row.get("hash") in selected_hashes)
                except Exception:
                    pass
        self._restore_focus_row(len(self.data), self._index_of_hash(focused_hash))

    def _apply_sort(self):
        if self.sort_col == -1 or not self.data:
            return
        sort_keys = {
            COL_NAME: "name",
            COL_SIZE: "size",
            COL_STATUS: "state",
            COL_TIME_LEFT: "eta",
            COL_SEEDS: "seeds_connected",
            COL_LEECHERS: "leechers_connected",
            COL_RATIO: "ratio",
            COL_AVAILABILITY: "availability",
        }
        key = sort_keys.get(self.sort_col)
        if not key:
            return

        def sort_key(item):
            value = item.get(key)
            if value is None:
                if key in (
                    "size",
                    "eta",
                    "seeds_connected",
                    "leechers_connected",
                    "ratio",
                    "availability",
                ):
                    return -1
                return ""
            return value

        try:
            self.data.sort(key=sort_key, reverse=not self.sort_asc)
        except Exception:
            pass

    def get_selected_hashes(self):
        selection = []
        item = self.GetFirstSelected()
        while item != -1:
            try:
                selection.append(self.data[item]["hash"])
            except Exception:
                pass
            item = self.GetNextSelected(item)
        return selection
