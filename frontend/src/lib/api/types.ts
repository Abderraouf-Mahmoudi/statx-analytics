export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  trace_id: string;
}

export type FootballJobTitle = "director" | "coach" | "analyst" | "scout" | "medical" | "media" | "other";

export interface SessionView {
  user_id: string;
  organization_id: string;
  display_name: string;
  email: string;
  role: string;
  job_title: FootballJobTitle;
  locale: string;
}
