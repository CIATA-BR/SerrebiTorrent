from pathlib import Path


def test_late_search_results_become_actionable_after_deadline():
    source = Path("search_dialog.py").read_text(encoding="utf-8")
    start = source.index("    def _add_rows(self, token, source, items):")
    end = source.index("    def _search_done(self, token):", start)
    block = source[start:end]

    assert "self.search_btn.IsEnabled()" in block
    assert "self.add_btn.Enable(True)" in block
    assert "self.list.SetName(" in block
    assert "self.list.Select(0)" in block
    assert "self.list.Focus(0)" in block
