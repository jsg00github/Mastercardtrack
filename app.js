/* ==========================================
   CardTrack - Full Application Logic
   Spanish (Argentinian) Version with API
   ========================================== */

// API Configuration
const API_BASE = window.location.origin + '/api';

// State Management
const state = {
    token: localStorage.getItem('cardtrack_token'),
    user: null,
    categories: [],
    transactions: [],
    statements: [],
    analytics: null,
    currentTab: 'upload',
    editingCategory: null,
    // Filter state - null means show all
    currency: null,  // null = all, 'ars' or 'usd'
    selectedMonth: null,
    selectedYear: null,
    period: 'month',  // 'month', 'quarter', 'year'
    // Transaction filter state
    txCurrency: null,  // null = all
    txMonth: null,
    txYear: null
};

// DOM Elements
const elements = {
    // Auth
    authModal: document.getElementById('authModal'),
    loginForm: document.getElementById('loginForm'),
    registerForm: document.getElementById('registerForm'),
    loginUsername: document.getElementById('loginUsername'),
    loginPassword: document.getElementById('loginPassword'),
    loginBtn: document.getElementById('loginBtn'),
    registerEmail: document.getElementById('registerEmail'),
    registerUsername: document.getElementById('registerUsername'),
    registerPassword: document.getElementById('registerPassword'),
    registerBtn: document.getElementById('registerBtn'),
    showRegister: document.getElementById('showRegister'),
    showLogin: document.getElementById('showLogin'),
    authError: document.getElementById('authError'),

    // App
    appContainer: document.getElementById('appContainer'),
    userName: document.getElementById('userName'),
    logoutBtn: document.getElementById('logoutBtn'),

    // Navigation
    navTabs: document.querySelectorAll('.nav-tab'),
    tabContents: document.querySelectorAll('.tab-content'),

    // Upload
    uploadArea: document.getElementById('uploadArea'),
    fileInput: document.getElementById('fileInput'),
    uploadProgress: document.getElementById('uploadProgress'),
    progressFill: document.getElementById('progressFill'),
    progressPercent: document.getElementById('progressPercent'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    progressStatus: document.getElementById('progressStatus'),
    processingCard: document.getElementById('processingCard'),
    uploadResult: document.getElementById('uploadResult'),
    resultMessage: document.getElementById('resultMessage'),
    goToDashboard: document.getElementById('goToDashboard'),

    // Dashboard
    totalSpending: document.getElementById('totalSpending'),
    totalTransactions: document.getElementById('totalTransactions'),
    avgTransaction: document.getElementById('avgTransaction'),
    topCategory: document.getElementById('topCategory'),
    topCategoryAmount: document.getElementById('topCategoryAmount'),
    donutTotal: document.getElementById('donutTotal'),
    breakdownList: document.getElementById('breakdownList'),
    dateButtons: document.querySelectorAll('.date-btn'),
    downloadPdf: document.getElementById('downloadPdf'),
    dashboardContent: document.getElementById('dashboardContent'),

    // Transactions
    searchInput: document.getElementById('searchInput'),
    categoryFilter: document.getElementById('categoryFilter'),
    sortFilter: document.getElementById('sortFilter'),
    transactionsList: document.getElementById('transactionsList'),
    emptyTransactions: document.getElementById('emptyTransactions'),
    loadingTransactions: document.getElementById('loadingTransactions'),
    goToUpload: document.getElementById('goToUpload'),

    // Analytics
    recommendationsList: document.getElementById('recommendationsList'),
    emptyRecommendations: document.getElementById('emptyRecommendations'),

    // Categories
    categoriesList: document.getElementById('categoriesList'),
    addCategoryBtn: document.getElementById('addCategoryBtn'),
    categoryModal: document.getElementById('categoryModal'),
    categoryModalTitle: document.getElementById('categoryModalTitle'),
    categoryName: document.getElementById('categoryName'),
    categoryIcon: document.getElementById('categoryIcon'),
    categoryColor: document.getElementById('categoryColor'),
    colorPreview: document.getElementById('colorPreview'),
    closeCategoryModal: document.getElementById('closeCategoryModal'),
    cancelCategory: document.getElementById('cancelCategory'),
    saveCategory: document.getElementById('saveCategory'),

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage'),

    // Date Banner
    dateBanner: document.getElementById('dateBanner'),
    proximoCierre: document.getElementById('proximoCierre'),
    proximoVencimiento: document.getElementById('proximoVencimiento'),

    // Statements
    statementsContainer: document.getElementById('statementsContainer'),
    noStatements: document.getElementById('noStatements'),

    // Dashboard Filters
    currencyToggle: document.getElementById('currencyToggle'),
    monthFilter: document.getElementById('monthFilter'),
    yearFilter: document.getElementById('yearFilter'),
    quarterBtn: document.getElementById('quarterBtn'),

    // Transaction Filters
    txCurrencyToggle: document.getElementById('txCurrencyToggle'),
    txMonthFilter: document.getElementById('txMonthFilter'),
    txYearFilter: document.getElementById('txYearFilter')
};

// Chart instances
let barChart = null;
let donutChart = null;
let trendChart = null;

// ============ Helper Functions ============

function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatCurrency(amount, isDollar = false) {
    if (amount === null || amount === undefined) return '$0';
    const formatted = formatNumber(amount);
    return isDollar ? `U$${formatted}` : `$${formatted}`;
}

// ============ API Functions ============

async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    // Debug: Log token status
    console.log(`[API] ${endpoint} - Token present: ${!!state.token}`);

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        // Debug: Log response status
        console.log(`[API] ${endpoint} - Response: ${response.status}`);

        if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/register')) {
            console.log('[API] 401 received, logging out');
            logout();
            throw new Error('Sesión expirada');
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Error en la solicitud');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// ============ Authentication ============

async function login() {
    const username = elements.loginUsername.value.trim();
    const password = elements.loginPassword.value;

    if (!username || !password) {
        showAuthError('Completá todos los campos');
        return;
    }

    elements.loginBtn.disabled = true;
    elements.loginBtn.textContent = 'Ingresando...';

    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        console.log('[Login] Response data:', data);
        console.log('[Login] access_token present:', !!data.access_token);

        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('cardtrack_token', data.access_token);

        console.log('[Login] state.token set to:', state.token ? 'TOKEN_PRESENT' : 'NO_TOKEN');

        await showApp();
    } catch (error) {
        showAuthError(error.message);
    } finally {
        elements.loginBtn.disabled = false;
        elements.loginBtn.textContent = 'Ingresar';
    }
}

