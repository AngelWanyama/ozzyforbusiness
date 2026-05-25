/**
 * Ozzy for Business API Client
 * Handles all communication with the FastAPI backend
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  constructor() {
    this.baseUrl = API_BASE;
  }

  getToken() {
    return localStorage.getItem('ozzy_access_token');
  }

  setToken(token) {
    localStorage.setItem('ozzy_access_token', token);
  }

  clearToken() {
    localStorage.removeItem('ozzy_access_token');
  }

  async request(endpoint, options = {}) {
    const token = this.getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 403 || response.status === 401) {
      // Token expired or invalid
      this.clearToken();
      window.location.hash = '#/login';
      throw new Error('Authentication failed');
    }

    // Handle PDF responses
    if (response.headers.get('content-type')?.includes('application/pdf')) {
      return response;
    }

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `Request failed: ${response.status}`);
    }
    return data;
  }

  // Auth endpoints
  async requestOTP(phoneNumber) {
    return this.request('/auth/otp/request', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber }),
    });
  }

  async verifyOTP(phoneNumber, code) {
    const data = await this.request('/auth/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber, code }),
    });
    this.setToken(data.access_token);
    return data;
  }

  // User endpoints
  async getUserPlan() {
    return this.request('/users/plan');
  }

  async getUserUsage() {
    return this.request('/users/usage');
  }

  async upgradePlan() {
    return this.request('/users/upgrade', { method: 'POST', body: JSON.stringify({}) });
  }

  // Transaction endpoints
  async getTransactions(skip = 0, limit = 100) {
    return this.request(`/transactions?skip=${skip}&limit=${limit}`);
  }

  async createTransaction(transactionData) {
    return this.request('/transactions', {
      method: 'POST',
      body: JSON.stringify(transactionData),
    });
  }

  // Summary/Report endpoints
  async getReportSummary() {
    return this.request('/reports/summary');
  }

  async getAccountingReport({ type, period, startDate, endDate, exportPdf } = {}) {
    let params = `type=${type}&period=${period || 'monthly'}`;
    if (startDate) params += `&start_date=${startDate}`;
    if (endDate) params += `&end_date=${endDate}`;
    if (exportPdf) params += `&export_pdf=true`;

    if (exportPdf) {
      const token = this.getToken();
      const url = `${this.baseUrl}/reports/accounting?${params}`;
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to export PDF');
      }
      return response;
    }
    return this.request(`/reports/accounting?${params}`);
  }

  // Summary endpoints
  async getLatestSummary() {
    return this.request('/summaries/latest');
  }

  async getDailySummary(date) {
    return this.request(`/summaries/daily?date=${date}`);
  }

  // Inventory endpoints
  async getInventory(skip = 0, limit = 100) {
    return this.request(`/inventory?skip=${skip}&limit=${limit}`);
  }

  async createItem(itemData) {
    return this.request('/inventory', {
      method: 'POST',
      body: JSON.stringify(itemData),
    });
  }

  async updateItem(itemId, itemData) {
    return this.request(`/inventory/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify(itemData),
    });
  }

  async adjustStock(itemId, adjustmentAmount) {
    return this.request(`/inventory/${itemId}/adjust-stock`, {
      method: 'POST',
      body: JSON.stringify({ adjustment_amount: adjustmentAmount }),
    });
  }

  // Chat endpoint
  async processChat(text) {
    return this.request('/chat/process', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  }
}

export const api = new ApiClient();
export default api;
