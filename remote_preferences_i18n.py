# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Brazilian Portuguese presentation for remote-client preferences."""

from __future__ import annotations

import json

import wx

import main as legacy
from main_ui_i18n import resolved_language, tr_main


_PT_BR = {
    "{client} Remote Settings": "Configurações remotas do {client}",
    "General": "Geral",
    "Downloads": "Downloads",
    "Connection": "Conexão",
    "Speed": "Velocidade",
    "BitTorrent": "BitTorrent",
    "Scheduler": "Agendador",
    "Scheduling": "Agendamento",
    "Network": "Rede",
    "Limits": "Limites",
    "Queue": "Fila",
    "Files": "Arquivos",
    "Scripts": "Scripts",
    "Trackers": "Trackers",
    "Proxy": "Proxy",
    "Notifications": "Notificações",
    "Other": "Outros",
    "Preferences": "Preferências",
    "Web UI": "Interface Web",
    "Remote client did not return any recognized preferences.": "O cliente remoto não retornou preferências reconhecidas.",
    "Enter a JSON object (e.g. {\"/watched\": \"/home/user\"}).": "Digite um objeto JSON (ex.: {\"/watched\": \"/home/user\"}).",
    "Leave blank to retain the current password.": "Deixe em branco para manter a senha atual.",
    "Invalid JSON for {label}: {error}": "JSON inválido em {label}: {error}",
    "Invalid integer for {label}: {error}": "Número inteiro inválido em {label}: {error}",
    "Invalid number for {label}: {error}": "Número inválido em {label}: {error}",
    "Every day": "Todos os dias",
    "Every weekday": "Dias úteis",
    "Every weekend": "Fins de semana",
    "Every Monday": "Toda segunda-feira",
    "Every Tuesday": "Toda terça-feira",
    "Every Wednesday": "Toda quarta-feira",
    "Every Thursday": "Toda quinta-feira",
    "Every Friday": "Toda sexta-feira",
    "Every Saturday": "Todo sábado",
    "Every Sunday": "Todo domingo",
    "Prefer encryption": "Preferir criptografia",
    "Force encryption on": "Forçar criptografia ativada",
    "Force encryption off": "Forçar criptografia desativada",
    "Proxy disabled": "Proxy desativado",
    "HTTP (no auth)": "HTTP (sem autenticação)",
    "SOCKS5 (no auth)": "SOCKS5 (sem autenticação)",
    "HTTP (with auth)": "HTTP (com autenticação)",
    "SOCKS5 (with auth)": "SOCKS5 (com autenticação)",
    "SOCKS4 (no auth)": "SOCKS4 (sem autenticação)",
    "Use DyDNS": "Usar DyDNS",
    "Use NOIP": "Usar NOIP",
    "Pause torrent": "Pausar torrent",
    "Remove torrent": "Remover torrent",
    "TCP and uTP": "TCP e uTP",
    "Round-robin": "Round-robin",
    "Fastest upload": "Upload mais rápido",
    "Anti-leech": "Anti-leech",
    "Fixed slots": "Slots fixos",
    "Upload-rate based": "Baseado na taxa de upload",
    "Prefer TCP": "Preferir TCP",
    "Peer proportional": "Proporcional aos peers",
    "Auto": "Automático",
    "On": "Ativado",
    "Off": "Desativado",
    "None": "Nenhum",
    "Fetching {name} preferences...": "Obtendo preferências do {name}...",
    "Failed to retrieve preferences from remote client. The client might not support this feature or there is a connection issue.": "Não foi possível obter as preferências do cliente remoto. O cliente pode não oferecer suporte a esse recurso ou pode haver um problema de conexão.",
    "Failed to fetch preferences": "Falha ao obter preferências",
    "Failed to fetch remote preferences: {error}": "Falha ao obter preferências remotas: {error}",
    "Error fetching preferences": "Erro ao obter preferências",
    "Failed to retrieve preferences from remote client.": "Não foi possível obter as preferências do cliente remoto.",
    "Error": "Erro",
    "{name} preferences saved": "Preferências do {name} salvas",
    "Failed to update remote preferences: {error}": "Falha ao atualizar preferências remotas: {error}",
}

