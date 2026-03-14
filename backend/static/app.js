/* wodGod — Single-Page Application */

const API = '';
let token = localStorage.getItem('wodgod_token');
let currentUser = null;
let currentView = 'wod';

// ============================================================
// API Helper
// ============================================================
async function api(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    if (res.status === 401) {
        token = null;
        localStorage.removeItem('wodgod_token');
        render();
        throw new Error('Unauthorized');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || JSON.stringify(err));
    }
    return res.json();
}

// ============================================================
// Render Engine
// ============================================================
function render() {
    const app = document.getElementById('app');
    if (!token) {
        app.innerHTML = renderAuth();
        bindAuth();
        return;
    }
    if (!currentUser) {
        loadUser();
        return;
    }
    if (!currentUser.profile_complete) {
        app.innerHTML = renderSetup();
        bindSetup();
        return;
    }

    let content = renderHeader();
    if (currentView === 'wod') content += renderWodPage();
    else if (currentView === 'calendar') content += renderCalendarPage();
    else if (currentView === 'history') content += renderHistoryPage();
    else if (currentView === 'config') content += renderConfigPage();
    content += renderNav();

    app.innerHTML = content;
    bindNav();
    if (currentView === 'wod') loadWod();
    else if (currentView === 'calendar') loadCalendar();
    else if (currentView === 'history') loadHistory();
    else if (currentView === 'config') bindConfig();
}

// ============================================================
// Auth
// ============================================================
let authMode = 'login';

function renderAuth() {
    const isLogin = authMode === 'login';
    return `
    <div class="auth-container">
        <div class="auth-logo">wod<span>God</span></div>
        <div class="auth-subtitle">CrossFit Training Engine</div>
        <div id="auth-error" class="error-msg" style="display:none"></div>
        <div class="form-group">
            <label class="form-label">Username</label>
            <input class="form-input" id="auth-user" type="text" autocapitalize="none" autocomplete="username">
        </div>
        <div class="form-group">
            <label class="form-label">Password</label>
            <input class="form-input" id="auth-pass" type="password" autocomplete="${isLogin ? 'current-password' : 'new-password'}">
        </div>
        <button class="btn btn-primary" id="auth-submit">${isLogin ? 'Log In' : 'Create Account'}</button>
        <div class="auth-toggle">
            ${isLogin
                ? 'No account? <a id="auth-toggle">Register</a>'
                : 'Have an account? <a id="auth-toggle">Log In</a>'}
        </div>
    </div>`;
}

function bindAuth() {
    document.getElementById('auth-submit')?.addEventListener('click', async () => {
        const user = document.getElementById('auth-user').value.trim();
        const pass = document.getElementById('auth-pass').value;
        const errEl = document.getElementById('auth-error');
        if (!user || !pass) { errEl.textContent = 'Fill in all fields'; errEl.style.display = ''; return; }
        try {
            const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
            const data = await api(endpoint, { method: 'POST', body: JSON.stringify({ username: user, password: pass }) });
            token = data.token;
            localStorage.setItem('wodgod_token', token);
            currentUser = null;
            currentView = 'wod';
            render();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
        }
    });
    document.getElementById('auth-toggle')?.addEventListener('click', () => {
        authMode = authMode === 'login' ? 'register' : 'login';
        render();
    });
    document.getElementById('auth-pass')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') document.getElementById('auth-submit')?.click();
    });
}

// ============================================================
// Load User
// ============================================================
async function loadUser() {
    try {
        currentUser = await api('/auth/me');
        render();
    } catch {
        token = null;
        localStorage.removeItem('wodgod_token');
        render();
    }
}

