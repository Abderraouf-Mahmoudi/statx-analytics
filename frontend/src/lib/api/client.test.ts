import { afterEach, describe, expect, it, vi } from "vitest";
import { request } from "./client";

afterEach(() => vi.restoreAllMocks());

describe("API client", () => {
  it("uses credentials and propagates the readable CSRF cookie", async () => {
    Object.defineProperty(document, "cookie", { writable: true, value: "statx_csrf=token-123" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    await request<{ ok: boolean }>("/teams", { method: "POST", body: JSON.stringify({ name: "U17" }) });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/teams$/), expect.objectContaining({
      credentials: "include",
      headers: expect.objectContaining({ "x-csrf-token": "token-123" }),
    }));
  });
  it("lets the browser set the multipart boundary for FormData", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "Content-Type": "application/json" } }));
    const form = new FormData();
    form.append("source", "gallery");
    form.append("photo", new File(["portrait"], "player.png", { type: "image/png" }));
    await request<{ ok: boolean }>("/players/p1/photo", { method: "POST", body: form });
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Record<string, string>;
    expect(headers["content-type"]).toBeUndefined();
  });
});
