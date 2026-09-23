let torrentsMap = new Map();
let domRows = new Map(); 
let selectedHashes = new Set();
let currentFilter = 'All';
let currentProfileId = null;
let lastFocusedHash = null;
let lastUserActivity = 0;
let refreshIntervalId = null;
let refreshInFlight = false;
let forcedRefreshPending = false;

// Virtual Scrolling Config
const ROW_HEIGHT = 40;
const VIEWPORT_BUFFER = 10; 
let visibleTorrents = []; 

// Throttling
let lastProfileFetch = 0;
let detailsTimeout = null;
let csrfToken = null;
let actionMenuReturnFocus = null;
const modalReturnFocus = new WeakMap();

async function redirectIfSessionExpired(response) {
    if (response.status !== 403) return false;
    let body = '';
    try {
        body = (await response.clone().text()).trim();
    } catch (_error) {}
    if (body !== 'Unauthorized') return false;

    csrfToken = null;
    try {
        sessionStorage.setItem('serrebitorrent-session-expired', '1');
    } catch (_error) {}
    window.location.href = '/login.html';
    return true;
}

async function ensureCsrfToken() {
    if (csrfToken) return csrfToken;
    const res = await fetch('/api/v2/auth/csrf');
    if (await redirectIfSessionExpired(res)) {
        throw new Error('Unauthorized');
    }
    const data = await res.json();
    csrfToken = data.csrf_token;
    return csrfToken;
}

async function apiFetch(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const token = await ensureCsrfToken();
        const headers = new Headers(options.headers || {});
        headers.set('X-CSRF-Token', token);
        options.headers = headers;
    }
    const res = await fetch(url, options);
    await redirectIfSessionExpired(res);
    return res;
}

const els = {
    tbody: () => document.getElementById('torrentTableBody'),
    table: () => document.getElementById('torrentTable'),
    container: () => document.getElementById('tableScrollContainer'),
    contextMenu: () => document.getElementById('contextMenu'),
    selectAllCheck: () => document.getElementById('selectAllCheck'),
    aria: () => document.getElementById('aria-announcer'),
    stretcher: () => document.getElementById('tableStretcher'),
    sidebarNav: () => document.getElementById('sidebarNav'),
    actionsBtn: () => document.getElementById('torrentActionsBtn'),
    refreshRateInput: () => document.getElementById('webRefreshRate')
};

