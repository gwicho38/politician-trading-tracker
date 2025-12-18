import { ReactNode } from 'react';
import { WagmiProvider } from 'wagmi';
import { RainbowKitProvider, darkTheme } from '@rainbow-me/rainbowkit';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { config, isWalletDemoMode } from '@/config/wallet';
import '@rainbow-me/rainbowkit/styles.css';

// Create a separate query client for wagmi
const wagmiQueryClient = new QueryClient();

interface WalletProviderProps {
  children: ReactNode;
}

export const WalletProvider = ({ children }: WalletProviderProps) => {
  // Always provide WagmiProvider - hooks like useAccount need it even in demo mode
  // In demo mode, skip RainbowKitProvider to avoid WalletConnect API errors
  if (isWalletDemoMode) {
    return (
      <WagmiProvider config={config}>
        <QueryClientProvider client={wagmiQueryClient}>
          {children}
        </QueryClientProvider>
      </WagmiProvider>
    );
  }

  // Full wallet functionality when we have a real project ID
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={wagmiQueryClient}>
        <RainbowKitProvider
          theme={darkTheme({
            accentColor: 'hsl(142, 76%, 36%)',
            accentColorForeground: 'white',
            borderRadius: 'medium',
            fontStack: 'system',
          })}
        >
          {children}
        </RainbowKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
};
