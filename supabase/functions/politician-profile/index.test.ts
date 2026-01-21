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

// ============================================================================
// Ollama API Integration Tests (with mocking)
// ============================================================================

/**
 * Mock fetch implementation for testing Ollama API integration
 */
function createMockFetch(mockResponse: {
  status?: number;
  ok?: boolean;
  json?: () => Promise<unknown>;
  text?: () => Promise<string>;
}) {
  return () =>
    Promise.resolve({
      status: mockResponse.status ?? 200,
      ok: mockResponse.ok ?? true,
      json: mockResponse.json ?? (() => Promise.resolve({})),
      text: mockResponse.text ?? (() => Promise.resolve("")),
    } as Response);
}

/**
 * Simulates the edge function's Ollama API call logic
 * This mirrors the actual implementation in index.ts
 */
async function callOllamaApi(
  politician: PoliticianData,
  ollamaBaseUrl: string,
  ollamaApiKey: string | undefined,
  fetchFn: typeof fetch = fetch,
): Promise<{ bio: string; source: "ollama" | "fallback"; reason?: string }> {
  if (!ollamaApiKey) {
    return {
      bio: generateFallbackBio(politician),
      source: "fallback",
    };
  }

  const prompt = buildPrompt(politician);

  try {
    const response = await fetchFn(`${ollamaBaseUrl}/api/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ollamaApiKey}`,
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
      return {
        bio: generateFallbackBio(politician),
        source: "fallback",
        reason: "ollama_error",
      };
    }

    const data = await response.json() as { response?: string };

    return {
      bio: data.response || generateFallbackBio(politician),
      source: data.response ? "ollama" : "fallback",
    };
  } catch (_error) {
    return {
      bio: generateFallbackBio(politician),
      source: "fallback",
      reason: "connection_error",
    };
  }
}

Deno.test("Ollama API - returns source 'ollama' on successful response", async () => {
  const politician: PoliticianData = {
    name: "Nancy Pelosi",
    party: "D",
    chamber: "Representative",
    state: "California",
    totalTrades: 150,
    totalVolume: 50000000,
    topTickers: ["NVDA", "AAPL", "MSFT"],
  };

  const mockOllamaResponse = {
    response:
      "Nancy Pelosi is a Democratic Representative from California. She has disclosed over 150 trades with significant trading volume in technology stocks.",
    done: true,
    model: "llama3.1:8b",
  };

  const mockFetch = createMockFetch({
    ok: true,
    json: () => Promise.resolve(mockOllamaResponse),
  });

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "test-api-key",
    mockFetch,
  );

  assertEquals(result.source, "ollama");
  assertStringIncludes(result.bio, "Nancy Pelosi");
  assertEquals(result.bio, mockOllamaResponse.response);
});

Deno.test("Ollama API - returns source 'fallback' when no API key", async () => {
  const politician: PoliticianData = {
    name: "John Smith",
    party: "R",
    chamber: "Senator",
    state: "Texas",
    totalTrades: 50,
    totalVolume: 5000000,
  };

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    undefined, // No API key
    fetch,
  );

  assertEquals(result.source, "fallback");
  assertStringIncludes(result.bio, "John Smith");
  assertStringIncludes(result.bio, "Republican");
  assertStringIncludes(result.bio, "Senator");
});

Deno.test("Ollama API - falls back on HTTP error (non-200 status)", async () => {
  const politician: PoliticianData = {
    name: "Test Politician",
    party: "D",
    chamber: "Representative",
    state: "New York",
    totalTrades: 25,
    totalVolume: 1000000,
  };

  const mockFetch = createMockFetch({
    status: 500,
    ok: false,
    text: () => Promise.resolve("Internal Server Error"),
  });

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "test-api-key",
    mockFetch,
  );

  assertEquals(result.source, "fallback");
  assertEquals(result.reason, "ollama_error");
  assertStringIncludes(result.bio, "Test Politician");
});

Deno.test("Ollama API - falls back on 401 Unauthorized", async () => {
  const politician: PoliticianData = {
    name: "Auth Test",
    party: "R",
    chamber: "Senator",
    state: "Florida",
    totalTrades: 10,
    totalVolume: 500000,
  };

  const mockFetch = createMockFetch({
    status: 401,
    ok: false,
    text: () => Promise.resolve("API key required"),
  });

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "invalid-api-key",
    mockFetch,
  );

  assertEquals(result.source, "fallback");
  assertEquals(result.reason, "ollama_error");
});