// Initialization
window.addEventListener('DOMContentLoaded', () => {
    const container = els.container();
    if (container) {
        container.addEventListener('scroll', () => {
            window.requestAnimationFrame(renderVirtualRows);
        });
    }

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.setAttribute('inert', '');
        modal.addEventListener('show.bs.modal', (e) => {
            const origin = e.relatedTarget || document.activeElement;
            if (origin instanceof HTMLElement && !modal.contains(origin)) {
                modalReturnFocus.set(modal, origin);
            }
            modal.removeAttribute('inert');
        });
        modal.addEventListener('shown.bs.modal', () => {
            const selector = modal.dataset.initialFocus;
            const target = selector ? modal.querySelector(selector) : null;
            if (target instanceof HTMLElement) {
                target.focus();
            }
        });
        modal.addEventListener('hidden.bs.modal', () => {
            modal.setAttribute('inert', '');
            const origin = modalReturnFocus.get(modal);
            modalReturnFocus.delete(modal);
            if (origin && origin.isConnected) {
                setTimeout(() => origin.focus(), 0);
            }
        });
    });

    const filesTab = document.getElementById('files-tab');
    if (filesTab) {
        filesTab.addEventListener('shown.bs.tab', () => {
            void updateFilesDetails();
        });
    }

    const peersTab = document.getElementById('peers-tab');
    if (peersTab) {
        peersTab.addEventListener('shown.bs.tab', () => {
            void updatePeersDetails();
        });
    }

    const trackersTab = document.getElementById('trackers-tab');
    if (trackersTab) {
        trackersTab.addEventListener('shown.bs.tab', () => {
            void updateTrackersDetails();
        });
    }

    // Initial fetch
    refreshData(true);
    if (window.fetchProfiles) window.fetchProfiles(); 
    startRefreshLoop();

    // Refresh rate listener
    const rr = els.refreshRateInput();
    if (rr) {
        rr.addEventListener('change', () => {
            startRefreshLoop();
        });
    }

    // Aggressive global context menu suppression and handling for the torrent list area
    document.addEventListener('contextmenu', (e) => {
        const tableContainer = els.container();
        // Check if click is anywhere inside the torrent list container
        const torrentListSection = e.target.closest('.torrent-list-container');
        
        if (torrentListSection) {
            e.preventDefault();
            e.stopPropagation();
            
            const row = e.target.closest('tr[data-hash]');
            showContextMenu(e, row);
            return false;
        }
    }, true);

    const actionsBtn = els.actionsBtn();
    if (actionsBtn) {
        actionsBtn.addEventListener('shown.bs.dropdown', () => {
            // Force focus into the menu to trap NVDA focus
            const menu = document.getElementById('contextMenu');
            if (menu) {
                const firstItem = menu.querySelector('.dropdown-item');
                if (firstItem) {
                    // Short delay ensures Bootstrap animations/positioning don't interfere
                    setTimeout(() => {
                        firstItem.focus();
                        announceToSR("Action menu opened. Use arrow keys to navigate.", true);
                    }, 100);
                }
            }
        });
    }
 
    document.addEventListener('mousedown', (e) => {
        lastUserActivity = Date.now();
    });

    const selectAllCheck = els.selectAllCheck();
    if (selectAllCheck) {
        selectAllCheck.onchange = (e) => {
            if (e.target.checked) {
                visibleTorrents.forEach(t => selectedHashes.add(t.hash));
                announceToSR(`Selected all ${visibleTorrents.length} torrents`);
            } else {
                selectedHashes.clear();
                announceToSR("Selection cleared");
            }
            updateSelectionVisuals();
            updateDetailsDebounced();
        };
    }

    if (actionsBtn) {
        actionsBtn.addEventListener('show.bs.dropdown', (e) => {
            if (selectedHashes.size === 0) {
                e.preventDefault();
                announceToSR("Please select at least one torrent first.", true);
            } else {
                if (!actionMenuReturnFocus) {
                    actionMenuReturnFocus = document.activeElement || actionsBtn;
                }
                lastUserActivity = Date.now();
                announceToSR("Menu opened", true);
            }
        });
        actionsBtn.addEventListener('hidden.bs.dropdown', () => {
            announceToSR("Menu closed");
            const origin = actionMenuReturnFocus;
            actionMenuReturnFocus = null;
            if (origin && origin.isConnected) {
                setTimeout(() => origin.focus(), 10);
            } else if (lastFocusedHash) {
                setTimeout(() => focusRow(lastFocusedHash, true), 10);
            } else {
                setTimeout(() => actionsBtn.focus(), 10);
            }
        });
    }

    // Add Torrent Form Handler
    const addTorrentForm = document.getElementById('addTorrentForm');
    if (addTorrentForm) {
        addTorrentForm.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData();
            formData.append('urls', document.getElementById('torrentUrls').value);
            formData.append('savepath', document.getElementById('torrentSavePath').value);
            const files = document.getElementById('torrentFiles').files;
            for (let i = 0; i < files.length; i++) {
                formData.append('torrents', files[i]);
            }
            const res = await apiFetch('/api/v2/torrents/add', { method: 'POST', body: formData });
            if (res.ok) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('addTorrentModal'));
                if (modal) modal.hide();
                e.target.reset();
                refreshData(true); 
            } else {
                alert("Failed to add torrent: " + await res.text());
            }
        };
    }

    document.addEventListener('click', (e) => {
        const link = e.target.closest('.sidebar-link');
        if (!link) return;
        e.preventDefault();
        activateSidebarLink(link, e);
    });

    document.addEventListener('keydown', (e) => {
        // Handle Context Menu via Keyboard (Applications Key or Shift+F10)
        if (e.key === 'ContextMenu' || (e.shiftKey && e.key === 'F10')) {  
            const inTorrentList = document.activeElement.closest('.torrent-list-container');
            
            if (inTorrentList) {
                e.preventDefault();
                e.stopPropagation();
                const activeRow = document.activeElement.closest('tr[data-hash]');
                const targetRow = activeRow || (lastFocusedHash ? domRows.get(lastFocusedHash) : null);
                showContextMenu(e, targetRow);
                return false;
            }
        }

        if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') return;

        const sidebarNav = els.sidebarNav();
        if (sidebarNav && sidebarNav.contains(document.activeElement)) {
            handleSidebarNavigation(e);
            return;
        }

        const focusedRow = document.activeElement.closest('tr[data-hash]');
        // The grid itself holds focus when the list emptied; arrows must still enter the rows.
        if (!focusedRow && document.activeElement !== els.table()) return;

        lastUserActivity = Date.now();
        if (visibleTorrents.length === 0) return;

        // Arrow Key Navigation Logic
        const navKeys = ['ArrowDown', 'ArrowUp', 'Home', 'End', 'PageUp', 'PageDown'];
        if (navKeys.includes(e.key)) {
            e.preventDefault();
            
            const currentIndex = focusedRow
                ? visibleTorrents.findIndex(t => t.hash === focusedRow.dataset.hash)
                : -1;

            let nextIndex = currentIndex;
            if (e.key === 'ArrowDown') nextIndex++;
            else if (e.key === 'ArrowUp') nextIndex--;
            else if (e.key === 'Home') nextIndex = 0;
            else if (e.key === 'End') nextIndex = visibleTorrents.length - 1;
            else if (e.key === 'PageDown') nextIndex += 10;
            else if (e.key === 'PageUp') nextIndex -= 10;

            if (nextIndex < 0) nextIndex = 0;
            if (nextIndex >= visibleTorrents.length) nextIndex = visibleTorrents.length - 1;

            if (visibleTorrents.length > 0) {
                if (e.shiftKey && currentIndex !== -1) {
                    // Range selection
                    const start = Math.min(currentIndex, nextIndex);
                    const end = Math.max(currentIndex, nextIndex);
                    for (let i = start; i <= end; i++) {
                        selectedHashes.add(visibleTorrents[i].hash);
                    }
                    lastFocusedHash = visibleTorrents[nextIndex].hash;
                    updateSelectionVisuals();
                    focusRow(lastFocusedHash);
                    updateDetailsDebounced();
                } else if (e.ctrlKey) {
                    // Just move focus
                    focusRow(visibleTorrents[nextIndex].hash);
                } else {
                    // Normal navigation
                    navigateToIndex(nextIndex);
                }
            }
            return;
        }

        // Space toggles selection for the focused torrent row without moving focus.
        if (e.key === ' ' && focusedRow) {
            e.preventDefault();
            const hash = focusedRow.dataset.hash;
            const torrent = torrentsMap.get(hash);
            const selecting = !selectedHashes.has(hash);
            toggleSelection(hash);
            focusRow(hash, true);
            announceToSR(`${selecting ? 'Selected' : 'Deselected'} ${torrent?.name || 'torrent'}`);
            return;
        }

        // Ctrl+A Select All
        if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
            e.preventDefault();
            visibleTorrents.forEach(t => selectedHashes.add(t.hash));
            updateSelectionVisuals();
            announceToSR(`Selected all ${visibleTorrents.length} torrents`);
            return;
        }
    });

    // --- Settings & Remote Prefs Logic ---
    const settingsModal = document.getElementById('settingsModal');
    if (settingsModal) {
        settingsModal.addEventListener('show.bs.modal', loadAppSettings);
    }
    
    const remoteTab = document.getElementById('remote-settings-tab');
    if (remoteTab) {
        remoteTab.addEventListener('shown.bs.tab', loadRemoteSettings);
    }
    
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.onsubmit = async (e) => {
            e.preventDefault();
            const fd = new FormData(settingsForm);
            const data = {};
            for (const [key, value] of fd.entries()) {
                data[key] = value;
            }
            const minTray = document.getElementById('minToTray');
            if (minTray) data['min_to_tray'] = !!minTray.checked;
            
            try {
                const res = await apiFetch('/api/v2/app/prefs', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    alert('Settings saved.');
                    const modal = bootstrap.Modal.getInstance(settingsModal);
                    if(modal) modal.hide();
                } else {
                    alert('Error saving settings.');
                }
            } catch (err) { console.error(err); alert('Error saving settings.'); }
        };
    }
    
    const remoteForm = document.getElementById('remoteSettingsForm');
    if (remoteForm) {
        remoteForm.onsubmit = async (e) => {
            e.preventDefault();
            const data = {};
            const inputs = remoteForm.querySelectorAll('input, select');
            inputs.forEach(input => {
                const key = input.name;
                if (!key) return;
                if (input.type === 'checkbox') {
                    data[key] = input.checked; 
                } else if (input.type === 'number') {
                    data[key] = parseFloat(input.value);
                } else {
                    data[key] = input.value;
                }
            });
            
            try {
                const res = await apiFetch('/api/v2/app/remote_prefs', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (res.ok) {
                    alert('Remote settings saved.');
                } else {
                    alert('Error saving remote settings: ' + await res.text());
                }
            } catch (err) { console.error(err); alert('Error saving remote settings.'); }
        };
    }
});

