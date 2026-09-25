# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Localized RSS presentation layered over the legacy implementation."""

from __future__ import annotations

import wx

import main as legacy
from main_ui_i18n import resolved_language, tr_main


_PT_BR = {
    "RSS Articles": "Artigos RSS",
    "RSS Feeds": "Feeds RSS",
    "Title": "Título",
    "Link": "Link",
    "Add Feed": "Adicionar feed",
    "Remove Feed": "Remover feed",
    "Refresh All": "Atualizar todos",
    "Rules": "Regras",
    "Import FlexGet": "Importar FlexGet",
    "Error": "Erro",
    "Enter RSS Feed URL:": "Digite a URL do feed RSS:",
    "Remove feed {url}?": "Remover o feed {url}?",
    "Confirm": "Confirmar",
    "Import FlexGet Config": "Importar configuração do FlexGet",
    "YAML files (*.yml;*.yaml)|*.yml;*.yaml": "Arquivos YAML (*.yml;*.yaml)|*.yml;*.yaml",
    "Imported {feeds} feeds and {rules} rules.": "Importados {feeds} feeds e {rules} regras.",
    "Import Complete": "Importação concluída",
    "Failed to save RSS rule.": "Falha ao salvar a regra RSS.",
    "Import Failed: {error}": "Falha na importação: {error}",
    "Auto-added from RSS: {title}": "Adicionado automaticamente do RSS: {title}",
    "Adding torrent: {title}...": "Adicionando torrent: {title}...",
    "Added from RSS: {title}": "Adicionado do RSS: {title}",
    "Failed to add from RSS: {error}": "Falha ao adicionar do RSS: {error}",
    "Edit RSS Rule": "Editar regra RSS",
    "Add RSS Rule": "Adicionar regra RSS",
    "Regex Pattern:": "Padrão de expressão regular:",
    "Rule Type:": "Tipo de regra:",
    "Apply to Feeds (Uncheck all for Global):": "Aplicar aos feeds (desmarque todos para uso global):",
    "Accept": "Aceitar",
    "Reject": "Rejeitar",
    "RSS Rules Manager": "Gerenciador de regras RSS",
    "Type": "Tipo",
    "Pattern": "Padrão",
    "Scope": "Escopo",
    "Enabled": "Ativada",
    "Add Rule": "Adicionar regra",
    "Edit Rule": "Editar regra",
    "Delete": "Excluir",
    "Toggle": "Alternar",
    "Close": "Fechar",
    "Global": "Global",
    "None (No feeds)": "Nenhum (sem feeds)",
    "1 feed": "1 feed",
    "{count} feeds": "{count} feeds",
    "Yes": "Sim",
    "No": "Não",
}


def _language_from_frame(frame):
    try:
        return frame._language()
    except Exception:
        try:
            return frame.config_manager.get_preferences().get("language", "system")
        except Exception:
            return "system"


def _language_from_parent(parent):
    current = parent
    for _ in range(6):
        if current is None:
            break
        frame = getattr(current, "frame", None)
        if frame is not None:
            return _language_from_frame(frame)
        try:
            current = current.GetParent()
        except Exception:
            break
    return "system"


def tr_rss(text, language=None):
    translated = tr_main(text, language)
    if translated != text:
        return translated
    if resolved_language(language) == "pt-BR":
        return _PT_BR.get(text, text)
    return text


def _set_column_text(control, index, label):
    try:
        column = control.GetColumn(index)
        column.SetText(label)
        control.SetColumn(index, column)
    except Exception:
        pass


class LocalizedArticleListCtrl(legacy.ArticleListCtrl):
    def __init__(self, parent, panel):
        super().__init__(parent, panel)
        language = _language_from_frame(panel.frame)
        self.SetName(tr_rss("RSS Articles", language))
        _set_column_text(self, 0, tr_rss("Title", language))
        _set_column_text(self, 1, tr_rss("Link", language))


