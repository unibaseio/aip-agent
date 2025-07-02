// AIP DEX Trading Bot Dashboard JavaScript
class TradingBotDashboard {
    constructor() {
        this.currentFilter = 'all';
        this.refreshInterval = null;
        this.revenueChart = null;
        this.currentBotId = null;

        this.init();
    }

    init() {
        this.updateCurrentTime();
        this.loadSystemOverview();
        this.loadBots();
        this.loadRecentTransactions();

        // Set default refresh interval to 1 minute
        this.changeRefreshInterval(60);

        // Update time every second
        setInterval(() => this.updateCurrentTime(), 1000);
    }

    updateCurrentTime() {
        const now = new Date();
        document.getElementById('current-time').textContent = now.toLocaleString('zh-CN');
    }

    async loadSystemOverview() {
        try {
            const response = await fetch('/api/system/overview');
            if (!response.ok) throw new Error('Failed to load system overview');

            const data = await response.json();
            this.updateSystemStats(data);
        } catch (error) {
            console.error('Error loading system overview:', error);
            this.showError('Failed to load system overview');
        }
    }

    updateSystemStats(data) {
        // Ensure data exists and has default values
        const safeData = {
            total_bots: data?.total_bots || 0,
            active_bots: data?.active_bots || 0,
            total_trades_24h: data?.total_trades_24h || 0,
            total_volume_24h_usd: data?.total_volume_24h_usd || 0,
            today_profit_usd: data?.today_profit_usd || 0,
            total_assets_usd: data?.total_assets_usd || 0
        };

        document.getElementById('total-bots').textContent = safeData.total_bots;
        document.getElementById('active-bots').textContent = safeData.active_bots;
        document.getElementById('total-trades-24h').textContent = safeData.total_trades_24h;
        document.getElementById('total-volume-24h').textContent = this.formatUSD(safeData.total_volume_24h_usd);
        document.getElementById('today-profit').textContent = this.formatUSD(safeData.today_profit_usd);
        document.getElementById('total-assets').textContent = this.formatUSD(safeData.total_assets_usd);
    }

    async loadBots() {
        try {
            const response = await fetch('/api/bots');
            if (!response.ok) throw new Error('Failed to load bots');

            const bots = await response.json();
            this.renderBots(bots);
        } catch (error) {
            console.error('Error loading bots:', error);
            this.showError('Failed to load trading bots');
        }
    }

    renderBots(bots) {
        const container = document.getElementById('bots-container');
        container.innerHTML = '';

        const filteredBots = this.filterBotsByType(bots, this.currentFilter);

        if (filteredBots.length === 0) {
            container.innerHTML = `
                <div class="col-12 text-center">
                    <p class="text-secondary">No bots found</p>
                </div>
            `;
            return;
        }

        filteredBots.forEach(bot => {
            const botCard = this.createBotCard(bot);
            container.appendChild(botCard);
        });
    }

    filterBotsByType(bots, filter) {
        switch (filter) {
            case 'active':
                return bots.filter(bot => bot.is_active);
            case 'bsc':
                return bots.filter(bot => bot.chain === 'bsc');
            case 'solana':
                return bots.filter(bot => bot.chain === 'solana');
            default:
                return bots;
        }
    }

    createBotCard(bot) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4 mb-3';

        // Handle profit, status, and safe display values
        const profitClass = parseFloat(bot.total_profit_usd) >= 0 ? 'profit-positive' : 'profit-negative';
        const totalTrades = bot.total_trades || 0;
        const profitableTrades = bot.profitable_trades || 0;
        const winRateText = totalTrades > 0 ? `${profitableTrades}/${totalTrades}` : '-';
        const winRatePercent = totalTrades > 0 ? (profitableTrades / totalTrades * 100) : 0;
        const statusBadge = bot.is_active ? '<span class="status-badge status-active ms-2">ACTIVE</span>' : '';
        const strategyType = bot.strategy_type || '-';
        const chain = bot.chain ? bot.chain.toUpperCase() : '-';
        const accountShort = bot.account_address ? `${bot.account_address.substring(0, 8)}...${bot.account_address.substring(bot.account_address.length - 6)}` : '-';

