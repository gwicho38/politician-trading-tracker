import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'supabase';
import { corsHeaders } from '../_shared/cors.ts';

interface PoliticianData {
  name: string;
  party: string;
  chamber: string;
  state: string;
  totalTrades: number;
  totalVolume: number;
  topTickers?: string[];
}

async function getPartyName(partyCode: string): Promise<string> {
  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
    if (!supabaseUrl || !supabaseKey) {
      // Fallback if no Supabase credentials
      const fallback: Record<string, string> = { D: "Democratic", R: "Republican", I: "Independent" };
      return fallback[partyCode] || partyCode || "Independent";
    }
    const supabase = createClient(supabaseUrl, supabaseKey);
    const { data } = await supabase.from("parties").select("name").eq("code", partyCode).single();
    return data?.name || partyCode || "Independent";
  } catch {
    const fallback: Record<string, string> = { D: "Democratic", R: "Republican", I: "Independent" };
    return fallback[partyCode] || partyCode || "Independent";
  }
}

// TODO: Review serve handler - handles politician profile bio generation requests
// - Validates politician data input
// - Calls Ollama API for AI-generated bios
// - Falls back to template-based bios on API failure
serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { politician } = await req.json() as { politician: PoliticianData };

    if (!politician || !politician.name) {
      return new Response(
        JSON.stringify({ error: "Politician data required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const partyName = await getPartyName(politician.party);

    const ollamaApiKey = Deno.env.get("OLLAMA_API_KEY");
    const ollamaBaseUrl = Deno.env.get("OLLAMA_API_BASE") || "https://ollama.lefv.info";

    if (!ollamaApiKey) {
      // Return fallback profile if no API key
      return new Response(
        JSON.stringify({
          bio: generateFallbackBio(politician, partyName),
          source: "fallback",
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Build prompt for ollama
    const prompt = buildPrompt(politician, partyName);

    try {
      const response = await fetch(`${ollamaBaseUrl}/api/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${ollamaApiKey}`,
        },
        body: JSON.stringify({
          model: "llama3.1:8b",
          prompt: prompt,
          stream: false,
          options: {
            temperature: 0.7,
            num_predict: 300,
          },
        }),
      });

      if (!response.ok) {
        console.error("Ollama API error:", response.status, await response.text());
        return new Response(
          JSON.stringify({
            bio: generateFallbackBio(politician, partyName),
            source: "fallback",
            reason: "ollama_error",
          }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      const data = await response.json();
      const cleanedBio = data.response ? cleanOllamaResponse(data.response) : null;

      return new Response(
        JSON.stringify({
          bio: cleanedBio || generateFallbackBio(politician, partyName),
          source: cleanedBio ? "ollama" : "fallback",
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    } catch (ollamaError) {
      console.error("Ollama connection error:", ollamaError);
      return new Response(
        JSON.stringify({
          bio: generateFallbackBio(politician, partyName),
          source: "fallback",
          reason: "connection_error",
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }
  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});

// TODO: Review buildPrompt - constructs LLM prompt for biography generation
// - Formats politician data into structured prompt
// - Includes trading statistics and top securities
function buildPrompt(politician: PoliticianData, partyName: string): string {
  const tickersList = politician.topTickers?.slice(0, 5).join(", ") || "various securities";

  const chamberDisplay = politician.chamber?.toLowerCase().includes("rep") ? "Representative" :
                         politician.chamber?.toLowerCase().includes("sen") ? "Senator" :
                         politician.chamber?.toLowerCase() === "mep" || politician.chamber?.toLowerCase().includes("eu") ? "Member of the European Parliament" :
                         politician.chamber || "Member of Congress";

  return `Write a 2-3 sentence professional biography. Start directly with the person's name - do not include any preamble, introduction, or "Here is..." text.

Subject: ${politician.name}, a ${partyName} ${chamberDisplay} from ${politician.state}.
Trading data: ${politician.totalTrades} disclosed trades, approximately $${formatVolume(politician.totalVolume)} in volume. Top securities: ${tickersList}.

Requirements:
- Start immediately with "${politician.name} is..." or "${politician.name} serves..."
- Keep tone neutral and professional
- Do not invent dates, committees, or other unverified details
- Focus on role and trading activity`;
}

// TODO: Review generateFallbackBio - creates template-based biography when LLM unavailable
// - Uses resolved party name from parties table
// - Formats chamber type and trading statistics
function generateFallbackBio(politician: PoliticianData, partyName: string): string {
  const chamberFull = politician.chamber?.toLowerCase().includes("rep") ? "Representative" :
                      politician.chamber?.toLowerCase().includes("sen") ? "Senator" :
                      politician.chamber?.toLowerCase() === "mep" || politician.chamber?.toLowerCase().includes("eu") ? "Member of the European Parliament" :
                      politician.chamber || "Member of Congress";

  const tickersList = politician.topTickers?.slice(0, 3).join(", ");
  const tickersNote = tickersList ? ` Their most frequently traded securities include ${tickersList}.` : "";

  return `${politician.name} is a ${partyName} ${chamberFull} from ${politician.state || "the United States"}. According to public financial disclosure filings, they have reported ${politician.totalTrades} trades with an estimated trading volume of $${formatVolume(politician.totalVolume)}.${tickersNote}`;
}

// TODO: Review formatVolume - formats dollar amounts with K/M/B suffixes
function formatVolume(volume: number): string {
  if (volume >= 1000000000) {
    return (volume / 1000000000).toFixed(1) + "B";
  } else if (volume >= 1000000) {
    return (volume / 1000000).toFixed(1) + "M";
  } else if (volume >= 1000) {
    return (volume / 1000).toFixed(1) + "K";
  }
  return volume.toFixed(0);
}

// TODO: Review cleanOllamaResponse - strips LLM preamble text from generated bios
// - Removes common patterns like "Here is...", "Sure!", etc.
// - Returns clean biography text starting with politician name
function cleanOllamaResponse(response: string): string {
  // Common LLM preamble patterns to strip
  const preamblePatterns = [
    /^here is a \d+-\d+ sentence (professional )?biography[^:]*:\s*/i,
    /^here is the (professional )?biography[^:]*:\s*/i,
    /^here is a (professional )?biography[^:]*:\s*/i,
    /^here's a \d+-\d+ sentence[^:]*:\s*/i,
    /^here's the[^:]*:\s*/i,
    /^here you go[^:]*:\s*/i,
    /^sure[,!]?\s*(here[^:]*:\s*)?/i,
    /^certainly[,!]?\s*(here[^:]*:\s*)?/i,
    /^of course[,!]?\s*(here[^:]*:\s*)?/i,
  ];

  let cleaned = response.trim();

  for (const pattern of preamblePatterns) {
    cleaned = cleaned.replace(pattern, "");
  }

  // Also strip any leading newlines after removing preamble
  cleaned = cleaned.replace(/^\n+/, "").trim();

  return cleaned;
}
