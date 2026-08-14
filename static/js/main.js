// ==========================================================================
// GESTOR CAISES & RECORDATORIOS PERSONALES - JAVASCRIPT ENGINE
// ==========================================================================

let appState = {
    tareas: [],
    unidades: [],
    categorias: [],
    frecuencias: {},
    config: {},
    filtroEstado: 'activas',
    filtroTipo: 'todas', // 'todas', 'unidad', 'personal'
    filtroUnidad: 'Todas',
    filtroFrecuencia: 'Todas'
};

document.addEventListener('DOMContentLoaded', () => {
    cargarTema();
    initNavigation();
    cargarTodo();
    iniciarAutoSincronizacion();
});

function iniciarAutoSincronizacion() {
    // Sincronización automática silenciosa en segundo plano cada 15 segundos
    setInterval(() => {
        cargarTodoSilencioso();
    }, 15000);

    // Sincronizar automáticamente en cuanto se abre la pantalla del celular
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            cargarTodoSilencioso();
        }
    });

    window.addEventListener('focus', () => {
        cargarTodoSilencioso();
    });
}

async function cargarTodoSilencioso() {
    try {
        await Promise.all([
            cargarUnidades(),
            cargarCategorias(),
            cargarFrecuencias(),
            cargarTareasSilencioso()
        ]);
    } catch (e) {}
}

async function cargarTareasSilencioso() {
    try {
        appState.filtroUnidad = document.getElementById('select-filtro-unidad').value;
        appState.filtroFrecuencia = document.getElementById('select-filtro-frecuencia').value;

        const queryParams = new URLSearchParams({
            estado: appState.filtroEstado,
            tipo: appState.filtroTipo === 'todas' ? '' : appState.filtroTipo,
            unidad: appState.filtroUnidad,
            frecuencia: appState.filtroFrecuencia,
            busqueda: document.getElementById('input-search').value
        });

        const res = await fetch(`/api/tareas?${queryParams.toString()}`);
        const json = await res.json();
        if (json.status === 'success') {
            appState.tareas = json.data;
            renderTasksGrid(json.data);
            renderDashboardMetrics();
        }
    } catch (e) {}
}

function cargarTema() {
    const temaGuardado = localStorage.getItem('app_theme') || 'dark';
    if (temaGuardado === 'light') {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        actualizarBotonTema(true);
    } else {
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        actualizarBotonTema(false);
    }
}

function toggleTema() {
    const esClaro = document.body.classList.contains('light-theme');
    if (esClaro) {
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        localStorage.setItem('app_theme', 'dark');
        actualizarBotonTema(false);
    } else {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        localStorage.setItem('app_theme', 'light');
        actualizarBotonTema(true);
    }
}

function actualizarBotonTema(esClaro) {
    const icon = document.getElementById('icon-theme');
    const text = document.getElementById('text-theme');
    if (icon && text) {
        if (esClaro) {
            icon.className = 'fa-solid fa-moon';
            text.innerText = 'Oscuro';
        } else {
            icon.className = 'fa-solid fa-sun';
            text.innerText = 'Claro';
        }
    }
}

// --- NAVIGATION ---
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            const targetId = item.getAttribute('data-target');
            document.querySelectorAll('.app-section').forEach(sec => sec.classList.remove('active'));
            const targetSec = document.getElementById(targetId);
            if (targetSec) targetSec.classList.add('active');

            // Auto-cerrar sidebar en móviles tras hacer clic
            cerrarMobileSidebar();

            if (targetId === 'sec-dashboard') {
                renderDashboardMetrics();
            } else if (targetId === 'sec-historial') {
                cargarHistorial();
            }
        });
    });
}

function toggleMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.querySelector('.sidebar-backdrop');
    if (sidebar) sidebar.classList.toggle('mobile-open');
    if (backdrop) backdrop.classList.toggle('active');
}

function cerrarMobileSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const backdrop = document.querySelector('.sidebar-backdrop');
    if (sidebar) sidebar.classList.remove('mobile-open');
    if (backdrop) backdrop.classList.remove('active');
}