// ============================================================
// First-Time Setup
// ============================================================
function renderSetup() {
    return `
    <div class="auth-container">
        <div class="auth-logo">wod<span>God</span></div>
        <div class="auth-subtitle">Complete Your Profile</div>
        <div id="setup-error" class="error-msg" style="display:none"></div>
        <div class="form-group">
            <label class="form-label">Name</label>
            <input class="form-input" id="setup-name" type="text">
        </div>
        <div class="form-group">
            <label class="form-label">Age</label>
            <input class="form-input" id="setup-age" type="number" min="10" max="100">
        </div>
        <div class="form-group">
            <label class="form-label">Weight (kg)</label>
            <input class="form-input" id="setup-weight" type="number" step="0.1" min="30">
        </div>
        <div class="form-group">
            <label class="form-label">Height (cm)</label>
            <input class="form-input" id="setup-height" type="number" step="0.1" min="100">
        </div>
        <div class="form-group">
            <label class="form-label">Sex</label>
            <select class="form-select" id="setup-sex">
                <option value="male">Male</option>
                <option value="female">Female</option>
            </select>
        </div>
        <div class="form-group">
            <label class="form-label">Training Age (years, optional)</label>
            <input class="form-input" id="setup-training-age" type="number" step="0.5" min="0" value="0">
        </div>
        <button class="btn btn-primary" id="setup-submit">Start Training</button>
    </div>`;
}

function bindSetup() {
    document.getElementById('setup-submit')?.addEventListener('click', async () => {
        const errEl = document.getElementById('setup-error');
        try {
            const body = {
                name: document.getElementById('setup-name').value.trim(),
                age: parseInt(document.getElementById('setup-age').value),
                weight_kg: parseFloat(document.getElementById('setup-weight').value),
                height_cm: parseFloat(document.getElementById('setup-height').value),
                sex: document.getElementById('setup-sex').value,
                training_age_yr: parseFloat(document.getElementById('setup-training-age').value) || 0,
            };
            await api('/auth/setup-profile', { method: 'POST', body: JSON.stringify(body) });
            currentUser = null;
            render();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
        }
    });
}

// ============================================================
// Header + Nav
// ============================================================
function renderHeader() {
    return `
    <div class="header">
        <h1>wod<span>God</span></h1>
    </div>`;
}

function renderNav() {
    return `
    <nav class="nav"><div class="nav-inner">
        <button class="nav-btn ${currentView === 'wod' ? 'active' : ''}" data-view="wod">
            <span class="nav-btn-icon">&#9889;</span>WOD
        </button>
        <button class="nav-btn ${currentView === 'calendar' ? 'active' : ''}" data-view="calendar">
            <span class="nav-btn-icon">&#128197;</span>Calendar
        </button>
        <button class="nav-btn ${currentView === 'history' ? 'active' : ''}" data-view="history">
            <span class="nav-btn-icon">&#128200;</span>History
        </button>
        <button class="nav-btn ${currentView === 'config' ? 'active' : ''}" data-view="config">
            <span class="nav-btn-icon">&#9881;</span>Config
        </button>
    </div></nav>`;
}

function bindNav() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            currentView = btn.dataset.view;
            render();
        });
    });
}

// ============================================================
// View WOD
// ============================================================
let todayWod = null;
let wodLoaded = false;

