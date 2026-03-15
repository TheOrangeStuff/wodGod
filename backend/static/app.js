/* wodGod — Single-Page Application */

const API = '';
let token = localStorage.getItem('wodgod_token');
let currentUser = null;
let currentView = 'workouts';

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
    if (currentView === 'workouts') content += renderWorkoutsPage();
    else if (currentView === 'stats') content += renderStatsPage();
    else if (currentView === 'config') content += renderConfigPage();
    content += renderNav();

    app.innerHTML = content;
    bindNav();
    if (currentView === 'workouts') loadWorkouts();
    else if (currentView === 'stats') loadStats();
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
            currentView = 'workouts';
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
let setupUnits = 'metric';

function renderSetup() {
    const isMetric = setupUnits === 'metric';
    const weightLabel = isMetric ? 'Weight (kg)' : 'Weight (lbs)';
    const heightLabel = isMetric ? 'Height (cm)' : 'Height (in)';
    return `
    <div class="auth-container">
        <div class="auth-logo">wod<span>God</span></div>
        <div class="auth-subtitle">Complete Your Profile</div>
        <div id="setup-error" class="error-msg" style="display:none"></div>
        <div class="form-group">
            <label class="form-label">Units</label>
            <div class="unit-toggle" id="setup-unit-toggle">
                <button class="unit-toggle-btn ${isMetric ? 'active' : ''}" data-unit="metric">Metric</button>
                <button class="unit-toggle-btn ${!isMetric ? 'active' : ''}" data-unit="imperial">Imperial</button>
            </div>
        </div>
        <div class="form-group">
            <label class="form-label">Name</label>
            <input class="form-input" id="setup-name" type="text">
        </div>
        <div class="form-group">
            <label class="form-label">Age</label>
            <input class="form-input" id="setup-age" type="number" min="10" max="100">
        </div>
        <div class="form-group">
            <label class="form-label">${weightLabel}</label>
            <input class="form-input" id="setup-weight" type="number" step="0.1" min="1">
        </div>
        <div class="form-group">
            <label class="form-label">${heightLabel}</label>
            <input class="form-input" id="setup-height" type="number" step="0.1" min="1">
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
    // Unit toggle
    document.querySelectorAll('#setup-unit-toggle .unit-toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            setupUnits = btn.dataset.unit;
            // Preserve entered values across re-render
            const savedName = document.getElementById('setup-name')?.value || '';
            const savedAge = document.getElementById('setup-age')?.value || '';
            const savedWeight = document.getElementById('setup-weight')?.value || '';
            const savedHeight = document.getElementById('setup-height')?.value || '';
            const savedSex = document.getElementById('setup-sex')?.value || 'male';
            const savedTraining = document.getElementById('setup-training-age')?.value || '0';

            const app = document.getElementById('app');
            app.innerHTML = renderSetup();
            bindSetup();

            // Restore values
            document.getElementById('setup-name').value = savedName;
            document.getElementById('setup-age').value = savedAge;
            document.getElementById('setup-weight').value = savedWeight;
            document.getElementById('setup-height').value = savedHeight;
            document.getElementById('setup-sex').value = savedSex;
            document.getElementById('setup-training-age').value = savedTraining;
        });
    });

    document.getElementById('setup-submit')?.addEventListener('click', async () => {
        const errEl = document.getElementById('setup-error');
        try {
            let weightKg = parseFloat(document.getElementById('setup-weight').value);
            let heightCm = parseFloat(document.getElementById('setup-height').value);

            // Convert imperial to metric for storage
            if (setupUnits === 'imperial') {
                weightKg = weightKg * 0.453592;  // lbs to kg
                heightCm = heightCm * 2.54;       // inches to cm
            }

            const body = {
                name: document.getElementById('setup-name').value.trim(),
                age: parseInt(document.getElementById('setup-age').value),
                weight_kg: Math.round(weightKg * 10) / 10,
                height_cm: Math.round(heightCm * 10) / 10,
                sex: document.getElementById('setup-sex').value,
                training_age_yr: parseFloat(document.getElementById('setup-training-age').value) || 0,
                unit_system: setupUnits,
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
    const showAdd = currentView === 'workouts';
    return `
    <div class="header">
        <div class="header-spacer"></div>
        <h1>wod<span>God</span></h1>
        ${showAdd ? '<button class="header-add-btn" id="add-custom-btn" title="Add Custom Workout">+</button>' : '<div class="header-spacer"></div>'}
    </div>`;
}

function renderNav() {
    return `
    <nav class="nav"><div class="nav-inner">
        <button class="nav-btn ${currentView === 'workouts' ? 'active' : ''}" data-view="workouts">
            <span class="nav-btn-icon">&#9889;</span>Workouts
        </button>
        <button class="nav-btn ${currentView === 'stats' ? 'active' : ''}" data-view="stats">
            <span class="nav-btn-icon">&#9776;</span>Stats
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
// Unified Workouts View
// ============================================================
let allWorkouts = null;
let workoutsFilter = 'today'; // 'today', 'future', 'past', 'all'

function renderWorkoutsPage() {
    let html = '<div class="page-title">Workouts</div>';

    // Filter tabs
    html += `<div class="filter-tabs">
        <button class="filter-tab ${workoutsFilter === 'today' ? 'active' : ''}" data-filter="today">Today</button>
        <button class="filter-tab ${workoutsFilter === 'future' ? 'active' : ''}" data-filter="future">Future</button>
        <button class="filter-tab ${workoutsFilter === 'past' ? 'active' : ''}" data-filter="past">Past</button>
        <button class="filter-tab ${workoutsFilter === 'all' ? 'active' : ''}" data-filter="all">All</button>
    </div>`;

    if (!allWorkouts) return html + '<div class="loading" style="min-height:auto;padding:40px 0">Loading workouts...</div>';

    if (allWorkouts.length === 0) {
        html += `<div class="empty">
            <p>No workouts generated yet.</p>
            <button class="btn btn-primary" id="gen-week-btn" style="margin-top:16px;max-width:260px;margin-left:auto;margin-right:auto">Generate This Week</button>
        </div>`;
        return html;
    }

    const filtered = workoutsFilter === 'all'
        ? allWorkouts
        : allWorkouts.filter(w => w.time_period === workoutsFilter.toUpperCase());

    if (filtered.length === 0) {
        html += `<div class="empty">No ${workoutsFilter} workouts.</div>`;
    }

    const today = new Date().toISOString().split('T')[0];
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    // Check if any future workouts exist to decide whether to show generate button
    const hasFuture = allWorkouts.some(w => w.time_period === 'FUTURE');
    const hasToday = allWorkouts.some(w => w.time_period === 'TODAY');

    filtered.forEach((w, idx) => {
        const d = new Date(w.scheduled_date + 'T12:00:00');
        const dayName = days[d.getDay()];
        const dayNum = d.getDate();
        const monthStr = d.toLocaleDateString(undefined, { month: 'short' });
        const isToday = w.time_period === 'TODAY';

        const detailLine = w.is_custom
            ? `RPE ${w.intensity_target_rpe} | Custom`
            : `RPE ${w.intensity_target_rpe} | CNS ${w.cns_load}`;

        // Show badge only for COMPLETE and MISSED statuses
        let badgeHtml = '';
        if (w.status === 'COMPLETE') {
            badgeHtml = `<div class="workout-status-badge badge-complete">Complete</div>`;
        } else if (w.status === 'MISSED') {
            badgeHtml = `<div class="workout-status-badge badge-missed">Missed</div>`;
        }

        html += `<div class="workout-item${isToday ? ' is-today' : ''}" data-workout-idx="${idx}" data-workout-id="${w.id}">
            <div class="workout-date">
                <div class="workout-date-day">${dayNum}</div>
                <div class="workout-date-label">${dayName}</div>
                <div class="workout-date-month">${monthStr}</div>
            </div>
            <div class="workout-info">
                <div class="workout-focus">${w.focus}</div>
                <div class="workout-detail">${detailLine}</div>
            </div>
            ${badgeHtml}
        </div>`;
    });

    // Generate week button at the bottom if no future workouts
    if (!hasFuture && !hasToday) {
        html += `<div class="gen-week-prompt">
            <p class="gen-week-hint">All workouts complete. Tap below to generate your next week of programming.</p>
            <button class="btn btn-primary" id="gen-week-btn">Generate This Week</button>
        </div>`;
    }

    return html;
}

async function loadWorkouts() {
    try {
        allWorkouts = await api('/workouts/all');
        const app = document.getElementById('app');
        let content = renderHeader();
        content += renderWorkoutsPage();
        content += renderNav();
        app.innerHTML = content;
        bindNav();
        bindWorkoutsPage();
    } catch {
        allWorkouts = [];
        render();
    }
}

function bindWorkoutsPage() {
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            workoutsFilter = tab.dataset.filter;
            // Re-render just the content without refetching
            const app = document.getElementById('app');
            let content = renderHeader();
            content += renderWorkoutsPage();
            content += renderNav();
            app.innerHTML = content;
            bindNav();
            bindWorkoutsPage();
        });
    });

    // Workout item clicks
    const filtered = workoutsFilter === 'all'
        ? allWorkouts
        : (allWorkouts || []).filter(w => w.time_period === workoutsFilter.toUpperCase());

    document.querySelectorAll('.workout-item[data-workout-idx]').forEach(el => {
        el.addEventListener('click', () => {
            const idx = parseInt(el.dataset.workoutIdx);
            if (filtered[idx]) showWorkoutDetail(filtered[idx]);
        });
    });

    // Add custom workout button
    document.getElementById('add-custom-btn')?.addEventListener('click', () => {
        showCustomWorkoutDateModal();
    });

    // Generate week button
    document.getElementById('gen-week-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('gen-week-btn');
        btn.disabled = true;
        btn.textContent = 'Generating...';
        try {
            await api('/workouts/generate-week', { method: 'POST' });
            allWorkouts = null;
            render();
        } catch (e) {
            btn.textContent = 'Failed — Retry';
            btn.disabled = false;
        }
    });
}

