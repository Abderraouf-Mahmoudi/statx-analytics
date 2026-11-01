import { z } from "zod";
export const positionSchema = z.enum(["GK", "RB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST", "OTHER"]);
export const playerSchema = z.object({ first_name: z.string().min(1), last_name: z.string().min(1), birth_date: z.string().optional(), primary_position: positionSchema, preferred_foot: z.string().optional() });
export const registrationSchema = z.object({ player_id: z.string().uuid(), season_id: z.string().uuid(), shirt_number: z.coerce.number().int().min(0).max(99), position: positionSchema });
