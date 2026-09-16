const appURL = (configured: string | undefined, productionPath: string, devPort: number) =>
  new URL(configured ?? (import.meta.env.PROD ? productionPath : `http://localhost:${devPort}/`),
    window.location.origin);

export const activityUserURL = (activityId: string) => {
  const url = appURL(import.meta.env.VITE_USER_WEB_BASE_URL, "/user/", 5175);
  url.pathname = `${url.pathname.replace(/\/$/, "")}/activity/${encodeURIComponent(activityId)}`;
  return url.toString();
};

export const activityScreenURL = (activityId: string) => {
  const url = appURL(import.meta.env.VITE_SCREEN_WEB_BASE_URL, "/screen/", 5174);
  url.searchParams.set("activity_id", activityId);
  return url.toString();
};