// ============================================================
// Custom Workout Flow
// ============================================================
function showCustomWorkoutDateModal() {
    const today = new Date().toISOString().split('T')[0];
    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">Custom Workout</div>
        <div class="form-group">
            <label class="form-label">When did you do this workout?</label>
            <input class="form-input" id="custom-date" type="date" value="${today}">
        </div>
        <button class="btn btn-primary" id="custom-date-next">Next</button>
        <button class="btn btn-secondary" id="custom-date-cancel" style="margin-top:8px">Cancel</button>
    </div>`;

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));

    const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
    document.getElementById('custom-date-cancel').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

    document.getElementById('custom-date-next').addEventListener('click', () => {
        const dateVal = document.getElementById('custom-date').value;
        if (!dateVal) return;
        close();
        setTimeout(() => showCustomWorkoutDescModal(dateVal), 220);
    });
}

function showCustomWorkoutDescModal(scheduledDate) {
    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';
    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">Describe Your Workout</div>
        <div id="custom-error" class="error-msg" style="display:none"></div>
        <div class="form-group">
            <label class="form-label">What did you do?</label>
            <textarea class="form-input custom-desc-input" id="custom-desc" rows="4" placeholder="e.g. Ran a 5K in 30 minutes. Best mile pace was 8 minutes."></textarea>
        </div>
        <button class="btn btn-primary" id="custom-submit">Add Workout</button>
        <button class="btn btn-secondary" id="custom-cancel" style="margin-top:8px">Cancel</button>
    </div>`;

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));
    document.getElementById('custom-desc').focus();

    const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
    document.getElementById('custom-cancel').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

    document.getElementById('custom-submit').addEventListener('click', async () => {
        const desc = document.getElementById('custom-desc').value.trim();
        const errEl = document.getElementById('custom-error');
        if (!desc) { errEl.textContent = 'Please describe your workout'; errEl.style.display = ''; return; }

        const btn = document.getElementById('custom-submit');
        btn.disabled = true;
        btn.textContent = 'Adding...';

        try {
            await api('/workouts/custom', {
                method: 'POST',
                body: JSON.stringify({ description: desc, scheduled_date: scheduledDate }),
            });
            close();
            allWorkouts = null;
            render();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
            btn.disabled = false;
            btn.textContent = 'Add Workout';
        }
    });
}