function renderWodPage() {
    if (!wodLoaded) return '<div class="loading">Loading today\'s WOD...</div>';
    if (!todayWod || !todayWod.workout) {
        return `
        <div class="empty">
            <p>No workout scheduled for today.</p>
            <p style="margin-top:8px;font-size:12px;color:var(--text-dim)">Generate your week from the Calendar tab.</p>
        </div>`;
    }

    const w = todayWod.workout;
    const wj = typeof w.workout_json === 'string' ? JSON.parse(w.workout_json) : w.workout_json;
    const logged = todayWod.logged;

    let html = '';

    // Meta tags
    html += `<div class="wod-meta">
        <span class="wod-tag tag-rpe">RPE ${w.intensity_target_rpe}</span>
        <span class="wod-tag tag-cns-${w.cns_load}">CNS ${w.cns_load}</span>
    </div>`;

    html += `<div class="card"><div class="card-title">${w.focus}</div>`;

    // Primary strength
    if (wj.primary_strength) {
        html += renderStrengthSection('Primary Strength', wj.primary_strength);
    }
    // Secondary strength
    if (wj.secondary_strength) {
        html += renderStrengthSection('Secondary Strength', wj.secondary_strength);
    }
    // Conditioning
    if (wj.conditioning) {
        html += `<div class="wod-section">
            <div class="wod-section-title">${(wj.conditioning.type || 'WOD').toUpperCase()} — ${wj.conditioning.time_cap_minutes} min</div>`;
        (wj.conditioning.movements || []).forEach(m => {
            html += `<div class="wod-movement">
                <span class="wod-movement-name">${formatMovement(m.movement)}</span>
                <span class="wod-movement-detail">${m.reps ? m.reps + ' reps' : m.distance_m ? m.distance_m + 'm' : m.calories ? m.calories + ' cal' : ''}</span>
            </div>`;
        });
        html += '</div>';
    }
    // Aerobic
    if (wj.aerobic_prescription) {
        html += `<div class="wod-section">
            <div class="wod-section-title">Aerobic — ${wj.aerobic_prescription.type}</div>
            <div class="wod-movement">
                <span class="wod-movement-name">${formatMovement(wj.aerobic_prescription.modality)}</span>
                <span class="wod-movement-detail">${wj.aerobic_prescription.duration_minutes} min</span>
            </div>
        </div>`;
    }
    // Mobility
    if (wj.mobility_prompt) {
        html += `<div class="wod-section">
            <div class="wod-section-title">Mobility</div>
            <div class="mobility-text">${wj.mobility_prompt}</div>
        </div>`;
    }

    html += '</div>';

    // Log button or logged status
    if (logged) {
        const log = todayWod.log;
        html += `<div class="card" style="border-color: var(--green)">
            <div class="card-title" style="color: var(--green)">Completed</div>
            <div class="history-stats">
                <span>RPE: ${log.actual_rpe}</span>
                <span>${new Date(log.completed_at).toLocaleTimeString()}</span>
            </div>
        </div>`;
    } else {
        html += `<button class="btn btn-primary" id="start-wod-btn">Log Workout</button>`;
    }

    return html;
}

function renderStrengthSection(title, block) {
    const pct = block.load_percentage ? `${Math.round(block.load_percentage * 100)}%` : '';
    return `<div class="wod-section">
        <div class="wod-section-title">${title}</div>
        <div class="wod-movement">
            <span class="wod-movement-name">${formatMovement(block.movement)}</span>
            <span class="wod-movement-detail">${block.scheme} @ ${pct} | Rest ${block.rest_seconds}s</span>
        </div>
    </div>`;
}

async function loadWod() {
    try {
        todayWod = await api('/workouts/today');
        wodLoaded = true;
        // Re-render just the content
        const app = document.getElementById('app');
        let content = renderHeader();
        content += renderWodPage();
        content += renderNav();
        app.innerHTML = content;
        bindNav();

        // Bind log button
        document.getElementById('start-wod-btn')?.addEventListener('click', () => showLogModal());
    } catch (e) {
        wodLoaded = true;
        todayWod = null;
        render();
    }
}

// ============================================================
// Log Workout Modal
// ============================================================
let selectedRpe = 7;