class LocalizedRuleEditDialog(legacy.RuleEditDialog):
    def __init__(self, parent, manager, rule=None):
        super().__init__(parent, manager, rule)
        self._rss_language = _language_from_parent(parent)
        self.SetTitle(tr_rss("Edit RSS Rule" if rule else "Add RSS Rule", self._rss_language))

        label_map = {
            "Regex Pattern:": "Regex Pattern:",
            "Rule Type:": "Rule Type:",
            "Apply to Feeds (Uncheck all for Global):": "Apply to Feeds (Uncheck all for Global):",
        }
        for child in self.GetChildren():
            if isinstance(child, wx.StaticText):
                source = child.GetLabel()
                if source in label_map:
                    child.SetLabel(tr_rss(source, self._rss_language))

        canonical_type = self.rule.get("type", "accept")
        if resolved_language(self._rss_language) == "pt-BR":
            self.type_choice.Set([tr_rss("Accept", self._rss_language), tr_rss("Reject", self._rss_language)])
            self.type_choice.SetSelection(0 if canonical_type == "accept" else 1)

        self.pattern_input.SetName(tr_rss("Regex Pattern:", self._rss_language))
        self.type_choice.SetName(tr_rss("Rule Type:", self._rss_language))
        self.check_list.SetName(
            tr_rss("Apply to Feeds (Uncheck all for Global):", self._rss_language)
        )

    def get_rule_data(self):
        checked_indices = self.check_list.GetCheckedItems()
        scope = None
        if checked_indices:
            scope = [self.feeds_list[index] for index in checked_indices]

        if resolved_language(self._rss_language) == "pt-BR":
            rule_type = "accept" if self.type_choice.GetSelection() == 0 else "reject"
        else:
            rule_type = self.type_choice.GetStringSelection()
        return {
            "pattern": self.pattern_input.GetValue(),
            "type": rule_type,
            "scope": scope,
            "enabled": self.rule.get("enabled", True),
        }


class LocalizedRulesManagerDialog(legacy.RulesManagerDialog):
    def __init__(self, parent, manager):
        self._rss_language = _language_from_parent(parent)
        super().__init__(parent, manager)
        self.SetTitle(tr_rss("RSS Rules Manager", self._rss_language))

        for index, source in enumerate(("Type", "Pattern", "Scope", "Enabled")):
            _set_column_text(self.list, index, tr_rss(source, self._rss_language))
        self.list.SetName(tr_rss("RSS Rules Manager", self._rss_language))

        for child in self.GetChildren():
            if isinstance(child, wx.Button):
                source = child.GetLabel()
                if source in {"Add Rule", "Edit Rule", "Delete", "Toggle", "Close"}:
                    child.SetLabel(tr_rss(source, self._rss_language))
        self.refresh_list()

    def _report_rule_save_failure(self):
        wx.MessageBox(
            tr_rss("Failed to save RSS rule.", self._rss_language),
            tr_rss("Error", self._rss_language),
            wx.OK | wx.ICON_ERROR,
        )

    def refresh_list(self):
        self.list.DeleteAllItems()
        language = getattr(self, "_rss_language", _language_from_parent(self))
        for index, rule in enumerate(self.manager.rules):
            rule_type = rule.get("type", "accept")
            type_text = tr_rss("Accept" if rule_type == "accept" else "Reject", language)
            row = self.list.InsertItem(index, type_text)
            self.list.SetItem(row, 1, rule["pattern"])

            scope = rule.get("scope")
            scope_text = tr_rss("Global", language)
            if isinstance(scope, list):
                if not scope:
                    scope_text = tr_rss("None (No feeds)", language)
                elif len(scope) == 1:
                    scope_text = tr_rss("1 feed", language)
                else:
                    scope_text = tr_rss("{count} feeds", language).format(count=len(scope))
            self.list.SetItem(row, 2, scope_text)
            self.list.SetItem(
                row,
                3,
                tr_rss("Yes" if rule.get("enabled", True) else "No", language),
            )


