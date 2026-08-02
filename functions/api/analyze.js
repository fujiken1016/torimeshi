// POST /api/analyze — 写真(base64) → Claude Vision で料理とPFCを推定
import { callAnthropic, extractJson, json } from "./_lib.js";

const ANALYZE_SYSTEM =
  "あなたはトレーニー向け食事記録アプリの栄養推定エンジン。" +
  "写真に写っている料理を推定し、写っている量（1食分）のタンパク質(P)・脂質(F)・炭水化物(C)を" +
  "グラム単位で見積もる。ボディメイクの実用に足る、現実的で控えめすぎない推定を出す。" +
  "必ず次のJSONだけを返す（前置き・説明・コードフェンス禁止）:\n" +
  '{"name":"料理名(日本語,簡潔)","P":数値,"F":数値,"C":数値,"confidence":0〜1,"note":"一言メモ(日本語,20字以内)"}';

export async function onRequestPost({ request, env }) {
  try {
    const { image = "", mode = "cut" } = await request.json();
    const m = String(image).match(/^data:(image\/[a-zA-Z.+-]+);base64,([\s\S]*)$/);
    if (!m) return json({ error: "server_error", message: "bad_image" }, 400);
    let media = m[1];
    const data = m[2];
    if (!["image/png", "image/jpeg", "image/webp", "image/gif"].includes(media)) media = "image/jpeg";

    const { text } = await callAnthropic(env, {
      max_tokens: 400,
      system: ANALYZE_SYSTEM,
      messages: [{
        role: "user",
        content: [
          { type: "image", source: { type: "base64", media_type: media, data } },
          { type: "text", text: `目標モード: ${mode}。この食事のPFCを推定してJSONで返して。` },
        ],
      }],
    });

    const d = extractJson(text);
    const P = Math.max(0, Math.round(Number(d.P) || 0));
    const F = Math.max(0, Math.round(Number(d.F) || 0));
    const C = Math.max(0, Math.round(Number(d.C) || 0));
    return json({
      name: String(d.name || "料理").slice(0, 40),
      P, F, C, kcal: P * 4 + F * 9 + C * 4,
      confidence: Number(d.confidence) || 0.6,
      note: String(d.note || "").slice(0, 40),
    });
  } catch (e) {
    if (e && e.code === "no_api_key")
      return json({ error: "no_api_key", message: "ANTHROPIC_API_KEY 未設定" }, 503);
    return json({ error: "server_error", message: (e && e.message) || String(e) }, 500);
  }
}
