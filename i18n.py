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


_PT_BR: Mapping[str, str] = {
    # Generic actions.
    "Add": "Adicionar",
    "Edit": "Editar",
    "Remove": "Remover",
    "Close": "Fechar",
    "Cancel": "Cancelar",
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
    # Torrent/search UI.
    "Torrent List": "Lista de torrents",
    "Search for Torrents": "Pesquisar torrents",
    "Search for": "Pesquisar por",
    "Sort by": "Ordenar por",
    "Search sites...": "Sites de pesquisa...",
    "My indexers...": "Meus indexadores...",
    "Results": "Resultados",
    "Add selected": "Adicionar selecionados",
    "Search sites": "Sites de pesquisa",
    "Indexers to search": "Indexadores a pesquisar",
    "Select all": "Selecionar todos",
    "Select none": "Desmarcar todos",
    "Edit indexer": "Editar indexador",
    "Add indexer": "Adicionar indexador",
    "Indexer name": "Nome do indexador",
    "Indexer URL": "URL do indexador",
    "API key": "Chave de API",
    "My torrent indexers": "Meus indexadores de torrent",
    "Connection Manager": "Gerenciador de conexões",
    "Create Torrent": "Criar torrent",
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