class LocalizedRSSPanel(legacy.RSSPanel):
    def __init__(self, parent, frame):
        super().__init__(parent, frame)
        self._rss_language = _language_from_frame(frame)

        for child in self.GetChildren():
            if isinstance(child, wx.Button):
                source = child.GetLabel()
                if source in {"Add Feed", "Remove Feed", "Refresh All", "Rules", "Import FlexGet"}:
                    child.SetLabel(tr_rss(source, self._rss_language))
        self.feed_list.SetName(tr_rss("RSS Feeds", self._rss_language))

    def refresh_feeds_list(self):
        self.feed_list.Clear()
        language = getattr(self, "_rss_language", _language_from_frame(self.frame))
        for url in self.manager.feeds:
            data = self.manager.feeds[url]
            alias = data.get("alias")
            label = alias if alias else url
            if data.get("last_error"):
                label += f" ({tr_rss('Error', language)})"
            self.feed_list.Append(label, url)

    def on_add_feed(self, event):
        language = self._rss_language
        dlg = wx.TextEntryDialog(
            self,
            tr_rss("Enter RSS Feed URL:", language),
            tr_rss("Add Feed", language),
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                url = dlg.GetValue().strip()
                try:
                    added = self.manager.add_feed(url)
                except ValueError as exc:
                    wx.MessageBox(
                        tr_rss("Error adding URL: {error}", language).format(error=exc),
                        tr_rss("Error", language),
                        wx.OK | wx.ICON_ERROR,
                    )
                    return
                if added:
                    self.refresh_feeds_list()
                    self._submit_feed_update(url)
        finally:
            dlg.Destroy()

    def on_remove_feed(self, event):
        selection = self.feed_list.GetSelection()
        if selection == wx.NOT_FOUND:
            return
        url = self.feed_list.GetClientData(selection)
        language = self._rss_language
        message = tr_rss("Remove feed {url}?", language).format(url=url)
        if wx.MessageBox(message, tr_rss("Confirm", language), wx.YES_NO) == wx.YES:
            self.manager.remove_feed(url)
            self.refresh_feeds_list()
            self.article_list.SetItemCount(0)
            self.current_articles = []

    def on_import_flexget(self, event):
        language = self._rss_language
        with wx.FileDialog(
            self,
            tr_rss("Import FlexGet Config", language),
            wildcard=tr_rss("YAML files (*.yml;*.yaml)|*.yml;*.yaml", language),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return
            path = file_dialog.GetPath()
            try:
                feeds, rules = self.manager.import_flexget_config(path)
                wx.MessageBox(
                    tr_rss("Imported {feeds} feeds and {rules} rules.", language).format(
                        feeds=feeds, rules=rules
                    ),
                    tr_rss("Import Complete", language),
                    wx.OK | wx.ICON_INFORMATION,
                )
                self.refresh_feeds_list()
                self.on_refresh_all(None)
            except Exception as exc:  # noqa: BLE001 - UI boundary
                wx.MessageBox(
                    tr_rss("Import Failed: {error}", language).format(error=exc),
                    tr_rss("Error", language),
                    wx.OK | wx.ICON_ERROR,
                )

    def _update_feed(self, url, client, generation):
        try:
            articles = self.manager.fetch_feed(url)
            matches = self.manager.get_matches(articles, feed_url=url)
            for match in matches:
                if self.manager.is_downloaded(url, match.get("uid")):
                    continue
                if client and generation == self.frame.client_generation:
                    try:
                        link = match["link"]
                        if not link.lower().startswith("magnet:"):
                            legacy.validate_public_torrent_url(link)
                        client.add_torrent_url(link)
                        self.manager.mark_downloaded(url, match.get("uid"))
                        status = tr_rss(
                            "Auto-added from RSS: {title}", self._rss_language
                        ).format(title=match["title"])
                        wx.CallAfter(self.frame.statusbar.SetStatusText, status, 0)
                    except Exception as exc:  # noqa: BLE001 - background item boundary
                        print(f"Auto-add error: {exc}")
            wx.CallAfter(self.refresh_feeds_list)
            wx.CallAfter(self.refresh_articles_if_selected, url)
        finally:
            with self._refreshing_feeds_lock:
                self._refreshing_feeds.discard(url)

    def on_download_article(self, event):
        index = event.GetIndex()
        if 0 <= index < len(self.current_articles):
            article = self.current_articles[index]
            status = tr_rss("Adding torrent: {title}...", self._rss_language).format(
                title=article["title"]
            )
            self.frame.statusbar.SetStatusText(status, 0)
            self.frame.thread_pool.submit(
                self.download_article,
                article,
                self.frame.client,
                self.frame.client_generation,
            )

    def download_article(self, article, client, generation):
        url = article["link"]
        if client and generation == self.frame.client_generation:
            try:
                if not url.lower().startswith("magnet:"):
                    legacy.validate_public_torrent_url(url)
                client.add_torrent_url(url)
                if generation == self.frame.client_generation:
                    status = tr_rss("Added from RSS: {title}", self._rss_language).format(
                        title=article["title"]
                    )
                    wx.CallAfter(self.frame.statusbar.SetStatusText, status, 0)
            except Exception as exc:  # noqa: BLE001 - background item boundary
                if generation == self.frame.client_generation:
                    message = tr_rss(
                        "Failed to add from RSS: {error}", self._rss_language
                    ).format(error=exc)
                    wx.CallAfter(wx.LogError, message)
