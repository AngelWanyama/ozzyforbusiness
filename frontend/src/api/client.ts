const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private baseUrl = API_BASE;

  getToken(): string | null {
    return localStorage.getItem('ozzy_access_token');
  }

  setToken(token: string) {
    localStorage.setItem('ozzy_access_token', token);
  }

  clearToken() {
    localStorage.removeItem('ozzy_access_token');
  }

  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options.headers as Record<string, string>) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(`${this.baseUrl}${endpoint}`, { ...options, headers });
    if (res.status === 403 || res.status === 401) { this.clearToken(); window.location.hash = '#/login'; throw new Error('Auth failed'); }
    if (res.headers.get('content-type')?.includes('application/pdf')) return res as any;
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Request failed: ${res.status}`);
    return data;
  }

  async requestOTP(phoneNumber: string) {
    return this.request<{ message: string; debug_code: string }>('/auth/otp/request', {
      method: 'POST', body: JSON.stringify({ phone_number: phoneNumber }),
    });
  }

  async verifyOTP(phoneNumber: string, code: string) {
    const data = await this.request<{ access_token: string; token_type: string }>('/auth/otp/verify', {
      method: 'POST', body: JSON.stringify({ phone_number: phoneNumber, code }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async getReportSummary() { return this.request<any>('/reports/summary'); }
  async getTransactions(skip = 0, limit = 200) { return this.request<{ total: number; items: any[] }>(`/transactions?skip=${skip}&limit=${limit}`); }
  async createTransaction(data: any) { return this.request('/transactions', { method: 'POST', body: JSON.stringify(data) }); }
  async updateTransaction(id: string, data: any) { return this.request(`/transactions/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
  async deleteTransaction(id: string) { return this.request(`/transactions/${id}`, { method: 'DELETE' }); }
  async getInventory() { return this.request<any[]>('/inventory'); }
  async createItem(data: any) { return this.request('/inventory', { method: 'POST', body: JSON.stringify(data) }); }
  async updateItem(id: string, data: any) { return this.request(`/inventory/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
  async adjustStock(id: string, amount: number) { return this.request(`/inventory/${id}/adjust-stock`, { method: 'POST', body: JSON.stringify({ adjustment_amount: amount }) }); }
  async getUserPlan() { return this.request<any>('/users/plan'); }
  async getUserUsage() { return this.request<any>('/users/usage'); }
  async getAccountingReport(params: any) { return this.request<any>(`/reports/accounting?type=${params.type}&period=${params.period}`); }
  async getLatestSummary() { return this.request<any>('/summaries/latest'); }
}

export const api = new ApiClient();
export default api;