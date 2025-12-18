import { serve } from "https://deno.land/std@0.190.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface NonceRequest {
  wallet_address: string;
}

interface VerifyRequest {
  wallet_address: string;
  signature: string;
  message: string;
}

// Generate a random nonce
function generateNonce(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

// Verify Ethereum signature
async function verifySignature(message: string, signature: string, expectedAddress: string): Promise<boolean> {
  try {
    // Import viem for signature verification
    const { verifyMessage } = await import("https://esm.sh/viem@2.21.0");
    
    const isValid = await verifyMessage({
      address: expectedAddress as `0x${string}`,
      message,
      signature: signature as `0x${string}`,
    });
    
    return isValid;
  } catch (error) {
    console.error("Signature verification error:", error);
    return false;
  }
}

const handler = async (req: Request): Promise<Response> => {
  // Handle CORS preflight requests
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const url = new URL(req.url);
    const action = url.searchParams.get("action");

    if (action === "nonce") {
      // Generate nonce for wallet authentication
      const { wallet_address }: NonceRequest = await req.json();
      
      if (!wallet_address) {
        return new Response(
          JSON.stringify({ error: "Wallet address is required" }),
          { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }

      const normalizedAddress = wallet_address.toLowerCase();
      const nonce = generateNonce();

      // Clean up expired nonces
      await supabase
        .from("wallet_nonces")
        .delete()
        .lt("expires_at", new Date().toISOString());

      // Delete any existing nonces for this wallet
      await supabase
        .from("wallet_nonces")
        .delete()
        .eq("wallet_address", normalizedAddress);

      // Insert new nonce
      const { error: insertError } = await supabase
        .from("wallet_nonces")
        .insert({
          wallet_address: normalizedAddress,
          nonce,
          expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString(), // 5 minutes
        });

      if (insertError) {
        console.error("Error inserting nonce:", insertError);
        return new Response(
          JSON.stringify({ error: "Failed to generate nonce" }),
          { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }

      const message = `Sign this message to authenticate with CapitolTrades.\n\nNonce: ${nonce}\nWallet: ${normalizedAddress}`;

      console.log("Generated nonce for wallet:", normalizedAddress);

      return new Response(
        JSON.stringify({ nonce, message }),
        { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
      );
    }

    if (action === "verify") {
      // Verify signature and authenticate user
      const { wallet_address, signature, message }: VerifyRequest = await req.json();

      if (!wallet_address || !signature || !message) {
        return new Response(
          JSON.stringify({ error: "Wallet address, signature, and message are required" }),
          { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }

      const normalizedAddress = wallet_address.toLowerCase();

      // Extract nonce from message
      const nonceMatch = message.match(/Nonce: ([a-f0-9]+)/);
      if (!nonceMatch) {
        return new Response(
          JSON.stringify({ error: "Invalid message format" }),
          { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }
      const nonce = nonceMatch[1];

      // Verify nonce exists and is not expired
      const { data: nonceData, error: nonceError } = await supabase
        .from("wallet_nonces")
        .select("*")
        .eq("wallet_address", normalizedAddress)
        .eq("nonce", nonce)
        .gt("expires_at", new Date().toISOString())
        .single();

      if (nonceError || !nonceData) {
        console.error("Nonce verification failed:", nonceError);
        return new Response(
          JSON.stringify({ error: "Invalid or expired nonce" }),
          { status: 401, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }

      // Verify the signature
      const isValidSignature = await verifySignature(message, signature, wallet_address);

      if (!isValidSignature) {
        console.error("Signature verification failed for wallet:", normalizedAddress);
        return new Response(
          JSON.stringify({ error: "Invalid signature" }),
          { status: 401, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }

      // Delete the used nonce
      await supabase
        .from("wallet_nonces")
        .delete()
        .eq("wallet_address", normalizedAddress);

      // Check if user exists with this wallet
      const { data: existingProfile } = await supabase
        .from("profiles")
        .select("id")
        .eq("wallet_address", normalizedAddress)
        .single();

      let userId: string;
      let isNewUser = false;

      if (existingProfile) {
        userId = existingProfile.id;
        console.log("Existing user found:", userId);
      } else {
        // Create new user with wallet address as email (for Supabase auth)
        const walletEmail = `${normalizedAddress}@wallet.local`;
        const randomPassword = crypto.randomUUID();

        const { data: newUser, error: createError } = await supabase.auth.admin.createUser({
          email: walletEmail,
          password: randomPassword,
          email_confirm: true,
          user_metadata: {
            wallet_address: normalizedAddress,
            display_name: `${wallet_address.slice(0, 6)}...${wallet_address.slice(-4)}`,
          },
        });

        if (createError || !newUser.user) {
          console.error("Error creating user:", createError);
          return new Response(
            JSON.stringify({ error: "Failed to create user" }),
            { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
          );
        }

        userId = newUser.user.id;
        isNewUser = true;
        console.log("New user created:", userId);
      }

      // Generate a magic link for the user
      const walletEmail = `${normalizedAddress}@wallet.local`;
      const { data: linkData, error: linkError } = await supabase.auth.admin.generateLink({
        type: "magiclink",
        email: walletEmail,
      });

      if (linkError || !linkData) {
        console.error("Error generating magic link:", linkError);
        return new Response(
          JSON.stringify({ error: "Failed to generate authentication token" }),
          { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
        );
      }

      // Extract the token from the action link
      const actionLink = new URL(linkData.properties.action_link);
      const token = actionLink.searchParams.get("token");
      const tokenType = actionLink.searchParams.get("type");

      console.log("Authentication successful for wallet:", normalizedAddress);

      return new Response(
        JSON.stringify({
          success: true,
          isNewUser,
          userId,
          token,
          tokenType,
          email: walletEmail,
        }),
        { status: 200, headers: { "Content-Type": "application/json", ...corsHeaders } }
      );
    }

    return new Response(
      JSON.stringify({ error: "Invalid action" }),
      { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error("Error in wallet-auth function:", errorMessage);
    return new Response(
      JSON.stringify({ error: errorMessage }),
      { status: 500, headers: { "Content-Type": "application/json", ...corsHeaders } }
    );
  }
};

serve(handler);