// ============================================================
// Stats Page
// ============================================================
let statsData = null;
let statsCharts = {};

function renderStatsPage() {
    let html = '<div class="page-title">Stats</div>';

    if (!statsData) {
        return html + '<div class="loading" style="min-height:auto;padding:40px 0">Loading stats...</div>';
    }

    if (!statsData.rpe_trend.length && !statsData.volume_per_week.length && !statsData.movement_balance.length) {
        return html + '<div class="empty">No workout data yet. Complete some workouts to see your stats.</div>';
    }

    html += `
        <div class="stats-chart-card card">
            <div class="card-title">Movement Balance</div>
            <canvas id="chart-movement-balance"></canvas>
        </div>
        <div class="stats-chart-card card">
            <div class="card-title">RPE Trend</div>
            <canvas id="chart-rpe-trend"></canvas>
        </div>
        <div class="stats-chart-card card">
            <div class="card-title">Training Volume / Week</div>
            <canvas id="chart-volume-week"></canvas>
        </div>
    `;

    return html;
}

async function loadStats() {
    try {
        statsData = await api('/stats');
        const app = document.getElementById('app');
        let content = renderHeader();
        content += renderStatsPage();
        content += renderNav();
        app.innerHTML = content;
        bindNav();
        if (statsData) renderCharts();
    } catch {
        statsData = { rpe_trend: [], volume_per_week: [], movement_balance: [] };
        render();
    }
}