function clickBottomNav(targetId, btn) {
    document.querySelectorAll('.bottom-item').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    // Sincronizar con sidebar
    document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.remove('active');
        if (n.getAttribute('data-target') === targetId) {
            n.classList.add('active');
        }
    });

    document.querySelectorAll('.app-section').forEach(sec => sec.classList.remove('active'));
    const targetSec = document.getElementById(targetId);
    if (targetSec) targetSec.classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (targetId === 'sec-dashboard') {
        renderDashboardMetrics();
    } else if (targetId === 'sec-historial') {
        cargarHistorial();
    }
}

// --- DATA FETCHING ---
async function cargarTodo() {
    await Promise.all([
        cargarUnidades(),
        cargarCategorias(),
        cargarFrecuencias(),
        cargarConfiguracion(),
        cargarTareas()
    ]);
}

async function cargarUnidades() {
    try {
        const res = await fetch('/api/unidades');
        const json = await res.json();
        if (json.status === 'success') {
            appState.unidades = json.data;
            renderUnidadesUI();
        }
    } catch (e) { console.error("Error cargando unidades:", e); }
}

async function cargarCategorias() {
    try {
        const res = await fetch('/api/categorias');
        const json = await res.json();
        if (json.status === 'success') {
            appState.categorias = json.data;
            renderCategoriasUI();
        }
    } catch (e) { console.error("Error cargando categorías:", e); }
}

async function cargarFrecuencias() {
    try {
        const res = await fetch('/api/frecuencias');
        const json = await res.json();
        if (json.status === 'success') {
            appState.frecuencias = json.data;
            renderFrecuenciasUI();
        }
    } catch (e) { console.error("Error cargando frecuencias:", e); }
}

async function cargarConfiguracion() {
    try {
        const res = await fetch('/api/configuracion');
        const json = await res.json();
        if (json.status === 'success') {
            appState.config = json.data;
            document.getElementById('cfg-token').value = json.data.telegram_token || '';
            document.getElementById('cfg-chat-id').value = json.data.telegram_chat_id || '';
            document.getElementById('cfg-hora').value = json.data.hora_notificacion_diaria || '08:00';
            document.getElementById('cfg-dias').value = json.data.dias_aviso_defecto || 5;
        }
    } catch (e) { console.error("Error cargando configuración:", e); }
}

async function cargarTareas() {
    const container = document.getElementById('tasks-container');
    container.innerHTML = `
        <div class="loading-state" style="text-align: center; padding: 40px; width: 100%;">
            <span style="font-size: 32px; display: block; margin-bottom: 8px;">🔄</span>
            <p>Cargando pendientes...</p>
        </div>
    `;

    try {
        appState.filtroUnidad = document.getElementById('select-filtro-unidad').value;
        appState.filtroFrecuencia = document.getElementById('select-filtro-frecuencia').value;

        const queryParams = new URLSearchParams({
            estado: appState.filtroEstado,
            tipo: appState.filtroTipo === 'todas' ? '' : appState.filtroTipo,
            unidad: appState.filtroUnidad,
            frecuencia: appState.filtroFrecuencia,
            busqueda: document.getElementById('input-search').value
        });

        const res = await fetch(`/api/tareas?${queryParams.toString()}`);
        const json = await res.json();
        if (json.status === 'success') {
            appState.tareas = json.data;
            renderTasksGrid(json.data);
            renderDashboardMetrics();
        }
    } catch (e) {
        console.error("Error cargando tareas:", e);
        container.innerHTML = `<p class="error-msg">Error conectando con el servidor.</p>`;
    }
}