Deno.test("Ollama API - falls back on network/connection error", async () => {
  const politician: PoliticianData = {
    name: "Network Test",
    party: "D",
    chamber: "Representative",
    state: "Ohio",
    totalTrades: 15,
    totalVolume: 750000,
  };

  // Simulate network error by throwing
  const mockFetch = () => Promise.reject(new Error("Network error: Connection refused"));

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "test-api-key",
    mockFetch,
  );

  assertEquals(result.source, "fallback");
  assertEquals(result.reason, "connection_error");
  assertStringIncludes(result.bio, "Network Test");
});

Deno.test("Ollama API - falls back when response has no content", async () => {
  const politician: PoliticianData = {
    name: "Empty Response",
    party: "R",
    chamber: "Senator",
    state: "Arizona",
    totalTrades: 30,
    totalVolume: 2000000,
  };

  // Ollama returns 200 but with empty response
  const mockFetch = createMockFetch({
    ok: true,
    json: () => Promise.resolve({ response: "", done: true }),
  });

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "test-api-key",
    mockFetch,
  );

  assertEquals(result.source, "fallback");
  assertStringIncludes(result.bio, "Empty Response");
});

Deno.test("Ollama API - handles malformed JSON response", async () => {
  const politician: PoliticianData = {
    name: "JSON Error",
    party: "D",
    chamber: "Representative",
    state: "Michigan",
    totalTrades: 20,
    totalVolume: 1500000,
  };

  // Simulate malformed JSON
  const mockFetch = () =>
    Promise.resolve({
      status: 200,
      ok: true,
      json: () => Promise.reject(new Error("Unexpected token")),
      text: () => Promise.resolve("not valid json"),
    } as Response);

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "test-api-key",
    mockFetch,
  );

  assertEquals(result.source, "fallback");
  assertEquals(result.reason, "connection_error");
});

Deno.test("Ollama API - request includes correct headers and body", async () => {
  const politician: PoliticianData = {
    name: "Request Test",
    party: "R",
    chamber: "Senator",
    state: "Nevada",
    totalTrades: 40,
    totalVolume: 3000000,
    topTickers: ["TSLA", "AMZN"],
  };

  let capturedRequest: { url: string; options: RequestInit } | null = null;

  const mockFetch = (url: string | URL | Request, options?: RequestInit) => {
    capturedRequest = { url: url.toString(), options: options! };
    return Promise.resolve({
      status: 200,
      ok: true,
      json: () => Promise.resolve({ response: "Test bio", done: true }),
      text: () => Promise.resolve(""),
    } as Response);
  };

  await callOllamaApi(
    politician,
    "https://ollama.test.local",
    "my-secret-key",
    mockFetch,
  );

  // Verify URL
  assertEquals(capturedRequest!.url, "https://ollama.test.local/api/generate");

  // Verify headers
  const headers = capturedRequest!.options.headers as Record<string, string>;
  assertEquals(headers["Content-Type"], "application/json");
  assertEquals(headers["Authorization"], "Bearer my-secret-key");

  // Verify body
  const body = JSON.parse(capturedRequest!.options.body as string);
  assertEquals(body.model, "llama3.1:8b");
  assertEquals(body.stream, false);
  assertStringIncludes(body.prompt, "Request Test");
  assertStringIncludes(body.prompt, "Senator");
  assertStringIncludes(body.prompt, "Nevada");
  assertStringIncludes(body.prompt, "TSLA, AMZN");
});

Deno.test("Ollama API - full profile generation flow with real-like data", async () => {
  const politician: PoliticianData = {
    name: "Marjorie Taylor Greene",
    party: "R",
    chamber: "Representative",
    state: "Georgia",
    totalTrades: 45,
    totalVolume: 2500000,
    topTickers: ["TSLA", "AMZN", "META"],
  };

  const mockOllamaResponse = {
    response:
      "Marjorie Taylor Greene is a Republican Representative from Georgia. With 45 disclosed trades totaling approximately $2.5M in volume, her portfolio shows significant activity in technology stocks including TSLA, AMZN, and META.",
    done: true,
    model: "llama3.1:8b",
    total_duration: 3000000000,
    eval_count: 50,
  };

  const mockFetch = createMockFetch({
    ok: true,
    json: () => Promise.resolve(mockOllamaResponse),
  });

  const result = await callOllamaApi(
    politician,
    "https://ollama.lefv.info",
    "test-api-key",
    mockFetch,
  );

  assertEquals(result.source, "ollama");
  assertStringIncludes(result.bio, "Marjorie Taylor Greene");
  assertStringIncludes(result.bio, "Republican");
  assertStringIncludes(result.bio, "Georgia");
});