async function register() {
    const email = elements.registerEmail.value.trim();
    const username = elements.registerUsername.value.trim();
    const password = elements.registerPassword.value;

    if (!email || !username || !password) {
        showAuthError('Completá todos los campos');
        return;
    }

    if (password.length < 6) {
        showAuthError('La contraseña debe tener al menos 6 caracteres');
        return;
    }

    elements.registerBtn.disabled = true;
    elements.registerBtn.textContent = 'Creando cuenta...';

    try {
        const data = await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ email, username, password })
        });

        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('cardtrack_token', data.access_token);

        showApp();
    } catch (error) {
        showAuthError(error.message);
    } finally {
        elements.registerBtn.disabled = false;
        elements.registerBtn.textContent = 'Crear Cuenta';
    }
}

function logout() {
    state.token = null;
    state.user = null;
    state.categories = [];
    state.transactions = [];
    localStorage.removeItem('cardtrack_token');

    elements.appContainer.classList.add('hidden');
    elements.authModal.classList.remove('hidden');
    elements.loginForm.classList.remove('hidden');
    elements.registerForm.classList.add('hidden');

    // Clear form fields
    elements.loginUsername.value = '';
    elements.loginPassword.value = '';
    elements.registerEmail.value = '';
    elements.registerUsername.value = '';
    elements.registerPassword.value = '';
}

function showAuthError(message) {
    elements.authError.textContent = message;
    elements.authError.classList.remove('hidden');
    setTimeout(() => {
        elements.authError.classList.add('hidden');
    }, 5000);
}

async function checkAuth() {
    if (!state.token) {
        elements.authModal.classList.remove('hidden');
        return;
    }

    try {
        const user = await apiRequest('/auth/me');
        state.user = user;
        showApp();
    } catch (error) {
        logout();
    }
}

async function showApp() {
    elements.authModal.classList.add('hidden');
    elements.appContainer.classList.remove('hidden');
    elements.userName.textContent = state.user?.username || '';

    // Load initial data
    await loadCategories();
    await loadStatements();
    await loadLatestDates();
    await loadAvailablePeriods();
    initCharts();
}

// ============ Categories ============

async function loadCategories() {
    try {
        state.categories = await apiRequest('/categories');
        renderCategories();
        updateCategoryFilter();
    } catch (error) {
        showToast('Error al cargar categorías', 'error');
    }
}

function renderCategories() {
    if (!elements.categoriesList) return;

    elements.categoriesList.innerHTML = state.categories.map(cat => `
        <div class="category-card" data-id="${cat.id}">
            <div class="category-icon-display" style="background: ${cat.color}20;">
                ${cat.icon}
            </div>
            <div class="category-info">
                <div class="category-name">${cat.name}</div>
                <div class="category-stats">${cat.is_default ? 'Predeterminada' : 'Personalizada'}</div>
            </div>
            <div class="category-actions">
                <button class="edit-category" title="Editar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="delete delete-category" title="Eliminar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        </div>
    `).join('');

    // Add event listeners
    elements.categoriesList.querySelectorAll('.edit-category').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.category-card');
            const id = parseInt(card.dataset.id);
            openCategoryModal(id);
        });
    });

    elements.categoriesList.querySelectorAll('.delete-category').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.category-card');
            const id = parseInt(card.dataset.id);
            deleteCategory(id);
        });
    });
}