function startRefreshLoop() {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    let rate = 2000;
    const input = els.refreshRateInput();
    if (input && input.value) rate = parseInt(input.value);
    if (rate < 500) rate = 500;
    refreshIntervalId = setInterval(() => refreshData(), rate);
}

// Arrows stay inside one listbox, so each listbox needs its own Tab stop:
// the selected option, else the first one.
function ensureSidebarTabStops() {
    ['profileList', 'filterList', 'trackerList'].forEach(id => {
        const listbox = document.getElementById(id);
        if (!listbox) return;
        const links = Array.from(listbox.querySelectorAll('.sidebar-link'));
        if (links.length === 0 || links.some(l => l.tabIndex === 0)) return;
        const target = links.find(l => l.getAttribute('aria-selected') === 'true') || links[0];
        target.tabIndex = 0;
    });
}

function handleSidebarNavigation(e) {
    const listbox = document.activeElement.closest('[role="listbox"]');
    if (!listbox) return;

    const links = Array.from(listbox.querySelectorAll('.sidebar-link'));
    if (links.length === 0) return;

    let currentIndex = links.indexOf(document.activeElement);
    if (currentIndex === -1) {
        currentIndex = links.findIndex(l => l.classList.contains('active'));
        if (currentIndex === -1) currentIndex = 0;
    }

    let nextIndex = -1;
    if (e.key === 'ArrowDown') nextIndex = (currentIndex + 1) % links.length;
    else if (e.key === 'ArrowUp') nextIndex = (currentIndex - 1 + links.length) % links.length;
    else if (e.key === 'Home') nextIndex = 0;
    else if (e.key === 'End') nextIndex = links.length - 1;
    else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateSidebarLink(links[currentIndex], e);
        return;
    }

    if (nextIndex !== -1) {
        e.preventDefault();
        const target = links[nextIndex];
        // Roving tabindex is scoped to the current listbox.
        links.forEach(l => l.setAttribute('tabindex', '-1'));
        target.setAttribute('tabindex', '0');
        target.focus();
    }
}

async function refreshData(force = false) {
    if (refreshInFlight) {
        if (force) forcedRefreshPending = true;
        return;
    }

    // Keep background refresh from mutating list/selection while a dialog is active.
    if (!force && document.querySelector('.modal.show')) return;
    // If user is actively typing or interacting, skip background refresh unless forced
    if (!force && Date.now() - lastUserActivity < 1000) return;

    refreshInFlight = true;
    try {
        const isFirstLoad = torrentsMap.size === 0;
        const activeRow = document.activeElement?.closest?.('tr[data-hash]') || null;
        const focusedHashBeforeRefresh = activeRow?.dataset?.hash || null;
        const focusedIndexBeforeRefresh = focusedHashBeforeRefresh
            ? visibleTorrents.findIndex(t => t.hash === focusedHashBeforeRefresh)
            : -1;
        // Get the full list from the client directly, info only provides MainFrame's filtered list
        const res = await fetch('/api/v2/torrents/all');
        if (await redirectIfSessionExpired(res)) return;
        const torrentsList = await res.json();
        
        // Also get stats from info
        const infoRes = await fetch('/api/v2/torrents/info');
        if (await redirectIfSessionExpired(infoRes)) return;
        const infoData = await infoRes.json();
        
        const listChanges = syncTorrentsMap(Array.isArray(torrentsList) ? torrentsList : []);
        updateFilteredList();
        renderVirtualRows();
        updateSidebarStats(infoData.stats, infoData.trackers);
        
        const now = Date.now();
        if (now - lastProfileFetch > 30000) { 
            if (window.fetchProfiles) window.fetchProfiles(); 
            lastProfileFetch = now; 
        }

        if (isFirstLoad && visibleTorrents.length > 0) {
            // Focus the first torrent on very first load
            setTimeout(() => focusRow(visibleTorrents[0].hash, true), 100);
        } else if (focusedHashBeforeRefresh && !torrentsMap.has(focusedHashBeforeRefresh)) {
            if (visibleTorrents.length > 0) {
                const fallbackIndex = Math.min(
                    Math.max(focusedIndexBeforeRefresh, 0),
                    visibleTorrents.length - 1,
                );
                const fallback = visibleTorrents[fallbackIndex];
                focusRow(fallback.hash, true);
                announceToSR(`Focused torrent is no longer available. Focus moved to ${fallback.name}.`, true);
            } else {
                lastFocusedHash = null;
                const table = els.table();
                if (table) {
                    table.tabIndex = 0;
                    table.focus();
                }
                announceToSR("Focused torrent is no longer available. The torrent list is empty.", true);
            }
        } else if (lastFocusedHash && torrentsMap.has(lastFocusedHash)) {
            focusRow(lastFocusedHash, false);
        } else if (lastFocusedHash) {
            lastFocusedHash = null;
        }

        if (!isFirstLoad) {
            const focusedRemovalWasAnnounced =
                focusedHashBeforeRefresh && listChanges.removed.some(t => t.hash === focusedHashBeforeRefresh);
            const addedCount = listChanges.added.length;
            const removedCount = focusedRemovalWasAnnounced
                ? listChanges.removed.length - 1
                : listChanges.removed.length;
            // Separate calls so each sentence is translated on its own.
            if (addedCount > 0) announceToSR(`${addedCount} torrent${addedCount === 1 ? '' : 's'} added.`);
            if (removedCount > 0) announceToSR(`${removedCount} torrent${removedCount === 1 ? '' : 's'} removed.`);
        }
    } catch (e) {
        console.error("Refresh error", e);
    } finally {
        refreshInFlight = false;
        if (forcedRefreshPending) {
            forcedRefreshPending = false;
            void refreshData(true);
        }
    }
}