function showLogModal() {
    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">Log Workout</div>
        <div id="log-error" class="error-msg" style="display:none"></div>
        <div class="form-group">
            <label class="form-label">How did it feel? (RPE)</label>
            <div class="rpe-scale" id="rpe-scale">
                ${[1,2,3,4,5,6,7,8,9,10].map(n =>
                    `<button class="rpe-btn ${n === selectedRpe ? 'selected' : ''}" data-rpe="${n}">${n}</button>`
                ).join('')}
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Missed Reps</label>
            <input class="form-input" id="log-missed" type="number" min="0" value="0">
        </div>
        <div class="form-group">
            <label class="form-label">Notes (optional)</label>
            <input class="form-input" id="log-notes" type="text" placeholder="How did it go?">
        </div>
        <button class="btn btn-primary" id="log-submit">Save Log</button>
        <button class="btn btn-secondary" id="log-cancel" style="margin-top:8px">Cancel</button>
    </div>`;

    document.body.appendChild(overlay);

    overlay.querySelectorAll('.rpe-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            selectedRpe = parseInt(btn.dataset.rpe);
            overlay.querySelectorAll('.rpe-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });

    document.getElementById('log-cancel').addEventListener('click', () => overlay.remove());

    document.getElementById('log-submit').addEventListener('click', async () => {
        const errEl = document.getElementById('log-error');
        try {
            await api(`/workouts/${todayWod.workout.id}/log`, {
                method: 'POST',
                body: JSON.stringify({
                    actual_rpe: selectedRpe,
                    missed_reps: parseInt(document.getElementById('log-missed').value) || 0,
                    notes: document.getElementById('log-notes').value || null,
                    performance_json: {},
                }),
            });
            overlay.remove();
            wodLoaded = false;
            todayWod = null;
            render();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
        }
    });
}

// ============================================================
// Calendar
// ============================================================
let calendarData = null;

function renderCalendarPage() {
    let html = '<div class="page-title">This Week</div>';
    if (!calendarData) return html + '<div class="loading">Loading calendar...</div>';

    const today = new Date().toISOString().split('T')[0];
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    if (calendarData.length === 0) {
        html += `<div class="empty">
            <p>No workouts generated yet.</p>
            <button class="btn btn-primary" id="gen-week-btn" style="margin-top:16px;max-width:260px;margin-left:auto;margin-right:auto">Generate This Week</button>
        </div>`;
        return html;
    }

    calendarData.forEach((w, idx) => {
        const d = new Date(w.scheduled_date + 'T12:00:00');
        const dayName = days[d.getDay()];
        const dayNum = d.getDate();
        const isToday = w.scheduled_date === today;
        const classes = `cal-day${isToday ? ' today' : ''}${w.logged ? ' logged' : ''}`;

        html += `<div class="${classes}" data-cal-idx="${idx}">
            <div class="cal-date">
                <div class="cal-date-day">${dayNum}</div>
                <div class="cal-date-label">${dayName}</div>
            </div>
            <div class="cal-info">
                <div class="cal-focus">${w.focus}</div>
                <div class="cal-detail">RPE ${w.intensity_target_rpe} | CNS ${w.cns_load}</div>
            </div>
            <div class="cal-status">${w.logged ? '&#10003;' : isToday ? '&#9654;' : '&#8250;'}</div>
        </div>`;
    });

    return html;
}

function showCalendarDetail(workout) {
    const wj = typeof workout.workout_json === 'string' ? JSON.parse(workout.workout_json) : (workout.workout_json || {});
    const d = new Date(workout.scheduled_date + 'T12:00:00');
    const dateStr = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    const details = renderWorkoutDetails(wj);

    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">${workout.focus}</div>
        <div class="history-detail-meta">
            <span>${dateStr} — Week ${workout.program_week}, Day ${workout.day_index}</span>
        </div>
        <div class="history-detail-stats">
            <span class="wod-tag tag-rpe">RPE ${workout.intensity_target_rpe}</span>
            <span class="wod-tag tag-cns-${workout.cns_load}">CNS ${workout.cns_load}</span>
            ${workout.logged ? '<span class="wod-tag" style="background:rgba(34,197,94,0.15);color:var(--green)">Completed</span>' : ''}
        </div>
        ${details ? `<div class="card" style="margin:12px 0 0;text-align:left">${details}</div>` : ''}
        <div class="history-detail-actions">
            <button class="btn btn-secondary" id="cal-detail-close">Close</button>
        </div>
    </div>`;

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));

    const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
    document.getElementById('cal-detail-close').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
}

async function loadCalendar() {
    try {
        calendarData = await api('/workouts/calendar');
        const app = document.getElementById('app');
        let content = renderHeader();
        content += renderCalendarPage();
        content += renderNav();
        app.innerHTML = content;
        bindNav();

        // Bind calendar item clicks
        document.querySelectorAll('.cal-day[data-cal-idx]').forEach(el => {
            el.addEventListener('click', () => {
                const idx = parseInt(el.dataset.calIdx);
                if (calendarData[idx]) showCalendarDetail(calendarData[idx]);
            });
        });

        // Bind generate button if present
        document.getElementById('gen-week-btn')?.addEventListener('click', async () => {
            const btn = document.getElementById('gen-week-btn');
            btn.disabled = true;
            btn.textContent = 'Generating...';
            try {
                await api('/workouts/generate-week', { method: 'POST' });
                calendarData = null;
                render();
            } catch (e) {
                btn.textContent = 'Failed — Retry';
                btn.disabled = false;
            }
        });
    } catch {
        calendarData = [];
        render();
    }
}