function updateCategoryFilter() {
    if (!elements.categoryFilter) return;

    elements.categoryFilter.innerHTML = `
        <option value="">Todas las Categorías</option>
        ${state.categories.map(cat => `
            <option value="${cat.id}">${cat.icon} ${cat.name}</option>
        `).join('')}
    `;
}

function openCategoryModal(categoryId = null) {
    state.editingCategory = categoryId;

    if (categoryId) {
        const cat = state.categories.find(c => c.id === categoryId);
        if (cat) {
            elements.categoryModalTitle.textContent = 'Editar Categoría';
            elements.categoryName.value = cat.name;
            elements.categoryIcon.value = cat.icon;
            elements.categoryColor.value = cat.color;
            elements.colorPreview.style.background = cat.color;
        }
    } else {
        elements.categoryModalTitle.textContent = 'Nueva Categoría';
        elements.categoryName.value = '';
        elements.categoryIcon.value = '📦';
        elements.categoryColor.value = '#00f0ff';
        elements.colorPreview.style.background = '#00f0ff';
    }

    elements.categoryModal.classList.remove('hidden');
}

function closeCategoryModal() {
    elements.categoryModal.classList.add('hidden');
    state.editingCategory = null;
}

async function saveCategory() {
    const name = elements.categoryName.value.trim();
    const icon = elements.categoryIcon.value.trim() || '📦';
    const color = elements.categoryColor.value;

    if (!name) {
        showToast('Ingresá un nombre para la categoría', 'error');
        return;
    }

    try {
        if (state.editingCategory) {
            await apiRequest(`/categories/${state.editingCategory}`, {
                method: 'PUT',
                body: JSON.stringify({ name, icon, color })
            });
            showToast('Categoría actualizada', 'success');
        } else {
            await apiRequest('/categories', {
                method: 'POST',
                body: JSON.stringify({ name, icon, color })
            });
            showToast('Categoría creada', 'success');
        }

        closeCategoryModal();
        await loadCategories();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteCategory(id) {
    if (!confirm('¿Seguro que querés eliminar esta categoría?')) return;

    try {
        await apiRequest(`/categories/${id}`, { method: 'DELETE' });
        showToast('Categoría eliminada', 'success');
        await loadCategories();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ============ Transactions ============

async function loadTransactions() {
    elements.loadingTransactions?.classList.remove('hidden');
    elements.transactionsList.innerHTML = '';
    elements.emptyTransactions?.classList.add('hidden');

    try {
        const categoryId = elements.categoryFilter?.value || '';
        const search = elements.searchInput?.value || '';

        // Build query params from filter state
        const params = new URLSearchParams();
        params.set('limit', '100');
        // Only filter by currency if explicitly selected
        if (state.txCurrency) {
            params.set('is_dollar', state.txCurrency === 'usd');
        }
        if (categoryId) params.set('category_id', categoryId);
        if (search) params.set('search', search);
        if (state.txMonth) params.set('month', state.txMonth);
        if (state.txYear) params.set('year', state.txYear);

        state.transactions = await apiRequest(`/transactions?${params.toString()}`);
        renderTransactions();
    } catch (error) {
        showToast('Error al cargar transacciones', 'error');
    } finally {
        elements.loadingTransactions?.classList.add('hidden');
    }
}

function renderTransactions() {
    let transactions = [...state.transactions];

    // Sort
    const sortValue = elements.sortFilter?.value || 'date-desc';
    switch (sortValue) {
        case 'date-desc':
            transactions.sort((a, b) => new Date(b.date) - new Date(a.date));
            break;
        case 'date-asc':
            transactions.sort((a, b) => new Date(a.date) - new Date(b.date));
            break;
        case 'amount-desc':
            transactions.sort((a, b) => b.amount - a.amount);
            break;
        case 'amount-asc':
            transactions.sort((a, b) => a.amount - b.amount);
            break;
    }

    if (transactions.length === 0) {
        elements.transactionsList.innerHTML = '';
        elements.emptyTransactions?.classList.remove('hidden');
        return;
    }

    elements.emptyTransactions?.classList.add('hidden');

    // Build category options HTML
    const categoryOptions = state.categories.map(c =>
        `<option value="${c.id}" data-icon="${c.icon}">${c.icon} ${c.name}</option>`
    ).join('');

    elements.transactionsList.innerHTML = transactions.map(t => {
        const cat = t.category || { id: null, name: 'Sin categoría', icon: '📦', color: '#778899' };
        const currencySymbol = t.is_dollar ? 'U$' : '$';

        return `
            <div class="transaction-item" data-id="${t.id}">
                <div class="transaction-left">
                    <div class="transaction-icon" style="background: ${cat.color}20;">
                        ${cat.icon}
                    </div>
                    <div class="transaction-details">
                        <span class="transaction-name">${t.merchant}</span>
                        <select class="category-select" data-transaction-id="${t.id}" onchange="updateTransactionCategory(${t.id}, this.value)">
                            ${state.categories.map(c =>
            `<option value="${c.id}" ${c.id === cat.id ? 'selected' : ''}>${c.icon} ${c.name}</option>`
        ).join('')}
                        </select>
                    </div>
                </div>
                <div class="transaction-right">
                    <span class="transaction-amount">-${currencySymbol}${formatNumber(t.amount)}</span>
                    <span class="transaction-date">${formatDate(t.date)}</span>
                    ${t.statement ? `<span class="statement-badge" title="Pertenece al resumen de ${MONTH_NAMES[t.statement.month - 1]}">🧾 ${MONTH_NAMES[t.statement.month - 1].substring(0, 3)}</span>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Update transaction category
async function updateTransactionCategory(transactionId, categoryId) {
    try {
        await apiRequest(`/transactions/${transactionId}`, {
            method: 'PATCH',
            body: JSON.stringify({ category_id: parseInt(categoryId) })
        });
        showToast('Categoría actualizada', 'success');
        // Reload analytics to reflect changes
        loadAnalytics();
    } catch (error) {
        showToast('Error al actualizar categoría', 'error');
        console.error('Error updating transaction category:', error);
    }
}

// ============ Analytics ============

async function loadAnalytics() {
    try {
        // Build query params from filter state
        const params = new URLSearchParams();
        params.set('period', state.period);
        // Only filter by currency if explicitly selected
        if (state.currency) {
            params.set('is_dollar', state.currency === 'usd');
        }
        if (state.selectedMonth) params.set('month', state.selectedMonth);
        if (state.selectedYear) params.set('year', state.selectedYear);

        state.analytics = await apiRequest(`/analytics?${params.toString()}`);
        updateDashboard();
        updateCharts();
        renderRecommendations();

        // Also update trend chart
        loadTrendData();
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function updateDashboard() {
    if (!state.analytics) return;

    const { total_spending, total_ars, total_usd, total_unified, dolar_rate, transaction_count, average_transaction, category_breakdown } = state.analytics;

    // Show unified total when viewing all currencies, otherwise show the filtered total
    let displayTotal;
    if (state.currency === null) {
        // "Todos" selected - show unified total (ARS + USD converted)
        displayTotal = total_unified > 0 ? total_unified : total_spending;
    } else {
        displayTotal = total_spending;
    }

    elements.totalSpending.textContent = formatCurrency(displayTotal);
    elements.totalTransactions.textContent = transaction_count.toLocaleString();
    elements.avgTransaction.textContent = formatCurrency(average_transaction);
    elements.donutTotal.textContent = formatCurrency(displayTotal);

    // Top category
    if (category_breakdown.length > 0) {
        const top = category_breakdown[0];
        elements.topCategory.textContent = `${top.category_icon} ${top.category_name}`;
        elements.topCategoryAmount.textContent = `${formatCurrency(top.total)} gastados`;
    } else {
        elements.topCategory.textContent = '-';
        elements.topCategoryAmount.textContent = 'Sin datos';
    }

    // Breakdown
    renderBreakdown(category_breakdown, total_spending);
}

function renderBreakdown(categoryBreakdown, totalSpending) {
    if (!elements.breakdownList) return;

    if (categoryBreakdown.length === 0) {
        elements.breakdownList.innerHTML = `
            <p style="color: var(--text-muted); text-align: center; padding: 2rem;">
                No hay datos para mostrar en este período
            </p>
        `;
        return;
    }

    elements.breakdownList.innerHTML = categoryBreakdown.map(cat => `
        <div class="breakdown-item">
            <div class="breakdown-icon" style="background: ${cat.category_color}20;">
                ${cat.category_icon}
            </div>
            <div class="breakdown-info">
                <div class="breakdown-name">${cat.category_name}</div>
                <div class="breakdown-count">${cat.count} transacci${cat.count !== 1 ? 'ones' : 'ón'}</div>
                <div class="breakdown-bar">
                    <div class="breakdown-fill" style="width: ${cat.percentage}%; background: ${cat.category_color};"></div>
                </div>
            </div>
            <div>
                <div class="breakdown-amount" style="color: ${cat.category_color};">${formatCurrency(cat.total)}</div>
                <div class="breakdown-percent">${cat.percentage.toFixed(1)}%</div>
            </div>
        </div>
    `).join('');
}

function renderRecommendations() {
    if (!elements.recommendationsList || !state.analytics) return;

    const { recommendations } = state.analytics;

    if (recommendations.length === 0) {
        elements.recommendationsList.innerHTML = '';
        elements.emptyRecommendations?.classList.remove('hidden');
        return;
    }

    elements.emptyRecommendations?.classList.add('hidden');

    const typeLabels = {
        warning: 'Atención',
        tip: 'Consejo',
        success: 'Logro',
        info: 'Info'
    };

    elements.recommendationsList.innerHTML = recommendations.map(rec => `
        <div class="recommendation-card ${rec.type}">
            <div class="recommendation-icon">${rec.icon}</div>
            <div class="recommendation-content">
                <div class="recommendation-type">${typeLabels[rec.type] || rec.type}</div>
                <div class="recommendation-message">${rec.message}</div>
            </div>
        </div>
    `).join('');
}

// ============ Charts ============

function initCharts() {
    Chart.defaults.color = '#a0a0b0';
    Chart.defaults.font.family = "'Inter', sans-serif";

    // Bar Chart
    const barCtx = document.getElementById('barChart')?.getContext('2d');
    if (barCtx) {
        barChart = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Gastos',
                    data: [],
                    backgroundColor: [],
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(20, 20, 35, 0.95)',
                        borderColor: 'rgba(0, 240, 255, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: (ctx) => formatCurrency(ctx.raw)
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { callback: (value) => '$' + value }
                    }
                }
            }
        });
    }

    // Donut Chart with external labels
    const donutCtx = document.getElementById('donutChart')?.getContext('2d');
    if (donutCtx) {
        donutChart = new Chart(donutCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [],
                    borderWidth: 0,
                    hoverOffset: 15
                }]
            },
            plugins: [ChartDataLabels],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                layout: {
                    padding: {
                        top: 30,
                        bottom: 30,
                        left: 80,
                        right: 80
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(20, 20, 35, 0.95)',
                        borderColor: 'rgba(0, 240, 255, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {
                            label: (ctx) => {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const percent = ((ctx.raw / total) * 100).toFixed(1);
                                return `${formatCurrency(ctx.raw)} (${percent}%)`;
                            }
                        }
                    },
                    datalabels: {
                        color: '#fff',
                        font: {
                            size: 11,
                            weight: '600'
                        },
                        anchor: 'end',
                        align: 'end',
                        offset: 10,
                        formatter: (value, ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const percent = ((value / total) * 100).toFixed(0);
                            if (percent < 5) return ''; // Hide small segments
                            const label = ctx.chart.data.labels[ctx.dataIndex];
                            return `${label}\n${percent}%`;
                        },
                        textAlign: 'center',
                        display: (ctx) => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const percent = (ctx.dataset.data[ctx.dataIndex] / total) * 100;
                            return percent >= 5; // Only show labels for segments >= 5%
                        }
                    }
                }
            }
        });
    }

    // Trend Chart
    const trendCtx = document.getElementById('trendChart')?.getContext('2d');
    if (trendCtx) {
        trendChart = new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Gasto Diario',
                    data: [],
                    fill: true,
                    backgroundColor: 'rgba(0, 240, 255, 0.1)',
                    borderColor: '#00f0ff',
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#00f0ff',
                    pointBorderColor: '#0a0a0f',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(20, 20, 35, 0.95)',
                        borderColor: 'rgba(0, 240, 255, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        displayColors: false,
                        callbacks: {
                            label: (ctx) => formatCurrency(ctx.raw)
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { callback: (value) => '$' + value }
                    }
                }
            }
        });
    }
}

