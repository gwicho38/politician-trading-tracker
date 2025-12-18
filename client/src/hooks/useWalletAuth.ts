import { useState } from 'react';
import { useAccount, useSignMessage } from 'wagmi';
import { supabase } from '@/integrations/supabase/client';

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
      // Step 1: Get nonce from edge function
      console.log('Requesting nonce for wallet:', address);
      const nonceResponse = await fetch(
        `${SUPABASE_URL}/functions/v1/wallet-auth?action=nonce`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ wallet_address: address }),
        }
      );

      if (!nonceResponse.ok) {
        const errorData = await nonceResponse.json();
        throw new Error(errorData.error || 'Failed to get nonce');
      }

      const { message } = await nonceResponse.json();
      console.log('Received message to sign');

      // Step 2: Sign the message with wallet
      const signature = await signMessageAsync({ message, account: address });
      console.log('Message signed');

      // Step 3: Verify signature and get auth token
      const verifyResponse = await fetch(
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
        }
      );

      if (!verifyResponse.ok) {
        const errorData = await verifyResponse.json();
        throw new Error(errorData.error || 'Verification failed');
      }

      const authData = await verifyResponse.json();
      console.log('Verification successful:', authData);

      // Step 4: Use the magic link token to sign in
      if (authData.token) {
        const { error: signInError } = await supabase.auth.verifyOtp({
          token_hash: authData.token,
          type: 'magiclink',
        });

        if (signInError) {
          console.error('Sign in error:', signInError);
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
      console.error('Wallet auth error:', errorMessage);
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
