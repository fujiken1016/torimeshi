// GET /api/health — 稼働確認
// ⚠️ 2026-09-03: 以前は has_key（APIキーの有無）とモデル名を外部に返していた。
// 「このエンドポイントを叩けば課金が起きる」ことを外部に教える情報なので返さない。
import { apiEnabled, json } from "./_lib.js";

export async function onRequestGet({ env }) {
  return json({ ok: true, api: apiEnabled(env) ? "enabled" : "disabled" });
}