function destroyCharts() {
    Object.values(statsCharts).forEach(c => c.destroy());
    statsCharts = {};
}

function renderCharts() {
    destroyCharts();

    const chartDefaults = {
        color: '#888',
        borderColor: '#2a2a2a',
        font: { family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif" },
    };
    Chart.defaults.color = chartDefaults.color;
    Chart.defaults.borderColor = chartDefaults.borderColor;

    // Movement Balance Radar
    const mbEl = document.getElementById('chart-movement-balance');
    if (mbEl && statsData.movement_balance.length) {
        const labels = statsData.movement_balance.map(m => m.category.replace(/_/g, ' '));
        const data = statsData.movement_balance.map(m => m.count);
        statsCharts.movementBalance = new Chart(mbEl, {
            type: 'radar',
            data: {
                labels,
                datasets: [{
                    label: 'Sessions (21d)',
                    data,
                    backgroundColor: 'rgba(255, 77, 0, 0.15)',
                    borderColor: '#ff4d00',
                    borderWidth: 2,
                    pointBackgroundColor: '#ff4d00',
                    pointRadius: 3,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    r: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, color: '#888', backdropColor: 'transparent' },
                        grid: { color: '#2a2a2a' },
                        angleLines: { color: '#2a2a2a' },
                        pointLabels: { color: '#e8e8e8', font: { size: 11 } },
                    },
                },
            },
        });
    }

    // RPE Trend Line
    const rpeEl = document.getElementById('chart-rpe-trend');
    if (rpeEl && statsData.rpe_trend.length) {
        const labels = statsData.rpe_trend.map(r => {
            const d = new Date(r.date + 'T12:00:00');
            return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        });
        const data = statsData.rpe_trend.map(r => r.rpe);
        statsCharts.rpeTrend = new Chart(rpeEl, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'RPE',
                    data,
                    borderColor: '#ff4d00',
                    backgroundColor: 'rgba(255, 77, 0, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointBackgroundColor: '#ff4d00',
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { min: 1, max: 10, ticks: { stepSize: 1 }, grid: { color: '#2a2a2a' } },
                    x: { grid: { display: false } },
                },
            },
        });
    }

    // Volume per Week Bar
    const volEl = document.getElementById('chart-volume-week');
    if (volEl && statsData.volume_per_week.length) {
        const labels = statsData.volume_per_week.map(v => v.week_label);
        const data = statsData.volume_per_week.map(v => v.sessions);
        statsCharts.volumeWeek = new Chart(volEl, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Sessions',
                    data,
                    backgroundColor: 'rgba(255, 77, 0, 0.6)',
                    borderColor: '#ff4d00',
                    borderWidth: 1,
                    borderRadius: 4,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 }, grid: { color: '#2a2a2a' } },
                    x: { grid: { display: false } },
                },
            },
        });
    }
}

