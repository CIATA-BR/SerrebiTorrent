from accessible_virtual_list import AccessibleVirtualListMixin


class DummyList(AccessibleVirtualListMixin):
    def __init__(self, *, count=3, focused=-1, has_focus=True):
        self.count = count
        self.focused = focused
        self.has_focus = has_focus
        self.states = []
        self.visible = []
        self.refreshed = 0

    def GetItemCount(self):
        return self.count

    def SetItemCount(self, count):
        self.count = count
        self.focused = -1

    def GetFocusedItem(self):
        return self.focused

    def _list_has_focus(self):
        return self.has_focus

    def SetItemState(self, idx, state, mask):
        self.states.append((idx, state, mask))
        if state:
            self.focused = idx
        elif self.focused == idx:
            self.focused = -1

    def EnsureVisible(self, idx):
        self.visible.append(idx)

    def Refresh(self):
        self.refreshed += 1


def test_restore_focus_seeds_first_row_when_list_has_focus():
    control = DummyList(focused=-1, has_focus=True)
    control._restore_focus_row(3)
    assert control.focused == 0
    assert control.visible == [0]


def test_background_refresh_does_not_move_existing_focus():
    control = DummyList(focused=2, has_focus=False)
    control._restore_focus_row(3, preserve_idx=0)
    assert control.focused == 2
    assert control.states == []


def test_item_count_change_restores_preserved_focus_row():
    control = DummyList(count=2, focused=1, has_focus=True)
    control.set_virtual_item_count(4, preserve_idx=1)
    assert control.count == 4
    assert control.focused == 1
    assert control.refreshed == 1


def test_preserved_focus_is_clamped_after_rows_disappear():
    control = DummyList(count=5, focused=4, has_focus=True)
    control.set_virtual_item_count(2, preserve_idx=4)
    assert control.focused == 1