_WORDS = {
    "Enabled": "Ativado",
    "Enable": "Ativar",
    "Disabled": "Desativado",
    "Download": "Download",
    "Downloads": "Downloads",
    "Upload": "Upload",
    "Uploads": "Uploads",
    "Rate": "Taxa",
    "Limit": "Limite",
    "Limits": "Limites",
    "Path": "Caminho",
    "Directory": "Diretório",
    "Default": "Padrão",
    "Maximum": "Máximo",
    "Max": "Máx.",
    "Minimum": "Mínimo",
    "Min": "Mín.",
    "Connections": "Conexões",
    "Connection": "Conexão",
    "Port": "Porta",
    "Random": "Aleatória",
    "Start": "Iniciar",
    "Started": "Iniciados",
    "Paused": "Pausados",
    "Files": "Arquivos",
    "File": "Arquivo",
    "Incomplete": "Incompleto",
    "Rename": "Renomear",
    "Trash": "Excluir",
    "Original": "Original",
    "Cache": "Cache",
    "Size": "Tamanho",
    "Time": "Tempo",
    "Days": "Dias",
    "Day": "Dia",
    "Hour": "Hora",
    "Address": "Endereço",
    "Interface": "Interface",
    "Current": "Atual",
    "Network": "Rede",
    "Peer": "Peer",
    "Peers": "Peers",
    "Torrent": "Torrent",
    "Torrents": "Torrents",
    "Ratio": "Proporção",
    "Seed": "Seed",
    "Seeding": "Semeadura",
    "Queue": "Fila",
    "Checking": "Verificação",
    "Memory": "Memória",
    "Disk": "Disco",
    "Read": "Leitura",
    "Write": "Gravação",
    "Username": "Usuário",
    "Password": "Senha",
    "Authentication": "Autenticação",
    "Auth": "Autenticação",
    "Secure": "Seguro",
    "Protection": "Proteção",
    "Session": "Sessão",
    "Timeout": "Tempo limite",
    "Alternative": "Alternativa",
    "Custom": "Personalizados",
    "Headers": "Cabeçalhos",
    "Header": "Cabeçalho",
    "Mail": "E-mail",
    "Notification": "Notificação",
    "Sender": "Remetente",
    "Processing": "Processamento",
    "Refresh": "Atualização",
    "Interval": "Intervalo",
    "Articles": "Artigos",
    "Rules": "Regras",
    "Rule": "Regra",
    "Proxy": "Proxy",
    "Host": "Host",
    "Global": "Global",
    "Local": "Local",
    "Auto": "Automático",
    "Automatic": "Automático",
    "Anonymous": "Anônimo",
    "Encryption": "Criptografia",
    "Resolve": "Resolver",
    "Countries": "Países",
    "Country": "País",
    "Script": "Script",
    "Done": "Concluído",
    "Filename": "Nome do arquivo",
}


def _language_from_parent(parent):
    current = parent
    for _ in range(6):
        if current is None:
            break
        try:
            return current._language()
        except Exception:
            pass
        try:
            prefs = current.config_manager.get_preferences()
            return prefs.get("language", "system")
        except Exception:
            pass
        try:
            current = current.GetParent()
        except Exception:
            break
    return "system"


def tr_remote(text, language=None):
    translated = tr_main(text, language)
    if translated != text:
        return translated
    if resolved_language(language) == "pt-BR":
        return _PT_BR.get(text, text)
    return text


def _translate_field_label(label, language):
    if resolved_language(language) != "pt-BR":
        return label
    direct = _PT_BR.get(label)
    if direct:
        return direct
    return " ".join(_WORDS.get(word, word) for word in label.split(" "))