// --- UI RENDERING ---
function renderTasksGrid(tareas) {
    const container = document.getElementById('tasks-container');
    if (!tareas || tareas.length === 0) {
        container.innerHTML = `
            <div class="empty-state glass-card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <span style="font-size: 42px; color: var(--accent); margin-bottom: 12px; display: block;">📋</span>
                <h3>¡Todo al día! No hay pendientes en esta vista</h3>
                <p style="color: var(--text-muted); margin-top: 6px;">Haz clic en <b>"+ Nueva Tarea en Lote"</b> para registrar tus pendientes por unidades de salud o personales.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tareas.map(t => {
        const estado = t.estado_calculado || (t.completada ? 'completada' : 'pendiente');
        const freqNombre = appState.frecuencias[t.frecuencia] || t.frecuencia || 'Única vez';
        const horaStr = t.hora_entrega ? `⏰ ${t.hora_entrega} hrs` : '';
        const recPorDia = t.recordatorios_por_dia || 1;

        let badgeEstadoHtml = '';
        if (t.completada) {
            badgeEstadoHtml = `<span class="badge badge-unit">✅ Realizada</span>`;
        } else if (estado === 'vencida') {
            badgeEstadoHtml = `<span class="badge badge-status-red">🚨 VENCIDA</span>`;
        } else if (estado === 'por_vencer') {
            badgeEstadoHtml = `<span class="badge badge-status-orange">⚡ AVISO ACTIVO</span>`;
        } else {
            badgeEstadoHtml = `<span class="badge badge-status-green">🌱 EN TIEMPO</span>`;
        }

        const esPersonal = t.tipo_destino === 'personal' || t.unidad === 'Personal / General';
        const unidadIcon = esPersonal ? '👤' : '🏥';
        const esRecurrente = t.frecuencia && t.frecuencia !== 'unica' && !t.completada;

        return `
            <div class="task-card status-${estado}">
                <div class="task-card-header">
                    <div class="task-badges">
                        <span class="badge badge-unit"><span>${unidadIcon}</span> ${t.unidad}</span>
                        <span class="badge badge-category">${t.categoria}</span>
                        <span class="badge badge-freq"><span>🔄</span> ${freqNombre}</span>
                    </div>
                    ${badgeEstadoHtml}
                </div>

                <h3 class="task-title">${t.tarea}</h3>
                ${t.descripcion ? `<p class="task-desc">${t.descripcion}</p>` : ''}

                <div class="task-meta">
                    <div class="meta-row">
                        <span><span>🔔</span> Avisos inician:</span>
                        <span class="highlight">${t.fecha_inicio} (${recPorDia}x al día)</span>
                    </div>
                    <div class="meta-row">
                        <span><span>📅</span> Fecha y Hora Límite:</span>
                        <span class="highlight" style="color: ${estado === 'vencida' ? 'var(--status-red)' : 'var(--text-main)'}; font-weight: 700;">
                            ${t.fecha_entrega} ${horaStr}
                        </span>
                    </div>
                </div>

                <div class="task-card-actions">
                    ${!t.completada ? `
                        <button class="btn-complete" onclick="completarTarea('${t.id}')">
                            <span>✅</span> Marcar Realizada
                        </button>
                        <button class="btn-small-action" title="Postergar 3 Días" onclick="postergarTarea('${t.id}', 3)">
                            +3d
                        </button>
                        <button class="btn-small-action" title="Editar Tarea" onclick="abrirModalEditar('${t.id}')">
                            <span>✏️</span>
                        </button>
                    ` : `
                        <button class="btn-complete" style="background: rgba(255,255,255,0.1); cursor: default;" disabled>
                            <span>✅</span> En Historial
                        </button>
                    `}
                    ${esRecurrente ? `
                        <button class="btn-small-action" title="Finalizar Serie Recurrente (No volver a repetir)" onclick="finalizarSerie('${t.id}')" style="color: var(--status-orange);">
                            <span>🛑</span>
                        </button>
                    ` : ''}
                    <button class="btn-small-action" title="Eliminar Tarea Definitivamente" onclick="eliminarTarea('${t.id}')" style="color: var(--status-red);">
                        <span>🗑️</span>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderUnidadesUI() {
    const selFiltro = document.getElementById('select-filtro-unidad');
    const selEdit = document.getElementById('edit-unidad');

    const opciones = `<option value="Todas">Todas las Unidades</option>` +
        appState.unidades.map(u => `<option value="${u}">${u}</option>`).join('');

    selFiltro.innerHTML = opciones;
    selEdit.innerHTML = appState.unidades.map(u => `<option value="${u}">${u}</option>`).join('');

    const cCheckboxes = document.getElementById('container-unidades-checkboxes');
    cCheckboxes.innerHTML = appState.unidades.map((u, i) => `
        <label class="unit-checkbox-item">
            <input type="checkbox" name="unidad_chk" value="${u}" checked>
            <span>${u}</span>
        </label>
    `).join('');

    const listAdmin = document.getElementById('list-unidades');
    listAdmin.innerHTML = appState.unidades.map(u => `
        <li>
            <span><span style="margin-right: 8px;">🏥</span> ${u}</span>
            <button class="btn-del-item" title="Eliminar" onclick="eliminarUnidad('${u}')"><span>🗑️</span></button>
        </li>
    `).join('');
}

function renderCategoriasUI() {
    const selNew = document.getElementById('t-categoria');
    const selEdit = document.getElementById('edit-categoria');
    const options = appState.categorias.map(c => `<option value="${c}">${c}</option>`).join('');

    selNew.innerHTML = options;
    selEdit.innerHTML = options;

    const listAdmin = document.getElementById('list-categorias');
    listAdmin.innerHTML = appState.categorias.map(c => `
        <li>
            <span><span style="margin-right: 8px;">🏷️</span> ${c}</span>
            <button class="btn-del-item" title="Eliminar" onclick="eliminarCategoria('${c}')"><span>🗑️</span></button>
        </li>
    `).join('');
}

function renderFrecuenciasUI() {
    const selFiltro = document.getElementById('select-filtro-frecuencia');
    const selNew = document.getElementById('t-frecuencia');
    const selEdit = document.getElementById('edit-frecuencia');

    let optsFiltro = `<option value="Todas">Todas las Frecuencias</option>`;
    let optsSelect = ``;

    for (let key in appState.frecuencias) {
        optsFiltro += `<option value="${key}">${appState.frecuencias[key]}</option>`;
        optsSelect += `<option value="${key}">${appState.frecuencias[key]}</option>`;
    }

    selFiltro.innerHTML = optsFiltro;
    selNew.innerHTML = optsSelect;
    selEdit.innerHTML = optsSelect;
    selNew.value = 'mensual';
}

async function renderDashboardMetrics() {
    try {
        const res = await fetch('/api/dashboard');
        const json = await res.json();
        if (json.status === 'success') {
            const data = json.data;
            document.getElementById('stat-total-activas').innerText = data.total_activas;
            document.getElementById('stat-vencidas').innerText = data.vencidas;
            document.getElementById('stat-por-vencer').innerText = data.por_vencer;
            document.getElementById('stat-cumplidas').innerText = data.total_cumplidas;

            const bContainer = document.getElementById('unit-breakdown-container');
            if (data.por_unidad) {
                bContainer.innerHTML = Object.keys(data.por_unidad).map(u => {
                    const info = data.por_unidad[u];
                    return `
                        <div class="unit-metrics-row">
                            <div class="unit-name"><b>${u}</b></div>
                            <div class="unit-badges-group">
                                <span class="badge badge-status-orange">${info.pendientes} PENDIENTES</span>
                                <span class="badge badge-unit">${info.completadas} CUMPLIDAS</span>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        }
    } catch (e) { console.error("Error dashboard metrics:", e); }
}

async function cargarHistorial() {
    const tbody = document.getElementById('tbl-historial-body');
    try {
        const res = await fetch('/api/historial');
        const json = await res.json();
        if (json.status === 'success') {
            if (json.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:20px;">No hay tareas registradas en el historial.</td></tr>`;
                return;
            }
            tbody.innerHTML = json.data.map(h => `
                <tr>
                    <td>${h.fecha_cumplimiento}</td>
                    <td><b>${h.tarea}</b></td>
                    <td><span class="badge badge-unit">${h.unidad}</span></td>
                    <td>${h.categoria}</td>
                    <td>${appState.frecuencias[h.frecuencia] || h.frecuencia}</td>
                    <td>${h.fecha_entrega_original}</td>
                    <td>${h.notas || '-'}</td>
                </tr>
            `).join('');
        }
    } catch (e) { console.error("Error cargando historial:", e); }
}

// --- FILTERS & ACTIONS ---
function cambiarFiltroTipo(btn, tipo) {
    document.querySelectorAll('.scope-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    appState.filtroTipo = tipo;
    cargarTareas();
}

function cambiarFiltroEstado(btn, estado) {
    document.querySelectorAll('#pills-estado .pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    appState.filtroEstado = estado;
    cargarTareas();
}

function filtrarTareasLocal() {
    cargarTareas();
}

// --- TASK OPERATIONS ---
async function completarTarea(id) {
    try {
        const res = await fetch(`/api/tareas/${id}/completar`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({notas: "Completada desde la Web App"})
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cargarTareas();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error al completar la tarea.", 'error'); }
}

async function finalizarSerie(id) {
    if (!confirm("¿Deseas dar por terminada definitivamente esta serie recurrente? (No se volverá a reprogramar en futuros ciclos).")) return;
    try {
        const res = await fetch(`/api/tareas/${id}/finalizar_serie`, { method: 'POST' });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cargarTareas();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error al finalizar serie.", 'error'); }
}

async function postergarTarea(id, dias) {
    try {
        const res = await fetch(`/api/tareas/${id}/postergar`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({dias: dias})
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cargarTareas();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error al postergar tarea.", 'error'); }
}

async function eliminarTarea(id) {
    const t = appState.tareas.find(item => item.id === id);
    const esRecurrente = t && t.frecuencia && t.frecuencia !== 'unica';

    let msgConfirm = "¿Seguro que deseas eliminar esta tarea definitivamente?";
    if (esRecurrente) {
        msgConfirm = "Esta es una tarea recurrente. ¿Deseas eliminarla y cancelar todos sus eventos/repeticiones futuras?";
    }

    if (!confirm(msgConfirm)) return;
    try {
        const res = await fetch(`/api/tareas/${id}`, { method: 'DELETE' });
        const json = await res.json();
        if (json.status === 'success') {
            showToast("Tarea eliminada definitivamente.", 'success');
            cargarTareas();
        }
    } catch (e) { showToast("Error al eliminar.", 'error'); }
}

// --- MODALS & FORMS ---
function abrirModalNuevaTarea() {
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 7);
    document.getElementById('t-fecha-entrega').value = defaultDate.toISOString().split('T')[0];
    document.getElementById('t-hora-entrega').value = "09:00";
    document.getElementById('t-recordatorios-dia').value = "1";
    
    document.getElementById('modal-tarea').classList.add('active');
}

function cerrarModalTarea() {
    document.getElementById('modal-tarea').classList.remove('active');
}

function toggleDestinoMode() {
    const tipo = document.querySelector('input[name="tipo_destino"]:checked').value;
    const boxUnidades = document.getElementById('box-unidades-lote');
    if (tipo === 'personal') {
        boxUnidades.style.display = 'none';
    } else {
        boxUnidades.style.display = 'block';
    }
}

function toggleSelectAllUnidades() {
    const chks = document.querySelectorAll('input[name="unidad_chk"]');
    const countChecked = Array.from(chks).filter(c => c.checked).length;
    const selectAll = countChecked < chks.length;
    chks.forEach(c => c.checked = selectAll);
}

async function guardarNuevaTarea(event) {
    event.preventDefault();

    const titulo = document.getElementById('t-titulo').value.trim();
    const descripcion = document.getElementById('t-descripcion').value.trim();
    const tipoDestino = document.querySelector('input[name="tipo_destino"]:checked').value;
    const categoria = document.getElementById('t-categoria').value;
    const frecuencia = document.getElementById('t-frecuencia').value;
    const fechaEntrega = document.getElementById('t-fecha-entrega').value;
    const horaEntrega = document.getElementById('t-hora-entrega').value;
    const diasAviso = document.getElementById('t-dias-aviso').value;
    const recordatoriosPorDia = document.getElementById('t-recordatorios-dia').value;

    let unidades = [];
    if (tipoDestino === 'unidad') {
        const chks = document.querySelectorAll('input[name="unidad_chk"]:checked');
        unidades = Array.from(chks).map(c => c.value);
        if (unidades.length === 0) {
            showToast("Debes seleccionar al menos una Unidad de Salud.", 'error');
            return;
        }
    }

    const recordatorios = [];
    if (document.getElementById('chk-rec-telegram').checked) recordatorios.push("Telegram");
    if (document.getElementById('chk-rec-visual').checked) recordatorios.push("Visual en App");

    try {
        const res = await fetch('/api/tareas', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                tarea: titulo,
                descripcion: descripcion,
                tipo_destino: tipoDestino,
                unidades: unidades,
                categoria: categoria,
                frecuencia: frecuencia,
                fecha_entrega: fechaEntrega,
                hora_entrega: horaEntrega,
                dias_aviso: diasAviso,
                recordatorios_por_dia: recordatoriosPorDia,
                recordatorios: recordatorios
            })
        });

        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cerrarModalTarea();
            document.getElementById('form-nueva-tarea').reset();
            cargarTareas();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error guardando la tarea.", 'error'); }
}

function abrirModalEditar(id) {
    const t = appState.tareas.find(item => item.id === id);
    if (!t) return;

    document.getElementById('edit-id').value = t.id;
    document.getElementById('edit-titulo').value = t.tarea;
    document.getElementById('edit-descripcion').value = t.descripcion || '';
    document.getElementById('edit-unidad').value = t.unidad;
    document.getElementById('edit-categoria').value = t.categoria;
    document.getElementById('edit-frecuencia').value = t.frecuencia;
    document.getElementById('edit-fecha-entrega').value = t.fecha_entrega;
    document.getElementById('edit-hora-entrega').value = t.hora_entrega || '09:00';
    document.getElementById('edit-dias-aviso').value = t.dias_aviso;
    document.getElementById('edit-recordatorios-dia').value = t.recordatorios_por_dia || 1;

    document.getElementById('modal-editar').classList.add('active');
}

function cerrarModalEditar() {
    document.getElementById('modal-editar').classList.remove('active');
}

async function guardarEdicionTarea(event) {
    event.preventDefault();
    const id = document.getElementById('edit-id').value;
    const body = {
        tarea: document.getElementById('edit-titulo').value,
        descripcion: document.getElementById('edit-descripcion').value,
        unidad: document.getElementById('edit-unidad').value,
        categoria: document.getElementById('edit-categoria').value,
        frecuencia: document.getElementById('edit-frecuencia').value,
        fecha_entrega: document.getElementById('edit-fecha-entrega').value,
        hora_entrega: document.getElementById('edit-hora-entrega').value,
        dias_aviso: document.getElementById('edit-dias-aviso').value,
        recordatorios_por_dia: document.getElementById('edit-recordatorios-dia').value
    };

    try {
        const res = await fetch(`/api/tareas/${id}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cerrarModalEditar();
            cargarTareas();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error al actualizar tarea.", 'error'); }
}

// --- ADMIN UNITS & CATEGORIES ---
async function agregarUnidad() {
    const input = document.getElementById('input-nueva-unidad');
    const val = input.value.trim();
    if (!val) return;

    try {
        const res = await fetch('/api/unidades', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({nombre: val})
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            input.value = '';
            cargarUnidades();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error agregando unidad.", 'error'); }
}

async function eliminarUnidad(nombre) {
    if (!confirm(`¿Eliminar la unidad "${nombre}"?`)) return;
    try {
        const res = await fetch('/api/unidades', {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({nombre: nombre})
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cargarUnidades();
        }
    } catch (e) { showToast("Error al eliminar.", 'error'); }
}

async function agregarCategoria() {
    const input = document.getElementById('input-nueva-categoria');
    const val = input.value.trim();
    if (!val) return;

    try {
        const res = await fetch('/api/categorias', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({nombre: val})
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            input.value = '';
            cargarCategorias();
        } else {
            showToast(json.message, 'error');
        }
    } catch (e) { showToast("Error agregando categoría.", 'error'); }
}

async function eliminarCategoria(nombre) {
    if (!confirm(`¿Eliminar la categoría "${nombre}"?`)) return;
    try {
        const res = await fetch('/api/categorias', {
            method: 'DELETE',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({nombre: nombre})
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cargarCategorias();
        }
    } catch (e) { showToast("Error al eliminar.", 'error'); }
}

async function guardarConfiguracion(e) {
    e.preventDefault();
    const token = document.getElementById('cfg-token').value.trim();
    const chatId = document.getElementById('cfg-chat-id').value.trim();
    const hora = document.getElementById('cfg-hora').value;
    const dias = document.getElementById('cfg-dias').value;

    try {
        const res = await fetch('/api/configuracion', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                telegram_token: token,
                telegram_chat_id: chatId,
                hora_notificacion_diaria: hora,
                dias_aviso_defecto: dias
            })
        });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
        }
    } catch (e) { showToast("Error guardando configuración.", 'error'); }
}

async function limpiarHistorial() {
    if (!confirm("¿Deseas vaciar todo el historial de tareas cumplidas?")) return;
    try {
        const res = await fetch('/api/historial', { method: 'DELETE' });
        const json = await res.json();
        if (json.status === 'success') {
            showToast(json.message, 'success');
            cargarHistorial();
            renderDashboardMetrics();
        }
    } catch (e) { showToast("Error vaciando historial.", 'error'); }
}

function descargarPDF() {
    window.open('/api/reporte/pdf', '_blank');
}

// --- UTILS ---
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.className = `toast toast-${type}`;
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 4000);
}
