"""Localization helpers for the main window while it is being split out of main.py."""

from __future__ import annotations

from i18n import normalize_language, system_language, translate


_PT_BR_MAIN = {
    # Sidebar and torrent states.
    "All": "Todos",
    "Downloading": "Baixando",
    "Finished": "Concluídos",
    "Seeding": "Semeando",
    "Stopped": "Parados",
    "Failed": "Com falha",
    "Trackers": "Trackers",
    "Categories": "Categorias",
    "Torrent List": "Lista de torrents",
    "Unknown": "Desconhecido",
    "Checking": "Verificando",
    "Downloaded: {percent:.1f}%": "Baixado: {percent:.1f}%",
    # Main list columns.
    "Name": "Nome",
    "Size": "Tamanho",
    "Status": "Status",
    "Time Left": "Tempo restante",
    "Seeds": "Seeds",
    "Leechers": "Leechers",
    "Ratio": "Proporção",
    "Availability": "Disponibilidade",
    # Details pane.
    "Files": "Arquivos",
    "Peers": "Peers",
    "Progress": "Progresso",
    "Priority": "Prioridade",
    "Skip": "Ignorar",
    "Normal": "Normal",
    "High": "Alta",
    "Client": "Cliente",
    "Down Speed": "Velocidade de download",
    "Up Speed": "Velocidade de upload",
    "Message": "Mensagem",
    # Menus.
    "&File": "&Arquivo",
    "&Actions": "&Ações",
    "&Tools": "&Ferramentas",
    "&Help": "A&juda",
    "&Connect": "&Conectar",
    "&Connect...\tCtrl+Shift+C": "&Conectar...\tCtrl+Shift+C",
    "Connection Manager...\tCtrl+Shift+C": "Gerenciador de conexões...\tCtrl+Shift+C",
    "&Add Torrent File...\tCtrl+O": "&Adicionar arquivo torrent...\tCtrl+O",
    "Add &URL/Magnet...\tCtrl+U": "Adicionar &URL/Magnet...\tCtrl+U",
    "Create &Torrent...\tCtrl+N": "Criar &torrent...\tCtrl+N",
    "E&xit": "Sai&r",
    "&Start\tCtrl+S": "&Iniciar\tCtrl+S",
    "&Pause\tCtrl+P": "&Pausar\tCtrl+P",
    "&Resume\tCtrl+R": "&Retomar\tCtrl+R",
    "Force Re&check": "Forçar &reverificação",
    "Force Reannoun&ce": "Forçar novo anún&cio",
    "Copy &Info Hash\tCtrl+I": "Copiar &info hash\tCtrl+I",
    "Copy &Magnet Link\tCtrl+M": "Copiar link &magnet\tCtrl+M",
    "Open Download &Folder": "Abrir &pasta de download",
    "&Remove\tDel": "&Remover\tDel",
    "Remove with &Data\tShift+Del": "Remover com &dados\tShift+Del",
    "Select &All\tCtrl+A": "Selecionar &todos\tCtrl+A",
    "&Search for Torrents...\tCtrl+F": "&Pesquisar torrents...\tCtrl+F",
    "Register &Associations": "Registrar &associações",
    "Check for &Updates...\tF5": "Verificar &atualizações...\tF5",
    "Local Session &Settings...\tCtrl+,": "&Configurações da sessão local...\tCtrl+,",
    "qBittorrent Remote &Settings...": "&Configurações remotas do qBittorrent...",
    "Transmission Remote &Settings...": "&Configurações remotas do Transmission...",
    "rTorrent Remote &Settings...": "&Configurações remotas do rTorrent...",
    "&About SerrebiTorrent": "&Sobre o SerrebiTorrent",
    # Menu help text exposed by wx and assistive technology.
    "Connect to this profile": "Conectar a este perfil",
    "Add/edit/delete profiles and connect": "Adicionar, editar ou excluir perfis e conectar",
    "Connect or switch profile": "Conectar ou trocar de perfil",
    "Manage Profiles & Connect": "Gerenciar perfis e conectar",
    "Add a torrent from a local file": "Adicionar um torrent de um arquivo local",
    "Add a torrent from a URL or Magnet link": "Adicionar um torrent de uma URL ou link magnet",
    "Create a .torrent file from a file or folder": "Criar um arquivo .torrent a partir de um arquivo ou pasta",
    "Exit application": "Sair do aplicativo",
    "Start selected torrents": "Iniciar os torrents selecionados",
    "Pause selected torrents": "Pausar os torrents selecionados",
    "Resume selected torrents": "Retomar os torrents selecionados",
    "Force a recheck/verification (if supported)": "Forçar uma reverificação, se houver suporte",
    "Force an immediate tracker announce (if supported)": "Forçar um anúncio imediato ao tracker, se houver suporte",
    "Copy the info hash for selected torrents": "Copiar o info hash dos torrents selecionados",
    "Copy a magnet link for selected torrents": "Copiar o link magnet dos torrents selecionados",
    "Open the download folder (if available)": "Abrir a pasta de download, se disponível",
    "Remove selected torrents": "Remover os torrents selecionados",
    "Remove selected torrents and data": "Remover os torrents selecionados e seus dados",
    "Select all torrents": "Selecionar todos os torrents",
    "Search torrent indexers and add what you find": "Pesquisar indexadores de torrent e adicionar os resultados encontrados",
    "Associate .torrent and magnet links with this app": "Associar arquivos .torrent e links magnet a este aplicativo",
    "Check for updates": "Verificar atualizações",
    "Edit connected qBittorrent settings": "Editar as configurações do qBittorrent conectado",
    "Edit connected Transmission settings": "Editar as configurações do Transmission conectado",
    "Edit connected rTorrent settings": "Editar as configurações do rTorrent conectado",
    "Configure local session and application settings": "Configurar a sessão local e o aplicativo",
    "About this application": "Sobre este aplicativo",
    # Context menu.
    "Start": "Iniciar",
    "Pause": "Pausar",
    "Resume": "Retomar",
    "Force Recheck": "Forçar reverificação",
    "Force Reannounce": "Forçar novo anúncio",
    "Copy Info Hash": "Copiar info hash",
    "Copy Magnet Link": "Copiar link magnet",
    "Open Download Folder": "Abrir pasta de download",
    "Remove": "Remover",
    "Remove with Data": "Remover com dados",
    # Common status text.
    "Disconnected": "Desconectado",
    "Connecting...": "Conectando...",
    "Connection Failed": "Falha na conexão",
    "Connected to {name}": "Conectado a {name}",
    "Local session active": "Sessão local ativa",
    "Profile": "Perfil",
    "Not connected to any client.": "Nenhum cliente conectado.",
    "No torrents selected.": "Nenhum torrent selecionado.",
    "No torrent selected.": "Nenhum torrent selecionado.",
    "Info hash copied to clipboard.": "Info hash copiado para a área de transferência.",
    "Magnet link(s) copied to clipboard.": "Link(s) magnet copiado(s) para a área de transferência.",
    "Failed to access clipboard.": "Falha ao acessar a área de transferência.",
    "Opened download folder.": "Pasta de download aberta.",
    "Download folder not available.": "Pasta de download indisponível.",
    "Failed to apply settings: {error}": "Falha ao aplicar as configurações: {error}",
    "Another instance of SerrebiTorrent is already running.": "Outra instância do SerrebiTorrent já está em execução.",
    "Error": "Erro",
    # About dialog.
    "A Windows desktop torrent manager designed for keyboard-first use and screen readers.":
        "Um gerenciador de torrents para Windows projetado para uso prioritário pelo teclado e leitores de tela.",
}


def resolved_language(language: str | None) -> str:
    if language in (None, "", "system"):
        return system_language()
    return normalize_language(language)


def tr_main(text: str, language: str | None = None) -> str:
    """Translate main-window text while preserving the shared i18n fallback."""
    translated = translate(text, language)
    if translated != text:
        return translated
    if resolved_language(language) == "pt-BR":
        return _PT_BR_MAIN.get(text, text)
    return text


def sidebar_label(key: str, count: int | None = None, language: str | None = None) -> str:
    label = tr_main(key, language)
    return f"{label} ({count})" if count is not None else label


def formatted_status(source: str, language: str | None = None, **values) -> str:
    return tr_main(source, language).format(**values)
