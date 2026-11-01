import { z } from "zod";

export const setupSchema = z.object({
  organization_name: z.string().min(2, "Le nom du club est requis"),
  admin_display_name: z.string().min(2, "Le nom administrateur est requis"),
  email: z.string().email("Adresse e-mail invalide"),
  password: z.string().min(12, "Le mot de passe doit contenir au moins 12 caractères"),
  country_code: z.string().length(2).default("TN"),
  default_locale: z.enum(["fr", "ar"]).default("fr"),
  timezone: z.string().default("Africa/Tunis"),
  job_title: z.enum(["director", "coach", "analyst", "scout", "medical", "media", "other"]),
  selected_club: z.object({
    team_provider_id: z.string().min(1), team_name: z.string().min(1), logo_url: z.string().url().nullable().optional(),
    league_provider_id: z.string().min(1), league_name: z.string().min(1), season: z.number().int().min(2000),
  }).optional(),
});

export type SetupPayload = z.infer<typeof setupSchema>;
