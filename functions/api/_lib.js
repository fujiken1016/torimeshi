// トレ飯相棒 — Cloudflare Pages Functions 共通ロジック
// Anthropic REST API を fetch で呼ぶだけ（キーは env に隠す）
export const MODEL = "claude-opus-4-8"; // 既定。安くするなら env の TORIMESHI_MODEL に claude-sonnet-5 / claude-haiku-4-5

export function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

export function extractJson(text) {
  let t = (text || "").trim().replace(/^```(?:json)?/m, "").replace(/```$/m, "").trim();
  const m = t.match(/\{[\s\S]*\}/);
  return JSON.parse(m ? m[0] : t);
}

// Anthropic Messages API 呼び出し。失敗時は {code} を投げる
export async function callAnthropic(env, body) {
  const key = env && env.ANTHROPIC_API_KEY;
  if (!key) throw { code: "no_api_key" };
  const model = (env && env.TORIMESHI_MODEL) || MODEL;
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({ model, ...body }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = (j && j.error && j.error.message) || ("HTTP " + r.status);
    throw { code: "anthropic_error", message: msg };
  }
  const text = (j.content || []).filter((b) => b.type === "text").map((b) => b.text).join("");
  return { text, model: j.model || model };
}