class LocalizedRemotePreferencesDialog(legacy.RemotePreferencesDialog):
    def __init__(self, parent, prefs, client_name="qBittorrent"):
        self._remote_language = _language_from_parent(parent)
        super().__init__(parent, prefs, client_name)
        language = self._remote_language
        self.SetTitle(tr_remote("{client} Remote Settings", language).format(client=client_name))

        for child in self.GetChildren():
            if isinstance(child, wx.Notebook):
                for index in range(child.GetPageCount()):
                    child.SetPageText(index, tr_remote(child.GetPageText(index), language))
                    page = child.GetPage(index)
                    if child.GetPageText(index) == tr_remote("Preferences", language):
                        for nested in page.GetChildren():
                            if isinstance(nested, wx.StaticText):
                                nested.SetLabel(
                                    tr_remote(
                                        "Remote client did not return any recognized preferences.",
                                        language,
                                    )
                                )
                break

        for key, meta in self.field_controls.items():
            control = meta.get("control")
            if control is not None:
                try:
                    control.SetName(self._format_label(key))
                except Exception:
                    pass

    def _format_label(self, key):
        label = super()._format_label(key)
        return _translate_field_label(label, getattr(self, "_remote_language", "system"))

    def _create_non_bool_control(self, panel, key, value, field_type):
        if field_type == "choice":
            choices = self.ENUM_CHOICES.get(key, [])
            labels = [tr_remote(label, self._remote_language) for label, _ in choices]
            control = wx.Choice(panel, choices=labels)
            selection = 0
            for index, (_, stored_value) in enumerate(choices):
                if stored_value == value:
                    selection = index
                    break
            control.SetSelection(selection)
            return control

        control = super()._create_non_bool_control(panel, key, value, field_type)
        if field_type == "json":
            control.SetToolTip(
                tr_remote(
                    'Enter a JSON object (e.g. {"/watched": "/home/user"}).',
                    self._remote_language,
                )
            )
        if key in self.PASSWORD_FIELDS:
            control.SetHint(
                tr_remote(
                    "Leave blank to retain the current password.",
                    self._remote_language,
                )
            )
        return control

    def GetPreferences(self):
        prefs = {}
        for key, meta in self.field_controls.items():
            control = meta["control"]
            field_type = meta["type"]

            if field_type == "bool":
                prefs[key] = bool(control.GetValue())
                continue
            if field_type == "choice":
                selection = control.GetSelection()
                choices = meta.get("choices") or []
                if choices and selection >= 0:
                    prefs[key] = choices[selection][1]
                continue

            text = control.GetValue()
            if field_type == "json":
                stripped = text.strip()
                if not stripped:
                    prefs[key] = {}
                    continue
                try:
                    prefs[key] = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        tr_remote("Invalid JSON for {label}: {error}", self._remote_language).format(
                            label=self._format_label(key), error=exc
                        )
                    ) from exc
                continue
            if field_type == "int":
                stripped = text.strip()
                if stripped == "":
                    prefs[key] = self.prefs.get(key, 0)
                    continue
                try:
                    prefs[key] = int(stripped)
                except ValueError as exc:
                    raise ValueError(
                        tr_remote("Invalid integer for {label}: {error}", self._remote_language).format(
                            label=self._format_label(key), error=exc
                        )
                    ) from exc
                continue
            if field_type == "float":
                stripped = text.strip()
                if stripped == "":
                    prefs[key] = self.prefs.get(key, 0.0)
                    continue
                try:
                    prefs[key] = float(stripped)
                except ValueError as exc:
                    raise ValueError(
                        tr_remote("Invalid number for {label}: {error}", self._remote_language).format(
                            label=self._format_label(key), error=exc
                        )
                    ) from exc
                continue
            if key in self.PASSWORD_FIELDS and not text:
                continue
            prefs[key] = text
        return prefs


def localized_on_remote_preferences(self, event):
    if not self.connected:
        return
    name = "Remote Client"
    if isinstance(self.client, legacy.QBittorrentClient):
        name = "qBittorrent"
    elif isinstance(self.client, legacy.RTorrentClient):
        name = "rTorrent"
    elif isinstance(self.client, legacy.TransmissionClient):
        name = "Transmission"
    elif isinstance(self.client, legacy.LocalClient):
        name = "Local"
    language = self._language() if hasattr(self, "_language") else "system"
    self.statusbar.SetStatusText(
        tr_remote("Fetching {name} preferences...", language).format(name=name), 0
    )
    self.thread_pool.submit(self._fetch_remote_preferences, self.client, self.client_generation)


