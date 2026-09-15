"""Reusable accessibility support for virtual wx.ListCtrl controls."""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes

import wx

EVENT_OBJECT_FOCUS = 0x8005
OBJID_CLIENT = -4
_NOTIFY_WIN_EVENT = None


def notify_win_event(event, hwnd, object_id, child_id):
    """Send a Windows accessibility focus event; fail safely elsewhere."""
    if os.name != "nt" or not hwnd:
        return False

    global _NOTIFY_WIN_EVENT
    if _NOTIFY_WIN_EVENT is None:
        try:
            fn = ctypes.windll.user32.NotifyWinEvent
            fn.argtypes = [wintypes.DWORD, wintypes.HWND, wintypes.LONG, wintypes.LONG]
            fn.restype = None
            _NOTIFY_WIN_EVENT = fn
        except Exception:
            _NOTIFY_WIN_EVENT = False

    if not _NOTIFY_WIN_EVENT:
        return False

    try:
        _NOTIFY_WIN_EVENT(event, hwnd, object_id, child_id)
        return True
    except Exception:
        return False


class AccessibleVirtualListMixin:
    """Keep one focused row alive across virtual-list refreshes for screen readers."""

    _ACCESSIBLE_NAV_KEYS = {
        wx.WXK_UP,
        wx.WXK_DOWN,
        wx.WXK_LEFT,
        wx.WXK_RIGHT,
        wx.WXK_HOME,
        wx.WXK_END,
        wx.WXK_PAGEUP,
        wx.WXK_PAGEDOWN,
    }

    def init_accessible_virtual_list(self, *, pulse_navigation=False):
        self._accessible_pulse_navigation = pulse_navigation
        self._last_accessible_focus_event_idx = None
        self._last_accessible_focus_event_at = 0.0
        self.Bind(wx.EVT_SET_FOCUS, self._on_accessible_set_focus)
        if pulse_navigation:
            self.Bind(wx.EVT_KEY_DOWN, self._on_accessible_key_down)
            self.Bind(wx.EVT_LIST_ITEM_FOCUSED, self._on_accessible_item_focused)

    def _list_has_focus(self):
        try:
            return wx.Window.FindFocus() is self
        except Exception:
            return False

    def _restore_focus_row(self, item_count, preserve_idx=None, force=False):
        if item_count <= 0:
            return
        idx = preserve_idx if (preserve_idx is not None and preserve_idx >= 0) else 0
        idx = min(idx, item_count - 1)
        current = self.GetFocusedItem()
        has_focus = self._list_has_focus()
        force = bool(force and has_focus)
        if current == idx and not force:
            return
        if not has_focus and current != -1:
            return
        try:
            if force and current == idx:
                self.SetItemState(idx, 0, wx.LIST_STATE_FOCUSED)
            self.SetItemState(idx, wx.LIST_STATE_FOCUSED, wx.LIST_STATE_FOCUSED)
            if has_focus:
                self.EnsureVisible(idx)
        except Exception:
            pass

    def set_virtual_item_count(self, item_count, preserve_idx=None):
        if preserve_idx is None:
            preserve_idx = self.GetFocusedItem()
        count_changed = self.GetItemCount() != item_count
        if count_changed:
            self.SetItemCount(item_count)
        self.Refresh()
        self._restore_focus_row(item_count, preserve_idx, force=count_changed)

    def _force_current_focus_row(self, fallback_idx=None):
        item_count = self.GetItemCount()
        if item_count <= 0 or not self._list_has_focus():
            return None
        idx = self.GetFocusedItem()
        if idx < 0:
            idx = fallback_idx if fallback_idx is not None and fallback_idx >= 0 else 0
        self._restore_focus_row(item_count, idx, force=True)
        return idx

    def _on_accessible_set_focus(self, event):
        event.Skip()
        wx.CallAfter(self._force_current_focus_row)

    def _on_accessible_item_focused(self, event):
        event.Skip()
        if getattr(self, "_accessible_pulse_navigation", False):
            wx.CallAfter(self._notify_accessible_focus_event, event.GetIndex())

    def _on_accessible_key_down(self, event):
        before_idx = self.GetFocusedItem()
        nav_key = event.GetKeyCode() in self._ACCESSIBLE_NAV_KEYS
        event.Skip()
        if nav_key:
            wx.CallAfter(self._force_focus_after_navigation, before_idx)

    def _force_focus_after_navigation(self, before_idx):
        if not getattr(self, "_accessible_pulse_navigation", False):
            return
        idx = self.GetFocusedItem()
        if idx == before_idx and idx >= 0:
            return
        idx = self._force_current_focus_row(before_idx)
        if idx is not None:
            self._notify_accessible_focus_event(idx)

    def _notify_accessible_focus_event(self, idx):
        if idx is None or idx < 0 or not self._list_has_focus():
            return False

        now = time.monotonic()
        last_idx = getattr(self, "_last_accessible_focus_event_idx", None)
        last_at = getattr(self, "_last_accessible_focus_event_at", 0.0)
        if last_idx == idx and now - last_at < 0.08:
            return False

        try:
            hwnd = int(self.GetHandle())
        except Exception:
            return False

        if notify_win_event(EVENT_OBJECT_FOCUS, hwnd, OBJID_CLIENT, idx + 1):
            self._last_accessible_focus_event_idx = idx
            self._last_accessible_focus_event_at = now
            return True
        return False