// ============================================================
// Workout Detail Modal
// ============================================================
function showWorkoutDetail(workout) {
    const wj = typeof workout.workout_json === 'string' ? JSON.parse(workout.workout_json) : (workout.workout_json || {});
    const d = new Date(workout.scheduled_date + 'T12:00:00');
    const dateStr = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    const isCustom = workout.is_custom || false;
    const details = isCustom ? '' : renderWorkoutDetails(wj);

    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';

    let statusBadge = workout.status
        ? `<span class="wod-tag badge-${workout.status.toLowerCase()}">${workout.status}</span>`
        : `<span class="wod-tag badge-${workout.time_period.toLowerCase()}">${workout.time_period}</span>`;
    let actionsHtml = '';

    if (workout.time_period === 'TODAY' && !workout.status) {
        // Today, not yet logged
        actionsHtml = `
            <div class="history-detail-actions">
                <button class="btn btn-primary" id="detail-log-btn">Log Workout</button>
                <button class="btn btn-secondary" id="detail-close">Close</button>
            </div>`;
    } else if (workout.status === 'COMPLETE') {
        actionsHtml = `
            <div class="history-detail-actions">
                <button class="btn btn-secondary btn-sm" id="detail-edit-log">Edit Log</button>
                <button class="btn btn-secondary btn-sm btn-danger-text" id="detail-mark-missed">Mark Missed</button>
                <button class="btn btn-secondary btn-sm" id="detail-close">Close</button>
            </div>`;
    } else if (workout.status === 'MISSED') {
        actionsHtml = `
            <div class="history-detail-actions">
                <button class="btn btn-primary btn-sm" id="detail-mark-complete">Mark Complete</button>
                <button class="btn btn-secondary btn-sm" id="detail-close">Close</button>
            </div>`;
    } else {
        // FUTURE or TODAY+COMPLETE (already logged today)
        actionsHtml = `
            <div class="history-detail-actions">
                <button class="btn btn-secondary" id="detail-close">Close</button>
            </div>`;
    }

    // Show log info if available
    let logInfo = '';
    if (workout.log) {
        const completedDate = new Date(workout.log.completed_at);
        const timeStr = completedDate.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
        logInfo = `<div class="detail-log-info">
            <span>RPE: ${workout.log.actual_rpe}</span>
            <span>Logged at ${timeStr}</span>
            ${workout.log.missed_reps > 0 ? `<span style="color:var(--red)">Missed: ${workout.log.missed_reps} reps</span>` : ''}
        </div>`;
        if (workout.log.notes) {
            logInfo += `<div class="history-detail-notes">${workout.log.notes}</div>`;
        }
    }

    const metaLine = isCustom
        ? `<span>${dateStr} — Custom Workout</span>`
        : `<span>${dateStr} — Week ${workout.program_week}, Day ${workout.day_index}</span>`;

    const customDescHtml = isCustom && (workout.custom_description || wj.custom_description)
        ? `<div class="card" style="margin:12px 0 0;text-align:left">
            <div class="wod-section">
                <div class="wod-section-title">Description</div>
                <div class="mobility-text">${(workout.custom_description || wj.custom_description || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
            </div>
            ${wj.summary && wj.summary !== (workout.custom_description || wj.custom_description) ? `<div class="wod-section" style="margin-top:12px"><div class="wod-section-title">AI Summary</div><div class="mobility-text">${wj.summary.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div></div>` : ''}
           </div>`
        : '';

    overlay.innerHTML = `
    <div class="readiness-modal">
        <div class="readiness-title">${workout.focus}</div>
        <div class="history-detail-meta">
            ${metaLine}
        </div>
        <div class="history-detail-stats">
            <span class="wod-tag tag-rpe">RPE ${workout.intensity_target_rpe}</span>
            <span class="wod-tag tag-cns-${workout.cns_load}">CNS ${workout.cns_load}</span>
            ${statusBadge}
        </div>
        ${isCustom ? customDescHtml : (details ? `<div class="card" style="margin:12px 0 0;text-align:left">${details}</div>` : '')}
        ${logInfo}
        ${actionsHtml}
    </div>`;

    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));

    const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
    document.getElementById('detail-close')?.addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

    // Log workout (TODAY)
    document.getElementById('detail-log-btn')?.addEventListener('click', () => {
        close();
        showLogModal(workout);
    });

    // Edit log (COMPLETE)
    document.getElementById('detail-edit-log')?.addEventListener('click', () => {
        close();
        showEditLogModal(workout);
    });

    // Mark as MISSED (remove log)
    document.getElementById('detail-mark-missed')?.addEventListener('click', async () => {
        try {
            await api(`/workouts/${workout.id}/log`, { method: 'DELETE' });
            close();
            allWorkouts = null;
            render();
        } catch (e) {
            alert('Failed to update: ' + e.message);
        }
    });

    // Mark as COMPLETE (add log)
    document.getElementById('detail-mark-complete')?.addEventListener('click', () => {
        close();
        showLogModal(workout);
    });
}

