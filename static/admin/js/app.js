// Advanced Admin Panel JavaScript
// Global Variables
let currentTab = 'dashboard';
let usersData = [];
let variablesData = [];
let analyticsData = {};
let systemStats = {};
let logEntries = [];
let websocket = null;
let logsWebsocket = null;
let autoScroll = true;

// API Configuration
const API_BASE = '/api';

// Utility Functions
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Add active class to nav item
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    currentTab = tabName;
    
    // Load tab-specific data
    loadTabData(tabName);
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas ${getNotificationIcon(type)}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification(`API Error: ${error.message}`, 'error');
        throw error;
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        const stats = await apiCall('/admin/stats');
        systemStats = stats;
        
        // Update stat cards
        document.getElementById('total-users').textContent = formatNumber(stats.total_users || 0);
        document.getElementById('total-downloads').textContent = formatNumber(stats.total_downloads || 0);
        document.getElementById('total-admins').textContent = formatNumber(stats.total_admins || 0);
        document.getElementById('total-banned').textContent = formatNumber(stats.total_banned || 0);
        
        // Update quick stats
        document.getElementById('active-downloads').textContent = formatNumber(stats.active_downloads || 0);
        document.getElementById('storage-used').textContent = formatBytes(stats.storage_used || 0);
        document.getElementById('api-requests').textContent = formatNumber(stats.api_requests || 0);
        document.getElementById('uptime').textContent = stats.uptime || '0h 0m';
        
        // Update change indicators
        updateChangeIndicators(stats);
        
        // Load recent activity
        await loadRecentActivity();
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

function updateChangeIndicators(stats) {
    const changes = [
        { id: 'users-change', value: stats.users_today || 0 },
        { id: 'downloads-change', value: stats.downloads_today || 0 },
        { id: 'admins-change', value: stats.new_admins || 0 },
        { id: 'banned-change', value: stats.banned_today || 0 }
    ];
    
    changes.forEach(change => {
        const element = document.getElementById(change.id);
        if (element) {
            const prefix = change.value >= 0 ? '+' : '';
            const className = change.value >= 0 ? 'positive' : 'negative';
            element.textContent = `${prefix}${formatNumber(change.value)} ${currentTab === 'dashboard' ? 'today' : 'new'}`;
            element.className = `stat-change ${className}`;
        }
    });
}

