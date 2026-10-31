import { createPlayer, registerPlayer, uploadPlayerPhoto } from "./api";
import type { CreateRosterPayload } from "./PlayerForm";

interface RosterWorkflowDependencies {
  createPlayer: typeof createPlayer;
  registerPlayer: typeof registerPlayer;
  uploadPhoto: typeof uploadPlayerPhoto;
}

const defaults: RosterWorkflowDependencies = {
  createPlayer,
  registerPlayer,
  uploadPhoto: uploadPlayerPhoto,
};

export async function createRosterEntry(
  payload: CreateRosterPayload,
  dependencies: RosterWorkflowDependencies = defaults,
): Promise<{ photoQueued: boolean }> {
  const player = await dependencies.createPlayer(payload.player);
  const { team_id, ...registration } = payload.registration;
  await dependencies.registerPlayer(team_id, { ...registration, player_id: player.public_id });
  if (!payload.photo) return { photoQueued: false };
  try {
    await dependencies.uploadPhoto(player.public_id, payload.photo.source, payload.photo.file);
    return { photoQueued: true };
  } catch {
    // Identity and registration are already valid. The portrait can be retried
    // from the player workspace without reporting the whole creation as failed.
    return { photoQueued: false };
  }
}
