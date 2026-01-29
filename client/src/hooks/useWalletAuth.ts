import { useState } from 'react';
import { useAccount, useSignMessage } from 'wagmi';
import { supabase } from '@/integrations/supabase/client';
import { fetchWithRetry } from '@/lib/fetchWithRetry';
import { logDebug, logError } from '@/lib/logger';

const SUPABASE_URL = "https://ogdwavsrcyleoxfsswbt.supabase.co";

interface WalletAuthResult {
  success: boolean;
  isNewUser?: boolean;
  userId?: string;
  error?: string;
}

export const useWalletAuth = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { address, isConnected } = useAccount();
  const { signMessageAsync } = useSignMessage();

  const authenticate = async (): Promise<WalletAuthResult> => {
    if (!address || !isConnected) {
      return { success: false, error: 'Wallet not connected' };
    }

    setIsLoading(true);
    setError(null);

    try {
      // Step 1: Get nonce from edge function (with retry for network issues)
      logDebug('Requesting nonce', 'wallet-auth', { address });
      const nonceResponse = await fetchWithRetry(
        `${SUPABASE_URL}/functions/v1/wallet-auth?action=nonce`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ wallet_address: address }),
          maxRetries: 2,
        }
      );

      if (!nonceResponse.ok) {
        const errorData = await nonceResponse.json();
        throw new Error(errorData.error || 'Failed to get nonce');
      }

      const { message } = await nonceResponse.json();
      logDebug('Received message to sign', 'wallet-auth');

      // Step 2: Sign the message with wallet
      const signature = await signMessageAsync({ message, account: address });
      logDebug('Message signed', 'wallet-auth');

      // Step 3: Verify signature and get auth token (with retry for network issues)
      const verifyResponse = await fetchWithRetry(
        `${SUPABASE_URL}/functions/v1/wallet-auth?action=verify`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            wallet_address: address,
            signature,
            message,
          }),
          maxRetries: 2,
        }
      );

      if (!verifyResponse.ok) {
        const errorData = await verifyResponse.json();
        throw new Error(errorData.error || 'Verification failed');
      }

      const authData = await verifyResponse.json();
      logDebug('Verification successful', 'wallet-auth', { isNewUser: authData.isNewUser });

      // Step 4: Use the magic link token to sign in
      if (authData.token) {
        const { error: signInError } = await supabase.auth.verifyOtp({
          token_hash: authData.token,
          type: 'magiclink',
        });

        if (signInError) {
          logError('Sign in error', 'wallet-auth', undefined, { error: signInError.message });
          throw new Error(signInError.message);
        }
      }

      return {
        success: true,
        isNewUser: authData.isNewUser,
        userId: authData.userId,
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
      logError('Wallet auth error', 'wallet-auth', err instanceof Error ? err : undefined);
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  return {
    authenticate,
    isLoading,
    error,
    isConnected,
    address,
  };
};