        col.innerHTML = `
            <div class="card bot-card" onclick="dashboard.showBotDetails('${bot.id}')">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h6 class="mb-1 d-flex align-items-center">
                            ${bot.bot_name}
                            ${statusBadge}
                        </h6>
                    </div>
                    <small class="text-secondary">${accountShort}</small>
                    <div class="row text-center mt-3">
                        <div class="col-6">
                            <div class="mb-2">
                                <h6 class="mb-0">${this.formatUSD(bot.total_assets_usd)}</h6>
                                <small class="text-secondary">Total Assets</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="mb-2">
                                <h6 class="mb-0 ${profitClass}">${this.formatUSD(bot.total_profit_usd)}</h6>
                                <small class="text-secondary">Total Profit</small>
                            </div>
                        </div>
                    </div>
                    <div class="row text-center">
                        <div class="col-6">
                            <small class="text-secondary">${strategyType}</small>
                        </div>
                        <div class="col-6">
                            <small class="text-secondary">${chain}</small>
                        </div>
                    </div>
                    <div class="mt-3">
                        <div class="d-flex justify-content-between">
                            <small class="text-secondary">Win Rate</small>
                            <small class="text-primary">${winRateText}</small>
                        </div>
                        <div class="progress" style="height: 4px;">
                            <div class="progress-bar bg-primary" style="width: ${winRatePercent}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        return col;
    }

    async loadRecentTransactions() {
        try {
            const response = await fetch('/api/transactions/recent');
            if (!response.ok) throw new Error('Failed to load recent transactions');

            const transactions = await response.json();
            this.renderRecentTransactions(transactions);
        } catch (error) {
            console.error('Error loading recent transactions:', error);
            this.showError('Failed to load recent transactions');
        }
    }

    renderRecentTransactions(transactions) {
        const tbody = document.getElementById('recent-transactions');
        tbody.innerHTML = '';

        if (transactions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-secondary">No recent transactions</td>
                </tr>
            `;
            return;
        }

        transactions.forEach(tx => {
            const row = this.createTransactionRow(tx);
            tbody.appendChild(row);
        });
    }

    createTransactionRow(tx) {
        const row = document.createElement('tr');

        const typeIcon = tx.transaction_type === 'buy' ? 'fa-arrow-up text-success' : 'fa-arrow-down text-danger';
        const statusClass = this.getStatusClass(tx.status);
        const pnlClass = tx.realized_pnl_usd && parseFloat(tx.realized_pnl_usd) >= 0 ? 'profit-positive' : 'profit-negative';

        row.innerHTML = `
            <td>${tx.bot_name}</td>
            <td><i class="fas ${typeIcon}"></i> ${tx.transaction_type.toUpperCase()}</td>
            <td>${tx.token_symbol}</td>
            <td>${this.formatUSD(tx.amount_usd)}</td>
            <td>${this.formatNumber(tx.token_amount)}</td>
            <td>${this.formatUSD(tx.price_usd)}</td>
            <td class="${pnlClass}">${tx.realized_pnl_usd ? this.formatUSD(tx.realized_pnl_usd) : '-'}</td>
            <td><span class="status-badge ${statusClass}">${tx.status}</span></td>
            <td>${this.formatDateTime(tx.created_at)}</td>
        `;

        return row;
    }

    getStatusClass(status) {
        switch (status) {
            case 'executed': return 'status-active';
            case 'pending': return 'status-warning';
            case 'failed': return 'status-inactive';
            default: return 'status-secondary';
        }
    }

    async showBotDetails(botId) {
        this.currentBotId = botId;

        try {
            const [botDetails, positions, transactions, llmDecisions, revenue] = await Promise.all([
                fetch(`/api/bots/${botId}`).then(r => r.json()),
                fetch(`/api/bots/${botId}/positions`).then(r => r.json()),
                fetch(`/api/bots/${botId}/transactions`).then(r => r.json()),
                fetch(`/api/bots/${botId}/llm-decisions`).then(r => r.json()),
                fetch(`/api/bots/${botId}/revenue`).then(r => r.json())
            ]);

            this.renderBotDetails(botDetails, positions, transactions, llmDecisions, revenue);

            const modal = new bootstrap.Modal(document.getElementById('botDetailModal'));
            modal.show();
        } catch (error) {
            console.error('Error loading bot details:', error);
            this.showError('Failed to load bot details');
        }
    }

    renderBotDetails(bot, positions, transactions, llmDecisions, revenue) {
        document.getElementById('modal-bot-name').textContent = bot.bot_name;

        // Bot Info
        document.getElementById('bot-info').innerHTML = `
            <div class="row">
                <div class="col-6">
                    <p><strong>Account:</strong> ${bot.account_address}</p>
                    <p><strong>Chain:</strong> ${bot.chain.toUpperCase()}</p>
                    <p><strong>Strategy:</strong> ${bot.strategy_type}</p>
                    <p><strong>Status:</strong> <span class="status-badge ${bot.is_active ? 'status-active' : 'status-inactive'}">${bot.is_active ? 'Active' : 'Inactive'}</span></p>
                </div>
                <div class="col-6">
                    <p><strong>Initial Balance:</strong> ${this.formatUSD(bot.initial_balance_usd)}</p>
                    <p><strong>Current Balance:</strong> ${this.formatUSD(bot.current_balance_usd)}</p>
                    <p><strong>Total Assets:</strong> ${this.formatUSD(bot.total_assets_usd)}</p>
                    <p><strong>Last Activity:</strong> ${this.formatDateTime(bot.last_activity_at)}</p>
                </div>
            </div>
        `;

        // Performance Stats
        const winRate = bot.total_trades > 0 ? (bot.profitable_trades / bot.total_trades * 100).toFixed(1) : 0;
        document.getElementById('performance-stats').innerHTML = `
            <div class="row">
                <div class="col-6">
                    <p><strong>Total Trades:</strong> ${bot.total_trades}</p>
                    <p><strong>Profitable Trades:</strong> ${bot.profitable_trades}</p>
                    <p><strong>Win Rate:</strong> ${winRate}%</p>
                    <p><strong>Total Profit:</strong> <span class="${parseFloat(bot.total_profit_usd) >= 0 ? 'profit-positive' : 'profit-negative'}">${this.formatUSD(bot.total_profit_usd)}</span></p>
                </div>
                <div class="col-6">
                    <p><strong>Max Drawdown:</strong> ${bot.max_drawdown_percentage}%</p>
                    <p><strong>Max Position Size:</strong> ${bot.max_position_size}%</p>
                    <p><strong>Stop Loss:</strong> ${bot.stop_loss_percentage}%</p>
                    <p><strong>Take Profit:</strong> ${bot.take_profit_percentage}%</p>
                </div>
            </div>
        `;

        // Current Positions
        this.renderCurrentPositions(positions);

        // Transaction Timeline
        this.renderTransactionTimeline(transactions);

        // LLM Decisions
        this.renderLLMDecisions(llmDecisions);

        // Revenue Chart
        this.renderRevenueChart(revenue);
    }

    renderCurrentPositions(positions) {
        const tbody = document.getElementById('current-positions');
        tbody.innerHTML = '';

        if (positions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-secondary">No active positions</td>
                </tr>
            `;
            return;
        }

        positions.forEach(pos => {
            const row = document.createElement('tr');
            const pnlClass = parseFloat(pos.unrealized_pnl_usd) >= 0 ? 'profit-positive' : 'profit-negative';

            row.innerHTML = `
                <td>${pos.token_symbol}</td>
                <td>${this.formatNumber(pos.quantity)}</td>
                <td>${this.formatUSD(pos.average_cost_usd)}</td>
                <td>${this.formatUSD(pos.current_price_usd)}</td>
                <td>${this.formatUSD(pos.current_value_usd)}</td>
                <td class="${pnlClass}">${this.formatUSD(pos.unrealized_pnl_usd)}</td>
                <td class="${pnlClass}">${pos.unrealized_pnl_percentage}%</td>
            `;

            tbody.appendChild(row);
        });
    }

    renderTransactionTimeline(transactions) {
        const timeline = document.getElementById('transaction-timeline');
        timeline.innerHTML = '';

        if (transactions.length === 0) {
            timeline.innerHTML = '<p class="text-secondary">No transactions found</p>';
            return;
        }

        transactions.slice(0, 10).forEach(tx => {
            const item = document.createElement('div');
            item.className = 'timeline-item';

            const typeIcon = tx.transaction_type === 'buy' ? 'fa-arrow-up text-success' : 'fa-arrow-down text-danger';
            const pnlText = tx.realized_pnl_usd ? ` (${this.formatUSD(tx.realized_pnl_usd)})` : '';

            item.innerHTML = `
                <div class="card">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">
                                    <i class="fas ${typeIcon}"></i>
                                    ${tx.transaction_type.toUpperCase()} ${tx.token_symbol}${pnlText}
                                </h6>
                                <p class="mb-1 text-secondary">
                                    Amount: ${this.formatUSD(tx.amount_usd)} | 
                                    Token Amount: ${this.formatNumber(tx.token_amount)} | 
                                    Price: ${this.formatUSD(tx.price_usd)}
                                </p>
                                <small class="text-secondary">${this.formatDateTime(tx.created_at)}</small>
                            </div>
                            <span class="status-badge ${this.getStatusClass(tx.status)}">${tx.status}</span>
                        </div>
                    </div>
                </div>
            `;

            timeline.appendChild(item);
        });
    }

    renderLLMDecisions(llmDecisions) {
        const container = document.getElementById('llm-decisions');
        if (!container) return;

        container.innerHTML = '';

        if (llmDecisions.length === 0) {
            container.innerHTML = '<p class="text-secondary">No LLM decisions found</p>';
            return;
        }

        llmDecisions.slice(0, 10).forEach(decision => {
            const item = document.createElement('div');
            item.className = 'timeline-item mb-3';

            const decisionTypeIcon = decision.decision_type === 'sell_analysis' ? 'fa-arrow-down text-danger' : 'fa-arrow-up text-success';
            const phaseText = decision.decision_phase === 'phase_1_sell' ? 'Sell Analysis' : 'Buy Analysis';
            const confidenceClass = decision.confidence_score >= 0.7 ? 'text-success' : decision.confidence_score >= 0.5 ? 'text-warning' : 'text-danger';

            item.innerHTML = `
                <div class="card">
                    <div class="card-body p-3">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">
                                    <i class="fas ${decisionTypeIcon}"></i>
                                    ${phaseText}
                                    <span class="badge bg-secondary ms-2">${decision.decision_type}</span>
                                </h6>
                                <p class="mb-2 text-secondary">
                                    <strong>Action:</strong> ${decision.recommended_action || 'No action'} | 
                                    <strong>Confidence:</strong> <span class="${confidenceClass}">${(decision.confidence_score * 100).toFixed(1)}%</span>
                                </p>
                                ${decision.recommended_token_symbol ? `<p class="mb-2"><strong>Token:</strong> ${decision.recommended_token_symbol}</p>` : ''}
                                ${decision.reasoning ? `<p class="mb-2"><strong>Reasoning:</strong> ${decision.reasoning.substring(0, 200)}${decision.reasoning.length > 200 ? '...' : ''}</p>` : ''}
                                <small class="text-secondary">${this.formatDateTime(decision.created_at)}</small>
                            </div>
                            <div class="text-end">
                                <span class="badge ${decision.was_executed ? 'bg-success' : 'bg-secondary'}">${decision.was_executed ? 'Executed' : 'Not Executed'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            container.appendChild(item);
        });
    }

    renderRevenueChart(revenueData) {
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded');
            return;
        }

        const canvas = document.getElementById('revenueChart');
        if (!canvas) {
            console.error('Revenue chart canvas not found');
            return;
        }

        // 彻底销毁旧实例，防止Canvas is already in use报错
        if (this.revenueChart) {
            try {
                this.revenueChart.destroy();
            } catch (e) {
                console.warn('Chart destroy error:', e);
            }
            this.revenueChart = null;
        }

        if (!revenueData || revenueData.length === 0) {
            canvas.parentElement.innerHTML = '<div class="text-center text-secondary py-5">No revenue data available</div>';
            return;
        }

        // Prepare data with formatted labels
        const labels = revenueData.map((item, index) => {
            try {
                // Use created_at field for time labels
                let date;
                if (item.created_at) {
                    // Try to parse the date
                    date = new Date(item.created_at);

                    // Check if date is valid
                    if (isNaN(date.getTime())) {
                        // If invalid, use index as fallback
                        return `Point ${index + 1}`;
                    }
                } else {
                    // If no timestamp, use index as fallback
                    return `Point ${index + 1}`;
                }

                // Format the date
                return date.toLocaleDateString('zh-CN', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } catch (error) {
                console.warn('Error formatting date:', error, item.created_at);
                return `Point ${index + 1}`;
            }
        });
        const data = revenueData.map(item => parseFloat(item.total_profit_usd));

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        this.revenueChart = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Total Profit (USD)',
                    data: data,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: isDark ? '#f9fafc' : '#1e293b'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: isDark ? '#d1d5db' : '#64748b',
                            autoSkip: false,
                            maxRotation: 45,
                            minRotation: 0
                        },
                        grid: {
                            color: isDark ? '#4b5563' : '#e2e8f0'
                        }
                    },
                    y: {
                        ticks: {
                            color: isDark ? '#d1d5db' : '#64748b',
                            callback: function (value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        grid: {
                            color: isDark ? '#4b5563' : '#e2e8f0'
                        }
                    }
                }
            }
        });
    }

    filterBots(filter) {
        this.currentFilter = filter;
        this.loadBots();
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadSystemOverview();
            this.loadBots();
            this.loadRecentTransactions();
        }, 60000); // 1 minute default
    }

    changeRefreshInterval(seconds) {
        this.stopAutoRefresh();

        if (seconds > 0) {
            this.refreshInterval = setInterval(() => {
                this.loadSystemOverview();
                this.loadBots();
                this.loadRecentTransactions();
            }, seconds * 1000);
        }

        // Update button text to show current interval
        const button = document.querySelector('[data-bs-toggle="dropdown"]');
        if (button) {
            if (seconds === 0) {
                button.innerHTML = '<i class="fas fa-cog me-1"></i>Auto Refresh: Off';
            } else {
                const intervalText = seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m`;
                button.innerHTML = `<i class="fas fa-cog me-1"></i>Auto Refresh: ${intervalText}`;
            }
        }

        // Update dropdown items to show current selection
        this.updateRefreshDropdownSelection(seconds);

        console.log(`Auto-refresh interval changed to ${seconds} seconds`);
    }

    updateRefreshDropdownSelection(selectedSeconds) {
        const dropdownItems = document.querySelectorAll('.dropdown-menu .dropdown-item');
        dropdownItems.forEach(item => {
            item.classList.remove('active');
            const onclick = item.getAttribute('onclick');
            if (onclick) {
                const match = onclick.match(/changeRefreshInterval\((\d+)\)/);
                if (match && parseInt(match[1]) === selectedSeconds) {
                    item.classList.add('active');
                }
            }
        });
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async refreshData() {
        const refreshBtn = document.querySelector('.refresh-btn i');
        refreshBtn.className = 'fas fa-sync-alt loading';

        try {
            await Promise.all([
                this.loadSystemOverview(),
                this.loadBots(),
                this.loadRecentTransactions()
            ]);

            if (this.currentBotId) {
                await this.showBotDetails(this.currentBotId);
            }
        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showError('Failed to refresh data');
        } finally {
            refreshBtn.className = 'fas fa-sync-alt';
        }
    }

    showError(message) {
        // Simple error notification
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(alert);

        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    // Utility functions
    formatUSD(amount) {
        // Handle null, undefined, empty string, or NaN
        if (amount === null || amount === undefined || amount === '' || isNaN(amount)) {
            return '$0.00';
        }

        // Convert to number if it's a string
        const numAmount = typeof amount === 'string' ? parseFloat(amount) : Number(amount);

        // Check if conversion was successful
        if (isNaN(numAmount)) {
            return '$0.00';
        }

        // For very small amounts, use scientific notation or show more decimals
        if (Math.abs(numAmount) === 0) {
            return '$0.00';
        }

        // Format with 6 significant digits
        const formatted = this.formatSignificantDigits(numAmount, 6);
        return '$' + formatted;
    }

    formatSignificantDigits(num, significantDigits) {
        // Handle zero
        if (num === 0) return '0.00';

        // Get the order of magnitude
        const magnitude = Math.floor(Math.log10(Math.abs(num)));

        // Calculate decimal places needed for significant digits
        let decimalPlaces;
        if (magnitude >= 0) {
            // For numbers >= 1, decimal places = significantDigits - (magnitude + 1)
            decimalPlaces = Math.max(0, significantDigits - (magnitude + 1));
        } else {
            // For numbers < 1, decimal places = significantDigits + Math.abs(magnitude) - 1
            decimalPlaces = significantDigits + Math.abs(magnitude) - 1;
        }

        // Limit maximum decimal places to avoid overly long numbers
        decimalPlaces = Math.min(decimalPlaces, 10);

        // For very large numbers, use scientific notation if needed
        if (magnitude >= 12) {
            return num.toExponential(significantDigits - 1);
        }

        // Format the number
        const formatted = num.toFixed(decimalPlaces);

        // Remove trailing zeros after decimal point, but keep at least 2 decimal places for currency
        if (formatted.includes('.')) {
            let trimmed = formatted.replace(/0+$/, '');
            if (trimmed.endsWith('.')) {
                trimmed += '00'; // Ensure at least 2 decimal places for currency
            } else if (trimmed.split('.')[1].length === 1) {
                trimmed += '0'; // Ensure at least 2 decimal places for currency
            }
            return trimmed;
        }

        return formatted + '.00'; // Add .00 for whole numbers
    }

    formatNumber(num) {
        // Handle null, undefined, empty string, or NaN
        if (num === null || num === undefined || num === '' || isNaN(num)) {
            return '0';
        }

        // Convert to number if it's a string
        const numValue = typeof num === 'string' ? parseFloat(num) : Number(num);

        // Check if conversion was successful
        if (isNaN(numValue)) {
            return '0';
        }

        return new Intl.NumberFormat('en-US').format(numValue);
    }

    formatDateTime(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    }

    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN');
    }
}

// Global functions for HTML onclick handlers
function filterBots(filter) {
    if (dashboard) {
        dashboard.filterBots(filter);
    }
}

function refreshData() {
    if (dashboard) {
        dashboard.refreshData();
    }
}

function changeRefreshInterval(seconds) {
    if (dashboard) {
        dashboard.changeRefreshInterval(seconds);
    }
}

function stopAutoRefresh() {
    if (dashboard) {
        dashboard.stopAutoRefresh();
    }
}

// Initialize dashboard when DOM is loaded and Chart.js is ready
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    // Wait for Chart.js to be loaded
    if (typeof Chart !== 'undefined') {
        dashboard = new TradingBotDashboard();
    } else {
        // If Chart.js is not loaded yet, wait a bit and try again
        setTimeout(() => {
            if (typeof Chart !== 'undefined') {
                dashboard = new TradingBotDashboard();
            } else {
                console.error('Chart.js failed to load');
                // Initialize without chart functionality
                dashboard = new TradingBotDashboard();
            }
        }, 1000);
    }
}); 