function updateCharts() {
    if (!state.analytics) return;

    const { category_breakdown } = state.analytics;

    // Update Bar Chart
    if (barChart) {
        barChart.data.labels = category_breakdown.map(c => c.category_name);
        barChart.data.datasets[0].data = category_breakdown.map(c => Math.round(c.total));
        barChart.data.datasets[0].backgroundColor = category_breakdown.map(c => c.category_color);
        barChart.update('none');
    }

    // Update Donut Chart
    if (donutChart) {
        donutChart.data.labels = category_breakdown.map(c => c.category_name);
        donutChart.data.datasets[0].data = category_breakdown.map(c => Math.round(c.total));
        donutChart.data.datasets[0].backgroundColor = category_breakdown.map(c => c.category_color);
        donutChart.update('none');
    }

    // Load trend data
    loadTrendData();
}

async function loadTrendData() {
    try {
        // Build query params from filter state
        const params = new URLSearchParams();
        params.set('period', state.period);
        // Only filter by currency if explicitly selected
        if (state.currency) {
            params.set('is_dollar', state.currency === 'usd');
        }
        if (state.selectedMonth) params.set('month', state.selectedMonth);
        if (state.selectedYear) params.set('year', state.selectedYear);

        const trend = await apiRequest(`/analytics/trend?${params.toString()}`);

        if (trendChart && trend.length > 0) {
            trendChart.data.labels = trend.map(d => d.date);
            trendChart.data.datasets[0].data = trend.map(d => Math.round(d.total));
            trendChart.update('none');
        }
    } catch (error) {
        console.error('Error loading trend:', error);
    }
}