function syncTorrentsMap(newData) {
    const newHashes = new Set(newData.map(t => t.hash));
    const added = newData.filter(t => !torrentsMap.has(t.hash));
    const removed = [];

    for (const h of torrentsMap.keys()) {
        if (!newHashes.has(h)) {
            const previous = torrentsMap.get(h);
            if (previous) removed.push(previous);
            torrentsMap.delete(h);
            const tr = domRows.get(h);
            if (tr) { tr.remove(); domRows.delete(h); }
            selectedHashes.delete(h);
        }
    }
    newData.forEach(t => torrentsMap.set(t.hash, t));
    return { added, removed };
}

function updateFilteredList() {
    visibleTorrents = Array.from(torrentsMap.values()).filter(t => {
        if (currentFilter === 'All') return true;
        if (currentFilter === 'RSS') return false;
        const pct = t.size > 0 ? (t.done / t.size * 100) : 0;
        if (currentFilter === 'Downloading') return t.state === 1 && (pct < 100);
        if (currentFilter === 'Seeding') return t.state === 1 && (pct >= 100);
        if (currentFilter === 'Finished') return pct >= 100;
        if (currentFilter === 'Stopped') return t.state === 0;
        if (currentFilter === 'Failed') {
            const msg = (t.message || '').toLowerCase();
            return msg && !msg.includes('success') && !msg.includes('ok');
        }
        if (t.tracker_domain === currentFilter) return true;
        return false;
    });
    visibleTorrents.sort((a, b) => a.name.localeCompare(b.name));
    
    const table = els.table();
    if (table) table.setAttribute('aria-rowcount', visibleTorrents.length);
    const stretcher = els.stretcher();
    if (stretcher) stretcher.style.height = (visibleTorrents.length * ROW_HEIGHT) + 'px';
}

function renderVirtualRows() {
    const container = els.container();
    const tbody = els.tbody();
    if (!container || !tbody) return;
    const startIndex = Math.max(0, Math.floor(container.scrollTop / ROW_HEIGHT) - VIEWPORT_BUFFER);
    const endIndex = Math.min(visibleTorrents.length - 1, Math.ceil((container.scrollTop + container.clientHeight) / ROW_HEIGHT) + VIEWPORT_BUFFER);
    const visibleSubList = visibleTorrents.slice(startIndex, endIndex + 1);
    const visibleHashes = new Set(visibleSubList.map(t => t.hash));

    tbody.style.transform = `translateY(${startIndex * ROW_HEIGHT}px)`;

    for (const [hash, tr] of domRows.entries()) {
        if (!visibleHashes.has(hash) && hash !== lastFocusedHash) {
            tr.remove(); domRows.delete(hash);
        }
    }
    visibleSubList.forEach((t, i) => {
        const absoluteIndex = startIndex + i;
        let tr = domRows.get(t.hash);
        if (!tr) { tr = createRowElement(t); domRows.set(t.hash, tr); }
        updateRowData(tr, t, absoluteIndex);
        if (tbody.children[i] !== tr) tbody.insertBefore(tr, tbody.children[i] || null);
    });
    updateSelectionVisuals();
}

function createRowElement(t) {
    const tr = document.createElement('tr');
    tr.dataset.hash = t.hash;
    tr.style.height = ROW_HEIGHT + 'px';
    tr.setAttribute('role', 'row');
    tr.setAttribute('aria-label', t.name);
    tr.tabIndex = -1;
    
    tr.innerHTML = `
        <td role="gridcell"><input type="checkbox" class="row-check" tabindex="-1"></td>
        <td role="gridcell" class="col-name"></td>
        <td role="gridcell" class="col-size text-nowrap"></td>
        <td role="gridcell" class="col-status text-nowrap"></td>
        <td role="gridcell"><div class="progress" aria-hidden="true"><div class="progress-bar"></div></div></td>
        <td role="gridcell" class="col-speed text-nowrap"></td>
    `;
    
    const check = tr.querySelector('.row-check');
    check.onclick = (e) => { e.stopPropagation(); toggleSelection(t.hash); };

    tr.onclick = (e) => { 
        if (e.ctrlKey || e.metaKey) toggleSelection(t.hash); 
        else selectByHash(t.hash); 
    };
    tr.addEventListener('focus', () => { lastFocusedHash = t.hash; });
    return tr;
}

function updateRowData(tr, t, absIndex) {
    const progress = t.size > 0 ? (t.done / t.size * 100).toFixed(1) : 0;
    const isSelected = selectedHashes.has(t.hash);
    const statusText = t.state === 1 ? (progress >= 100 ? 'Seeding' : 'Downloading') : 'Paused';
    const speedText = progress >= 100
        ? `UL: ${fmtSize(t.up_rate)}/s`
        : `DL: ${fmtSize(t.down_rate)}/s | UL: ${fmtSize(t.up_rate)}/s`;
    
    tr.setAttribute('aria-rowindex', absIndex + 1);
    tr.setAttribute('aria-selected', isSelected);
    
    const check = tr.querySelector('.row-check');
    check.checked = isSelected;
    check.setAttribute('aria-label', `Select ${t.name}`);
    
    const nameCell = tr.querySelector('.col-name');
    if (nameCell.textContent !== t.name) { nameCell.textContent = t.name; nameCell.title = t.name; }
    
    const sizeCell = tr.querySelector('.col-size');
    const sz = fmtSize(t.size);
    if (sizeCell.textContent !== sz) sizeCell.textContent = sz;
    
    const statusCell = tr.querySelector('.col-status');
    if (statusCell.textContent !== statusText) statusCell.textContent = statusText;
    
    const bar = tr.querySelector('.progress-bar');
    bar.style.width = progress + '%';
    bar.textContent = progress + '%';
    
    const speedCell = tr.querySelector('.col-speed');
    if (speedCell.textContent !== speedText) speedCell.textContent = speedText;

    tr.classList.toggle('selected', isSelected);
}

