export interface ActivitySession {
  activityId: string;
  logout: () => void;
}

export const activitySessionKey = Symbol("activity-session");