// ============================================================
// Log Workout Modal
// ============================================================
let selectedRpe = 7;

function showLogModal(workout) {
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
            await api(`/workouts/${workout.id}/log`, {
                method: 'POST',
                body: JSON.stringify({
                    actual_rpe: selectedRpe,
                    missed_reps: parseInt(document.getElementById('log-missed').value) || 0,
                    notes: document.getElementById('log-notes').value || null,
                    performance_json: {},
                }),
            });
            overlay.remove();
            allWorkouts = null;
            render();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
        }
    });
}

// ============================================================
// Edit Log Modal
// ============================================================
function showEditLogModal(workout) {
    const log = workout.log;
    if (!log) return;

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
            await api(`/logs/${log.log_id}`, {
                method: 'PUT',
                body: JSON.stringify({
                    actual_rpe: editRpe,
                    missed_reps: parseInt(document.getElementById('edit-missed').value) || 0,
                    notes: document.getElementById('edit-notes').value || null,
                    performance_json: {},
                }),
            });
            close();
            allWorkouts = null;
            render();
        } catch (e) {
            errEl.textContent = e.message;
            errEl.style.display = '';
        }
    });
}

// ============================================================
// Shared Workout Rendering
// ============================================================
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
    document.getElementById('config-edit-profile')?.addEventListener('click', () => {
        showEditProfileModal();
    });
    document.getElementById('config-logout')?.addEventListener('click', () => {
        showLogoutConfirm();
    });
    document.getElementById('config-settings')?.addEventListener('click', () => {
        showSettingsModal();
    });
}

