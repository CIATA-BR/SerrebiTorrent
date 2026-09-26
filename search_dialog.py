# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Tools, Search for Torrents: find a torrent without leaving the client.

Three dialogs live here. TorrentSearchDialog is the search itself; it hands
the chosen rows back to MainFrame, which owns every path into the session.
SourcesDialog switches indexers on and off, and IndexersDialog manages the
user's own Torznab feeds -- a Prowlarr or Jackett instance, which is how a
private tracker is searched without this program ever holding a tracker
login.

Ported from blindDL, adapted to SerrebiTorrent's preferences and its
add-torrent paths. Every list here is a plain (non-virtual) wx.ListCtrl, so
each row keeps a real accessible and NVDA reads it while arrowing without the
focus bookkeeping the main torrent list needs.
"""

from __future__ import annotations

import threading

import wx

import torrent_search
from i18n import translator

PROWLARR_HINT = "http://localhost:9696/api/v1/search"
JACKETT_HINT = "http://localhost:9117/api/v2.0/indexers/all/results/torznab/api"

SORT_SEEDERS = 0
SORT_RELEVANCE = 1
SORT_SIZE = 2
SORT_NEWEST = 3
SORT_NAME = 4
SORT_LABELS = [
    "Most seeders",
    "Best match",
    "Largest",
    "Newest",
    "Name",
]


def _translator_for(config_manager):
    prefs = config_manager.get_preferences()
    return translator(prefs.get("language", "system"))


def _fmt(_, source, **values):
    return _(source).format(**values)


def _sorted_results(items, mode):
    """Order the merged results. Ties keep each indexer's own ranking."""
    indexed = list(enumerate(items))
    if mode == SORT_RELEVANCE:
        key = lambda pair: (-pair[1].get("score", 0), -pair[1]["seeders"], pair[0])
    elif mode == SORT_SIZE:
        key = lambda pair: (-pair[1].get("size_bytes", 0), pair[0])
    elif mode == SORT_NEWEST:
        key = lambda pair: (-pair[1].get("posted", 0), pair[0])
    elif mode == SORT_NAME:
        key = lambda pair: (pair[1]["title"].casefold(), pair[0])
    else:
        key = lambda pair: (-pair[1]["seeders"], -pair[1].get("score", 0), pair[0])
    return [item for _index, item in sorted(indexed, key=key)]