def localized_fetch_remote_preferences(self, client, generation):
    language = self._language() if hasattr(self, "_language") else "system"
    try:
        prefs = client.get_app_preferences()
        if generation != self.client_generation:
            return
        if prefs is None:
            wx.CallAfter(
                wx.MessageBox,
                tr_remote(
                    "Failed to retrieve preferences from remote client. The client might not support this feature or there is a connection issue.",
                    language,
                ),
                tr_remote("Error", language),
                wx.OK | wx.ICON_ERROR,
            )
            wx.CallAfter(
                self.statusbar.SetStatusText,
                tr_remote("Failed to fetch preferences", language),
                0,
            )
            return
        wx.CallAfter(self._show_remote_preferences_dialog, prefs, client, generation)
    except Exception as exc:  # noqa: BLE001 - remote client boundary
        wx.CallAfter(
            wx.LogError,
            tr_remote("Failed to fetch remote preferences: {error}", language).format(error=exc),
        )
        wx.CallAfter(
            self.statusbar.SetStatusText,
            tr_remote("Error fetching preferences", language),
            0,
        )


def localized_show_remote_preferences_dialog(self, prefs, client=None, generation=None):
    language = self._language() if hasattr(self, "_language") else "system"
    if generation is not None and generation != self.client_generation:
        return
    if prefs is None:
        wx.MessageBox(
            tr_remote("Failed to retrieve preferences from remote client.", language),
            tr_remote("Error", language),
            wx.OK | wx.ICON_ERROR,
        )
        return
    client = client or self.client
    client_name = "Remote"
    if isinstance(client, legacy.QBittorrentClient):
        client_name = "qBittorrent"
    elif isinstance(client, legacy.RTorrentClient):
        client_name = "rTorrent"
    elif isinstance(client, legacy.TransmissionClient):
        client_name = "Transmission"
    elif isinstance(client, legacy.LocalClient):
        client_name = "Local"

    dlg = LocalizedRemotePreferencesDialog(self, prefs, client_name)
    try:
        if dlg.ShowModal() == wx.ID_OK:
            try:
                parsed = dlg.GetPreferences()
                self.thread_pool.submit(
                    self._apply_remote_preferences, client, generation, parsed
                )
            except ValueError as exc:
                wx.MessageBox(str(exc), tr_remote("Error", language), wx.OK | wx.ICON_ERROR)
    finally:
        dlg.Destroy()


def localized_apply_remote_preferences(self, client, generation, prefs):
    language = self._language() if hasattr(self, "_language") else "system"
    try:
        if generation is not None and generation != self.client_generation:
            return
        client.set_app_preferences(prefs)
        name = "Remote"
        if isinstance(client, legacy.QBittorrentClient):
            name = "qBittorrent"
        elif isinstance(client, legacy.RTorrentClient):
            name = "rTorrent"
        elif isinstance(client, legacy.TransmissionClient):
            name = "Transmission"
        elif isinstance(client, legacy.LocalClient):
            name = "Local"
        wx.CallAfter(
            self.statusbar.SetStatusText,
            tr_remote("{name} preferences saved", language).format(name=name),
            0,
        )
        wx.CallAfter(self._update_client_default_save_path)
    except Exception as exc:  # noqa: BLE001 - remote client boundary
        wx.CallAfter(
            wx.LogError,
            tr_remote("Failed to update remote preferences: {error}", language).format(error=exc),
        )


def install_remote_preferences_localization():
    legacy.RemotePreferencesDialog = LocalizedRemotePreferencesDialog
    legacy.MainFrame.on_remote_preferences = localized_on_remote_preferences
    legacy.MainFrame._fetch_remote_preferences = localized_fetch_remote_preferences
    legacy.MainFrame._show_remote_preferences_dialog = localized_show_remote_preferences_dialog
    legacy.MainFrame._apply_remote_preferences = localized_apply_remote_preferences
