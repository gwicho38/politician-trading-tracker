/**
 * CartContext
 * Global cart state management with localStorage persistence
 */

import React, { createContext, useContext, useReducer, useEffect, useCallback, useMemo } from 'react';
import { toast } from 'sonner';
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

// Provider
export function CartProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, initialState);

  // Load cart from localStorage on mount
  useEffect(() => {
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

  // Save cart to localStorage when items change
  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(state.items));
    } catch (e) {
      console.error('Failed to save cart to localStorage:', e);
    }
  }, [state.items]);

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
