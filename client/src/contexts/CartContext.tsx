/**
 * CartContext
 * Global cart state management with Supabase persistence for authenticated users
 * Falls back to localStorage for unauthenticated users
 */

import React, { createContext, useContext, useReducer, useEffect, useCallback, useMemo, useRef } from 'react';
import { toast } from 'sonner';
import { supabase } from '@/integrations/supabase/client';
import type { CartItem, CartSignal, CartContextValue, CartState } from '@/types/cart';
import { CART_STORAGE_KEY } from '@/types/cart';

// Action types
type CartAction =
  | { type: 'ADD_ITEM'; payload: { signal: CartSignal; quantity: number } }
  | { type: 'REMOVE_ITEM'; payload: { ticker: string } }
  | { type: 'UPDATE_QUANTITY'; payload: { ticker: string; quantity: number } }
  | { type: 'CLEAR_CART' }
  | { type: 'TOGGLE_CART' }
  | { type: 'OPEN_CART' }
  | { type: 'CLOSE_CART' }
  | { type: 'LOAD_CART'; payload: { items: CartItem[] } };

// Initial state
const initialState: CartState = {
  items: [],
  isOpen: false,
};

// Reducer
function cartReducer(state: CartState, action: CartAction): CartState {
  switch (action.type) {
    case 'ADD_ITEM': {
      const existingIndex = state.items.findIndex(
        (item) => item.signal.ticker === action.payload.signal.ticker
      );

      if (existingIndex >= 0) {
        // Update existing item quantity
        const newItems = [...state.items];
        newItems[existingIndex] = {
          ...newItems[existingIndex],
          quantity: newItems[existingIndex].quantity + action.payload.quantity,
        };
        return { ...state, items: newItems };
      }

      // Add new item
      return {
        ...state,
        items: [
          ...state.items,
          {
            signal: action.payload.signal,
            quantity: action.payload.quantity,
            addedAt: new Date().toISOString(),
          },
        ],
      };
    }

    case 'REMOVE_ITEM':
      return {
        ...state,
        items: state.items.filter((item) => item.signal.ticker !== action.payload.ticker),
      };

    case 'UPDATE_QUANTITY': {
      if (action.payload.quantity < 1) return state;
      return {
        ...state,
        items: state.items.map((item) =>
          item.signal.ticker === action.payload.ticker
            ? { ...item, quantity: action.payload.quantity }
            : item
        ),
      };
    }

    case 'CLEAR_CART':
      return { ...state, items: [] };

    case 'TOGGLE_CART':
      return { ...state, isOpen: !state.isOpen };

    case 'OPEN_CART':
      return { ...state, isOpen: true };

    case 'CLOSE_CART':
      return { ...state, isOpen: false };

    case 'LOAD_CART':
      return { ...state, items: action.payload.items };

    default:
      return state;
  }
}

// Context
const CartContext = createContext<CartContextValue | null>(null);

// Helper: Convert CartItem to Supabase row
function cartItemToRow(item: CartItem, userId: string) {
  return {
    user_id: userId,
    signal_id: item.signal.id,
    ticker: item.signal.ticker,
    asset_name: item.signal.asset_name,
    signal_type: item.signal.signal_type,
    confidence_score: item.signal.confidence_score,
    politician_activity_count: item.signal.politician_activity_count,
    buy_sell_ratio: item.signal.buy_sell_ratio,
    target_price: item.signal.target_price,
    source: item.signal.source,
    quantity: item.quantity,
    total_transaction_volume: item.signal.total_transaction_volume,
    bipartisan: item.signal.bipartisan,
    signal_strength: item.signal.signal_strength,
    generated_at: item.signal.generated_at,
    added_at: item.addedAt,
  };
}

// Cart database row type
interface CartDatabaseRow {
  signal_id: string;
  ticker: string;
  asset_name: string;
  signal_type: string;
  confidence_score: string | number;
  politician_activity_count: number;
  buy_sell_ratio?: string | number | null;
  target_price?: string | number | null;
  source: string;
  total_transaction_volume?: string | number | null;
  bipartisan?: boolean | null;
  signal_strength?: string | null;
  generated_at: string;
  quantity: number;
  added_at: string;
}

// Helper: Convert Supabase row to CartItem
function rowToCartItem(row: CartDatabaseRow): CartItem {
  return {
    signal: {
      id: row.signal_id,
      ticker: row.ticker,
      asset_name: row.asset_name,
      signal_type: row.signal_type,
      confidence_score: parseFloat(row.confidence_score),
      politician_activity_count: row.politician_activity_count,
      buy_sell_ratio: row.buy_sell_ratio ? parseFloat(row.buy_sell_ratio) : undefined,
      target_price: row.target_price ? parseFloat(row.target_price) : undefined,
      source: row.source,
      total_transaction_volume: row.total_transaction_volume ? parseFloat(row.total_transaction_volume) : undefined,
      bipartisan: row.bipartisan,
      signal_strength: row.signal_strength,
      generated_at: row.generated_at,
    },
    quantity: row.quantity,
    addedAt: row.added_at,
  };
}

