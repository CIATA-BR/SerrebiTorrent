# Copyright (c) serrebidev and contributors
# SPDX-License-Identifier: MIT

"""Small, dependency-free localization helper for SerrebiTorrent.

English source strings remain the canonical fallback. Catalogs can translate
only the strings they know, which lets localization be introduced screen by
screen without breaking untranslated UI or accessibility names.
"""

from __future__ import annotations

import locale
import os
from typing import Mapping

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "pt-BR")
LANGUAGE_OPTIONS = (
    ("system", "System"),
    ("en", "English"),
    ("pt-BR", "Português (Brasil)"),
)


def normalize_language(value: str | None) -> str:
    """Return a supported language tag, falling back to English."""
    raw = str(value or "").strip().replace("_", "-").lower()
    if raw in {"pt", "pt-br", "pt-brazil", "portuguese-brazil"}:
        return "pt-BR"
    if raw.startswith("pt-br.") or raw.startswith("pt-br@"):  # POSIX locale suffixes
        return "pt-BR"
    return DEFAULT_LANGUAGE


def system_language() -> str:
    """Resolve the OS locale without changing the process locale."""
    for env_name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(env_name)
        if value:
            resolved = normalize_language(value)
            if resolved != DEFAULT_LANGUAGE or value.lower().startswith("en"):
                return resolved

    try:
        current = locale.getlocale()[0]
    except Exception:
        current = None
    return normalize_language(current)


def language_options(language: str | None = None):
    """Return stable preference values paired with localized display labels."""
    tr = translator(language)
    return [(value, tr(label)) for value, label in LANGUAGE_OPTIONS]


