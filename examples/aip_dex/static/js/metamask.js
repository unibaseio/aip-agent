// MetaMask Login Module
class MetaMaskLogin {
    constructor() {
        this.isConnected = false;
        this.currentAccount = null;
        this.ownerId = null;
        this.provider = null;
        this.init();
    }

    init() {
        this.checkConnection();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // MetaMask connection events
        if (typeof window.ethereum !== 'undefined') {
            this.provider = window.ethereum;

            this.provider.on('accountsChanged', (accounts) => {
                this.handleAccountsChanged(accounts);
            });

            this.provider.on('chainChanged', (chainId) => {
                this.handleChainChanged(chainId);
            });

            this.provider.on('disconnect', () => {
                this.handleDisconnect();
            });

            // Listen for connection status
            this.provider.on('connect', (connectInfo) => {
                console.log('MetaMask connected:', connectInfo);
            });
        }
    }

    async checkConnection() {
        if (typeof window.ethereum !== 'undefined') {
            try {
                // Check if MetaMask is installed and accessible
                const isMetaMask = window.ethereum.isMetaMask;
                if (!isMetaMask) {
                    console.warn('MetaMask not detected');
                    return;
                }

                // Check if already connected
                const accounts = await window.ethereum.request({ method: 'eth_accounts' });
                if (accounts.length > 0) {
                    await this.handleAccountsChanged(accounts);
                } else {
                    // Check if user has previously connected and try to restore session
                    await this.tryRestoreSession();
                }
            } catch (error) {
                console.error('Error checking MetaMask connection:', error);
            }
        } else {
            console.warn('MetaMask not installed');
        }
    }

    async tryRestoreSession() {
        const savedOwnerId = localStorage.getItem('owner_id');
        const savedWallet = localStorage.getItem('wallet_address');
        const sessionExpiry = localStorage.getItem('session_expiry');

        if (savedOwnerId && savedWallet) {
            // Check if session is still valid (24 hours)
            const now = Date.now();
            const expiry = sessionExpiry ? parseInt(sessionExpiry) : 0;

            if (now < expiry) {
                // Session is still valid, try to reconnect silently
                try {
                    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                    if (accounts.length > 0 && accounts[0].toLowerCase() === savedWallet.toLowerCase()) {
                        // Same wallet, restore session without re-authentication
                        this.currentAccount = accounts[0];
                        this.ownerId = savedOwnerId;
                        this.isConnected = true;
                        this.updateUI();
                        console.log('Session restored successfully');
                        return true;
                    }
                } catch (error) {
                    console.log('Silent reconnection failed, user needs to manually connect');
                }
            } else {
                // Session expired, clear old data
                localStorage.removeItem('owner_id');
                localStorage.removeItem('wallet_address');
                localStorage.removeItem('session_expiry');
                console.log('Session expired, cleared old data');
            }
        }
        return false;
    }