// ============ File Upload ============

async function uploadFile(file) {
    const validTypes = ['application/pdf', 'text/csv', 'image/png', 'image/jpeg'];

    if (!validTypes.includes(file.type) && !file.name.endsWith('.csv')) {
        showToast('Subí un archivo PDF, CSV o imagen', 'error');
        return;
    }

    // Validate dolar rate is entered
    const dolarRateInput = document.getElementById('dolarRateInput');
    const dolarRate = parseFloat(dolarRateInput?.value) || 0;
    if (dolarRate <= 0) {
        showToast('⚠️ Ingresá la cotización del dólar tarjeta antes de subir', 'error');
        dolarRateInput?.focus();
        return;
    }

    // Show progress
    elements.uploadArea.classList.add('hidden');
    elements.uploadProgress.classList.remove('hidden');
    elements.fileName.textContent = file.name;
    elements.fileSize.textContent = formatFileSize(file.size);

    // Simulate progress
    await simulateProgress();

    // Show processing
    elements.uploadProgress.classList.add('hidden');
    elements.processingCard.classList.remove('hidden');

    // Process steps animation
    await simulateProcessing();

    // Upload to API
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('dolar_rate', dolarRate); // Use the validated value from above

        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${state.token}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Error al procesar el archivo');
        }

        const result = await response.json();

        // Show success
        elements.processingCard.classList.add('hidden');
        elements.uploadResult.classList.remove('hidden');
        elements.resultMessage.textContent = `Se importaron ${result.transactions_imported} transacciones (${formatCurrency(result.total_amount)})`;

        // Reload data
        await loadTransactions();
        await loadAnalytics();
        await loadStatements();
        await loadLatestDates();
        await loadAvailablePeriods();

    } catch (error) {
        showToast(error.message, 'error');
        resetUploadUI();
    }
}

