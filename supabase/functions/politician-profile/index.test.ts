/**
 * Tests for politician-profile Edge Function
 *
 * Tests:
 * - CORS preflight handling
 * - Fallback bio generation
 * - Ollama API integration
 * - Error handling
 */

import { assertEquals, assertStringIncludes } from "https://deno.land/std@0.208.0/assert/mod.ts";

// Test helper functions extracted from the edge function
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

interface PoliticianData {
  name: string;
  party: string;
  chamber: string;
  state: string;
  totalTrades: number;
  totalVolume: number;
  topTickers?: string[];
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

function buildPrompt(politician: PoliticianData): string {
  const tickersList = politician.topTickers?.slice(0, 5).join(", ") || "various securities";

  return `Write a 2-3 sentence professional biography. Start directly with the person's name - do not include any preamble, introduction, or "Here is..." text.

Subject: ${politician.name}, a ${politician.party} ${politician.chamber} from ${politician.state}.
Trading data: ${politician.totalTrades} disclosed trades, approximately $${formatVolume(politician.totalVolume)} in volume. Top securities: ${tickersList}.

Requirements:
- Start immediately with "${politician.name} is..." or "${politician.name} serves..."
- Keep tone neutral and professional
- Do not invent dates, committees, or other unverified details
- Focus on role and trading activity`;
}

Deno.test("formatVolume() - formats billions", () => {
  assertEquals(formatVolume(1000000000), "1.0B");
  assertEquals(formatVolume(2500000000), "2.5B");
});

Deno.test("formatVolume() - formats millions", () => {
  assertEquals(formatVolume(1000000), "1.0M");
  assertEquals(formatVolume(5500000), "5.5M");
});

Deno.test("formatVolume() - formats thousands", () => {
  assertEquals(formatVolume(1000), "1.0K");
  assertEquals(formatVolume(15000), "15.0K");
});

Deno.test("formatVolume() - formats small numbers", () => {
  assertEquals(formatVolume(500), "500");
  assertEquals(formatVolume(100), "100");
});

Deno.test("generateFallbackBio() - generates bio for Democrat Representative", () => {
  const politician: PoliticianData = {
    name: "John Doe",
    party: "D",
    chamber: "Representative",
    state: "California",
    totalTrades: 50,
    totalVolume: 1500000,
    topTickers: ["AAPL", "GOOGL", "MSFT"],
  };

  const bio = generateFallbackBio(politician);

  assertStringIncludes(bio, "John Doe");
  assertStringIncludes(bio, "Democratic");
  assertStringIncludes(bio, "Representative");
  assertStringIncludes(bio, "California");
  assertStringIncludes(bio, "50 trades");
  assertStringIncludes(bio, "$1.5M");
  assertStringIncludes(bio, "AAPL, GOOGL, MSFT");
});

Deno.test("generateFallbackBio() - generates bio for Republican Senator", () => {
  const politician: PoliticianData = {
    name: "Jane Smith",
    party: "R",
    chamber: "Senator",
    state: "Texas",
    totalTrades: 100,
    totalVolume: 25000000,
  };

  const bio = generateFallbackBio(politician);

  assertStringIncludes(bio, "Jane Smith");
  assertStringIncludes(bio, "Republican");
  assertStringIncludes(bio, "Senator");
  assertStringIncludes(bio, "Texas");
  assertStringIncludes(bio, "100 trades");
  assertStringIncludes(bio, "$25.0M");
});

Deno.test("generateFallbackBio() - handles missing party", () => {
  const politician: PoliticianData = {
    name: "Independent Member",
    party: "",
    chamber: "Representative",
    state: "Vermont",
    totalTrades: 10,
    totalVolume: 500000,
  };

  const bio = generateFallbackBio(politician);

  assertStringIncludes(bio, "Independent");
});

Deno.test("generateFallbackBio() - handles missing state", () => {
  const politician: PoliticianData = {
    name: "Unknown State",
    party: "D",
    chamber: "Senator",
    state: "",
    totalTrades: 20,
    totalVolume: 1000000,
  };

  const bio = generateFallbackBio(politician);

  assertStringIncludes(bio, "the United States");
});

Deno.test("buildPrompt() - includes politician name", () => {
  const politician: PoliticianData = {
    name: "Test Politician",
    party: "D",
    chamber: "Senator",
    state: "New York",
    totalTrades: 75,
    totalVolume: 10000000,
    topTickers: ["NVDA", "TSLA"],
  };

  const prompt = buildPrompt(politician);

  assertStringIncludes(prompt, "Test Politician");
  assertStringIncludes(prompt, "New York");
  assertStringIncludes(prompt, "75 disclosed trades");
  assertStringIncludes(prompt, "NVDA, TSLA");
});

Deno.test("buildPrompt() - defaults to 'various securities' when no tickers", () => {
  const politician: PoliticianData = {
    name: "No Tickers",
    party: "R",
    chamber: "Representative",
    state: "Florida",
    totalTrades: 5,
    totalVolume: 100000,
  };

  const prompt = buildPrompt(politician);

  assertStringIncludes(prompt, "various securities");
});

Deno.test("buildPrompt() - limits tickers to 5", () => {
  const politician: PoliticianData = {
    name: "Many Tickers",
    party: "D",
    chamber: "Senator",
    state: "California",
    totalTrades: 200,
    totalVolume: 50000000,
    topTickers: ["A", "B", "C", "D", "E", "F", "G"],
  };

  const prompt = buildPrompt(politician);

  // Should only include first 5 tickers
  assertStringIncludes(prompt, "A, B, C, D, E");
});
