(() => {
    'use strict';

    const PT_BR = {
        'Skip to torrent list': 'Pular para a lista de torrents',
        'Add Torrent': 'Adicionar torrent',
        'Add': 'Adicionar',
        'Refresh': 'Atualizar',
        'Start': 'Iniciar',
        'Pause': 'Pausar',
        'Resume': 'Retomar',
        'Remove': 'Remover',
        'Settings': 'Configurações',
        'Logout': 'Sair',
        'Navigation': 'Navegação',
        'Navigation Sidebar': 'Barra lateral de navegação',
        'PROFILES': 'PERFIS',
        'Add Profile': 'Adicionar perfil',
        'Profiles': 'Perfis',
        'Status': 'Status',
        'Status Filters': 'Filtros de status',
        'All': 'Todos',
        'Downloading': 'Baixando',
        'Seeding': 'Semeando',
        'Finished': 'Concluídos',
        'Stopped': 'Parados',
        'Failed': 'Com falha',
        'RSS Downloader': 'Baixador RSS',
        'Trackers': 'Trackers',
        'Torrents': 'Torrents',
        'torrents': 'torrents',
        'Select': 'Selecionar',
        'Name': 'Nome',
        'Size': 'Tamanho',
        'Progress': 'Progresso',
        'Speed': 'Velocidade',
        'Torrent Details': 'Detalhes do torrent',
        'General': 'Geral',
        'Files': 'Arquivos',
        'Peers': 'Peers',
        'Select a torrent.': 'Selecione um torrent.',
        'Torrent Actions': 'Ações do torrent',
        'Torrent actions': 'Ações do torrent',
        'Force Recheck': 'Forçar reverificação',
        'Force Reannounce': 'Forçar novo anúncio',
        'Copy Info Hash': 'Copiar info hash',
        'Copy Magnet Link': 'Copiar link magnet',
        'Open Download Folder': 'Abrir pasta de download',
        'Remove with Data': 'Remover com dados',
        'Select All': 'Selecionar tudo',
        'Add Connection Profile': 'Adicionar perfil de conexão',
        'Close': 'Fechar',
        'Type': 'Tipo',
        'URL / Path': 'URL / Caminho',
        'Username': 'Nome de usuário',
        'Password': 'Senha',
        'Create Profile': 'Criar perfil',
        'My Remote Server': 'Meu servidor remoto',
        'Local libtorrent': 'libtorrent local',
        'URLs / Magnets (one per line)': 'URLs / Magnets (um por linha)',
        'Torrent Files': 'Arquivos torrent',
        'Save Path (Optional)': 'Caminho para salvar (opcional)',
        'Preferences': 'Preferências',
        'Application': 'Aplicativo',
        'Remote Client': 'Cliente remoto',
        'Web UI': 'Interface Web',
        'Download Path': 'Caminho de download',
        'RSS Update Interval (s)': 'Intervalo de atualização RSS (s)',
        'Global DL Limit (B/s)': 'Limite global de download (B/s)',
        'Global UL Limit (B/s)': 'Limite global de upload (B/s)',
        'Minimize to Tray': 'Minimizar para a bandeja',
        'Save App Settings': 'Salvar configurações do aplicativo',
        'Loading remote settings...': 'Carregando configurações remotas...',
        'Save Remote Settings': 'Salvar configurações remotas',
        'Theme': 'Tema',
        'Light (Classic)': 'Claro (clássico)',
        'Dark (Night)': 'Escuro (noturno)',
        'UI Refresh Rate (ms)': 'Taxa de atualização da interface (ms)',
        'Language': 'Idioma',
        'System default': 'Padrão do sistema',
        'English': 'Inglês',
        'Portuguese (Brazil)': 'Português (Brasil)',
        'Language changes reload this page after saving.': 'Alterações de idioma recarregam esta página após salvar.',
        'Action menu opened. Use arrow keys to navigate.': 'Menu de ações aberto. Use as setas para navegar.',
        'Selection cleared': 'Seleção limpa',
        'Please select at least one torrent first.': 'Selecione pelo menos um torrent primeiro.',
        'Menu opened': 'Menu aberto',
        'Menu closed': 'Menu fechado',
        'Settings saved.': 'Configurações salvas.',
        'Error saving settings.': 'Erro ao salvar as configurações.',
        'Remote settings saved.': 'Configurações remotas salvas.',
        'Error saving remote settings.': 'Erro ao salvar as configurações remotas.',
        'Failed to load settings.': 'Falha ao carregar as configurações.',
        'Failed to add torrents.': 'Falha ao adicionar torrents.',
        'Invalid torrent URL.': 'URL de torrent inválida.',
        'Switching client profile...': 'Alternando perfil do cliente...',
        'Copied to clipboard': 'Copiado para a área de transferência',
        'Loading...': 'Carregando...',
        'No remote settings available (or Local client active).': 'Nenhuma configuração remota disponível (ou o cliente local está ativo).',
        'Paused': 'Pausado',
        'Path': 'Caminho',
        'Hash': 'Hash',
        'N/A': 'N/D',
        'Login - SerrebiTorrent': 'Entrar - SerrebiTorrent',
        'Login': 'Entrar',
        'Invalid credentials.': 'Credenciais inválidas.',
        'Too many failed attempts. Try again later.': 'Muitas tentativas de login falharam. Tente novamente mais tarde.'
    };

    const REMOTE_WORDS = {
        enabled: 'ativado', enable: 'ativar', disabled: 'desativado',
        download: 'download', downloads: 'downloads', upload: 'upload', uploads: 'uploads',
        rate: 'taxa', limit: 'limite', limits: 'limites', path: 'caminho', directory: 'diretório',
        default: 'padrão', maximum: 'máximo', max: 'máx.', minimum: 'mínimo', min: 'mín.',
        connections: 'conexões', connection: 'conexão', port: 'porta', random: 'aleatória',
        start: 'iniciar', started: 'iniciados', paused: 'pausados', files: 'arquivos', file: 'arquivo',
        incomplete: 'incompleto', rename: 'renomear', trash: 'excluir', original: 'original',
        cache: 'cache', size: 'tamanho', time: 'tempo', days: 'dias', day: 'dia', hour: 'hora',
        address: 'endereço', interface: 'interface', current: 'atual', network: 'rede', peer: 'peer',
        peers: 'peers', torrent: 'torrent', torrents: 'torrents', ratio: 'proporção', seed: 'seed',
        seeding: 'semeadura', queue: 'fila', checking: 'verificação', memory: 'memória', disk: 'disco',
        read: 'leitura', write: 'gravação', username: 'usuário', password: 'senha',
        authentication: 'autenticação', auth: 'autenticação', secure: 'seguro', protection: 'proteção',
        session: 'sessão', timeout: 'tempo limite', alternative: 'alternativa', custom: 'personalizado',
        headers: 'cabeçalhos', header: 'cabeçalho', mail: 'e-mail', notification: 'notificação',
        sender: 'remetente', processing: 'processamento', refresh: 'atualização', interval: 'intervalo',
        articles: 'artigos', rules: 'regras', rule: 'regra', proxy: 'proxy', host: 'host',
        global: 'global', local: 'local', auto: 'automático', automatic: 'automático', anonymous: 'anônimo',
        encryption: 'criptografia', resolve: 'resolver', countries: 'países', country: 'país',
        script: 'script', done: 'concluído', filename: 'nome do arquivo', save: 'salvar'
    };

    const PT_PATTERNS = [
        [/^Selected all (\d+) torrents$/, 'Selecionados todos os $1 torrents'],
        [/^(\d+) torrents selected\.$/, '$1 torrents selecionados.'],
        [/^Failed to add torrent: (.+)$/, 'Falha ao adicionar torrent: $1'],
        [/^Error saving remote settings: (.+)$/, 'Erro ao salvar as configurações remotas: $1'],
        [/^Failed to (.+) torrent\(s\)\.$/, 'Falha ao executar $1 no(s) torrent(s).'],
        [/^Failed to (.+) torrent\(s\): (.+)$/, 'Falha ao executar $1 no(s) torrent(s): $2'],
        [/^Remove failed: (.+)$/, 'Falha ao remover: $1'],
        [/^Remove (\d+) torrent\?$/, 'Remover $1 torrent?'],
        [/^Remove (\d+) torrents\?$/, 'Remover $1 torrents?'],
        [/^Remove (\d+) torrent and delete downloaded data\?$/, 'Remover $1 torrent e excluir os dados baixados?'],
        [/^Remove (\d+) torrents and delete downloaded data\?$/, 'Remover $1 torrents e excluir os dados baixados?'],
        [/^Size: (.+)$/, 'Tamanho: $1'],
        [/^Path: (.+)$/, 'Caminho: $1'],
        [/^Auto-added from RSS: (.+)$/, 'Adicionado automaticamente do RSS: $1'],
        [/^Added from RSS: (.+)$/, 'Adicionado do RSS: $1'],
        [/^Adding torrent: (.+)\.\.\.$/, 'Adicionando torrent: $1...']
    ];

    const ATTRS = ['title', 'aria-label', 'placeholder'];
    let currentLanguage = 'en';
    let configuredLanguage = 'system';
    let pendingLanguage = null;
    let observer = null;
    let externalTranslations = {};
    let availableLanguages = [];

    function rawLanguage(value) {
        return String(value || '').trim().replace('_', '-');
    }

    function normalizeLanguage(value) {
        const raw = rawLanguage(value);
        const lower = raw.toLowerCase();
        if (lower === 'pt' || lower === 'pt-br' || lower.startsWith('pt-br.')) return 'pt-BR';
        if (lower === 'en' || lower.startsWith('en-') || lower.startsWith('en.')) return 'en';
        if (!raw) return 'en';
        const known = availableLanguages.find((item) => item.code.toLowerCase() === lower);
        return known ? known.code : raw;
    }

    function resolveAvailableLanguage(value) {
        const raw = rawLanguage(value);
        const lower = raw.toLowerCase();
        const builtin = normalizeLanguage(raw);
        if (builtin === 'pt-BR' || builtin === 'en') return builtin;
        const exact = availableLanguages.find((item) => item.code.toLowerCase() === lower);
        if (exact) return exact.code;
        const base = lower.split('-', 1)[0];
        const matches = availableLanguages.filter((item) => item.code.toLowerCase().split('-', 1)[0] === base);
        return matches.length === 1 ? matches[0].code : 'en';
    }

    function systemLanguage() {
        return resolveAvailableLanguage(navigator.language || navigator.userLanguage || 'en');
    }

    async function loadLanguageIndex() {
        try {
            const response = await fetch('/locales/index.json', {cache: 'no-store'});
            if (!response.ok) return [];
            const payload = await response.json();
            availableLanguages = Array.isArray(payload.languages) ? payload.languages.filter(
                (item) => item && typeof item.code === 'string' && typeof item.name === 'string'
            ) : [];
        } catch (_error) {
            availableLanguages = [];
        }
        return availableLanguages;
    }

    async function loadExternalCatalog(language) {
        externalTranslations = {};
        if (!language || language === 'en') return;
        try {
            const response = await fetch(`/locales/${encodeURIComponent(language)}.json`, {cache: 'no-store'});
            if (!response.ok) return;
            const payload = await response.json();
            if (payload && payload.translations && typeof payload.translations === 'object') {
                externalTranslations = payload.translations;
            }
        } catch (_error) {
            externalTranslations = {};
        }
    }

    function t(value) {
        if (value == null) return value;
        const text = String(value);
        if (currentLanguage !== 'en' && Object.prototype.hasOwnProperty.call(externalTranslations, text)) {
            return externalTranslations[text];
        }
        if (currentLanguage !== 'pt-BR') return text;
        if (Object.prototype.hasOwnProperty.call(PT_BR, text)) return PT_BR[text];
        for (const [pattern, replacement] of PT_PATTERNS) {
            if (pattern.test(text)) return text.replace(pattern, replacement);
        }
        return text;
    }

    function translateRemoteLabel(value) {
        const exact = t(value);
        if (exact !== value) return exact;
        if (currentLanguage !== 'pt-BR') return value;
        return String(value).split(/\s+/).map((word) => REMOTE_WORDS[word.toLowerCase()] || word).join(' ');
    }

    function isUserContentTextNode(node) {
        const parent = node.parentElement;
        if (!parent) return false;
        return parent.matches('.col-name, #details-general h3');
    }

    function translateTextNode(node) {
        const raw = node.nodeValue;
        if (!raw || !raw.trim() || isUserContentTextNode(node)) return;
        const leading = raw.match(/^\s*/)?.[0] || '';
        const trailing = raw.match(/\s*$/)?.[0] || '';
        const core = raw.trim();
        let translated = t(core);
        const parent = node.parentElement;
        if (translated === core && parent && parent.matches('#remoteSettingsFields label')) {
            translated = translateRemoteLabel(core);
        }
        if (translated !== core) node.nodeValue = leading + translated + trailing;
    }

    function translateElement(element) {
        if (!(element instanceof Element)) return;
        for (const attr of ATTRS) {
            if (!element.hasAttribute(attr)) continue;
            const source = element.getAttribute(attr);
            let translated = source;
            if (attr === 'aria-label' && element.classList.contains('row-check') && source.startsWith('Select ')) {
                if (currentLanguage === 'pt-BR') translated = `Selecionar ${source.slice(7)}`;
                else if (currentLanguage !== 'en' && externalTranslations['Select {name}']) {
                    translated = externalTranslations['Select {name}'].replace('{name}', source.slice(7));
                }
            } else if (!(element.matches('tr[data-hash]') && attr === 'aria-label') && !(element.classList.contains('col-name') && attr === 'title')) {
                translated = t(source);
            }
            if (translated !== source) element.setAttribute(attr, translated);
        }
        for (const child of element.childNodes) {
            if (child.nodeType === Node.TEXT_NODE) translateTextNode(child);
        }
    }

    function translateTree(root = document) {
        if (currentLanguage === 'en') return;
        if (currentLanguage === 'pt-BR') document.documentElement.lang = 'pt-BR';
        else document.documentElement.lang = currentLanguage;
        if (root instanceof Element) translateElement(root);
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            if (node.nodeType === Node.TEXT_NODE) translateTextNode(node);
            else translateElement(node);
        }
    }

    function populateExternalLanguageOptions() {
        const select = document.getElementById('appLanguage');
        if (!select) return;
        const existing = new Set(Array.from(select.options).map((option) => option.value));
        for (const item of availableLanguages) {
            if (!item.code || existing.has(item.code) || item.code === 'en' || item.code === 'pt-BR') continue;
            const option = document.createElement('option');
            option.value = item.code;
            option.textContent = item.name;
            select.appendChild(option);
            existing.add(item.code);
        }
        select.value = configuredLanguage || 'system';
    }

    function ensureLanguageControl() {
        const form = document.getElementById('settingsForm');
        if (!form || document.getElementById('appLanguage')) {
            populateExternalLanguageOptions();
            return;
        }
        const tray = document.getElementById('minToTray');
        const trayGroup = tray ? tray.closest('.form-check') : null;
        const group = document.createElement('div');
        group.className = 'mb-3';
        group.innerHTML = `
            <label class="form-label" for="appLanguage">Language</label>
            <select class="form-select" id="appLanguage" name="language">
                <option value="system">System default</option>
                <option value="en">English</option>
                <option value="pt-BR">Portuguese (Brazil)</option>
            </select>
            <div class="form-text">Language changes reload this page after saving.</div>`;
        if (trayGroup) form.insertBefore(group, trayGroup);
        else form.insertBefore(group, form.querySelector('button[type="submit"]'));
        populateExternalLanguageOptions();
        const select = document.getElementById('appLanguage');
        if (select) select.value = configuredLanguage || 'system';
        if (currentLanguage !== 'en') translateTree(group);
    }

    function installObserver() {
        if (observer) observer.disconnect();
        observer = new MutationObserver((mutations) => {
            if (currentLanguage === 'en') return;
            for (const mutation of mutations) {
                if (mutation.type === 'attributes') {
                    translateElement(mutation.target);
                    continue;
                }
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.TEXT_NODE) translateTextNode(node);
                    else if (node.nodeType === Node.ELEMENT_NODE) translateTree(node);
                }
            }
        });
        observer.observe(document.documentElement, {
            subtree: true,
            childList: true,
            attributes: true,
            attributeFilter: ATTRS
        });
    }

    const originalAlert = window.alert.bind(window);
    const originalConfirm = window.confirm.bind(window);
    window.alert = (message) => {
        originalAlert(t(message));
        if (message === 'Settings saved.' && pendingLanguage && pendingLanguage !== configuredLanguage) {
            const resolved = pendingLanguage === 'system' ? systemLanguage() : resolveAvailableLanguage(pendingLanguage);
            try { localStorage.setItem('serrebitorrent-language', resolved); } catch (_error) {}
            setTimeout(() => window.location.reload(), 700);
        }
    };
    window.confirm = (message) => originalConfirm(t(message));

    function wrapAnnouncements() {
        if (typeof window.announceToSR !== 'function' || window.announceToSR.__i18nWrapped) return;
        const original = window.announceToSR;
        const wrapped = function(message, assertive = false) {
            return original.call(this, t(message), assertive);
        };
        wrapped.__i18nWrapped = true;
        window.announceToSR = wrapped;
    }

    async function loadLanguagePreference() {
        let configured = null;
        try {
            const response = await fetch('/api/v2/app/prefs', {cache: 'no-store'});
            if (response.ok) {
                const prefs = await response.json();
                configured = prefs.language || 'system';
            }
        } catch (_error) {
            configured = null;
        }

        await loadLanguageIndex();
        configuredLanguage = configured || 'system';
        if (configuredLanguage === 'system') {
            currentLanguage = systemLanguage();
        } else {
            currentLanguage = resolveAvailableLanguage(configuredLanguage);
            // If a configured catalog was removed or renamed, keep the control
            // synchronized with the language that is actually being rendered.
            configuredLanguage = currentLanguage;
        }
        await loadExternalCatalog(currentLanguage);

        try { localStorage.setItem('serrebitorrent-language', currentLanguage); } catch (_error) {}
        ensureLanguageControl();
        const select = document.getElementById('appLanguage');
        if (select) select.value = configuredLanguage;
        if (currentLanguage !== 'en') translateTree(document);
        else document.documentElement.lang = 'en';
        wrapAnnouncements();
        installObserver();
        return currentLanguage;
    }

    try {
        const cached = localStorage.getItem('serrebitorrent-language');
        if (cached) currentLanguage = rawLanguage(cached) || 'en';
    } catch (_error) {}

    window.SerrebiI18n = {
        t,
        get language() { return currentLanguage; },
        get availableLanguages() { return availableLanguages.slice(); },
        ready: null,
        apply: translateTree
    };

    window.SerrebiI18n.ready = loadLanguagePreference();

    document.addEventListener('DOMContentLoaded', () => {
        ensureLanguageControl();
        const form = document.getElementById('settingsForm');
        if (form) {
            form.addEventListener('submit', () => {
                const select = document.getElementById('appLanguage');
                pendingLanguage = select ? select.value : null;
            }, true);
        }
        if (currentLanguage !== 'en') translateTree(document);
        setTimeout(wrapAnnouncements, 0);
        installObserver();
    });
})();