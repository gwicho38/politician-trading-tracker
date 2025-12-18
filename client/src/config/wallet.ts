import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { createConfig, http } from 'wagmi';
import { mainnet, polygon, arbitrum, optimism, base } from 'wagmi/chains';

// WalletConnect project ID - get one at https://cloud.walletconnect.com
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || '';

// Demo mode when no project ID is configured
const isDemoMode = !projectId || projectId === 'demo-project-id';

// In demo mode, create a minimal config without WalletConnect (no network errors)
// In production, use full RainbowKit config with real project ID
export const config = isDemoMode
  ? createConfig({
      chains: [mainnet],
      transports: {
        [mainnet.id]: http(),
      },
    })
  : getDefaultConfig({
      appName: 'Politician Trading Tracker',
      projectId,
      chains: [mainnet, polygon, arbitrum, optimism, base],
      ssr: false,
    });

// Export demo mode flag for conditional rendering
export const isWalletDemoMode = isDemoMode;
