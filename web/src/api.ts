import type { Answers, Options, RecommendResponse } from "./types";

/** Erreur lisible côté interface : `kind` décide du message et de l'action proposée. */
export class ApiError extends Error {
  constructor(public kind: "offline" | "no_match" | "invalid" | "server") {
    super(kind);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("offline");
  }
  if (response.status === 404) throw new ApiError("no_match");
  if (response.status === 422) throw new ApiError("invalid");
  // Le proxy Vite renvoie 502/504 quand l'API Python n'est pas lancée.
  if (response.status >= 502) throw new ApiError("offline");
  if (!response.ok) throw new ApiError("server");
  return response.json() as Promise<T>;
}

export const fetchOptions = () => request<Options>("/api/options");

export const fetchRecommendations = (answers: Answers) =>
  request<RecommendResponse>("/api/recommend", {
    method: "POST",
    body: JSON.stringify(answers),
  });
