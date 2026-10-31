// Small fetch wrapper. Errors come back from the server as stable codes
// (e.g. "vin_wrong_length") that we translate in i18n/locales/*/common.json.

export class ApiError extends Error {
  constructor(
    public code: string,
    public status: number,
    public details: Record<string, unknown> = {},
  ) {
    super(code);
  }
}

function readCookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${name}=`))
    ?.split("=")[1];
}

type Options = { method?: string; body?: unknown; signal?: AbortSignal };

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  const csrf = readCookie("cc_csrf");
  if (csrf && method !== "GET") headers["X-CSRF-Token"] = csrf;

  let res: Response;
  try {
    res = await fetch(`/api/v1${path}`, {
      method,
      headers,
      credentials: "same-origin",
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError("network_error", 0);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = data?.error;
    throw new ApiError(err?.code ?? "unknown_error", res.status, err?.details ?? {});
  }
  return data as T;
}
