export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function api<T>(path: string, init: RequestInit = {}, csrf?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("content-type", "application/json");
  if (csrf) headers.set("x-csrf-token", csrf);
  const response = await fetch(path, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Falha na requisicao local." }));
    throw new ApiError(response.status, readableError(body.detail) ?? `Erro HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

function readableError(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      if (typeof item === "string") return item;
      if (!item || typeof item !== "object") return "Entrada invalida";
      const error = item as { loc?: unknown[]; msg?: unknown };
      const field = Array.isArray(error.loc)
        ? error.loc.filter((part): part is string => typeof part === "string" && part !== "body").join(" → ")
        : "";
      const message = typeof error.msg === "string" ? error.msg : "Entrada invalida";
      return field ? `${field}: ${message}` : message;
    }).join("; ");
  }
  if (detail && typeof detail === "object" && "msg" in detail) {
    const message = (detail as { msg: unknown }).msg;
    return typeof message === "string" ? message : null;
  }
  return null;
}
