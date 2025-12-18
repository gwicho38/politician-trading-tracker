import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { mainnet, polygon, arbitrum, optimism, base } from 'wagmi/chains';

// WalletConnect project ID - get one at https://cloud.walletconnect.com
const projectId = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || 'demo-project-id';

// For demo purposes, we'll use a minimal config that doesn't cause errors
// In production, replace 'demo-project-id' with a real WalletConnect project ID
const isDemoMode = projectId === 'demo-project-id';

export const config = getDefaultConfig({
  appName: 'Politician Trading Tracker',
  projectId: isDemoMode ? 'demo-project-id' : projectId,
  chains: isDemoMode ? [mainnet] : [mainnet, polygon, arbitrum, optimism, base],
  ssr: false,
});

// Export demo mode flag for conditional rendering
export const isWalletDemoMode = isDemoMode;
