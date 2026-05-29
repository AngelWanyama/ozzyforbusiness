export interface User {
  id: string;
  phone_number: string;
  business_name?: string;
  business_type?: string;
  currency: string;
  plan_type: 'FREE' | 'PAID';
  payment_expiry_date?: string;
  transactions_this_month: number;
}

export interface Transaction {
  id: string;
  user_id: string;
  type: 'sale' | 'expense' | 'inventory_adjustment';
  amount: number;
  currency: string;
  item_id?: string;
  description?: string;
  quantity: number;
  transaction_date: string;
}

export interface Item {
  id: string;
  user_id: string;
  name: string;
  category?: string;
  unit_price: number;
  stock_level: number;
  is_service: boolean;
}

export interface SummaryReport {
  total_sales: number;
  total_expenses: number;
  net_profit: number;
  currency: string;
}