// ============================================================
// History
// ============================================================
let historyData = null;

function renderHistoryPage() {
    let html = '<div class="page-title">History</div>';
    if (!historyData) return html + '<div class="loading">Loading history...</div>';
    if (historyData.length === 0) return html + '<div class="empty">No completed workouts yet.</div>';

    historyData.forEach((log, idx) => {
        const date = new Date(log.completed_at);
        const dateStr = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        html += `<div class="history-item" data-history-idx="${idx}">
            <div class="history-header">
                <span class="history-focus">${log.focus}</span>
                <span class="history-date">${dateStr}</span>
            </div>
            <div class="history-stats">
                <span>RPE: ${log.actual_rpe}</span>
                <span>Week ${log.program_week}, Day ${log.day_index}</span>
                ${log.missed_reps > 0 ? `<span style="color:var(--red)">Missed: ${log.missed_reps}</span>` : ''}
            </div>
            ${log.notes ? `<div style="font-size:12px;color:var(--text-dim);margin-top:6px">${log.notes}</div>` : ''}
        </div>`;
    });

    return html;
}

function renderWorkoutDetails(wj) {
    let details = '';
    if (wj.primary_strength) {
        details += renderStrengthSection('Primary Strength', wj.primary_strength);
    }
    if (wj.secondary_strength) {
        details += renderStrengthSection('Secondary Strength', wj.secondary_strength);
    }
    if (wj.conditioning) {
        details += `<div class="wod-section">
            <div class="wod-section-title">${(wj.conditioning.type || 'WOD').toUpperCase()} — ${wj.conditioning.time_cap_minutes} min</div>`;
        (wj.conditioning.movements || []).forEach(m => {
            details += `<div class="wod-movement">
                <span class="wod-movement-name">${formatMovement(m.movement)}</span>
                <span class="wod-movement-detail">${m.reps ? m.reps + ' reps' : m.distance_m ? m.distance_m + 'm' : m.calories ? m.calories + ' cal' : ''}</span>
            </div>`;
        });
        details += '</div>';
    }
    if (wj.aerobic_prescription) {
        details += `<div class="wod-section">
            <div class="wod-section-title">Aerobic — ${wj.aerobic_prescription.type}</div>
            <div class="wod-movement">
                <span class="wod-movement-name">${formatMovement(wj.aerobic_prescription.modality)}</span>
                <span class="wod-movement-detail">${wj.aerobic_prescription.duration_minutes} min</span>
            </div>
        </div>`;
    }
    if (wj.mobility_prompt) {
        details += `<div class="wod-section">
            <div class="wod-section-title">Mobility</div>
            <div class="mobility-text">${wj.mobility_prompt}</div>
        </div>`;
    }
    return details;
}