    async connectWallet() {
        if (typeof window.ethereum === 'undefined') {
            this.showError('MetaMask is not installed. Please install MetaMask to continue.');
            return false;
        }

        try {
            // Check if MetaMask is installed
            const isMetaMask = window.ethereum.isMetaMask;
            if (!isMetaMask) {
                this.showError('MetaMask is not installed. Please install MetaMask to continue.');
                return false;
            }

            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length > 0) {
                await this.handleAccountsChanged(accounts);
                return true;
            } else {
                this.showError('No accounts found. Please unlock MetaMask.');
                return false;
            }
        } catch (error) {
            if (error.code === 4001) {
                this.showError('User rejected the connection request.');
            } else {
                this.showError('Error connecting to MetaMask: ' + error.message);
            }
            return false;
        }
    }

    async handleAccountsChanged(accounts) {
        if (accounts.length === 0) {
            this.handleDisconnect();
        } else if (accounts[0] !== this.currentAccount) {
            this.currentAccount = accounts[0];
            await this.onAccountChanged();
        }
    }

    async handleChainChanged(chainId) {
        console.log('Chain changed to:', chainId);
        // Reload the page when chain changes
        window.location.reload();
    }

    handleDisconnect() {
        this.isConnected = false;
        this.currentAccount = null;
        this.ownerId = null;
        this.updateUI();
    }

    async onAccountChanged() {
        this.isConnected = true;
        await this.authenticateUser();
        this.updateUI();
    }

    async authenticateUser() {
        if (!this.currentAccount) return;

        try {
            // Check if we already have a valid session for this wallet
            const savedOwnerId = localStorage.getItem('owner_id');
            const savedWallet = localStorage.getItem('wallet_address');
            const sessionExpiry = localStorage.getItem('session_expiry');

            if (savedOwnerId && savedWallet && sessionExpiry) {
                const now = Date.now();
                const expiry = parseInt(sessionExpiry);

                if (now < expiry && savedWallet.toLowerCase() === this.currentAccount.toLowerCase()) {
                    // Valid session exists, use it without re-signing
                    this.ownerId = savedOwnerId;
                    this.isConnected = true;
                    this.updateUI();
                    console.log('Using existing session');
                    return;
                }
            }

            // Get signature for authentication
            const message = `Login to AIP DEX Trading Bot\n\nWallet: ${this.currentAccount}\nTimestamp: ${Date.now()}`;
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, this.currentAccount]
            });

            // Send authentication request to backend
            const response = await fetch('/api/v1/auth/metamask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    wallet_address: this.currentAccount,
                    signature: signature,
                    message: message
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.ownerId = data.owner_id;

                // Store session data with 24-hour expiry
                const expiry = Date.now() + (24 * 60 * 60 * 1000); // 24 hours
                localStorage.setItem('owner_id', this.ownerId);
                localStorage.setItem('wallet_address', this.currentAccount);
                localStorage.setItem('session_expiry', expiry.toString());

                this.showSuccess('Successfully authenticated with MetaMask');
            } else {
                const error = await response.json();
                this.showError('Authentication failed: ' + error.detail);
            }
        } catch (error) {
            console.error('Authentication error:', error);
            this.showError('Authentication failed: ' + error.message);
        }
    }

    getAuthToken() {
        return localStorage.getItem('auth_token') || 'aip-dex-default-token-2025';
    }

    updateUI() {
        const loginBtn = document.getElementById('metamask-login-btn');
        const userInfo = document.getElementById('user-info');
        const claimBotBtn = document.getElementById('claim-bot-btn');

        if (this.isConnected && this.currentAccount) {
            // Show user info
            if (loginBtn) loginBtn.style.display = 'none';
            if (userInfo) {
                userInfo.style.display = 'block';
                userInfo.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="fas fa-wallet text-success me-2"></i>
                        <span class="text-success fw-medium">${this.formatAddress(this.currentAccount)}</span>
                        <button class="btn btn-outline-danger btn-sm ms-2" onclick="metamaskLogin.disconnect()">
                            <i class="fas fa-sign-out-alt"></i>
                        </button>
                    </div>
                `;
            }
            if (claimBotBtn) claimBotBtn.style.display = 'block';
        } else {
            // Show login button
            if (loginBtn) loginBtn.style.display = 'block';
            if (userInfo) userInfo.style.display = 'none';
            if (claimBotBtn) claimBotBtn.style.display = 'none';
        }
    }

    async disconnect() {
        this.isConnected = false;
        this.currentAccount = null;
        this.ownerId = null;
        localStorage.removeItem('owner_id');
        localStorage.removeItem('wallet_address');
        localStorage.removeItem('session_expiry');
        this.updateUI();
        this.showSuccess('Disconnected from MetaMask');
    }

    formatAddress(address) {
        if (!address) return '';
        return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'danger');
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // Bot claiming functionality
    async claimUnclaimedBot(botId) {
        if (!this.isConnected || !this.ownerId) {
            this.showError('Please connect MetaMask first');
            return false;
        }

        try {
            const response = await fetch(`/api/v1/bots/${botId}/claim`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    owner_id: this.ownerId,
                    wallet_address: this.currentAccount
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showSuccess('Successfully claimed bot!');
                return true;
            } else {
                const error = await response.json();
                this.showError('Failed to claim bot: ' + error.detail);
                return false;
            }
        } catch (error) {
            console.error('Error claiming bot:', error);
            this.showError('Error claiming bot: ' + error.message);
            return false;
        }
    }

    // Strategy management
    async createStrategy(strategyData) {
        if (!this.isConnected || !this.ownerId) {
            this.showError('Please connect MetaMask first');
            return null;
        }

        try {
            const response = await fetch('/api/v1/strategies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    ...strategyData,
                    owner_id: this.ownerId
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showSuccess('Strategy created successfully!');
                return data;
            } else {
                const error = await response.json();
                this.showError('Failed to create strategy: ' + error.detail);
                return null;
            }
        } catch (error) {
            console.error('Error creating strategy:', error);
            this.showError('Error creating strategy: ' + error.message);
            return null;
        }
    }

    async configureBot(botId, strategyId) {
        if (!this.isConnected || !this.ownerId) {
            this.showError('Please connect MetaMask first');
            return false;
        }

        try {
            const response = await fetch(`/api/v1/bots/${botId}/configure`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.getAuthToken()}`
                },
                body: JSON.stringify({
                    owner_id: this.ownerId,
                    strategy_id: strategyId
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showSuccess('Bot configured successfully!');
                return true;
            } else {
                const error = await response.json();
                this.showError('Failed to configure bot: ' + error.detail);
                return false;
            }
        } catch (error) {
            console.error('Error configuring bot:', error);
            this.showError('Error configuring bot: ' + error.message);
            return false;
        }
    }

    async getUnclaimedBots() {
        try {
            const response = await fetch('/api/v1/bots/unclaimed', {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                return await response.json();
            } else {
                console.error('Failed to get unclaimed bots');
                return [];
            }
        } catch (error) {
            console.error('Error getting unclaimed bots:', error);
            return [];
        }
    }

    async getMyStrategies() {
        if (!this.ownerId) return [];

        try {
            const response = await fetch(`/api/v1/strategies/owner/${this.ownerId}`, {
                headers: {
                    'Authorization': `Bearer ${this.getAuthToken()}`
                }
            });

            if (response.ok) {
                return await response.json();
            } else {
                console.error('Failed to get strategies');
                return [];
            }
        } catch (error) {
            console.error('Error getting strategies:', error);
            return [];
        }
    }

    // Check if MetaMask is available
    isMetaMaskAvailable() {
        return typeof window.ethereum !== 'undefined' && window.ethereum.isMetaMask;
    }

    // Get current network
    async getCurrentNetwork() {
        if (!this.isMetaMaskAvailable()) return null;

        try {
            const chainId = await window.ethereum.request({ method: 'eth_chainId' });
            return chainId;
        } catch (error) {
            console.error('Error getting network:', error);
            return null;
        }
    }

    // Switch network (if needed)
    async switchNetwork(chainId) {
        if (!this.isMetaMaskAvailable()) return false;

        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: chainId }],
            });
            return true;
        } catch (error) {
            console.error('Error switching network:', error);
            return false;
        }
    }
}

// Initialize MetaMask login globally
let metamaskLogin = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    if (typeof MetaMaskLogin !== 'undefined') {
        metamaskLogin = new MetaMaskLogin();
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MetaMaskLogin;
} 