function navigateToIndex(index) {
    if (index < 0 || index >= visibleTorrents.length) return;
    const t = visibleTorrents[index];
    selectedHashes.clear();
    selectedHashes.add(t.hash);
    lastFocusedHash = t.hash;
    scrollToRow(t.hash, index);
    renderVirtualRows();
    focusRow(t.hash);
    updateDetailsDebounced();
}

function selectByHash(hash) {
    selectedHashes.clear();
    selectedHashes.add(hash);
    lastFocusedHash = hash;
    updateSelectionVisuals();
    focusRow(hash);
    updateDetailsDebounced();
}

function toggleSelection(hash) {
    if (selectedHashes.has(hash)) selectedHashes.delete(hash);
    else selectedHashes.add(hash);
    lastFocusedHash = hash;
    updateSelectionVisuals();
    updateDetailsDebounced();
}

function focusRow(hash, shouldPerformFocus = true) {
    lastFocusedHash = hash;
    const row = domRows.get(hash) || document.querySelector(`tr[data-hash="${hash}"]`);
    if (row) {
        document.querySelectorAll('#torrentTableBody tr').forEach(tr => tr.tabIndex = -1);
        row.tabIndex = 0;
        if (shouldPerformFocus && document.activeElement !== row) row.focus();
    }
}

function scrollToRow(hash, index) {
    const container = els.container();
    const targetTop = index * ROW_HEIGHT;
    if (targetTop < container.scrollTop) container.scrollTop = targetTop;
    else if (targetTop + ROW_HEIGHT > container.scrollTop + container.clientHeight) {
        container.scrollTop = targetTop - container.clientHeight + ROW_HEIGHT;
    }
}

function updateSelectionVisuals() {
    domRows.forEach((tr, hash) => {
        const isSelected = selectedHashes.has(hash);
        tr.setAttribute('aria-selected', isSelected);
        tr.classList.toggle('selected', isSelected);
        const check = tr.querySelector('.row-check');
        if (check) check.checked = isSelected;
    });
    const allSelected = visibleTorrents.length > 0 && visibleTorrents.every(t => selectedHashes.has(t.hash));
    const selectAllCheck = els.selectAllCheck();
    if (selectAllCheck) { 
        selectAllCheck.checked = allSelected; 
        selectAllCheck.indeterminate = !allSelected && selectedHashes.size > 0; 
    }
}

function updateSidebarStats(stats, trackers) {
    if (!stats) return;
    const trackerList = document.getElementById('trackerList');
    // Rebuild only on change: this runs every refresh, and re-focusing a rebuilt
    // item makes screen readers announce it again each time.
    const trackerSignature = trackers ? JSON.stringify([currentFilter, trackers]) : null;
    if (trackerList && trackers && trackerList.dataset.signature !== trackerSignature) {
        trackerList.dataset.signature = trackerSignature;
        const focusedTracker = trackerList.contains(document.activeElement)
            ? document.activeElement.dataset.filter
            : null;
        trackerList.innerHTML = '';
        Object.entries(trackers).sort((a,b)=>b[1]-a[1]).forEach(([domain, count]) => {
            const isActive = currentFilter === domain;
            const a = document.createElement('a');
            a.href = '#';
            a.className = `sidebar-link ${isActive ? 'active' : ''}`;
            a.dataset.filter = domain;
            a.role = 'option';
            a.setAttribute('aria-selected', isActive);
            a.tabIndex = isActive ? 0 : -1;
            a.textContent = `${domain} (${count})`;
            trackerList.appendChild(a);
        });
        if (focusedTracker) {
            const target = Array.from(trackerList.querySelectorAll('.sidebar-link'))
                .find(link => link.dataset.filter === focusedTracker);
            if (target) {
                trackerList.querySelectorAll('.sidebar-link').forEach(link => { link.tabIndex = -1; });
                target.tabIndex = 0;
                target.focus();
            }
        }
        ensureSidebarTabStops();
    }
}

function activateSidebarLink(link, event) {
    if (!link) return;
    const profileId = link.dataset.profileId;
    const filter = link.dataset.filter;
    if (profileId) switchProfile(profileId, event);
    else if (filter) setFilter(filter, event);
}

function setFilter(f, event) {
    if (event) event.preventDefault();
    currentFilter = f;
    selectedHashes.clear();
    lastFocusedHash = null;
    
    document.querySelectorAll('.sidebar-link').forEach(l => {
        const isActive = l.dataset.filter === f;
        l.classList.toggle('active', isActive);
        l.setAttribute('aria-selected', isActive);
        l.tabIndex = isActive ? 0 : -1;
    });
    ensureSidebarTabStops();

    updateFilteredList();
    const container = els.container();
    if (container) container.scrollTop = 0;
    renderVirtualRows();
    if (visibleTorrents.length > 0) focusRow(visibleTorrents[0].hash, true);
}

window.fetchProfiles = async function() {
    try {
        const res = await fetch('/api/v2/profiles');
        if (await redirectIfSessionExpired(res)) return;
        const data = await res.json();
        const list = document.getElementById('profileList');
        if (!list) return;
        const profileSignature = JSON.stringify(data);
        if (list.dataset.signature === profileSignature) return;
        list.dataset.signature = profileSignature;
        const focusedProfile = list.contains(document.activeElement)
            ? document.activeElement.dataset.profileId
            : null;
        list.innerHTML = '';
        currentProfileId = data.current_id;
        for (const id in data.profiles) {
            const p = data.profiles[id];
            const isActive = id === data.current_id;
            const a = document.createElement('a');
            a.href = '#';
            a.className = `sidebar-link ${isActive ? 'active' : ''}`;
            a.dataset.profileId = id;
            a.role = 'option';
            a.setAttribute('aria-selected', isActive);
            a.tabIndex = isActive ? 0 : -1;
            a.textContent = `${p.name} (${p.type})`;
            list.appendChild(a);
        }
        if (focusedProfile) {
            const target = Array.from(list.querySelectorAll('.sidebar-link'))
                .find(link => link.dataset.profileId === focusedProfile);
            if (target) {
                list.querySelectorAll('.sidebar-link').forEach(link => { link.tabIndex = -1; });
                target.tabIndex = 0;
                target.focus();
            }
        }
        ensureSidebarTabStops();
    } catch (e) {
        console.error("fetchProfiles failed:", e);
    }
}

