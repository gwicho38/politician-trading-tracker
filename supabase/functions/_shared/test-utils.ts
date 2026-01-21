/**
 * Shared test utilities for Edge Function tests
 */

// Mock environment variables
export function mockEnv(vars: Record<string, string>) {
  const original = new Map<string, string>();

  return {
    setup() {
      for (const [key, value] of Object.entries(vars)) {
        const current = Deno.env.get(key);
        if (current !== undefined) {
          original.set(key, current);
        }
        Deno.env.set(key, value);
      }
    },
    teardown() {
      for (const key of Object.keys(vars)) {
        const originalValue = original.get(key);
        if (originalValue !== undefined) {
          Deno.env.set(key, originalValue);
        } else {
          Deno.env.delete(key);
        }
      }
    }
  };
}

// Create a mock Request object
export function createMockRequest(
  url: string,
  options: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
  } = {}
): Request {
  const { method = 'POST', body, headers = {} } = options;

  const init: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body && method !== 'GET') {
    init.body = JSON.stringify(body);
  }

  return new Request(url, init);
}

// Create mock Supabase client
export function createMockSupabaseClient(overrides: Partial<MockSupabaseClient> = {}): MockSupabaseClient {
  return {
    from: (table: string) => createMockQueryBuilder(table, overrides.data?.[table]),
    auth: {
      getUser: async () => overrides.user ?? { data: { user: null }, error: null },
    },
    ...overrides,
  };
}

interface MockSupabaseClient {
  from: (table: string) => MockQueryBuilder;
  auth: {
    getUser: (token: string) => Promise<{ data: { user: unknown }; error: unknown }>;
  };
  data?: Record<string, unknown[]>;
  user?: { data: { user: unknown }; error: unknown };
}

interface MockQueryBuilder {
  select: (columns?: string) => MockQueryBuilder;
  insert: (data: unknown) => MockQueryBuilder;
  update: (data: unknown) => MockQueryBuilder;
  upsert: (data: unknown, options?: unknown) => MockQueryBuilder;
  delete: () => MockQueryBuilder;
  eq: (column: string, value: unknown) => MockQueryBuilder;
  neq: (column: string, value: unknown) => MockQueryBuilder;
  in: (column: string, values: unknown[]) => MockQueryBuilder;
  is: (column: string, value: unknown) => MockQueryBuilder;
  not: (column: string, operator: string, value: unknown) => MockQueryBuilder;
  gte: (column: string, value: unknown) => MockQueryBuilder;
  lte: (column: string, value: unknown) => MockQueryBuilder;
  order: (column: string, options?: { ascending?: boolean }) => MockQueryBuilder;
  limit: (count: number) => MockQueryBuilder;
  single: () => Promise<{ data: unknown; error: unknown }>;
  maybeSingle: () => Promise<{ data: unknown; error: unknown }>;
  then: <T>(resolve: (value: { data: unknown[]; error: unknown }) => T) => Promise<T>;
}

function createMockQueryBuilder(table: string, data: unknown[] = []): MockQueryBuilder {
  const builder: MockQueryBuilder = {
    select: () => builder,
    insert: () => builder,
    update: () => builder,
    upsert: () => builder,
    delete: () => builder,
    eq: () => builder,
    neq: () => builder,
    in: () => builder,
    is: () => builder,
    not: () => builder,
    gte: () => builder,
    lte: () => builder,
    order: () => builder,
    limit: () => builder,
    single: async () => ({ data: data[0] ?? null, error: null }),
    maybeSingle: async () => ({ data: data[0] ?? null, error: null }),
    then: async (resolve) => resolve({ data, error: null }),
  };
  return builder;
}

// Parse JSON response helper
export async function parseJsonResponse<T>(response: Response): Promise<T> {
  return await response.json() as T;
}

// Assert response status and parse body
export async function assertResponse<T>(
  response: Response,
  expectedStatus: number
): Promise<T> {
  if (response.status !== expectedStatus) {
    const body = await response.text();
    throw new Error(`Expected status ${expectedStatus}, got ${response.status}: ${body}`);
  }
  return await response.json() as T;
}

// Standard CORS headers for testing
export const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};