function simulateProgress() {
    return new Promise(resolve => {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                resolve();
            }
            elements.progressFill.style.width = `${progress}%`;
            elements.progressPercent.textContent = `${Math.round(progress)}%`;
        }, 100);
    });
}

function simulateProcessing() {
    const steps = ['step1', 'step2', 'step3', 'step4'];
    const messages = ['Leyendo archivo...', 'Extrayendo datos...', 'Categorizando...', 'Finalizando...'];

    return new Promise(resolve => {
        let current = 0;

        const interval = setInterval(() => {
            if (current > 0) {
                document.getElementById(steps[current - 1])?.classList.add('completed');
                document.getElementById(steps[current - 1])?.classList.remove('active');
            }

            if (current < steps.length) {
                document.getElementById(steps[current])?.classList.add('active');
                document.getElementById('processingStep').textContent = messages[current];
                current++;
            } else {
                clearInterval(interval);
                steps.forEach(s => {
                    document.getElementById(s)?.classList.remove('active', 'completed');
                });
                document.getElementById('step1')?.classList.add('active');
                resolve();
            }
        }, 600);
    });
}

function resetUploadUI() {
    elements.uploadArea.classList.remove('hidden');
    elements.uploadProgress.classList.add('hidden');
    elements.processingCard.classList.add('hidden');
    elements.uploadResult.classList.add('hidden');
    elements.progressFill.style.width = '0%';
    elements.progressPercent.textContent = '0%';
    elements.fileInput.value = '';
}

// ============ PDF Export ============

function downloadPDF() {
    const element = elements.dashboardContent;

    showToast('Generando PDF...', 'info');

    const opt = {
        margin: 10,
        filename: `CardTrack_Dashboard_${new Date().toISOString().split('T')[0]}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true, backgroundColor: '#0a0a0f' },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    html2pdf().set(opt).from(element).save().then(() => {
        showToast('PDF descargado', 'success');
    });
}

// ============ Navigation ============

function switchTab(tabName) {
    state.currentTab = tabName;

    elements.navTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-section`);
    });

    // Load data for specific tabs
    if (tabName === 'dashboard') {
        loadAnalytics(getSelectedPeriod());
    } else if (tabName === 'transactions') {
        loadTransactions();
    } else if (tabName === 'analytics') {
        loadAnalytics(getSelectedPeriod());
    } else if (tabName === 'categories') {
        loadCategories();
    }
}

function getSelectedPeriod() {
    const activeBtn = document.querySelector('.date-btn.active');
    return activeBtn?.dataset.range || 'month';
}

// ============ Utilities ============

