import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { CartProvider, useCart } from './CartContext';
import type { CartSignal } from '@/types/cart';

// Mock Supabase
const mockSupabaseFrom = vi.fn();
const mockSupabaseAuth = {
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(() => ({
    data: { subscription: { unsubscribe: vi.fn() } },
  })),
};

vi.mock('@/integrations/supabase/client', () => ({
  supabase: {
    from: (...args: any[]) => mockSupabaseFrom(...args),
    auth: mockSupabaseAuth,
  },
}));

// Mock toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  },
}));

// Sample test data
const mockSignal: CartSignal = {
  id: 'test-signal-1',
  ticker: 'AAPL',
  asset_name: 'Apple Inc.',
  signal_type: 'buy',
  confidence_score: 0.85,
  politician_activity_count: 5,
  buy_sell_ratio: 1.5,
  source: 'trading_signals',
};

const mockSignal2: CartSignal = {
  id: 'test-signal-2',
  ticker: 'GOOGL',
  asset_name: 'Alphabet Inc.',
  signal_type: 'strong_buy',
  confidence_score: 0.92,
  politician_activity_count: 8,
  source: 'playground',
};

describe('CartContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    // Default: no auth session
    mockSupabaseAuth.getSession.mockResolvedValue({
      data: { session: null },
    });

    // Default: empty Supabase responses
    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockReturnThis(),
      insert: vi.fn().mockReturnThis(),
      delete: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockResolvedValue({ data: [], error: null }),
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe('Basic Cart Operations', () => {
    it('should start with an empty cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      expect(result.current.items).toEqual([]);
      expect(result.current.totalItems).toBe(0);
      expect(result.current.totalShares).toBe(0);
    });

    it('should add item to cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      expect(result.current.items).toHaveLength(1);
      expect(result.current.items[0].signal.ticker).toBe('AAPL');
      expect(result.current.items[0].quantity).toBe(10);
      expect(result.current.totalItems).toBe(1);
      expect(result.current.totalShares).toBe(10);
    });

    it('should update quantity when adding same ticker', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      act(() => {
        result.current.addToCart(mockSignal, 5);
      });

      expect(result.current.items).toHaveLength(1);
      expect(result.current.items[0].quantity).toBe(15);
      expect(result.current.totalShares).toBe(15);
    });

    it('should add multiple different items', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
        result.current.addToCart(mockSignal2, 20);
      });

      expect(result.current.items).toHaveLength(2);
      expect(result.current.totalItems).toBe(2);
      expect(result.current.totalShares).toBe(30);
    });

    it('should remove item from cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
        result.current.addToCart(mockSignal2, 20);
      });

      act(() => {
        result.current.removeFromCart('AAPL');
      });

      expect(result.current.items).toHaveLength(1);
      expect(result.current.items[0].signal.ticker).toBe('GOOGL');
      expect(result.current.totalItems).toBe(1);
    });

    it('should update item quantity', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      act(() => {
        result.current.updateQuantity('AAPL', 25);
      });

      expect(result.current.items[0].quantity).toBe(25);
      expect(result.current.totalShares).toBe(25);
    });

    it('should not update quantity to less than 1', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      act(() => {
        result.current.updateQuantity('AAPL', 0);
      });

      expect(result.current.items[0].quantity).toBe(10); // Unchanged
    });

    it('should clear cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
        result.current.addToCart(mockSignal2, 20);
      });

      act(() => {
        result.current.clearCart();
      });

      expect(result.current.items).toEqual([]);
      expect(result.current.totalItems).toBe(0);
    });

    it('should check if item is in cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      expect(result.current.isInCart('AAPL')).toBe(true);
      expect(result.current.isInCart('GOOGL')).toBe(false);
    });

    it('should get cart item by ticker', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      const item = result.current.getCartItem('AAPL');
      expect(item).toBeDefined();
      expect(item?.signal.ticker).toBe('AAPL');
      expect(item?.quantity).toBe(10);

      const notFound = result.current.getCartItem('MSFT');
      expect(notFound).toBeUndefined();
    });
  });

  describe('Cart UI State', () => {
    it('should toggle cart open/closed', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      expect(result.current.isOpen).toBe(false);

      act(() => {
        result.current.toggleCart();
      });
      expect(result.current.isOpen).toBe(true);

      act(() => {
        result.current.toggleCart();
      });
      expect(result.current.isOpen).toBe(false);
    });

    it('should open cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.openCart();
      });

      expect(result.current.isOpen).toBe(true);
    });

    it('should close cart', () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.openCart();
      });

      act(() => {
        result.current.closeCart();
      });

      expect(result.current.isOpen).toBe(false);
    });
  });

  describe('localStorage Persistence', () => {
    it('should save cart to localStorage', async () => {
      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      await waitFor(() => {
        const saved = localStorage.getItem('govmarket-cart');
        expect(saved).toBeDefined();
        const parsed = JSON.parse(saved!);
        expect(parsed).toHaveLength(1);
        expect(parsed[0].signal.ticker).toBe('AAPL');
      });
    });

    it('should load cart from localStorage on mount', async () => {
      // Pre-populate localStorage
      const savedCart = [
        {
          signal: mockSignal,
          quantity: 15,
          addedAt: new Date().toISOString(),
        },
      ];
      localStorage.setItem('govmarket-cart', JSON.stringify(savedCart));

      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      await waitFor(() => {
        expect(result.current.items).toHaveLength(1);
        expect(result.current.items[0].signal.ticker).toBe('AAPL');
        expect(result.current.items[0].quantity).toBe(15);
      });
    });

    it('should handle corrupted localStorage gracefully', async () => {
      localStorage.setItem('govmarket-cart', 'not-valid-json');

      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      // Should start with empty cart despite corrupted data
      await waitFor(() => {
        expect(result.current.items).toEqual([]);
      });
    });
  });

  describe('Supabase Sync (Authenticated)', () => {
    const mockUserId = 'test-user-123';

    beforeEach(() => {
      // Set up authenticated session
      mockSupabaseAuth.getSession.mockResolvedValue({
        data: {
          session: {
            user: { id: mockUserId },
          },
        },
      });

      mockSupabaseAuth.onAuthStateChange.mockImplementation((callback) => {
        // Simulate auth state change
        setTimeout(() => {
          callback('SIGNED_IN', { user: { id: mockUserId } });
        }, 0);
        return {
          data: { subscription: { unsubscribe: vi.fn() } },
        };
      });
    });

    it('should load cart from Supabase when authenticated', async () => {
      const supabaseCartData = [
        {
          signal_id: 'test-signal-1',
          ticker: 'AAPL',
          asset_name: 'Apple Inc.',
          signal_type: 'buy',
          confidence_score: 0.85,
          politician_activity_count: 5,
          source: 'trading_signals',
          quantity: 20,
          added_at: new Date().toISOString(),
        },
      ];

      mockSupabaseFrom.mockReturnValue({
        select: vi.fn().mockReturnThis(),
        insert: vi.fn().mockReturnThis(),
        delete: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        order: vi.fn().mockResolvedValue({ data: supabaseCartData, error: null }),
      });

      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      await waitFor(() => {
        expect(result.current.items).toHaveLength(1);
        expect(result.current.items[0].quantity).toBe(20);
      });
    });

    it('should sync cart to Supabase when items change', async () => {
      const mockInsert = vi.fn().mockResolvedValue({ error: null });
      const mockDelete = vi.fn().mockReturnThis();

      mockSupabaseFrom.mockReturnValue({
        select: vi.fn().mockReturnThis(),
        insert: mockInsert,
        delete: vi.fn().mockReturnValue({
          eq: mockDelete.mockResolvedValue({ error: null }),
        }),
        eq: vi.fn().mockReturnThis(),
        order: vi.fn().mockResolvedValue({ data: [], error: null }),
      });

      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      // Wait for initial load
      await waitFor(() => {
        expect(mockSupabaseFrom).toHaveBeenCalled();
      });

      act(() => {
        result.current.addToCart(mockSignal, 10);
      });

      // Sync happens on items change
      await waitFor(() => {
        expect(mockSupabaseFrom).toHaveBeenCalledWith('user_carts');
      });
    });

    it('should fall back to localStorage on Supabase error', async () => {
      // Pre-populate localStorage
      const savedCart = [
        {
          signal: mockSignal,
          quantity: 15,
          addedAt: new Date().toISOString(),
        },
      ];
      localStorage.setItem('govmarket-cart', JSON.stringify(savedCart));

      mockSupabaseFrom.mockReturnValue({
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        order: vi.fn().mockResolvedValue({ data: null, error: { message: 'DB Error' } }),
      });

      const { result } = renderHook(() => useCart(), {
        wrapper: CartProvider,
      });

      await waitFor(() => {
        // Should fall back to localStorage data
        expect(result.current.items).toHaveLength(1);
        expect(result.current.items[0].quantity).toBe(15);
      });
    });
  });
});

describe('useCart hook', () => {
  it('should throw error when used outside CartProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useCart());
    }).toThrow('useCart must be used within a CartProvider');

    consoleSpy.mockRestore();
  });
});
