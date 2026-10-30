export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  trace_id: string;
}

export interface SessionView {
  user_id: string;
  organization_id: string;
  display_name: string;
  email: string;
  role: string;
  locale: string;
}