function formatCurrency(amount) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('es-AR', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showToast(message, type = 'success') {
    elements.toast.className = `toast ${type}`;
    elements.toastMessage.textContent = message;
    elements.toast.classList.remove('hidden');

    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}

// ============ Event Listeners ============

function setupEventListeners() {
    // Auth
    elements.loginBtn?.addEventListener('click', login);
    elements.registerBtn?.addEventListener('click', register);

    elements.loginPassword?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });

    elements.registerPassword?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') register();
    });

    elements.showRegister?.addEventListener('click', (e) => {
        e.preventDefault();
        elements.loginForm.classList.add('hidden');
        elements.registerForm.classList.remove('hidden');
        elements.authError.classList.add('hidden');
    });

    elements.showLogin?.addEventListener('click', (e) => {
        e.preventDefault();
        elements.registerForm.classList.add('hidden');
        elements.loginForm.classList.remove('hidden');
        elements.authError.classList.add('hidden');
    });

    elements.logoutBtn?.addEventListener('click', logout);

    // Navigation
    elements.navTabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Upload
    elements.uploadArea?.addEventListener('click', () => elements.fileInput.click());
    elements.uploadArea?.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadArea.classList.add('drag-over');
    });
    elements.uploadArea?.addEventListener('dragleave', () => {
        elements.uploadArea.classList.remove('drag-over');
    });
    elements.uploadArea?.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadArea.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });
    elements.fileInput?.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            uploadFile(e.target.files[0]);
        }
    });

    elements.goToDashboard?.addEventListener('click', () => {
        resetUploadUI();
        switchTab('dashboard');
    });

    elements.goToUpload?.addEventListener('click', () => switchTab('upload'));

    // Dashboard
    elements.dateButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            elements.dateButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadAnalytics(btn.dataset.range);
        });
    });

    elements.downloadPdf?.addEventListener('click', downloadPDF);

    // Transactions filters
    elements.categoryFilter?.addEventListener('change', loadTransactions);
    elements.sortFilter?.addEventListener('change', renderTransactions);
    elements.searchInput?.addEventListener('input', debounce(loadTransactions, 300));

    // Categories
    elements.addCategoryBtn?.addEventListener('click', () => openCategoryModal());
    elements.closeCategoryModal?.addEventListener('click', closeCategoryModal);
    elements.cancelCategory?.addEventListener('click', closeCategoryModal);
    elements.saveCategory?.addEventListener('click', saveCategory);

    elements.categoryColor?.addEventListener('input', (e) => {
        elements.colorPreview.style.background = e.target.value;
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============ Statements ============

const MONTH_NAMES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

async function loadStatements() {
    try {
        state.statements = await apiRequest('/statements');
        renderStatements();
    } catch (error) {
        console.error('Error loading statements:', error);
        state.statements = [];
    }
}

function renderStatements() {
    if (!elements.statementsContainer) {
        console.error('statementsContainer not found');
        return;
    }

    if (!state.statements || state.statements.length === 0) {
        elements.noStatements?.classList.remove('hidden');
        // Clear any existing cards
        const cards = elements.statementsContainer.querySelectorAll('.statement-card');
        cards.forEach(card => card.remove());
        return;
    }

    elements.noStatements?.classList.add('hidden');

    // Clear existing cards
    const existingCards = elements.statementsContainer.querySelectorAll('.statement-card');
    existingCards.forEach(card => card.remove());

    // Create statement cards
    state.statements.forEach(statement => {
        const card = document.createElement('div');
        card.className = 'statement-card';
        card.dataset.statementId = statement.id;

        const monthName = MONTH_NAMES[statement.month - 1] || 'Mes';

        card.innerHTML = `
            <div class="statement-info">
                <div class="statement-title">${monthName} ${statement.year}</div>
                <div class="statement-meta">
                    <span class="pesos">$${formatNumber(statement.total_pesos)} ARS</span>
                    <span class="dollars">$${statement.total_dollars.toFixed(2)} USD</span>
                    <span class="count">${statement.transaction_count} txs</span>
                    ${statement.dolar_rate > 0 ? `<span class="dolar-rate">💲 TC: $${formatNumber(statement.dolar_rate)}</span>` : ''}
                    <span class="date-uploaded">📅 Subido: ${new Date(statement.created_at).toLocaleDateString('es-AR')}</span>
                </div>
            </div>
            <div class="statement-actions">
                <button class="btn-delete" onclick="deleteStatement(${statement.id})" title="Eliminar resumen">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;

        elements.statementsContainer.appendChild(card);
    });
}

async function deleteStatement(statementId) {
    if (!confirm('¿Estás seguro de eliminar este resumen y todas sus transacciones?')) {
        return;
    }

    try {
        await apiRequest(`/statements/${statementId}`, { method: 'DELETE' });
        showToast('Resumen eliminado correctamente', 'success');

        // Reload data
        await loadStatements();
        await loadLatestDates();
        await loadTransactions();
        await loadAnalytics();
    } catch (error) {
        showToast('Error al eliminar: ' + error.message, 'error');
    }
}

async function loadLatestDates() {
    try {
        const dates = await apiRequest('/statements/latest-dates');

        if (dates.proximo_cierre || dates.proximo_vencimiento) {
            elements.dateBanner?.classList.remove('hidden');

            if (dates.proximo_cierre && elements.proximoCierre) {
                elements.proximoCierre.textContent = formatDate(dates.proximo_cierre);
            }
            if (dates.proximo_vencimiento && elements.proximoVencimiento) {
                elements.proximoVencimiento.textContent = formatDate(dates.proximo_vencimiento);
            }
        } else {
            elements.dateBanner?.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error loading latest dates:', error);
        elements.dateBanner?.classList.add('hidden');
    }
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const day = date.getDate();
    const month = MONTH_NAMES[date.getMonth()];
    const year = date.getFullYear();
    return `${day} ${month} ${year}`;
}

// ============ Filter Functions ============

async function loadAvailablePeriods() {
    try {
        const data = await apiRequest('/available-periods');
        populatePeriodDropdowns(data);
    } catch (error) {
        console.error('Error loading available periods:', error);
    }
}

function populatePeriodDropdowns(data) {
    const { months, years } = data;

    // Populate month dropdowns
    [elements.monthFilter, elements.txMonthFilter].forEach(dropdown => {
        if (!dropdown) return;
        dropdown.innerHTML = '<option value="">Todos los meses</option>';
        months.forEach(m => {
            const monthName = MONTH_NAMES[m.month - 1];
            dropdown.innerHTML += `<option value="${m.month}" data-year="${m.year}">${monthName} ${m.year}</option>`;
        });
    });

    // Populate year dropdowns
    [elements.yearFilter, elements.txYearFilter].forEach(dropdown => {
        if (!dropdown) return;
        dropdown.innerHTML = '<option value="">Todos los años</option>';
        years.forEach(year => {
            dropdown.innerHTML += `<option value="${year}">${year}</option>`;
        });
    });
}

function setupFilterListeners() {
    // Dashboard currency toggle
    if (elements.currencyToggle) {
        elements.currencyToggle.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                elements.currencyToggle.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // Empty string means "all" (null)
                state.currency = btn.dataset.currency || null;
                loadAnalytics();
            });
        });
    }

    // Dashboard month filter
    elements.monthFilter?.addEventListener('change', (e) => {
        const option = e.target.selectedOptions[0];
        if (e.target.value) {
            state.selectedMonth = parseInt(e.target.value);
            state.selectedYear = parseInt(option.dataset.year);
            state.period = 'month';
        } else {
            state.selectedMonth = null;
            state.selectedYear = null;
        }
        loadAnalytics();
    });

    // Dashboard year filter
    elements.yearFilter?.addEventListener('change', (e) => {
        if (e.target.value) {
            state.selectedYear = parseInt(e.target.value);
            state.selectedMonth = null;
            state.period = 'year';
        } else {
            state.selectedYear = null;
        }
        loadAnalytics();
    });

    // Dashboard quarter button
    elements.quarterBtn?.addEventListener('click', () => {
        state.period = 'quarter';
        state.selectedMonth = null;
        state.selectedYear = null;
        elements.monthFilter.value = '';
        elements.yearFilter.value = '';
        loadAnalytics();
    });

    // Transaction currency toggle
    if (elements.txCurrencyToggle) {
        elements.txCurrencyToggle.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                elements.txCurrencyToggle.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // Empty string means "all" (null)
                state.txCurrency = btn.dataset.currency || null;
                loadTransactions();
            });
        });
    }

    // Transaction month filter
    elements.txMonthFilter?.addEventListener('change', (e) => {
        const option = e.target.selectedOptions[0];
        if (e.target.value) {
            state.txMonth = parseInt(e.target.value);
            state.txYear = parseInt(option.dataset.year);
        } else {
            state.txMonth = null;
            state.txYear = null;
        }
        loadTransactions();
    });

    // Transaction year filter
    elements.txYearFilter?.addEventListener('change', (e) => {
        if (e.target.value) {
            state.txYear = parseInt(e.target.value);
            state.txMonth = null;
        } else {
            state.txYear = null;
        }
        loadTransactions();
    });

    // Analytics currency toggle
    const analyticsCurrencyToggle = document.getElementById('analyticsCurrencyToggle');
    if (analyticsCurrencyToggle) {
        analyticsCurrencyToggle.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                analyticsCurrencyToggle.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                // Empty string means "all" (null)
                state.currency = btn.dataset.currency || null;
                loadAnalytics();
            });
        });
    }

    // Emoji picker
    const emojiPicker = document.getElementById('emojiPicker');
    if (emojiPicker) {
        emojiPicker.querySelectorAll('.emoji-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                elements.categoryIcon.value = btn.dataset.emoji;
            });
        });
    }
}

// ============ Initialize ============

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    setupFilterListeners();
    checkAuth();
});