// ============================================================================
// cleanOllamaResponse() Tests - Strip LLM Preambles
// ============================================================================

/**
 * Mirrors the cleanOllamaResponse function from index.ts
 * Strips common LLM preamble patterns from responses
 */
function cleanOllamaResponse(response: string): string {
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

  cleaned = cleaned.replace(/^\n+/, "").trim();

  return cleaned;
}

Deno.test("cleanOllamaResponse() - strips 'Here is a 2-3 sentence biography' preamble", () => {
  const input = "Here is a 2-3 sentence biography for the subject:\n\nNancy Pelosi is a Democratic Representative.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Nancy Pelosi is a Democratic Representative.");
});

Deno.test("cleanOllamaResponse() - strips 'Here is a 2-3 sentence professional biography' preamble", () => {
  const input = "Here is a 2-3 sentence professional biography:\n\nJohn Smith serves as a Senator from Texas.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "John Smith serves as a Senator from Texas.");
});

Deno.test("cleanOllamaResponse() - strips 'Here is the biography' preamble", () => {
  const input = "Here is the biography:\n\nJane Doe is a Republican Representative.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Jane Doe is a Republican Representative.");
});

Deno.test("cleanOllamaResponse() - strips 'Here is a biography' preamble", () => {
  const input = "Here is a biography:\nTest Person is a Senator.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Test Person is a Senator.");
});

Deno.test("cleanOllamaResponse() - strips 'Here's a 2-3 sentence' preamble", () => {
  const input = "Here's a 2-3 sentence bio:\nSample Politician is from California.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Sample Politician is from California.");
});

Deno.test("cleanOllamaResponse() - strips 'Here's the' preamble", () => {
  const input = "Here's the requested biography:\nTest Subject serves in Congress.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Test Subject serves in Congress.");
});

Deno.test("cleanOllamaResponse() - strips 'Here you go' preamble", () => {
  const input = "Here you go:\n\nAnother Politician is a Democrat.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Another Politician is a Democrat.");
});

Deno.test("cleanOllamaResponse() - strips 'Sure, here is' preamble", () => {
  const input = "Sure, here is the bio:\nPolitician Name is a Republican.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Politician Name is a Republican.");
});

Deno.test("cleanOllamaResponse() - strips 'Sure!' preamble", () => {
  const input = "Sure! Test Person is a Senator.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Test Person is a Senator.");
});

Deno.test("cleanOllamaResponse() - strips 'Certainly' preamble", () => {
  const input = "Certainly, here is the biography:\nCongress Member serves from Ohio.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Congress Member serves from Ohio.");
});

Deno.test("cleanOllamaResponse() - strips 'Of course' preamble", () => {
  const input = "Of course! Here is the bio:\nSenator Smith is from Nevada.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Senator Smith is from Nevada.");
});

Deno.test("cleanOllamaResponse() - returns clean response unchanged", () => {
  const input = "Nancy Pelosi is a Democratic Representative from California.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Nancy Pelosi is a Democratic Representative from California.");
});

Deno.test("cleanOllamaResponse() - handles leading/trailing whitespace", () => {
  const input = "  \n\nNancy Pelosi is a Democratic Representative.  \n";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Nancy Pelosi is a Democratic Representative.");
});

Deno.test("cleanOllamaResponse() - handles multiple newlines after preamble", () => {
  const input = "Here is a 2-3 sentence biography:\n\n\n\nJohn Smith is a Senator.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "John Smith is a Senator.");
});

Deno.test("cleanOllamaResponse() - case insensitive matching", () => {
  const input = "HERE IS A 2-3 SENTENCE BIOGRAPHY:\nTest Person is a Representative.";
  const result = cleanOllamaResponse(input);
  assertEquals(result, "Test Person is a Representative.");
});
