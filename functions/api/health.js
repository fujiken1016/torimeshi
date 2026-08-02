// GET /api/health — 稼働・キー有無・モデル確認
import { MODEL, json } from "./_lib.js";

export async function onRequestGet({ env }) {
  return json({ ok: true, model: (env && env.TORIMESHI_MODEL) || MODEL, has_key: !!(env && env.ANTHROPIC_API_KEY) });
}
