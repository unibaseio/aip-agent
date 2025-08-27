// Authentication Utilities Module
// 统一的认证工具模块，用于管理认证相关的功能

/**
 * 获取认证令牌
 * @returns {string} 认证令牌
 */
function getAuthToken() {
    return localStorage.getItem('auth_token') || 'aip-dex-default-token-2025';
}

/**
 * 设置认证令牌
 * @param {string} token - 要设置的认证令牌
 */
function setAuthToken(token) {
    if (token) {
        localStorage.setItem('auth_token', token);
    } else {
        localStorage.removeItem('auth_token');
    }
}

/**
 * 清除认证令牌
 */
function clearAuthToken() {
    localStorage.removeItem('auth_token');
}

/**
 * 检查是否有有效的认证令牌
 * @returns {boolean} 是否有有效令牌
 */
function hasValidAuthToken() {
    const token = getAuthToken();
    return token && token.length > 0;
}

/**
 * 获取带有认证头的请求配置
 * @param {Object} options - 额外的请求选项
 * @returns {Object} 包含认证头的请求配置
 */
function getAuthHeaders(options = {}) {
    return {
        ...options,
        headers: {
            'Authorization': `Bearer ${getAuthToken()}`,
            ...options.headers
        }
    };
}

// 如果在浏览器环境中，将函数添加到全局作用域
if (typeof window !== 'undefined') {
    window.AuthUtils = {
        getAuthToken,
        setAuthToken,
        clearAuthToken,
        hasValidAuthToken,
        getAuthHeaders
    };
}

// 如果在 Node.js 环境中，导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getAuthToken,
        setAuthToken,
        clearAuthToken,
        hasValidAuthToken,
        getAuthHeaders
    };
}