import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface PoliticianData {
  name: string;
  party: string;
  chamber: string;
  state: string;
  totalTrades: number;
  totalVolume: number;
  topTickers?: string[];
}

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

    const ollamaApiKey = Deno.env.get("OLLAMA_API_KEY");
    const ollamaBaseUrl = Deno.env.get("OLLAMA_API_BASE") || "https://ollama.lefv.info";

    if (!ollamaApiKey) {
      // Return fallback profile if no API key
      return new Response(
        JSON.stringify({
          bio: generateFallbackBio(politician),
          source: "fallback",
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // Build prompt for ollama
    const prompt = buildPrompt(politician);

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
            bio: generateFallbackBio(politician),
            source: "fallback",
            reason: "ollama_error",
          }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }

      const data = await response.json();

      return new Response(
        JSON.stringify({
          bio: data.response || generateFallbackBio(politician),
          source: data.response ? "ollama" : "fallback",
        }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    } catch (ollamaError) {
      console.error("Ollama connection error:", ollamaError);
      return new Response(
        JSON.stringify({
          bio: generateFallbackBio(politician),
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

function buildPrompt(politician: PoliticianData): string {
  const tickersList = politician.topTickers?.slice(0, 5).join(", ") || "various securities";

  return `Write a brief, factual 2-3 sentence professional biography for ${politician.name}, a ${politician.party} ${politician.chamber} from ${politician.state}.

Based on public financial disclosure data, they have reported ${politician.totalTrades} trades with approximately $${formatVolume(politician.totalVolume)} in disclosed trading volume. Their most frequently traded securities include ${tickersList}.

Keep the tone neutral and professional. Focus on their role and trading activity. Do not make up specific dates, committees, or other details not provided.`;
}

function generateFallbackBio(politician: PoliticianData): string {
  const partyFull = politician.party === "D" ? "Democratic" :
                    politician.party === "R" ? "Republican" :
                    politician.party || "Independent";

  const chamberFull = politician.chamber?.toLowerCase().includes("rep") ? "Representative" :
                      politician.chamber?.toLowerCase().includes("sen") ? "Senator" :
                      politician.chamber || "Member of Congress";

  const tickersList = politician.topTickers?.slice(0, 3).join(", ");
  const tickersNote = tickersList ? ` Their most frequently traded securities include ${tickersList}.` : "";

  return `${politician.name} is a ${partyFull} ${chamberFull} from ${politician.state || "the United States"}. According to public financial disclosure filings, they have reported ${politician.totalTrades} trades with an estimated trading volume of $${formatVolume(politician.totalVolume)}.${tickersNote}`;
}

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