async function loadRecentActivity() {
    try {
        const activity = await apiCall('/admin/activity/recent');
        const container = document.getElementById('recent-downloads');
        
        if (activity.length === 0) {
            container.innerHTML = `
                <div class="activity-item">
                    <div class="activity-icon"><i class="fas fa-info-circle"></i></div>
                    <div class="activity-content">
                        <div class="activity-title">No recent activity</div>
                        <div class="activity-time">--</div>
                    </div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = activity.map(item => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas ${getActivityIcon(item.type)}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${item.title}</div>
                    <div class="activity-time">${formatDate(item.timestamp)}</div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load recent activity:', error);
    }
}

function getActivityIcon(type) {
    const icons = {
        download: 'fa-download',
        upload: 'fa-upload',
        user_register: 'fa-user-plus',
        admin_action: 'fa-user-shield',
        error: 'fa-exclamation-triangle'
    };
    return icons[type] || 'fa-info-circle';
}

// User Management Functions
async function loadUsers() {
    try {
        const users = await apiCall('/admin/users');
        usersData = users;
        renderUsersTable(users);
        updateUsersCount(users);
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

function renderUsersTable(users) {
    const tbody = document.getElementById('users-table-body');
    
    if (users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="loading-cell">
                    <i class="fas fa-users"></i> No users found
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.user_id}</td>
            <td>${user.username || 'N/A'}</td>
            <td>${user.first_name || 'N/A'} ${user.last_name || ''}</td>
            <td>
                <span class="role-badge role-${user.is_admin ? 'admin' : 'user'}">
                    ${user.is_admin ? 'Admin' : 'User'}
                </span>
            </td>
            <td>${formatNumber(user.downloads_count || 0)}</td>
            <td>${formatDate(user.created_at)}</td>
            <td>
                <span class="status-badge status-${user.is_banned ? 'banned' : 'active'}">
                    ${user.is_banned ? 'Banned' : 'Active'}
                </span>
            </td>
            <td>
                <div class="user-actions">
                    ${!user.is_admin ? `
                        <button class="btn btn-sm btn-success" onclick="banUser(${user.user_id})">
                            <i class="fas fa-ban"></i>
                        </button>
                    ` : ''}
                    ${user.is_admin ? `
                        <button class="btn btn-sm btn-warning" onclick="demoteUser(${user.user_id})">
                            <i class="fas fa-user-minus"></i>
                        </button>
                    ` : `
                        <button class="btn btn-sm btn-info" onclick="promoteUser(${user.user_id})">
                            <i class="fas fa-user-plus"></i>
                        </button>
                    `}
                </div>
            </td>
        </tr>
    `).join('');
}

function updateUsersCount(users) {
    const countElement = document.getElementById('users-count');
    if (countElement) {
        countElement.textContent = `Showing ${users.length} of ${users.length} users`;
    }
}

function searchUsers() {
    const query = document.getElementById('user-search').value.toLowerCase();
    const filteredUsers = usersData.filter(user => 
        user.username?.toLowerCase().includes(query) ||
        user.first_name?.toLowerCase().includes(query) ||
        user.last_name?.toLowerCase().includes(query) ||
        user.user_id.toString().includes(query)
    );
    renderUsersTable(filteredUsers);
    updateUsersCount(filteredUsers);
}

function filterUsers() {
    const filter = document.getElementById('user-filter').value;
    let filteredUsers = [...usersData];
    
    switch (filter) {
        case 'admin':
            filteredUsers = usersData.filter(user => user.is_admin);
            break;
        case 'banned':
            filteredUsers = usersData.filter(user => user.is_banned);
            break;
        case 'active':
            filteredUsers = usersData.filter(user => !user.is_banned);
            break;
    }
    
    renderUsersTable(filteredUsers);
    updateUsersCount(filteredUsers);
}

async function banUser(userId) {
    if (!confirm('Are you sure you want to ban this user?')) return;
    
    try {
        await apiCall(`/admin/users/${userId}/ban`, { method: 'POST' });
        showNotification('User banned successfully', 'success');
        loadUsers();
    } catch (error) {
        console.error('Failed to ban user:', error);
    }
}

async function unbanUser(userId) {
    try {
        await apiCall(`/admin/users/${userId}/unban`, { method: 'POST' });
        showNotification('User unbanned successfully', 'success');
        loadUsers();
    } catch (error) {
        console.error('Failed to unban user:', error);
    }
}

async function promoteUser(userId) {
    if (!confirm('Are you sure you want to promote this user to admin?')) return;
    
    try {
        await apiCall(`/admin/users/${userId}/promote`, { method: 'POST' });
        showNotification('User promoted to admin', 'success');
        loadUsers();
    } catch (error) {
        console.error('Failed to promote user:', error);
    }
}

async function demoteUser(userId) {
    if (!confirm('Are you sure you want to demote this admin?')) return;
    
    try {
        await apiCall(`/admin/users/${userId}/demote`, { method: 'POST' });
        showNotification('Admin demoted to user', 'success');
        loadUsers();
    } catch (error) {
        console.error('Failed to demote user:', error);
    }
}

// Variable Management Functions
async function loadVariables() {
    try {
        const variables = await apiCall('/admin/variables');
        variablesData = variables;
        renderVariablesList(variables);
    } catch (error) {
        console.error('Failed to load variables:', error);
    }
}

function renderVariablesList(variables) {
    const container = document.getElementById('vars-list');
    
    if (variables.length === 0) {
        container.innerHTML = `
            <div class="var-item">
                <div class="var-key">No variables found</div>
                <div class="var-value">Create your first variable using the form above</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = variables.map(variable => `
        <div class="var-item">
            <div class="var-key">${variable.key}</div>
            <div class="var-value">${variable.value}</div>
            <div class="var-actions">
                <button class="var-btn edit" onclick="editVariable('${variable.key}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="var-btn delete" onclick="deleteVariable('${variable.key}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

function clearVarForm() {
    document.getElementById('var-key').value = '';
    document.getElementById('var-desc').value = '';
    document.getElementById('var-value').value = '';
}

async function saveVariable(event) {
    event.preventDefault();
    
    const key = document.getElementById('var-key').value;
    const description = document.getElementById('var-desc').value;
    const value = document.getElementById('var-value').value;
    
    try {
        await apiCall('/admin/variables', {
            method: 'POST',
            body: JSON.stringify({ key, description, value })
        });
        
        showNotification('Variable saved successfully', 'success');
        clearVarForm();
        loadVariables();
    } catch (error) {
        console.error('Failed to save variable:', error);
    }
}

function editVariable(key) {
    const variable = variablesData.find(v => v.key === key);
    if (variable) {
        document.getElementById('var-key').value = variable.key;
        document.getElementById('var-desc').value = variable.description || '';
        document.getElementById('var-value').value = variable.value;
        showNotification(`Editing variable: ${key}`, 'info');
    }
}

async function deleteVariable(key) {
    if (!confirm(`Are you sure you want to delete variable "${key}"?`)) return;
    
    try {
        await apiCall(`/admin/variables/${key}`, { method: 'DELETE' });
        showNotification('Variable deleted successfully', 'success');
        loadVariables();
    } catch (error) {
        console.error('Failed to delete variable:', error);
    }
}

// Broadcast Functions
async function sendBroadcast(event) {
    event.preventDefault();
    
    const message = document.getElementById('broadcast-msg').value;
    const preview = document.getElementById('broadcast-preview').checked;
    const persistent = document.getElementById('broadcast-persistent').checked;
    
    if (preview) {
        previewBroadcast();
        return;
    }
    
    try {
        const result = await apiCall('/admin/broadcast', {
            method: 'POST',
            body: JSON.stringify({
                message,
                persistent,
                timestamp: new Date().toISOString()
            })
        });
        
        showNotification(`Broadcast sent to ${result.sent_count} users`, 'success');
        document.getElementById('broadcast-msg').value = '';
        loadBroadcastHistory();
        
    } catch (error) {
        console.error('Failed to send broadcast:', error);
    }
}

function previewBroadcast() {
    const message = document.getElementById('broadcast-msg').value;
    const preview = document.getElementById('broadcast-result');
    
    preview.innerHTML = `
        <div class="broadcast-preview">
            <h4><i class="fas fa-eye"></i> Broadcast Preview</h4>
            <div class="preview-content">
                <div class="preview-message">${message}</div>
                <div class="preview-meta">
                    <span>Preview Mode</span>
                    <span>${new Date().toLocaleString()}</span>
                </div>
            </div>
        </div>
    `;
}

async function loadBroadcastHistory() {
    try {
        const history = await apiCall('/admin/broadcast/history');
        const container = document.getElementById('broadcast-history');
        
        if (history.length === 0) {
            container.innerHTML = '<p>No broadcast history found</p>';
            return;
        }
        
        container.innerHTML = history.map(broadcast => `
            <div class="broadcast-item">
                <div class="broadcast-content">
                    <div class="broadcast-text">${broadcast.message}</div>
                    <div class="broadcast-meta">
                        <span>Sent to ${broadcast.sent_count} users</span>
                        <span>${formatDate(broadcast.timestamp)}</span>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load broadcast history:', error);
    }
}

// Analytics Functions
async function loadAnalytics() {
    try {
        const period = document.getElementById('analytics-period').value;
        const analytics = await apiCall(`/admin/analytics?period=${period}`);
        analyticsData = analytics;
        
        renderAnalyticsCharts(analytics);
        renderAnalyticsStats(analytics);
        
    } catch (error) {
        console.error('Failed to load analytics:', error);
    }
}

function renderAnalyticsCharts(data) {
    // Downloads Chart
    const downloadsCtx = document.getElementById('downloads-chart').getContext('2d');
    new Chart(downloadsCtx, {
        type: 'line',
        data: {
            labels: data.downloads.labels || [],
            datasets: [{
                label: 'Downloads',
                data: data.downloads.data || [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#f1f5f9'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                }
            }
        }
    });
    
    // Users Chart
    const usersCtx = document.getElementById('users-chart').getContext('2d');
    new Chart(usersCtx, {
        type: 'bar',
        data: {
            labels: data.users.labels || [],
            datasets: [{
                label: 'New Users',
                data: data.users.data || [],
                backgroundColor: 'rgba(34, 197, 94, 0.8)',
                borderColor: '#22c55e',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#f1f5f9'
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                },
                y: {
                    ticks: {
                        color: '#94a3b8'
                    },
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)'
                    }
                }
            }
        }
    });
}

function renderAnalyticsStats(data) {
    document.getElementById('popular-platform').textContent = data.popular_platform || 'YouTube';
    document.getElementById('avg-downloads').textContent = formatNumber(data.avg_daily_downloads || 0);
    document.getElementById('peak-hour').textContent = data.peak_hour || '0:00';
    document.getElementById('active-user').textContent = data.most_active_user || 'N/A';
}

// Settings Functions
async function loadSettings() {
    try {
        const settings = await apiCall('/admin/settings');
        
        document.getElementById('max-downloads').value = settings.max_downloads_per_user || 100;
        document.getElementById('file-retention').value = settings.file_retention_hours || 24;
        document.getElementById('rate-limit').value = settings.api_rate_limit || 30;
        document.getElementById('max-file-size').value = settings.max_file_size_mb || 500;
        
        document.getElementById('enable-analytics').checked = settings.enable_analytics || false;
        document.getElementById('enable-logging').checked = settings.enable_logging || false;
        document.getElementById('maintenance-mode').checked = settings.maintenance_mode || false;
        
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveSettings(event) {
    event.preventDefault();
    
    const settings = {
        max_downloads_per_user: parseInt(document.getElementById('max-downloads').value),
        file_retention_hours: parseInt(document.getElementById('file-retention').value),
        api_rate_limit: parseInt(document.getElementById('rate-limit').value),
        max_file_size_mb: parseInt(document.getElementById('max-file-size').value),
        enable_analytics: document.getElementById('enable-analytics').checked,
        enable_logging: document.getElementById('enable-logging').checked,
        maintenance_mode: document.getElementById('maintenance-mode').checked
    };
    
    try {
        await apiCall('/admin/settings', {
            method: 'POST',
            body: JSON.stringify(settings)
        });
        
        showNotification('Settings saved successfully', 'success');
        
    } catch (error) {
        console.error('Failed to save settings:', error);
    }
}

async function cleanupDatabase() {
    if (!confirm('Are you sure you want to cleanup the database? This action cannot be undone.')) return;
    
    try {
        await apiCall('/admin/database/cleanup', { method: 'POST' });
        showNotification('Database cleaned successfully', 'success');
    } catch (error) {
        console.error('Failed to cleanup database:', error);
    }
}

async function backupDatabase() {
    try {
        const response = await fetch('/api/admin/database/backup');
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `backup-${new Date().toISOString().split('T')[0]}.sql`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification('Database backup downloaded', 'success');
        
    } catch (error) {
        console.error('Failed to backup database:', error);
    }
}

async function resetDatabase() {
    if (!confirm('Are you sure you want to reset the database? ALL DATA WILL BE LOST!')) return;
    if (!confirm('This is your final warning. All data will be permanently deleted!')) return;
    
    try {
        await apiCall('/admin/database/reset', { method: 'POST' });
        showNotification('Database reset successfully', 'success');
        setTimeout(() => location.reload(), 2000);
    } catch (error) {
        console.error('Failed to reset database:', error);
    }
}

// Modal Functions
function showModal(modalId) {
    document.getElementById(modalId).classList.add('show');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

// Utility Functions
function refreshDashboard() {
    loadDashboard();
    showNotification('Dashboard refreshed', 'info');
}

function exportDashboard() {
    // Implement dashboard export functionality
    showNotification('Dashboard export started', 'info');
}

function exportUsers() {
    // Implement users export functionality
    showNotification('Users export started', 'info');
}

function exportAnalytics() {
    // Implement analytics export functionality
    showNotification('Analytics export started', 'info');
}

function resetSettings() {
    if (confirm('Reset all settings to defaults?')) {
        loadSettings();
        showNotification('Settings reset to defaults', 'info');
    }
}

function refreshVariables() {
    loadVariables();
    showNotification('Variables refreshed', 'info');
}

function setLang(lang) {
    // Implement language switching
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === 'fa' ? 'rtl' : 'ltr';
    showNotification(`Language changed to ${lang}`, 'info');
}

// Tab Data Loading
async function loadTabData(tabName) {
    switch (tabName) {
        case 'dashboard':
            await loadDashboard();
            break;
        case 'users':
            await loadUsers();
            break;
        case 'variables':
            await loadVariables();
            break;
        case 'broadcast':
            await loadBroadcastHistory();
            break;
        case 'analytics':
            await loadAnalytics();
            break;
        case 'settings':
            await loadSettings();
            break;
        case 'logs':
            await loadLogs();
            break;
    }
}

// Live Logs Functions
async function loadLogs() {
    try {
        // Connect to WebSocket for live logs
        connectWebSocket();
        
        // Load initial logs
        const initialLogs = await apiCall('/admin/logs?limit=50');
        logEntries = initialLogs || [];
        renderLogs();
        
        // Set up auto-scroll
        document.getElementById('auto-scroll').addEventListener('change', function() {
            autoScroll = this.checked;
        });
        
    } catch (error) {
        console.error('Failed to load logs:', error);
        addLogEntry('Error loading logs: ' + error.message, 'error', 'system');
    }

    // Initialize WebSocket connections for live updates
    initializeWebSockets();
}

function connectWebSocket() {
    // Check if WebSocket is supported
    if (!window.WebSocket) {
        addLogEntry('WebSocket not supported in this browser', 'warning', 'system');
        return;
    }
    
    // Close existing connection if any
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.close();
    }
    
    // Connect to WebSocket server
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
    
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = function() {
        addLogEntry('Connected to live logs', 'success', 'system');
    };
    
    websocket.onmessage = function(event) {
        try {
            const logData = JSON.parse(event.data);
            addLogEntry(logData.message, logData.level, logData.source);
        } catch (error) {
            console.error('Error parsing log message:', error);
        }
    };
    
    websocket.onclose = function() {
        addLogEntry('Disconnected from live logs', 'warning', 'system');
        // Try to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
    };
    
    websocket.onerror = function(error) {
        addLogEntry('WebSocket error: ' + error.message, 'error', 'system');
    };
}

function addLogEntry(message, level, source) {
    const logEntry = {
        id: Date.now() + Math.random().toString(36).substr(2, 9),
        timestamp: new Date().toISOString(),
        message: message,
        level: level || 'info',
        source: source || 'system'
    };
    
    logEntries.push(logEntry);
    
    // Keep only the last 1000 entries
    if (logEntries.length > 1000) {
        logEntries = logEntries.slice(-1000);
    }
    
    renderLogs();
}

function renderLogs() {
    const container = document.getElementById('log-entries');
    const levelFilter = document.getElementById('log-level').value;
    const sourceFilter = document.getElementById('log-source').value;
    
    if (!container) return;
    
    // Filter logs
    const filteredLogs = logEntries.filter(log => {
        const levelMatch = levelFilter === 'all' || log.level === levelFilter;
        const sourceMatch = sourceFilter === 'all' || log.source === sourceFilter;
        return levelMatch && sourceMatch;
    });
    
    if (filteredLogs.length === 0) {
        container.innerHTML = '<div class="log-entry loading">No logs found matching filters</div>';
        return;
    }
    
    container.innerHTML = filteredLogs.map(log => `
        <div class="log-entry ${log.level}">
            <div class="log-header">
                <i class="fas ${getLogIcon(log.level)}"></i>
                <span class="log-level">${log.level.toUpperCase()}</span>
            </div>
            <div class="log-message">${escapeHtml(log.message)}</div>
            <div class="log-meta">
                <span class="log-time">${formatLogTime(log.timestamp)}</span>
                <span class="log-source ${log.source}">${log.source}</span>
            </div>
        </div>
    `).join('');
    
    // Auto-scroll if enabled
    if (autoScroll) {
        container.scrollTop = container.scrollHeight;
    }
}

function getLogIcon(level) {
    const icons = {
        info: 'fa-info-circle',
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        error: 'fa-exclamation-circle'
    };
    return icons[level] || 'fa-info-circle';
}

function formatLogTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

function filterLogs() {
    renderLogs();
}

function clearLogs() {
    if (confirm('Are you sure you want to clear all logs?')) {
        logEntries = [];
        renderLogs();
        showNotification('Logs cleared', 'info');
    }
}

function exportLogs() {
    const filteredLogs = logEntries.filter(log => {
        const levelFilter = document.getElementById('log-level').value;
        const sourceFilter = document.getElementById('log-source').value;
        const levelMatch = levelFilter === 'all' || log.level === levelFilter;
        const sourceMatch = sourceFilter === 'all' || log.source === sourceFilter;
        return levelMatch && sourceMatch;
    });
    
    if (filteredLogs.length === 0) {
        showNotification('No logs to export', 'warning');
        return;
    }
    
    const logText = filteredLogs.map(log =>
        `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.source}] ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs-${new Date().toISOString().split('T')[0]}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification('Logs exported successfully', 'success');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize Application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize first tab
    loadTabData('dashboard');
    
    // Auto-refresh dashboard every 30 seconds
    setInterval(() => {
        if (currentTab === 'dashboard') {
            loadDashboard();
        }
    }, 30000);
    
    // Character counter for broadcast message
    const broadcastMsg = document.getElementById('broadcast-msg');
    const charCount = document.getElementById('char-count');
    
    if (broadcastMsg && charCount) {
        broadcastMsg.addEventListener('input', function() {
            charCount.textContent = this.value.length;
            charCount.style.color = this.value.length > 900 ? '#ef4444' : '#94a3b8';
        });
    }
    
    // Add click outside modal to close
    document.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            closeModal(event.target.id);
        }
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case '1':
                    event.preventDefault();
                    showTab('dashboard');
                    break;
                case '2':
                    event.preventDefault();
                    showTab('users');
                    break;
                case '3':
                    event.preventDefault();
                    showTab('variables');
                    break;
                case '4':
                    event.preventDefault();
                    showTab('broadcast');
                    break;
                case '5':
                    event.preventDefault();
                    showTab('analytics');
                    break;
                case '6':
                    event.preventDefault();
                    showTab('settings');
                    break;
                case '7':
                    event.preventDefault();
                    showTab('logs');
                    break;
            }
        }
    });
    
    showNotification('Admin panel loaded successfully', 'success');
});

// Error handling
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    showNotification('An unexpected error occurred', 'error');
});

// Service Worker for offline functionality (if needed)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed');
            });
    });
}