async function switchProfile(id, event) {
    if (event) event.preventDefault();
    if (id === currentProfileId) return;
    announceToSR("Switching client profile...");
    const fd = new FormData(); fd.append('id', id);
    const res = await apiFetch('/api/v2/profiles/switch', { method: 'POST', body: fd });
    if (res.ok) { 
        selectedHashes.clear(); 
        lastFocusedHash = null; 
        lastUserActivity = 0; 
        currentProfileId = id; 
        torrentsMap.clear(); 
        domRows.forEach(tr => tr.remove());
        domRows.clear();
        visibleTorrents = [];
        
        // Update Sidebar visual state immediately
        document.querySelectorAll('.sidebar-link[data-profile-id]').forEach(l => {
            const isActive = l.dataset.profileId === id;
            l.classList.toggle('active', isActive);
            l.setAttribute('aria-selected', isActive);
            l.tabIndex = isActive ? 0 : -1;
        });

        lastProfileFetch = 0; // Force re-fetch next cycle
        if (window.fetchProfiles) window.fetchProfiles(); // Or just call it now
        
        setTimeout(() => refreshData(true), 500); 
    }
}

function updateDetailsDebounced() { if (detailsTimeout) clearTimeout(detailsTimeout); detailsTimeout = setTimeout(updateDetails, 200); }

function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function updateFilesDetails() {
    const pane = document.getElementById('details-files');
    if (!pane) return;

    const translate = window.SerrebiI18n?.t || ((value) => value);
    pane.replaceChildren();

    if (selectedHashes.size === 0) {
        const message = document.createElement('p');
        message.textContent = translate('Select a torrent.');
        pane.appendChild(message);
        return;
    }
    if (selectedHashes.size > 1) {
        const message = document.createElement('p');
        message.textContent = translate('Select one torrent to view files.');
        pane.appendChild(message);
        return;
    }

    const hash = Array.from(selectedHashes)[0];
    const selectionIsCurrent = () =>
        selectedHashes.size === 1 && selectedHashes.has(hash);

    const loading = document.createElement('p');
    loading.className = 'text-muted';
    loading.setAttribute('role', 'status');
    loading.textContent = translate('Loading files...');
    pane.appendChild(loading);

    try {
        const res = await fetch(`/api/v2/torrents/files?hash=${encodeURIComponent(hash)}`);
        if (!selectionIsCurrent()) return;
        if (await redirectIfSessionExpired(res)) return;
        if (!selectionIsCurrent()) return;
        if (!res.ok) {
            throw new Error(await res.text() || 'Failed to load files.');
        }
        const files = await res.json();
        if (!selectionIsCurrent()) return;

        pane.replaceChildren();
        if (!Array.isArray(files) || files.length === 0) {
            const message = document.createElement('p');
            message.textContent = translate('No files available.');
            pane.appendChild(message);
            return;
        }

        const table = document.createElement('table');
        table.className = 'table table-sm';
        table.setAttribute('aria-label', translate('Torrent Files'));

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        for (const label of ['Name', 'Size', 'Progress', 'Priority']) {
            const th = document.createElement('th');
            th.scope = 'col';
            th.textContent = translate(label);
            headerRow.appendChild(th);
        }
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        for (const file of files) {
            const row = document.createElement('tr');
            const priorityLabels = [
                translate('Do not download'),
                translate('Normal'),
                translate('High'),
            ];
            const values = [
                file?.name || '',
                fmtSize(Number(file?.size) || 0),
                `${Math.round(Math.max(0, Math.min(1, Number(file?.progress) || 0)) * 100)}%`,
                priorityLabels[Number(file?.priority)] || translate('Normal'),
            ];
            for (const value of values) {
                const td = document.createElement('td');
                td.textContent = value;
                row.appendChild(td);
            }
            tbody.appendChild(row);
        }
        table.appendChild(tbody);
        pane.appendChild(table);
    } catch (error) {
        if (!selectionIsCurrent()) return;
        pane.replaceChildren();
        const message = document.createElement('p');
        message.className = 'alert alert-danger';
        message.setAttribute('role', 'alert');
        message.textContent = translate('Failed to load torrent files.');
        pane.appendChild(message);
        console.error('Load torrent files failed:', error);
    }
}


async function updatePeersDetails() {
    const pane = document.getElementById('details-peers');
    if (!pane) return;

    const translate = window.SerrebiI18n?.t || ((value) => value);
    pane.replaceChildren();

    if (selectedHashes.size === 0) {
        const message = document.createElement('p');
        message.textContent = translate('Select a torrent.');
        pane.appendChild(message);
        return;
    }
    if (selectedHashes.size > 1) {
        const message = document.createElement('p');
        message.textContent = translate('Select one torrent to view peers.');
        pane.appendChild(message);
        return;
    }

    const hash = Array.from(selectedHashes)[0];
    const selectionIsCurrent = () =>
        selectedHashes.size === 1 && selectedHashes.has(hash);

    const loading = document.createElement('p');
    loading.className = 'text-muted';
    loading.setAttribute('role', 'status');
    loading.textContent = translate('Loading peers...');
    pane.appendChild(loading);

    try {
        const res = await fetch(`/api/v2/torrents/peers?hash=${encodeURIComponent(hash)}`);
        if (!selectionIsCurrent()) return;
        if (await redirectIfSessionExpired(res)) return;
        if (!selectionIsCurrent()) return;
        if (!res.ok) {
            throw new Error(await res.text() || 'Failed to load peers.');
        }
        const peers = await res.json();
        if (!selectionIsCurrent()) return;

        pane.replaceChildren();
        if (!Array.isArray(peers) || peers.length === 0) {
            const message = document.createElement('p');
            message.textContent = translate('No peers available.');
            pane.appendChild(message);
            return;
        }

        const table = document.createElement('table');
        table.className = 'table table-sm';
        table.setAttribute('aria-label', translate('Torrent Peers'));

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        for (const label of ['Address', 'Client', 'Progress', 'Down Speed', 'Up Speed']) {
            const th = document.createElement('th');
            th.scope = 'col';
            th.textContent = translate(label);
            headerRow.appendChild(th);
        }
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        for (const peer of peers) {
            const row = document.createElement('tr');
            const progress = Math.round(
                Math.max(0, Math.min(1, Number(peer?.progress) || 0)) * 100
            );
            const values = [
                peer?.address || '',
                peer?.client || '',
                `${progress}%`,
                `${fmtSize(Number(peer?.down_rate) || 0)}/s`,
                `${fmtSize(Number(peer?.up_rate) || 0)}/s`,
            ];
            for (const value of values) {
                const td = document.createElement('td');
                td.textContent = value;
                row.appendChild(td);
            }
            tbody.appendChild(row);
        }
        table.appendChild(tbody);
        pane.appendChild(table);
    } catch (error) {
        if (!selectionIsCurrent()) return;
        pane.replaceChildren();
        const message = document.createElement('p');
        message.className = 'alert alert-danger';
        message.setAttribute('role', 'alert');
        message.textContent = translate('Failed to load torrent peers.');
        pane.appendChild(message);
        console.error('Load torrent peers failed:', error);
    }
}