_PT_BR: Mapping[str, str] = {
    # Generic actions.
    "Add": "Adicionar",
    "Edit": "Editar",
    "Delete": "Excluir",
    "Remove": "Remover",
    "Close": "Fechar",
    "Cancel": "Cancelar",
    "Connect": "Conectar",
    "Set Default": "Definir como padrão",
    "Confirm": "Confirmar",
    "Warning": "Aviso",
    "Default": "Padrão",
    "OK": "OK",
    "Browse...": "Procurar...",
    "Select All": "Selecionar tudo",
    "Deselect All": "Desmarcar tudo",
    "Settings": "Configurações",
    "Search": "Pesquisar",
    "Name": "Nome",
    "Size": "Tamanho",
    "Status": "Status",
    "Progress": "Progresso",
    "Priority": "Prioridade",
    "Files": "Arquivos",
    "Peers": "Peers",
    "Trackers": "Trackers",
    "Categories": "Categorias",
    "All": "Todos",
    "Downloading": "Baixando",
    "Finished": "Concluídos",
    "Active": "Ativos",
    "System": "Sistema",
    "English": "English",
    "Português (Brasil)": "Português (Brasil)",
    # Connection/profile UI.
    "Connection Manager": "Gerenciador de conexões",
    "Connection profiles": "Perfis de conexão",
    "Choose a profile, then connect or manage it with the buttons below.":
        "Escolha um perfil e use os botões abaixo para conectar ou gerenciá-lo.",
    "Add Profile": "Adicionar perfil",
    "Edit Profile": "Editar perfil",
    "Profile Name:": "Nome do perfil:",
    "Profile Name": "Nome do perfil",
    "Client Type:": "Tipo de cliente:",
    "Client Type": "Tipo de cliente",
    "URL (e.g. scgi://... or http://...):": "URL (ex.: scgi://... ou http://...):",
    "URL or download path": "URL ou pasta de download",
    "Username": "Nome de usuário",
    "Password": "Senha",
    "Download Path:": "Pasta de download:",
    "Choose Download Folder": "Escolher pasta de download",
    "Delete this profile?": "Excluir este perfil?",
    "Please select a profile to connect.": "Selecione um perfil para conectar.",
    # Local settings UI.
    "Local Session Settings": "Configurações da sessão local",
    "General": "Geral",
    "Connection": "Conexão",
    "Proxy": "Proxy",
    "Language:": "Idioma:",
    "Default Download Path:": "Pasta padrão de downloads:",
    "Automatically start torrents": "Iniciar torrents automaticamente",
    "Minimize to System Tray": "Minimizar para a área de notificação",
    "Close to System Tray": "Fechar para a área de notificação",
    "Check for updates automatically on startup": "Verificar atualizações automaticamente ao iniciar",
    "Global Limits (0 or -1 for unlimited):": "Limites globais (0 ou -1 para ilimitado):",
    "Download Rate (bytes/s):": "Taxa de download (bytes/s):",
    "Upload Rate (bytes/s):": "Taxa de upload (bytes/s):",
    "Max Connections:": "Máximo de conexões:",
    "Max Upload Slots:": "Máximo de slots de upload:",
    "Listening Port:": "Porta de escuta:",
    "Announce IP (reported to trackers, blank = auto):":
        "IP de anúncio (informado aos trackers; em branco = automático):",
    "Enable UPnP Port Mapping": "Ativar mapeamento de porta UPnP",
    "Enable NAT-PMP Port Mapping": "Ativar mapeamento de porta NAT-PMP",
    "Enable DHT": "Ativar DHT",
    "Enable Local Service Discovery (LSD)": "Ativar descoberta de serviço local (LSD)",
    "Automatically add trackers from URL": "Adicionar trackers automaticamente a partir de uma URL",
    "Tracker List URL:": "URL da lista de trackers:",
    "RSS Update Interval (seconds):": "Intervalo de atualização do RSS (segundos):",
    "Reset RSS (Clear all feeds and rules)": "Redefinir RSS (apagar todos os feeds e regras)",
    "Enable Web UI": "Ativar interface Web",
    "Bind Host:": "Host de escuta:",
    "Port:": "Porta:",
    "Username:": "Nome de usuário:",
    "Password:": "Senha:",
    "Proxy Type:": "Tipo de proxy:",
    "Host:": "Host:",
    "Authentication (if required):": "Autenticação (se necessária):",
    "Choose Download Directory": "Escolher pasta de download",
    "Are you sure you want to clear ALL RSS feeds and rules?":
        "Tem certeza de que deseja apagar TODOS os feeds e regras de RSS?",
    "Confirm Reset": "Confirmar redefinição",
    "RSS data reset successfully.": "Dados de RSS redefinidos com sucesso.",
    "Success": "Sucesso",
    "Reset failed: {error}": "Falha ao redefinir: {error}",
    # Torrent/search UI.
    "Torrent List": "Lista de torrents",
    "Search for Torrents": "Pesquisar torrents",
    "Search for": "Pesquisar por",
    "&Search for:": "&Pesquisar por:",
    "Sea&rch": "Pes&quisar",
    "Sort by": "Ordenar por",
    "Sort &by:": "Ordenar &por:",
    "Search sites...": "Sites de pesquisa...",
    "Search si&tes...": "Sites de pes&quisa...",
    "My indexers...": "Meus indexadores...",
    "My &indexers...": "Meus &indexadores...",
    "Results": "Resultados",
    "&Add selected": "&Adicionar selecionados",
    "&Close": "&Fechar",
    "Search sites": "Sites de pesquisa",
    "&Indexers to search:": "&Indexadores a pesquisar:",
    "Indexers to search": "Indexadores a pesquisar",
    "Select &all": "Selecionar &todos",
    "Select &none": "Desmarcar t&odos",
    "Edit indexer": "Editar indexador",
    "Add indexer": "Adicionar indexador",
    "&Name:": "&Nome:",
    "Indexer name": "Nome do indexador",
    "&URL:": "&URL:",
    "Indexer URL": "URL do indexador",
    "API &key:": "&Chave de API:",
    "API key": "Chave de API",
    "My torrent indexers": "Meus indexadores de torrent",
    "&Indexers:": "&Indexadores:",
    "&Add...": "&Adicionar...",
    "&Edit...": "&Editar...",
    "&Remove": "&Remover",
    "Most seeders": "Mais seeds",
    "Best match": "Melhor correspondência",
    "Largest": "Maior",
    "Newest": "Mais recente",
    "Age": "Idade",
    "Indexer": "Indexador",
    "Category": "Categoria",
    "Enter adds the selected torrents. Control C copies the magnet link.":
        "Enter adiciona os torrents selecionados. Control C copia o link magnet.",
    "Type what to look for.": "Digite o que deseja pesquisar.",
    "Type what to look for first.": "Digite primeiro o que deseja pesquisar.",
    "No indexers are switched on. Use Search sites.":
        "Nenhum indexador está ativado. Use Sites de pesquisa.",
    "Searching {count} indexer...": "Pesquisando em {count} indexador...",
    "Searching {count} indexers...": "Pesquisando em {count} indexadores...",
    "Search failed: {error}": "Falha na pesquisa: {error}",
    "{count} result": "{count} resultado",
    "{count} results": "{count} resultados",
    "{count} result so far, {pending} still searching. Last: {source}.":
        "{count} resultado até agora, {pending} ainda pesquisando. Último: {source}.",
    "{count} results so far, {pending} still searching. Last: {source}.":
        "{count} resultados até agora, {pending} ainda pesquisando. Último: {source}.",
    "Nothing found. Try fewer words, or switch on more indexers in Search sites.":
        "Nada encontrado. Tente menos palavras ou ative mais indexadores em Sites de pesquisa.",
    "Results, {count} result": "Resultados, {count} resultado",
    "Results, {count} results": "Resultados, {count} resultados",
    "Sorted by {label}.": "Ordenado por {label}.",
    "Select a result first.": "Selecione primeiro um resultado.",
    "Those results carry a tracker file rather than a magnet link.":
        "Esses resultados contêm um arquivo de tracker em vez de um link magnet.",
    "Copied {count} magnet link.": "Copiado {count} link magnet.",
    "Copied {count} magnet links.": "Copiados {count} links magnet.",
    "Added your blindDL indexer: {names}.": "Adicionado seu indexador do blindDL: {names}.",
    "Added your blindDL indexers: {names}.": "Adicionados seus indexadores do blindDL: {names}.",
    "{count} indexer switched on.": "{count} indexador ativado.",
    "{count} indexers switched on.": "{count} indexadores ativados.",
    "A Torznab or Newznab search endpoint. Prowlarr: {prowlarr}. Jackett, all trackers at once: {jackett}":
        "Um endpoint de pesquisa Torznab ou Newznab. Prowlarr: {prowlarr}. Jackett, todos os trackers de uma vez: {jackett}",
    "Copy it from Prowlarr or Jackett's own settings. Leave it empty if the endpoint needs no key.":
        "Copie a chave das configurações do Prowlarr ou Jackett. Deixe em branco se o endpoint não exigir chave.",
    "Private trackers work through Prowlarr or Jackett, which\nkeep your tracker logins. SerrebiTorrent stores only this\nURL and key.":
        "Trackers privados funcionam pelo Prowlarr ou Jackett, que\nmantêm seus logins dos trackers. O SerrebiTorrent armazena apenas\nesta URL e a chave.",
    "Enter edits the selected indexer. Delete removes it.":
        "Enter edita o indexador selecionado. Delete o remove.",
    "Set": "Definida",
    "None": "Nenhuma",
    "An indexer needs both a name and a URL.": "Um indexador precisa de nome e URL.",
    "Another indexer is already called {name}. Choose a different name.":
        "Já existe outro indexador chamado {name}. Escolha um nome diferente.",
    "Removed {name}.": "{name} removido.",
    "{count} of your own indexer configured.": "{count} indexador próprio configurado.",
    "{count} of your own indexers configured.": "{count} indexadores próprios configurados.",
    # Torrent creator UI.
    "Create Torrent": "Criar torrent",
    "Source (file or folder):": "Origem (arquivo ou pasta):",
    "File...": "Arquivo...",
    "Folder...": "Pasta...",
    "Output .torrent file:": "Arquivo .torrent de saída:",
    "Save As...": "Salvar como...",
    "Torrent Options": "Opções do torrent",
    "Private torrent (disables DHT/PEX/LSD in most clients)":
        "Torrent privado (desativa DHT/PEX/LSD na maioria dos clientes)",
    "Piece size:": "Tamanho da peça:",
    "Public tracker list (press Enter to add to Included trackers).":
        "Lista de trackers públicos (pressione Enter para adicionar aos trackers incluídos).",
    "Included trackers (one per line):": "Trackers incluídos (um por linha):",
    "Add Tracker": "Adicionar tracker",
    "Remove Selected": "Remover selecionados",
    "Web Seeds (optional)": "Web seeds (opcional)",
    "One URL per line (HTTP/HTTPS).": "Uma URL por linha (HTTP/HTTPS).",
    "Metadata (optional)": "Metadados (opcional)",
    "Comment:": "Comentário:",
    "Source (written into info dict as 'source'):": "Origem (gravada no dicionário info como 'source'):",
    "Created by:": "Criado por:",
    "After Creation": "Após a criação",
    "Add created torrent to the currently connected client":
        "Adicionar o torrent criado ao cliente conectado atualmente",
    "Copy magnet link to clipboard": "Copiar link magnet para a área de transferência",
    "Select File": "Selecionar arquivo",
    "Select Folder": "Selecionar pasta",
    "Save Torrent As": "Salvar torrent como",
    "Torrent files (*.torrent)|*.torrent": "Arquivos torrent (*.torrent)|*.torrent",
    "Check for Updates": "Verificar atualizações",
    # Columns and common torrent terminology.
    "Seeds": "Seeds",
    "Leechers": "Leechers",
    "Ratio": "Proporção",
    "Availability": "Disponibilidade",
    "Time Left": "Tempo restante",
    "Down Speed": "Velocidade de download",
    "Up Speed": "Velocidade de upload",
    "Client": "Cliente",
    "Message": "Mensagem",
    "Title": "Título",
    "Link": "Link",
}

CATALOGS: Mapping[str, Mapping[str, str]] = {
    "pt-BR": _PT_BR,
}


def translate(text: str, language: str | None = None) -> str:
    """Translate one English source string, preserving unknown strings."""
    lang = system_language() if language in (None, "", "system") else normalize_language(language)
    if lang == DEFAULT_LANGUAGE:
        return text
    return CATALOGS.get(lang, {}).get(text, text)


def translator(language: str | None = None):
    """Return a gettext-style translation callable bound to one language."""
    return lambda text: translate(text, language)