// Provider
export function CartProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, initialState);
  const [userId, setUserId] = React.useState<string | null>(null);
  const syncingRef = useRef(false);
  const initialLoadRef = useRef(false);

  // Load cart from localStorage (defined first for use in other callbacks)
  const loadCartFromLocalStorage = useCallback(() => {
    try {
      const savedCart = localStorage.getItem(CART_STORAGE_KEY);
      if (savedCart) {
        const parsed = JSON.parse(savedCart);
        if (Array.isArray(parsed)) {
          dispatch({ type: 'LOAD_CART', payload: { items: parsed } });
        }
      }
    } catch (e) {
      console.error('Failed to load cart from localStorage:', e);
    }
  }, []);

  // Sync cart to Supabase
  const syncCartToSupabase = useCallback(async (items: CartItem[], uid: string) => {
    if (syncingRef.current) return;

    try {
      syncingRef.current = true;

      // Delete existing cart items for this user
      await supabase
        .from('user_carts')
        .delete()
        .eq('user_id', uid);

      // Insert new cart items
      if (items.length > 0) {
        const rows = items.map((item) => cartItemToRow(item, uid));
        const { error } = await supabase
          .from('user_carts')
          .insert(rows);

        if (error) {
          console.error('Failed to sync cart to Supabase:', error);
        }
      }
    } catch (e) {
      console.error('Failed to sync cart to Supabase:', e);
    } finally {
      syncingRef.current = false;
    }
  }, []);

  // Load cart from Supabase
  const loadCartFromSupabase = useCallback(async (uid: string) => {
    try {
      syncingRef.current = true;
      const { data, error } = await supabase
        .from('user_carts')
        .select('*')
        .eq('user_id', uid)
        .order('added_at', { ascending: true });

      if (error) {
        console.error('Failed to load cart from Supabase:', error);
        // Fall back to localStorage
        loadCartFromLocalStorage();
        return;
      }

      if (data && data.length > 0) {
        const items = data.map(rowToCartItem);
        dispatch({ type: 'LOAD_CART', payload: { items } });
      } else {
        // No server cart - check localStorage for items to migrate
        const savedCart = localStorage.getItem(CART_STORAGE_KEY);
        if (savedCart) {
          const parsed = JSON.parse(savedCart);
          if (Array.isArray(parsed) && parsed.length > 0) {
            // Migrate localStorage items to Supabase
            dispatch({ type: 'LOAD_CART', payload: { items: parsed } });
            await syncCartToSupabase(parsed, uid);
          }
        }
      }
    } catch (e) {
      console.error('Failed to load cart from Supabase:', e);
      loadCartFromLocalStorage();
    } finally {
      syncingRef.current = false;
    }
  }, [loadCartFromLocalStorage, syncCartToSupabase]);

  // Listen for auth changes - onAuthStateChange fires with INITIAL_SESSION on mount
  useEffect(() => {
    // Load from localStorage immediately as fallback
    loadCartFromLocalStorage();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('[CartContext] Auth state changed:', event);
      const newUserId = session?.user?.id || null;
      setUserId(newUserId);

      if (newUserId && !initialLoadRef.current) {
        // User logged in - load cart from Supabase
        await loadCartFromSupabase(newUserId);
        initialLoadRef.current = true;
      } else if (!newUserId) {
        // User logged out - reset
        initialLoadRef.current = false;
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [loadCartFromLocalStorage, loadCartFromSupabase]);

  // Save cart when items change
  useEffect(() => {
    // Always save to localStorage as backup
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(state.items));
    } catch (e) {
      console.error('Failed to save cart to localStorage:', e);
    }

    // Sync to Supabase if authenticated
    if (userId && initialLoadRef.current) {
      syncCartToSupabase(state.items, userId);
    }
  }, [state.items, userId, syncCartToSupabase]);

  // Actions
  const addToCart = useCallback((signal: CartSignal, quantity: number = 1) => {
    const existingItem = state.items.find((item) => item.signal.ticker === signal.ticker);

    if (existingItem) {
      toast.info(`${signal.ticker} quantity updated in cart`);
    } else {
      toast.success(`${signal.ticker} added to cart`);
    }

    dispatch({ type: 'ADD_ITEM', payload: { signal, quantity } });
  }, [state.items]);

  const removeFromCart = useCallback((ticker: string) => {
    dispatch({ type: 'REMOVE_ITEM', payload: { ticker } });
    toast.success(`${ticker} removed from cart`);
  }, []);

  const updateQuantity = useCallback((ticker: string, quantity: number) => {
    dispatch({ type: 'UPDATE_QUANTITY', payload: { ticker, quantity } });
  }, []);

  const clearCart = useCallback(() => {
    dispatch({ type: 'CLEAR_CART' });
    toast.success('Cart cleared');
  }, []);

  const isInCart = useCallback(
    (ticker: string) => state.items.some((item) => item.signal.ticker === ticker),
    [state.items]
  );

  const getCartItem = useCallback(
    (ticker: string) => state.items.find((item) => item.signal.ticker === ticker),
    [state.items]
  );

  const toggleCart = useCallback(() => {
    dispatch({ type: 'TOGGLE_CART' });
  }, []);

  const openCart = useCallback(() => {
    dispatch({ type: 'OPEN_CART' });
  }, []);

  const closeCart = useCallback(() => {
    dispatch({ type: 'CLOSE_CART' });
  }, []);

  // Computed values
  const totalItems = useMemo(() => state.items.length, [state.items]);
  const totalShares = useMemo(
    () => state.items.reduce((sum, item) => sum + item.quantity, 0),
    [state.items]
  );

  const value: CartContextValue = {
    ...state,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    isInCart,
    getCartItem,
    toggleCart,
    openCart,
    closeCart,
    totalItems,
    totalShares,
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

// Hook
export function useCart() {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
}

export default CartContext;