async function updateTrackersDetails() {
    const pane = document.getElementById('details-trackers');
    if (!pane) return;

    const translate = window.SerrebiI18n?.t || ((value) => value);
    pane.replaceChildren();

    if (selectedHashes.size === 0) {
        const message = document.createElement('p');
        message.textContent = translate('Select a torrent.');
        pane.appendChild(message);
        return;
    }
    if (selectedHashes.size > 1) {
        const message = document.createElement('p');
        message.textContent = translate('Select one torrent to view trackers.');
        pane.appendChild(message);
        return;
    }

    const hash = Array.from(selectedHashes)[0];
    const selectionIsCurrent = () =>
        selectedHashes.size === 1 && selectedHashes.has(hash);

    const loading = document.createElement('p');
    loading.className = 'text-muted';
    loading.setAttribute('role', 'status');
    loading.textContent = translate('Loading trackers...');
    pane.appendChild(loading);

    try {
        const res = await fetch(`/api/v2/torrents/trackers?hash=${encodeURIComponent(hash)}`);
        if (!selectionIsCurrent()) return;
        if (await redirectIfSessionExpired(res)) return;
        if (!selectionIsCurrent()) return;
        if (!res.ok) {
            throw new Error(await res.text() || 'Failed to load trackers.');
        }
        const trackers = await res.json();
        if (!selectionIsCurrent()) return;

        pane.replaceChildren();
        if (!Array.isArray(trackers) || trackers.length === 0) {
            const message = document.createElement('p');
            message.textContent = translate('No trackers available.');
            pane.appendChild(message);
            return;
        }

        const table = document.createElement('table');
        table.className = 'table table-sm';
        table.setAttribute('aria-label', translate('Torrent Trackers'));

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        for (const label of ['Tracker URL', 'Status', 'Peers', 'Message']) {
            const th = document.createElement('th');
            th.scope = 'col';
            th.textContent = translate(label);
            headerRow.appendChild(th);
        }
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        for (const tracker of trackers) {
            const row = document.createElement('tr');
            const values = [
                tracker?.url || '',
                tracker?.status || '',
                String(Number(tracker?.peers) || 0),
                tracker?.message || '',
            ];
            for (const value of values) {
                const td = document.createElement('td');
                td.textContent = value;
                row.appendChild(td);
            }
            tbody.appendChild(row);
        }
        table.appendChild(tbody);
        pane.appendChild(table);
    } catch (error) {
        if (!selectionIsCurrent()) return;
        pane.replaceChildren();
        const message = document.createElement('p');
        message.className = 'alert alert-danger';
        message.setAttribute('role', 'alert');
        message.textContent = translate('Failed to load torrent trackers.');
        pane.appendChild(message);
        console.error('Load torrent trackers failed:', error);
    }
}

async function updateDetails() {
    const detailPane = document.getElementById('details-general');
    if (selectedHashes.size === 0) {
        detailPane.innerHTML = '<p>Select a torrent.</p>';
    } else if (selectedHashes.size > 1) {
        detailPane.innerHTML = `<p>${selectedHashes.size} torrents selected.</p>`;
    } else {
        const hash = Array.from(selectedHashes)[0];
        const t = torrentsMap.get(hash);
        if (t) {
            // Escape torrent-supplied fields (name/hash/save_path) to prevent DOM XSS.
            detailPane.innerHTML = `<h3 class="fs-5">${escapeHtml(t.name)}</h3><p>Size: ${fmtSize(t.size)}<br>Hash: ${escapeHtml(t.hash)}<br>Path: ${escapeHtml(t.save_path || 'N/A')}</p>`;
        }
    }

    const filesTab = document.getElementById('files-tab');
    if (filesTab?.classList.contains('active')) {
        await updateFilesDetails();
    }

    const peersTab = document.getElementById('peers-tab');
    if (peersTab?.classList.contains('active')) {
        await updatePeersDetails();
    }

    const trackersTab = document.getElementById('trackers-tab');
    if (trackersTab?.classList.contains('active')) {
        await updateTrackersDetails();
    }
}

async function doAction(action, deleteFiles = false, actionLabel = null) {
    if (selectedHashes.size === 0) return;
    if (action === 'delete' && !confirmDeleteAction(deleteFiles)) return;
    const formData = new FormData();
    formData.append('hashes', Array.from(selectedHashes).join('|'));
    if (deleteFiles) formData.append('deleteFiles', 'true');
    try {
        const res = await apiFetch(`/api/v2/torrents/${action}`, { method: 'POST', body: formData });
        if (res.ok) {
            const sourceLabel = actionLabel || action;
            const translate = window.SerrebiI18n?.t || ((value) => value);
            const message = translate('{action} complete')
                .replace('{action}', translate(sourceLabel));
            announceToSR(message);
            hideContextMenu();
            setTimeout(() => refreshData(true), 100);
            return;
        }
        const message = (await res.text()) || `Failed to ${action} torrent(s).`;
        announceToSR(message, true);
        alert(message);
    } catch (err) {
        const message = `Failed to ${action} torrent(s): ${err?.message || err}`;
        announceToSR(message, true);
        alert(message);
    }
}

