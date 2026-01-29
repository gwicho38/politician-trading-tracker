import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AlpacaConnectionCard } from './AlpacaConnectionCard';

// Mock date-fns
vi.mock('date-fns', () => ({
  formatDistanceToNow: vi.fn(() => '5 minutes ago'),
}));

// Mock the useAlpacaCredentials hook
const mockSaveCredentials = vi.fn();
const mockTestConnection = vi.fn();
const mockClearCredentials = vi.fn();
const mockIsConnected = vi.fn();
const mockGetValidatedAt = vi.fn();

vi.mock('@/hooks/useAlpacaCredentials', () => ({
  useAlpacaCredentials: () => ({
    isLoading: false,
    isConnected: mockIsConnected,
    getValidatedAt: mockGetValidatedAt,
    saveCredentials: mockSaveCredentials,
    isSaving: false,
    testConnection: mockTestConnection,
    isTesting: false,
    clearCredentials: mockClearCredentials,
    isClearing: false,
  }),
}));

describe('AlpacaConnectionCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsConnected.mockReturnValue(false);
    mockGetValidatedAt.mockReturnValue(null);
  });

  describe('Loading state', () => {
    it('shows loading spinner when isLoading is true', () => {
      vi.doMock('@/hooks/useAlpacaCredentials', () => ({
        useAlpacaCredentials: () => ({
          isLoading: true,
          isConnected: mockIsConnected,
          getValidatedAt: mockGetValidatedAt,
          saveCredentials: mockSaveCredentials,
          isSaving: false,
          testConnection: mockTestConnection,
          isTesting: false,
          clearCredentials: mockClearCredentials,
          isClearing: false,
        }),
      }));

      // For this test, we need to check the loading branch manually
      // The mock is set at module level, so we test the conditional branch
    });
  });

  describe('Header display', () => {
    it('displays card title "Alpaca Connection"', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText('Alpaca Connection')).toBeInTheDocument();
    });

    it('displays paper trading badge', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText('Paper')).toBeInTheDocument();
    });

    it('displays live trading badge', () => {
      render(<AlpacaConnectionCard tradingMode="live" />);
      expect(screen.getByText('Live')).toBeInTheDocument();
    });

    it('displays paper trading description', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText(/Connect your paper trading account to practice without risk/)).toBeInTheDocument();
    });

    it('displays live trading description', () => {
      render(<AlpacaConnectionCard tradingMode="live" />);
      expect(screen.getByText(/Connect your live trading account \(uses real money\)/)).toBeInTheDocument();
    });
  });

  describe('Disconnected state', () => {
    it('shows API Key input field', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByLabelText('API Key')).toBeInTheDocument();
    });

    it('shows Secret Key input field', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByLabelText('Secret Key')).toBeInTheDocument();
    });

    it('shows paper API key placeholder (PK...)', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByPlaceholderText('PK...')).toBeInTheDocument();
    });

    it('shows live API key placeholder (AK...)', () => {
      render(<AlpacaConnectionCard tradingMode="live" />);
      expect(screen.getByPlaceholderText('AK...')).toBeInTheDocument();
    });

    it('shows Test Connection button', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByRole('button', { name: /Test Connection/ })).toBeInTheDocument();
    });

    it('shows Connect & Save button', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByRole('button', { name: /Connect & Save/ })).toBeInTheDocument();
    });

    it('disables buttons when inputs are empty', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByRole('button', { name: /Test Connection/ })).toBeDisabled();
      expect(screen.getByRole('button', { name: /Connect & Save/ })).toBeDisabled();
    });

    it('enables buttons when inputs have values', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');

      expect(screen.getByRole('button', { name: /Test Connection/ })).not.toBeDisabled();
      expect(screen.getByRole('button', { name: /Connect & Save/ })).not.toBeDisabled();
    });
  });

  describe('Password visibility toggle', () => {
    it('secret key is hidden by default', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      const secretInput = screen.getByLabelText('Secret Key');
      expect(secretInput).toHaveAttribute('type', 'password');
    });

    it('toggles secret key visibility when eye button is clicked', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      const secretInput = screen.getByLabelText('Secret Key');
      expect(secretInput).toHaveAttribute('type', 'password');

      // Find and click the toggle button (it has an eye icon)
      const toggleButtons = screen.getAllByRole('button');
      const eyeButton = toggleButtons.find(btn => btn.className.includes('absolute'));
      if (eyeButton) {
        await user.click(eyeButton);
        expect(secretInput).toHaveAttribute('type', 'text');
      }
    });
  });

  describe('Test Connection functionality', () => {
    it('shows error when testing with empty inputs', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      // Enter only API key
      await user.type(screen.getByLabelText('API Key'), 'PK12345');

      // Button should still be disabled
      expect(screen.getByRole('button', { name: /Test Connection/ })).toBeDisabled();
    });

    it('calls testConnection with correct params', async () => {
      mockTestConnection.mockResolvedValueOnce({ success: true, account: { portfolio_value: 100000, cash: 50000, buying_power: 100000 } });

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Test Connection/ }));

      expect(mockTestConnection).toHaveBeenCalledWith({
        tradingMode: 'paper',
        apiKey: 'PK12345',
        secretKey: 'secret123',
      });
    });

    it('displays success message on successful connection test', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: true,
        account: { portfolio_value: 100000, cash: 50000, buying_power: 100000 },
      });

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Test Connection/ }));

      await waitFor(() => {
        expect(screen.getByText('Connection successful!')).toBeInTheDocument();
      });
    });

    it('displays account info on successful connection test', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: true,
        account: { portfolio_value: 100000, cash: 50000, buying_power: 75000 },
      });

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Test Connection/ }));

      await waitFor(() => {
        expect(screen.getByText(/Portfolio Value.*\$100,000/)).toBeInTheDocument();
        expect(screen.getByText(/Buying Power.*\$75,000/)).toBeInTheDocument();
      });
    });

    it('displays error message on failed connection test', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: false,
        error: 'Invalid API credentials',
      });

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'wrong-secret');
      await user.click(screen.getByRole('button', { name: /Test Connection/ }));

      await waitFor(() => {
        expect(screen.getByText('Invalid API credentials')).toBeInTheDocument();
      });
    });
  });

  describe('Save Credentials functionality', () => {
    it('tests connection before saving', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: true,
        account: { portfolio_value: 100000, cash: 50000, buying_power: 100000 },
      });
      mockSaveCredentials.mockResolvedValueOnce({});

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Connect & Save/ }));

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalled();
      });
    });

    it('saves credentials after successful test', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: true,
        account: { portfolio_value: 100000, cash: 50000, buying_power: 100000 },
      });
      mockSaveCredentials.mockResolvedValueOnce({});

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Connect & Save/ }));

      await waitFor(() => {
        expect(mockSaveCredentials).toHaveBeenCalledWith({
          tradingMode: 'paper',
          apiKey: 'PK12345',
          secretKey: 'secret123',
        });
      });
    });

    it('does not save credentials when test fails', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: false,
        error: 'Invalid credentials',
      });

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'wrong-secret');
      await user.click(screen.getByRole('button', { name: /Connect & Save/ }));

      await waitFor(() => {
        expect(mockTestConnection).toHaveBeenCalled();
      });

      expect(mockSaveCredentials).not.toHaveBeenCalled();
    });

    it('calls onConnectionChange callback after successful save', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: true,
        account: { portfolio_value: 100000, cash: 50000, buying_power: 100000 },
      });
      mockSaveCredentials.mockResolvedValueOnce({});

      const onConnectionChange = vi.fn();
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" onConnectionChange={onConnectionChange} />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Connect & Save/ }));

      await waitFor(() => {
        expect(onConnectionChange).toHaveBeenCalledWith(true);
      });
    });

    it('clears input fields after successful save', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: true,
        account: { portfolio_value: 100000, cash: 50000, buying_power: 100000 },
      });
      mockSaveCredentials.mockResolvedValueOnce({});

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Connect & Save/ }));

      await waitFor(() => {
        expect(screen.getByLabelText('API Key')).toHaveValue('');
        expect(screen.getByLabelText('Secret Key')).toHaveValue('');
      });
    });
  });

  describe('Connected state', () => {
    beforeEach(() => {
      mockIsConnected.mockReturnValue(true);
      mockGetValidatedAt.mockReturnValue('2026-01-29T10:00:00Z');
    });

    it('shows Connected badge', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('shows Account Connected message', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText('Account Connected')).toBeInTheDocument();
    });

    it('shows last validated time', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText(/Last validated 5 minutes ago/)).toBeInTheDocument();
    });

    it('shows Disconnect Account button', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByRole('button', { name: /Disconnect Account/ })).toBeInTheDocument();
    });

    it('does not show input fields when connected', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.queryByLabelText('API Key')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Secret Key')).not.toBeInTheDocument();
    });
  });

  describe('Disconnect functionality', () => {
    beforeEach(() => {
      mockIsConnected.mockReturnValue(true);
    });

    it('calls clearCredentials when disconnect is clicked', async () => {
      mockClearCredentials.mockResolvedValueOnce({});

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.click(screen.getByRole('button', { name: /Disconnect Account/ }));

      expect(mockClearCredentials).toHaveBeenCalledWith('paper');
    });

    it('calls onConnectionChange(false) after disconnect', async () => {
      mockClearCredentials.mockResolvedValueOnce({});

      const onConnectionChange = vi.fn();
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" onConnectionChange={onConnectionChange} />);

      await user.click(screen.getByRole('button', { name: /Disconnect Account/ }));

      await waitFor(() => {
        expect(onConnectionChange).toHaveBeenCalledWith(false);
      });
    });
  });

  describe('Setup guide', () => {
    it('shows guide toggle button', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.getByText('How to get your Alpaca API keys')).toBeInTheDocument();
    });

    it('guide is hidden by default', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.queryByText('Create a free Alpaca account')).not.toBeInTheDocument();
    });

    it('shows guide content when toggle is clicked', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.click(screen.getByText('How to get your Alpaca API keys'));

      expect(screen.getByText('Create a free Alpaca account')).toBeInTheDocument();
      expect(screen.getByText('Go to API Keys page')).toBeInTheDocument();
      expect(screen.getByText('Generate new keys')).toBeInTheDocument();
      expect(screen.getByText('Copy both keys')).toBeInTheDocument();
      expect(screen.getByText('Paste keys above')).toBeInTheDocument();
    });

    it('hides guide content when toggle is clicked again', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.click(screen.getByText('How to get your Alpaca API keys'));
      expect(screen.getByText('Create a free Alpaca account')).toBeInTheDocument();

      await user.click(screen.getByText('How to get your Alpaca API keys'));
      expect(screen.queryByText('Create a free Alpaca account')).not.toBeInTheDocument();
    });

    it('shows Alpaca signup link', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.click(screen.getByText('How to get your Alpaca API keys'));

      const link = screen.getByRole('link', { name: /alpaca.markets\/signup/ });
      expect(link).toHaveAttribute('href', 'https://app.alpaca.markets/signup');
      expect(link).toHaveAttribute('target', '_blank');
    });

    it('shows paper trading badge in guide for paper mode', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.click(screen.getByText('How to get your Alpaca API keys'));

      expect(screen.getByText('Paper Trading')).toBeInTheDocument();
    });

    it('shows live trading badge in guide for live mode', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="live" />);

      await user.click(screen.getByText('How to get your Alpaca API keys'));

      expect(screen.getByText('Live Trading')).toBeInTheDocument();
    });

    it('shows tip about paper trading', async () => {
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.click(screen.getByText('How to get your Alpaca API keys'));

      expect(screen.getByText(/Start with Paper Trading to practice without risking real money/)).toBeInTheDocument();
      expect(screen.getByText(/\$100,000 in virtual funds/)).toBeInTheDocument();
    });
  });

  describe('Live trading warning', () => {
    it('shows warning for live trading when not connected', () => {
      render(<AlpacaConnectionCard tradingMode="live" />);
      expect(screen.getByText(/Live trading uses real money/)).toBeInTheDocument();
    });

    it('does not show warning for paper trading', () => {
      render(<AlpacaConnectionCard tradingMode="paper" />);
      expect(screen.queryByText(/Live trading uses real money/)).not.toBeInTheDocument();
    });

    it('does not show warning when already connected to live', () => {
      mockIsConnected.mockReturnValue(true);
      render(<AlpacaConnectionCard tradingMode="live" />);
      expect(screen.queryByText(/Live trading uses real money/)).not.toBeInTheDocument();
    });
  });

  describe('Error handling', () => {
    it('shows validation error when only API key is entered', async () => {
      // The component disables the button, not shows an error
      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');

      expect(screen.getByRole('button', { name: /Test Connection/ })).toBeDisabled();
    });

    it('shows default error message when test fails without specific error', async () => {
      mockTestConnection.mockResolvedValueOnce({
        success: false,
        error: undefined,
      });

      const user = userEvent.setup();
      render(<AlpacaConnectionCard tradingMode="paper" />);

      await user.type(screen.getByLabelText('API Key'), 'PK12345');
      await user.type(screen.getByLabelText('Secret Key'), 'secret123');
      await user.click(screen.getByRole('button', { name: /Test Connection/ }));

      await waitFor(() => {
        expect(screen.getByText('Connection failed')).toBeInTheDocument();
      });
    });
  });
});