function showEditProfileModal() {
    const u = currentUser;
    const isMetric = (u.unit_system || 'metric') === 'metric';
    let editUnits = u.unit_system || 'metric';

    // Convert stored metric values to display units
    const displayWeight = isMetric ? (u.weight_kg || '') : (u.weight_kg ? Math.round(u.weight_kg / 0.453592 * 10) / 10 : '');
    const displayHeight = isMetric ? (u.height_cm || '') : (u.height_cm ? Math.round(u.height_cm / 2.54 * 10) / 10 : '');
    const weightLabel = isMetric ? 'Weight (kg)' : 'Weight (lbs)';
    const heightLabel = isMetric ? 'Height (cm)' : 'Height (in)';

    const overlay = document.createElement('div');
    overlay.className = 'readiness-overlay';

    function renderEditForm() {
        const m = editUnits === 'metric';
        const wLabel = m ? 'Weight (kg)' : 'Weight (lbs)';
        const hLabel = m ? 'Height (cm)' : 'Height (in)';
        // Recalculate display values based on current editUnits
        const dw = m ? (u.weight_kg || '') : (u.weight_kg ? Math.round(u.weight_kg / 0.453592 * 10) / 10 : '');
        const dh = m ? (u.height_cm || '') : (u.height_cm ? Math.round(u.height_cm / 2.54 * 10) / 10 : '');

        return `
        <div class="readiness-modal">
            <div class="readiness-title">Edit Profile</div>
            <div id="edit-profile-error" class="error-msg" style="display:none"></div>
            <div id="edit-profile-success" class="success-msg" style="display:none"></div>
            <div class="form-group">
                <label class="form-label">Units</label>
                <div class="unit-toggle" id="edit-unit-toggle">
                    <button class="unit-toggle-btn ${m ? 'active' : ''}" data-unit="metric">Metric</button>
                    <button class="unit-toggle-btn ${!m ? 'active' : ''}" data-unit="imperial">Imperial</button>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">Username</label>
                <input class="form-input" id="edit-username" type="text" value="${u.username || ''}" autocapitalize="none">
            </div>
            <div class="form-group">
                <label class="form-label">New Password (leave blank to keep current)</label>
                <input class="form-input" id="edit-password" type="password" placeholder="Unchanged" autocomplete="new-password">
            </div>
            <div class="form-group">
                <label class="form-label">Name</label>
                <input class="form-input" id="edit-name" type="text" value="${u.name || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">Age</label>
                <input class="form-input" id="edit-age" type="number" min="10" max="100" value="${u.age || ''}">
            </div>
            <div class="form-group">
                <label class="form-label">${wLabel}</label>
                <input class="form-input" id="edit-weight" type="number" step="0.1" min="1" value="${dw}">
            </div>
            <div class="form-group">
                <label class="form-label">${hLabel}</label>
                <input class="form-input" id="edit-height" type="number" step="0.1" min="1" value="${dh}">
            </div>
            <div class="form-group">
                <label class="form-label">Sex</label>
                <select class="form-select" id="edit-sex">
                    <option value="male" ${u.sex === 'male' ? 'selected' : ''}>Male</option>
                    <option value="female" ${u.sex === 'female' ? 'selected' : ''}>Female</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Training Age (years)</label>
                <input class="form-input" id="edit-training-age" type="number" step="0.5" min="0" value="${u.training_age_yr || 0}">
            </div>
            <button class="btn btn-primary" id="edit-profile-save">Save Changes</button>
            <button class="btn btn-secondary" id="edit-profile-cancel" style="margin-top:8px">Cancel</button>
        </div>`;
    }

    overlay.innerHTML = renderEditForm();
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('active'));

    function bindEditForm() {
        const close = () => { overlay.classList.remove('active'); setTimeout(() => overlay.remove(), 200); };
        document.getElementById('edit-profile-cancel')?.addEventListener('click', close);
        overlay.addEventListener('click', e => { if (e.target === overlay) close(); });

        // Unit toggle inside modal
        overlay.querySelectorAll('#edit-unit-toggle .unit-toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Save current form values before re-render
                const savedUsername = document.getElementById('edit-username')?.value || '';
                const savedPassword = document.getElementById('edit-password')?.value || '';
                const savedName = document.getElementById('edit-name')?.value || '';
                const savedAge = document.getElementById('edit-age')?.value || '';
                const savedSex = document.getElementById('edit-sex')?.value || 'male';
                const savedTraining = document.getElementById('edit-training-age')?.value || '0';

                editUnits = btn.dataset.unit;
                overlay.innerHTML = renderEditForm();
                bindEditForm();

                // Restore non-unit fields
                document.getElementById('edit-username').value = savedUsername;
                document.getElementById('edit-password').value = savedPassword;
                document.getElementById('edit-name').value = savedName;
                document.getElementById('edit-age').value = savedAge;
                document.getElementById('edit-sex').value = savedSex;
                document.getElementById('edit-training-age').value = savedTraining;
            });
        });

        document.getElementById('edit-profile-save')?.addEventListener('click', async () => {
            const errEl = document.getElementById('edit-profile-error');
            const successEl = document.getElementById('edit-profile-success');
            errEl.style.display = 'none';
            successEl.style.display = 'none';

            try {
                const body = {};

                const newUsername = document.getElementById('edit-username').value.trim();
                if (newUsername && newUsername !== u.username) body.username = newUsername;

                const newPassword = document.getElementById('edit-password').value;
                if (newPassword) body.password = newPassword;

                const newName = document.getElementById('edit-name').value.trim();
                if (newName && newName !== u.name) body.name = newName;

                const newAge = parseInt(document.getElementById('edit-age').value);
                if (!isNaN(newAge) && newAge !== u.age) body.age = newAge;

                const newSex = document.getElementById('edit-sex').value;
                if (newSex !== u.sex) body.sex = newSex;

                const newTraining = parseFloat(document.getElementById('edit-training-age').value);
                if (!isNaN(newTraining) && newTraining !== u.training_age_yr) body.training_age_yr = newTraining;

                if (editUnits !== (u.unit_system || 'metric')) body.unit_system = editUnits;

                // Weight & height: convert from display units to metric for storage
                let newWeight = parseFloat(document.getElementById('edit-weight').value);
                if (!isNaN(newWeight)) {
                    if (editUnits === 'imperial') newWeight = newWeight * 0.453592;
                    newWeight = Math.round(newWeight * 10) / 10;
                    if (newWeight !== u.weight_kg) body.weight_kg = newWeight;
                }

                let newHeight = parseFloat(document.getElementById('edit-height').value);
                if (!isNaN(newHeight)) {
                    if (editUnits === 'imperial') newHeight = newHeight * 2.54;
                    newHeight = Math.round(newHeight * 10) / 10;
                    if (newHeight !== u.height_cm) body.height_cm = newHeight;
                }

                if (Object.keys(body).length === 0) {
                    errEl.textContent = 'No changes to save';
                    errEl.style.display = '';
                    return;
                }

                await api('/auth/profile', { method: 'PUT', body: JSON.stringify(body) });

                successEl.textContent = 'Profile updated';
                successEl.style.display = '';

                // Refresh user data
                currentUser = await api('/auth/me');
                // Update local reference
                Object.assign(u, currentUser);

                // Auto-close after a moment
                setTimeout(close, 800);
            } catch (e) {
                errEl.textContent = e.message;
                errEl.style.display = '';
            }
        });
    }

    bindEditForm();
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

                listEl.querySelectorAll('.llm-option').forEach(o => o.style.pointerEvents = 'none');
                statusEl.style.display = '';
                statusEl.style.color = 'var(--text-dim)';
                statusEl.textContent = 'Testing connection...';

                try {
                    const result = await api(`/settings/llm/${providerId}`, { method: 'POST' });
                    if (result.ok) {
                        statusEl.style.color = 'var(--green)';
                        statusEl.textContent = `AI ${result.name} Enabled`;
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
    allWorkouts = null;
    render();
});