function confirmDeleteAction(deleteFiles) {
    const count = selectedHashes.size;
    const label = count === 1 ? 'torrent' : 'torrents';
    const dataText = deleteFiles ? ' and delete downloaded data' : '';
    return window.confirm(`Remove ${count} ${label}${dataText}?`);
}

function fmtSize(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + units[i];
}

async function logout() { await apiFetch('/api/v2/auth/logout', { method: 'POST' }); window.location.href = '/login.html'; }

let pendingAnnouncement = null;

// Messages raised in the same tick are spoken together; otherwise the last one
// would overwrite the others before the live region ever showed them.
function announceToSR(m, assertive = false) {
    const a = els.aria();
    if (!a) return;
    if (pendingAnnouncement) {
        pendingAnnouncement.text += ' ' + m;
        pendingAnnouncement.assertive = pendingAnnouncement.assertive || assertive;
        return;
    }
    pendingAnnouncement = { text: m, assertive };
    a.textContent = '';
    setTimeout(() => {
        a.setAttribute('aria-live', pendingAnnouncement.assertive ? 'assertive' : 'polite');
        a.textContent = pendingAnnouncement.text;
        pendingAnnouncement = null;
    }, 50);
}

function applyTheme(theme) {
    if (theme === 'dark') { document.body.classList.add('dark-mode'); localStorage.setItem('web-theme', 'dark'); } 
    else { document.body.classList.remove('dark-mode'); localStorage.setItem('web-theme', 'light'); }
}

function showContextMenu(e, anchorRow = null) {
    const row = anchorRow || (e?.target && e.target.closest ? e.target.closest('tr[data-hash]') : null);
    if (row && row.dataset && row.dataset.hash && !selectedHashes.has(row.dataset.hash)) {
        selectByHash(row.dataset.hash);
    }

    const btn = els.actionsBtn();
    if (btn) {
        actionMenuReturnFocus = row || document.activeElement || btn;
        btn.focus();
        const dd = bootstrap.Dropdown.getOrCreateInstance(btn);
        dd.show();
    }
}

function hideContextMenu() { 
    const btn = els.actionsBtn();
    // Bootstrap comes from a CDN; without it (offline LAN) a successful action must not throw.
    if (btn && typeof bootstrap !== 'undefined') {
        const dd = bootstrap.Dropdown.getInstance(btn);
        if (dd) dd.hide();
    }
}

function toggleSelectAllBtn() {
    const isAllSelected = visibleTorrents.length > 0 && visibleTorrents.every(t => selectedHashes.has(t.hash));
    if (isAllSelected) {
        selectedHashes.clear();
        announceToSR("Selection cleared");
    } else {
        visibleTorrents.forEach(t => selectedHashes.add(t.hash));
        announceToSR(`Selected all ${visibleTorrents.length} torrents`);
    }
    updateSelectionVisuals();
    updateDetailsDebounced();
}

function copyToClipboard(type) {
    if (selectedHashes.size === 0) return;
    let text = "";
    if (type === 'hash') {
        text = Array.from(selectedHashes).join('\n');
    } else {
        text = Array.from(selectedHashes).map(h => `magnet:?xt=urn:btih:${h}`).join('\n');
    }
    navigator.clipboard.writeText(text).then(() => {
        announceToSR("Copied to clipboard");
    });
    hideContextMenu();
}

async function loadAppSettings() {
    try {
        const res = await fetch('/api/v2/app/prefs');
        if (await redirectIfSessionExpired(res)) return;
        const prefs = await res.json();
        const form = document.getElementById('settingsForm');
        if (!form) return;
        
        // Reset form
        form.reset();
        
        // Populate
        for (const key in prefs) {
            const el = form.elements[key];
            if (el) {
                if (el.type === 'checkbox') el.checked = prefs[key];
                else el.value = prefs[key];
            }
        }
        if (prefs.min_to_tray !== undefined) {
            const cb = document.getElementById('minToTray');
            if(cb) cb.checked = prefs.min_to_tray;
        }
        
    } catch (e) { console.error("Load app settings error", e); }
}

async function loadRemoteSettings() {
    const container = document.getElementById('remoteSettingsFields');
    if (!container) return;
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    
    try {
        const res = await fetch('/api/v2/app/remote_prefs');
        if (await redirectIfSessionExpired(res)) return;
        const data = await res.json();
        
        if (!data.prefs) {
            container.innerHTML = '<div class="alert alert-info">No remote settings available (or Local client active).</div>';
            return;
        }
        
        container.innerHTML = '';
        
        // Sort keys for consistent display
        const keys = Object.keys(data.prefs).sort();
        
        keys.forEach(key => {
            const val = data.prefs[key];
            const type = typeof val;
            
            const col = document.createElement('div');
            col.className = 'col-md-6 mb-3';
            
            const label = document.createElement('label');
            label.className = 'form-label small text-muted text-uppercase';
            label.textContent = key.replace(/_/g, ' ');
            label.htmlFor = 'rem_' + key;
            
            let input;
            if (type === 'boolean' || (val === 0 || val === 1) && (key.includes('enable') || key.includes('check'))) {
                col.className = 'col-md-6 mb-3 form-check ps-5 pt-4';
                input = document.createElement('input');
                input.type = 'checkbox';
                input.className = 'form-check-input';
                input.checked = !!val;
                label.className = 'form-check-label';
                col.appendChild(input);
                col.appendChild(label);
            } else {
                input = document.createElement('input');
                input.className = 'form-control form-control-sm';
                if (type === 'number') input.type = 'number';
                else input.type = 'text';
                input.value = val;
                
                col.appendChild(label);
                col.appendChild(input);
            }
            
            input.id = 'rem_' + key;
            input.name = key;
            
            container.appendChild(col);
        });
        
    } catch (e) {
        console.error("Load remote settings error", e);
        container.innerHTML = '<div class="alert alert-danger">Failed to load settings.</div>';
    }
}
