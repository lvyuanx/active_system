const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function apiURL(path: string): string {
  return `${baseURL}${path}`;
}
