/**
 * Cart Types
 * Unified cart types that work with both TradingSignal and PreviewSignal
 */

import type { SignalType } from './signal-playground';

/**
 * Unified signal representation for cart items
 * Contains the common fields needed for trading operations
 */
export interface CartSignal {
  // Unique identifier - ticker for preview signals, id for persisted signals
  id: string;
  ticker: string;
  asset_name?: string;
  signal_type: SignalType;
  confidence_score: number;
  politician_activity_count: number;
  buy_sell_ratio?: number;
  target_price?: number;
  // Source information
  source: 'trading_signals' | 'playground';
  // Optional fields from different sources
  total_transaction_volume?: number;
  bipartisan?: boolean;
  signal_strength?: string;
  generated_at?: string;
}

/**
 * Cart item with signal and quantity
 */
export interface CartItem {
  signal: CartSignal;
  quantity: number;
  addedAt: string;
}

/**
 * Cart state
 */
export interface CartState {
  items: CartItem[];
  isOpen: boolean;
}

/**
 * Cart context actions
 */
export interface CartActions {
  addToCart: (signal: CartSignal, quantity?: number) => void;
  removeFromCart: (ticker: string) => void;
  updateQuantity: (ticker: string, quantity: number) => void;
  clearCart: () => void;
  isInCart: (ticker: string) => boolean;
  getCartItem: (ticker: string) => CartItem | undefined;
  toggleCart: () => void;
  openCart: () => void;
  closeCart: () => void;
}

export interface CartContextValue extends CartState, CartActions {
  totalItems: number;
  totalShares: number;
}

export const CART_STORAGE_KEY = 'govmarket-cart';