function showHistoryDetail(log, logIndex) {
    const wj = typeof log.workout_json === 'string' ? JSON.parse(log.workout_json) : (log.workout_json || {});
    const completedDate = new Date(log.completed_at);
    const dateStr = completedDate.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
    const timeStr = completedDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
    const details = renderWorkoutDetails(wj);

    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">${log.focus}</div>
        <div class="history-detail-meta">
            <span>Completed ${dateStr} at ${timeStr}</span>
            <span>Week ${log.program_week}, Day ${log.day_index}</span>
        </div>
        <div class="history-detail-stats">
            <span class="wod-tag tag-rpe">RPE ${log.actual_rpe}</span>
            ${log.missed_reps > 0 ? `<span class="wod-tag" style="background:var(--red)">Missed ${log.missed_reps} reps</span>` : ''}
        </div>
        ${details ? `<div class="card" style="margin:12px 0 0;text-align:left">${details}</div>` : ''}
        ${log.notes ? `<div class="history-detail-notes">${log.notes}</div>` : ''}
        <div class="history-detail-actions">
            <button class="btn btn-primary" id="history-edit-btn">Edit</button>
            <button class="btn btn-secondary" id="history-detail-close">Close</button>
        </div>
    </div>`;

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));

    const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
    document.getElementById('history-detail-close').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    document.getElementById('history-edit-btn').addEventListener('click', () => {
        overlay.remove();
        showHistoryEditModal(log, logIndex);
    });
}

function showHistoryEditModal(log, logIndex) {
    let editRpe = log.actual_rpe;

    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">Edit Log</div>
        <div id="edit-log-error" class="error-msg" style="display:none"></div>
        <div class="form-group">
            <label class="form-label">RPE</label>
            <div class="rpe-scale" id="edit-rpe-scale">
                ${[1,2,3,4,5,6,7,8,9,10].map(n =>
                    `<button class="rpe-btn ${n === editRpe ? 'selected' : ''}" data-rpe="${n}">${n}</button>`
                ).join('')}
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Missed Reps</label>
            <input class="form-input" id="edit-missed" type="number" min="0" value="${log.missed_reps || 0}">
        </div>
        <div class="form-group">
            <label class="form-label">Notes (optional)</label>
            <input class="form-input" id="edit-notes" type="text" value="${(log.notes || '').replace(/"/g, '&quot;')}" placeholder="How did it go?">
        </div>
        <button class="btn btn-primary" id="edit-log-save">Save Changes</button>
        <button class="btn btn-secondary" id="edit-log-cancel" style="margin-top:8px">Cancel</button>
    </div>`;

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));

    overlay.querySelectorAll('.rpe-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            editRpe = parseInt(btn.dataset.rpe);
            overlay.querySelectorAll('.rpe-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });

    const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
    document.getElementById('edit-log-cancel').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

    document.getElementById('edit-log-save').addEventListener('click', async () => {
        const errEl = document.getElementById('edit-log-error');
        try {
            await api(`/logs/${log.id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    actual_rpe: editRpe,
                    missed_reps: parseInt(document.getElementById('edit-missed').value) || 0,
                    notes: document.getElementById('edit-notes').value || null,
                    performance_json: {},
                }),
            });
            // Update local data so the list reflects changes without refetching
            if (historyData && historyData[logIndex]) {
                historyData[logIndex].actual_rpe = editRpe;
                historyData[logIndex].missed_reps = parseInt(document.getElementById('edit-missed').value) || 0;
                historyData[logIndex].notes = document.getElementById('edit-notes').value || null;
            }
            close();
            loadHistory();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
        }
    });
}

async function loadHistory() {
    try {
        historyData = await api('/logs?limit=50');
        const app = document.getElementById('app');
        let content = renderHeader();
        content += renderHistoryPage();
        content += renderNav();
        app.innerHTML = content;
        bindNav();
        document.querySelectorAll('.history-item[data-history-idx]').forEach(el => {
            el.addEventListener('click', () => {
                const idx = parseInt(el.dataset.historyIdx);
                if (historyData[idx]) showHistoryDetail(historyData[idx], idx);
            });
        });
    } catch {
        historyData = [];
        render();
    }
}

// ============================================================
// Config
// ============================================================
function renderConfigPage() {
    return `
    <div class="page-title">Config</div>
    <div class="profile-menu">
        <div class="profile-menu-item" id="config-edit-profile">
            <span>Edit Profile</span>
            <span class="profile-menu-arrow">&#8250;</span>
        </div>
        <div class="profile-menu-item" id="config-settings">
            <span>AI Selection</span>
            <span class="profile-menu-arrow">&#8250;</span>
        </div>
        <div class="profile-menu-item profile-menu-logout" id="config-logout">
            <span>Log Out</span>
        </div>
    </div>`;
}

function bindConfig() {
    document.getElementById('config-logout')?.addEventListener('click', () => {
        showLogoutConfirm();
    });
    document.getElementById('config-settings')?.addEventListener('click', () => {
        showSettingsModal();
    });
}

async function showSettingsModal() {
    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">AI Selection</div>
        <div class="form-group">
            <label class="form-label">AI Model</label>
            <div id="llm-list" class="llm-list"><div class="loading" style="min-height:auto;padding:12px 0">Loading...</div></div>
        </div>
        <div id="llm-status" style="display:none;text-align:center;font-size:13px;font-weight:600;margin-bottom:12px"></div>
        <button class="btn btn-secondary" id="settings-close">Close</button>
    </div>`;

    document.body.appendChild(overlay);
    document.getElementById('settings-close').addEventListener('click', () => overlay.remove());

    // Load available providers
    try {
        const data = await api('/settings/llm');
        const listEl = document.getElementById('llm-list');
        if (data.providers.length === 0) {
            listEl.innerHTML = '<div style="color:var(--text-dim);font-size:13px;padding:8px 0">No AI models configured.</div>';
            return;
        }
        listEl.innerHTML = data.providers.map(p => `
            <div class="llm-option ${p.id === data.active ? 'active' : ''}" data-provider="${p.id}">
                <span class="llm-option-name">${p.name}</span>
                <span class="llm-option-check">${p.id === data.active ? '&#10003;' : ''}</span>
            </div>
        `).join('');

        listEl.querySelectorAll('.llm-option').forEach(el => {
            el.addEventListener('click', async () => {
                const providerId = el.dataset.provider;
                const statusEl = document.getElementById('llm-status');

                // Disable all options while testing
                listEl.querySelectorAll('.llm-option').forEach(o => o.style.pointerEvents = 'none');
                statusEl.style.display = '';
                statusEl.style.color = 'var(--text-dim)';
                statusEl.textContent = 'Testing connection...';

                try {
                    const result = await api(`/settings/llm/${providerId}`, { method: 'POST' });
                    if (result.ok) {
                        statusEl.style.color = 'var(--green)';
                        statusEl.textContent = `AI ${result.name} Enabled`;
                        // Update active state
                        listEl.querySelectorAll('.llm-option').forEach(o => {
                            o.classList.remove('active');
                            o.querySelector('.llm-option-check').textContent = '';
                        });
                        el.classList.add('active');
                        el.querySelector('.llm-option-check').textContent = '\u2713';
                    } else {
                        const pName = el.querySelector('.llm-option-name').textContent;
                        statusEl.style.color = 'var(--red)';
                        statusEl.textContent = `AI ${pName} Unavailable`;
                    }
                } catch (e) {
                    statusEl.style.color = 'var(--red)';
                    statusEl.textContent = 'Connection failed';
                }

                listEl.querySelectorAll('.llm-option').forEach(o => o.style.pointerEvents = '');
            });
        });
    } catch {
        document.getElementById('llm-list').innerHTML = '<div style="color:var(--red);font-size:13px">Failed to load settings.</div>';
    }
}

function showLogoutConfirm() {
    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal" style="text-align:center">
        <div class="readiness-title">Log Out</div>
        <p style="color:var(--text-dim);font-size:14px;margin-bottom:24px">Are you sure you want to log out?</p>
        <button class="btn btn-primary" id="confirm-logout" style="background:var(--red)">Log Out</button>
        <button class="btn btn-secondary" id="cancel-logout" style="margin-top:8px">Cancel</button>
    </div>`;

    document.body.appendChild(overlay);

    document.getElementById('confirm-logout').addEventListener('click', () => {
        overlay.remove();
        token = null;
        currentUser = null;
        localStorage.removeItem('wodgod_token');
        render();
    });

    document.getElementById('cancel-logout').addEventListener('click', () => {
        overlay.remove();
    });
}

// ============================================================
// Helpers
// ============================================================
function formatMovement(name) {
    if (!name) return '';
    return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ============================================================
// Boot
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    wodLoaded = false;
    todayWod = null;
    calendarData = null;
    historyData = null;

    render();
});