class TorrentSearchDialog(wx.Dialog):
    """Search the indexers and pick torrents to add."""

    def __init__(self, parent, config_manager):
        self.config_manager = config_manager
        self._ = _translator_for(config_manager)
        super().__init__(parent, title=self._("Search for Torrents"),
                         size=(900, 600),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.results = []
        self.chosen = []
        self._stop = threading.Event()
        self._token = 0
        self._pending = 0

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        query_row = wx.BoxSizer(wx.HORIZONTAL)
        query_label = wx.StaticText(panel, label=self._("&Search for:"))
        self.query = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.query.SetName(self._("Search for"))
        self.query.Bind(wx.EVT_TEXT_ENTER, self.on_search)
        self.search_btn = wx.Button(panel, label=self._("Sea&rch"))
        self.search_btn.Bind(wx.EVT_BUTTON, self.on_search)
        query_row.Add(query_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        query_row.Add(self.query, 1, wx.RIGHT, 6)
        query_row.Add(self.search_btn, 0)

        sort_row = wx.BoxSizer(wx.HORIZONTAL)
        sort_label = wx.StaticText(panel, label=self._("Sort &by:"))
        self.sort_choice = wx.Choice(panel, choices=[self._(label) for label in SORT_LABELS])
        self.sort_choice.SetName(self._("Sort by"))
        self.sort_choice.SetSelection(SORT_SEEDERS)
        self.sort_choice.Bind(wx.EVT_CHOICE, self.on_sort)
        sort_row.Add(sort_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        sort_row.Add(self.sort_choice, 0, wx.RIGHT, 12)
        sources_btn = wx.Button(panel, label=self._("Search si&tes..."))
        sources_btn.Bind(wx.EVT_BUTTON, self.on_sources)
        feeds_btn = wx.Button(panel, label=self._("My &indexers..."))
        feeds_btn.Bind(wx.EVT_BUTTON, self.on_feeds)
        sort_row.Add(sources_btn, 0, wx.RIGHT, 6)
        sort_row.Add(feeds_btn, 0)

        self.list = wx.ListCtrl(panel, style=wx.LC_REPORT)
        self.list.SetName(self._("Results"))
        self.list.SetHelpText(self._(
            "Enter adds the selected torrents. Control C copies the magnet link."))
        for index, (heading, width) in enumerate((
                ("Name", 380), ("Size", 90), ("Seeds", 60), ("Peers", 60),
                ("Age", 110), ("Indexer", 130), ("Category", 110))):
            self.list.InsertColumn(index, self._(heading))
            self.list.SetColumnWidth(index, width)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_add)
        self.list.Bind(wx.EVT_CHAR, self.on_char)

        self.status = wx.StaticText(panel, label=self._("Type what to look for."))

        self.add_btn = wx.Button(panel, wx.ID_OK, self._("&Add selected"))
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        self.add_btn.Enable(False)
        close_btn = wx.Button(panel, wx.ID_CANCEL, self._("&Close"))
        actions = wx.BoxSizer(wx.HORIZONTAL)
        actions.AddStretchSpacer()
        actions.Add(self.add_btn, 0, wx.RIGHT, 6)
        actions.Add(close_btn, 0)

        sizer.Add(query_row, 0, wx.EXPAND | wx.ALL, 8)
        sizer.Add(sort_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.status, 0, wx.ALL, 8)
        sizer.Add(actions, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        panel.SetSizer(sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self._adopt_blinddl_feeds()
        self.query.SetFocus()

    def _adopt_blinddl_feeds(self):
        """Pick up blindDL's own indexers, if it is installed on this machine.

        The two programs share an author and the same feed format, so a
        Prowlarr set up in one should not have to be typed into the other.
        Nothing is shipped with the app -- this reads a file on this
        computer, and only ever adds indexers that are not configured here
        already, so an edited URL or a replaced key is never overwritten.
        """
        prefs = self._prefs()
        try:
            added = torrent_search.import_blinddl_feeds(prefs)
        except Exception:  # noqa: BLE001 - an optional convenience, never fatal
            return
        if not added:
            return
        try:
            self.config_manager.set_preferences(prefs)
        except Exception:  # noqa: BLE001 - optional import must not break the dialog
            return
        names = ", ".join(feed["name"] for feed in added)
        key = "Added your blindDL indexer: {names}." if len(added) == 1 else "Added your blindDL indexers: {names}."
        self._say(_fmt(self._, key, names=names))

    # -- searching ----------------------------------------------------------

    def _prefs(self):
        return self.config_manager.get_preferences()

    def on_search(self, event=None):
        query = self.query.GetValue().strip()
        if not query:
            self._say(self._("Type what to look for first."))
            self.query.SetFocus()
            return
        prefs = self._prefs()
        sources = torrent_search.enabled_sources(
            prefs.get("disabled_torrent_sources") or (), prefs)
        if not sources:
            self._say(self._("No indexers are switched on. Use Search sites."))
            return

        # Any search already running belongs to an older query; let it finish
        # into a token nothing is listening for.
        self._stop.set()
        self._stop = threading.Event()
        self._token += 1
        token = self._token
        stop = self._stop

        self.results = []
        self.list.DeleteAllItems()
        self.add_btn.Enable(False)
        self._pending = len(sources)
        key = "Searching {count} indexer..." if len(sources) == 1 else "Searching {count} indexers..."
        self._say(_fmt(self._, key, count=len(sources)))
        self.search_btn.Enable(False)

        threading.Thread(
            target=self._search_worker,
            args=(query, sources, prefs, token, stop),
            name="torrent-search", daemon=True).start()

    def _search_worker(self, query, sources, prefs, token, stop):
        def on_indexer(source, items):
            wx.CallAfter(self._add_rows, token, source, items)

        try:
            torrent_search.search(
                query, timeout_s=torrent_search.SEARCH_TIMEOUT_S,
                on_site=on_indexer, stop=stop, sources=sources, prefs=prefs)
        except Exception as exc:  # noqa: BLE001 - reported, never fatal
            wx.CallAfter(self._say, _fmt(self._, "Search failed: {error}", error=exc))
        wx.CallAfter(self._search_done, token)

    def _result_count(self, count):
        key = "{count} result" if count == 1 else "{count} results"
        return _fmt(self._, key, count=count)

    def _add_rows(self, token, source, items):
        """One indexer answered. Results appear as they arrive."""
        if token != self._token or not self:
            return
        self._pending = max(0, self._pending - 1)
        had_results = bool(self.results)
        if items:
            self.results.extend(items)
            self._repopulate()
            # search() deliberately lets slow indexers report after its deadline.
            # If _search_done() already ran with zero results, make a late first
            # result usable without stealing keyboard focus back from the query.
            if self.search_btn.IsEnabled():
                self.add_btn.Enable(True)
                count = len(self.results)
                key = "Results, {count} result" if count == 1 else "Results, {count} results"
                self.list.SetName(_fmt(self._, key, count=count))
                if not had_results and self.list.GetItemCount():
                    self.list.Select(0)
                    self.list.Focus(0)
        count = len(self.results)
        if self._pending:
            key = ("{count} result so far, {pending} still searching. Last: {source}."
                   if count == 1 else
                   "{count} results so far, {pending} still searching. Last: {source}.")
            self._say(_fmt(self._, key, count=count, pending=self._pending, source=source))
        else:
            self._say(self._result_count(count) + ".")

    def _search_done(self, token):
        if token != self._token or not self:
            return
        self.search_btn.Enable(True)
        count = len(self.results)
        if not count:
            self._say(self._(
                "Nothing found. Try fewer words, or switch on more indexers in Search sites."))
            self.query.SetFocus()
            return
        self._say(self._result_count(count) + ".")
        self.add_btn.Enable(True)
        # NVDA reads a control's name when it takes focus, which is how the
        # count gets spoken without a status bar to point at.
        key = "Results, {count} result" if count == 1 else "Results, {count} results"
        self.list.SetName(_fmt(self._, key, count=count))
        if self.list.GetItemCount():
            self.list.Select(0)
            self.list.Focus(0)
        self.list.SetFocus()

    def _repopulate(self):
        """Redraw the list, keeping whatever row the user was on."""
        focused = self.list.GetFocusedItem()
        key = None
        if 0 <= focused < len(self.results):
            key = self.results[focused].get("id")

        self.results = _sorted_results(self.results,
                                       self.sort_choice.GetSelection())
        self.list.DeleteAllItems()
        for row, item in enumerate(self.results):
            self.list.InsertItem(row, item["title"])
            self.list.SetItem(row, 1, item.get("file_size") or "")
            self.list.SetItem(row, 2, str(item.get("seeders") or 0))
            self.list.SetItem(row, 3, str(item.get("leechers") or 0))
            self.list.SetItem(row, 4, item.get("age") or "")
            self.list.SetItem(row, 5, item.get("uploader") or item["source"])
            self.list.SetItem(row, 6, item.get("format") or "")

        if key is not None:
            for row, item in enumerate(self.results):
                if item.get("id") == key:
                    self.list.Select(row)
                    self.list.Focus(row)
                    break

    def on_sort(self, event=None):
        if not self.results:
            return
        self._repopulate()
        source_label = SORT_LABELS[self.sort_choice.GetSelection()]
        self._say(_fmt(self._, "Sorted by {label}.", label=self._(source_label)))

    def _say(self, message):
        self.status.SetLabel(message)

    # -- indexer settings ---------------------------------------------------

    def on_sources(self, event=None):
        dialog = SourcesDialog(self, self.config_manager)
        if dialog.ShowModal() == wx.ID_OK:
            dialog.apply()
            self._say(dialog.summary())
        dialog.Destroy()

    def on_feeds(self, event=None):
        dialog = IndexersDialog(self, self.config_manager)
        if dialog.ShowModal() == wx.ID_OK:
            dialog.apply()
            self._say(dialog.summary())
        dialog.Destroy()

    # -- picking ------------------------------------------------------------

    def _selected(self):
        rows = []
        row = self.list.GetFirstSelected()
        while row != -1:
            if 0 <= row < len(self.results):
                rows.append(self.results[row])
            row = self.list.GetNextSelected(row)
        return rows

    def on_add(self, event=None):
        picked = self._selected()
        if not picked:
            self._say(self._("Select a result first."))
            return
        self.chosen = picked
        self._stop.set()
        self.EndModal(wx.ID_OK)

    def on_char(self, event):
        if event.GetKeyCode() == ord("C") and event.ControlDown():
            self._copy_magnet()
            return
        event.Skip()

    def _copy_magnet(self):
        picked = self._selected()
        if not picked:
            self._say(self._("Select a result first."))
            return
        links = [torrent_search.magnet_for(item) for item in picked]
        links = [link for link in links if link]
        if not links:
            self._say(self._(
                "Those results carry a tracker file rather than a magnet link."))
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject("\n".join(links)))
            wx.TheClipboard.Close()
            key = "Copied {count} magnet link." if len(links) == 1 else "Copied {count} magnet links."
            self._say(_fmt(self._, key, count=len(links)))

    def on_close(self, event):
        self._stop.set()
        event.Skip()


class SourcesDialog(wx.Dialog):
    """Which indexers a search asks."""

    def __init__(self, parent, config_manager):
        self.config_manager = config_manager
        self._ = _translator_for(config_manager)
        super().__init__(parent, title=self._("Search sites"))
        prefs = config_manager.get_preferences()
        self.sources = torrent_search.sources_by_label(prefs)
        disabled = {str(name) for name in
                    (prefs.get("disabled_torrent_sources") or ())}

        sizer = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label=self._("&Indexers to search:"))
        self.checklist = wx.CheckListBox(self, choices=self.sources)
        self.checklist.SetName(self._("Indexers to search"))
        for index, source in enumerate(self.sources):
            self.checklist.Check(index, source not in disabled)

        all_btn = wx.Button(self, label=self._("Select &all"))
        none_btn = wx.Button(self, label=self._("Select &none"))
        all_btn.Bind(wx.EVT_BUTTON, lambda e: self._set_all(True))
        none_btn.Bind(wx.EVT_BUTTON, lambda e: self._set_all(False))
        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(all_btn, 0, wx.RIGHT, 8)
        row.Add(none_btn, 0)

        sizer.Add(label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.checklist, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL),
                  0, wx.ALL | wx.ALIGN_RIGHT, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize((420, 400))
        self.checklist.SetFocus()

    def _set_all(self, checked):
        for index in range(self.checklist.GetCount()):
            self.checklist.Check(index, checked)

    def apply(self):
        # The switched-off list is stored rather than the switched-on one, so
        # an indexer added in a later release is searched by default.
        disabled = [source for index, source in enumerate(self.sources)
                    if not self.checklist.IsChecked(index)]
        prefs = self.config_manager.get_preferences()
        prefs["disabled_torrent_sources"] = disabled
        self.config_manager.set_preferences(prefs)

    def summary(self):
        count = sum(1 for index in range(self.checklist.GetCount())
                    if self.checklist.IsChecked(index))
        key = "{count} indexer switched on." if count == 1 else "{count} indexers switched on."
        return _fmt(self._, key, count=count)


class IndexerDialog(wx.Dialog):
    """The name, URL and key of one feed."""

    def __init__(self, parent, translate, feed=None):
        self._ = translate
        super().__init__(parent,
                         title=self._("Edit indexer") if feed else self._("Add indexer"))
        feed = feed or {}
        sizer = wx.BoxSizer(wx.VERTICAL)

        name_label = wx.StaticText(self, label=self._("&Name:"))
        self.name_text = wx.TextCtrl(self, value=feed.get("name", ""))
        self.name_text.SetName(self._("Indexer name"))

        url_label = wx.StaticText(self, label=self._("&URL:"))
        self.url_text = wx.TextCtrl(self, value=feed.get("url", ""))
        self.url_text.SetName(self._("Indexer URL"))
        self.url_text.SetHelpText(_fmt(
            self._,
            "A Torznab or Newznab search endpoint. Prowlarr: {prowlarr}. Jackett, all trackers at once: {jackett}",
            prowlarr=PROWLARR_HINT,
            jackett=JACKETT_HINT,
        ))

        key_label = wx.StaticText(self, label=self._("API &key:"))
        self.key_text = wx.TextCtrl(self, value=feed.get("api_key", ""),
                                    style=wx.TE_PASSWORD)
        self.key_text.SetName(self._("API key"))
        self.key_text.SetHelpText(self._(
            "Copy it from Prowlarr or Jackett's own settings. Leave it empty if the endpoint needs no key."))

        hint = wx.StaticText(
            self,
            label=self._(
                "Private trackers work through Prowlarr or Jackett, which\n"
                "keep your tracker logins. SerrebiTorrent stores only this\n"
                "URL and key."))

        for label, control in ((name_label, self.name_text),
                               (url_label, self.url_text),
                               (key_label, self.key_text)):
            sizer.Add(label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 8)
            sizer.Add(control, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(hint, 0, wx.ALL, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL),
                  0, wx.ALL | wx.ALIGN_RIGHT, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize((560, self.GetSize().GetHeight()))
        self.name_text.SetFocus()

    def feed(self):
        return {
            "name": self.name_text.GetValue().strip(),
            "url": self.url_text.GetValue().strip(),
            "api_key": self.key_text.GetValue().strip(),
        }


class IndexersDialog(wx.Dialog):
    """The user's own Torznab feeds, with Add, Edit and Remove."""

    def __init__(self, parent, config_manager):
        self.config_manager = config_manager
        self._ = _translator_for(config_manager)
        super().__init__(parent, title=self._("My torrent indexers"))
        prefs = config_manager.get_preferences()
        self.feeds = [dict(feed) for feed in torrent_search.feeds(prefs)]

        sizer = wx.BoxSizer(wx.VERTICAL)
        list_label = wx.StaticText(self, label=self._("&Indexers:"))
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.list.SetName(self._("My torrent indexers"))
        self.list.SetHelpText(self._(
            "Enter edits the selected indexer. Delete removes it."))
        for index, heading in enumerate(("Name", "URL", "API key")):
            self.list.InsertColumn(index, self._(heading))
        self.list.SetColumnWidth(0, 150)
        self.list.SetColumnWidth(1, 330)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit)
        self.list.Bind(wx.EVT_CHAR, self.on_char)

        self.add_btn = wx.Button(self, label=self._("&Add..."))
        self.edit_btn = wx.Button(self, label=self._("&Edit..."))
        self.remove_btn = wx.Button(self, label=self._("&Remove"))
        self.add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.on_edit)
        self.remove_btn.Bind(wx.EVT_BUTTON, self.on_remove)
        actions = wx.BoxSizer(wx.HORIZONTAL)
        actions.Add(self.add_btn, 0, wx.RIGHT, 8)
        actions.Add(self.edit_btn, 0, wx.RIGHT, 8)
        actions.Add(self.remove_btn, 0)

        sizer.Add(list_label, 0, wx.TOP | wx.LEFT | wx.RIGHT, 8)
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 8)
        sizer.Add(actions, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        sizer.Add(self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL),
                  0, wx.ALL | wx.ALIGN_RIGHT, 8)
        self.SetSizerAndFit(sizer)
        self.SetSize((640, 420))
        self._refresh()
        self.list.SetFocus()

    def _refresh(self, select=-1):
        self.list.DeleteAllItems()
        for row, feed in enumerate(self.feeds):
            self.list.InsertItem(row, feed["name"])
            self.list.SetItem(row, 1, feed["url"])
            # Never redisplay the key itself; whether one is set is what the
            # user needs to check.
            self.list.SetItem(row, 2, self._("Set") if feed["api_key"] else self._("None"))
        if self.feeds:
            row = min(max(select, 0), len(self.feeds) - 1)
            self.list.Select(row)
            self.list.Focus(row)
        has = bool(self.feeds)
        self.edit_btn.Enable(has)
        self.remove_btn.Enable(has)

    def _selected(self):
        index = self.list.GetFirstSelected()
        return index if 0 <= index < len(self.feeds) else -1

    def _name_taken(self, name, skip=-1):
        lowered = name.casefold()
        if lowered in {source.casefold()
                       for source in torrent_search.ALL_SOURCES}:
            return True
        return any(feed["name"].casefold() == lowered
                   for index, feed in enumerate(self.feeds) if index != skip)

    def _ask(self, feed=None, index=-1):
        dialog = IndexerDialog(self, self._, feed)
        try:
            while dialog.ShowModal() == wx.ID_OK:
                entry = dialog.feed()
                if not entry["name"] or not entry["url"]:
                    wx.MessageBox(self._("An indexer needs both a name and a URL."),
                                  "SerrebiTorrent", wx.OK | wx.ICON_ERROR, self)
                    continue
                if self._name_taken(entry["name"], skip=index):
                    wx.MessageBox(
                        _fmt(self._,
                             "Another indexer is already called {name}. Choose a different name.",
                             name=entry["name"]),
                        "SerrebiTorrent", wx.OK | wx.ICON_ERROR, self)
                    continue
                return entry
            return None
        finally:
            dialog.Destroy()

    def on_add(self, event=None):
        entry = self._ask()
        if entry is None:
            return
        self.feeds.append(entry)
        self._refresh(len(self.feeds) - 1)
        self.list.SetFocus()

    def on_edit(self, event=None):
        index = self._selected()
        if index < 0:
            return
        entry = self._ask(self.feeds[index], index)
        if entry is None:
            return
        self.feeds[index] = entry
        self._refresh(index)
        self.list.SetFocus()

    def on_remove(self, event=None):
        index = self._selected()
        if index < 0:
            return
        removed = self.feeds.pop(index)
        self._refresh(index)
        self.list.SetFocus()
        wx.MessageBox(_fmt(self._, "Removed {name}.", name=removed["name"]),
                      "SerrebiTorrent", wx.OK | wx.ICON_INFORMATION, self)

    def on_char(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.on_remove()
            return
        event.Skip()

    def apply(self):
        """Save the feeds.

        A renamed or removed indexer leaves its name behind in the
        switched-off list, where it would silently switch off a later indexer
        that happened to reuse the name.
        """
        prefs = self.config_manager.get_preferences()
        prefs["torznab_feeds"] = [dict(feed) for feed in self.feeds]
        live = {source.casefold()
                for source in torrent_search.all_sources(prefs)}
        prefs["disabled_torrent_sources"] = [
            source for source in (prefs.get("disabled_torrent_sources") or ())
            if str(source).casefold() in live]
        self.config_manager.set_preferences(prefs)

    def summary(self):
        count = len(self.feeds)
        key = ("{count} of your own indexer configured."
               if count == 1 else
               "{count} of your own indexers configured.")
        return _fmt(self._, key, count=count)
