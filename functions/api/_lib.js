// トレ飯相棒 — Cloudflare Pages Functions 共通ロジック
// Anthropic REST API を fetch で呼ぶだけ（キーは env に隠す）
export const MODEL = "claude-opus-4-8"; // 既定。安くするなら env の TORIMESHI_MODEL に claude-sonnet-5 / claude-haiku-4-5

export function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

// 🔴 キルスイッチ（2026-09-03）
// 経緯：/api/analyze・/api/coach は認証もレート制限も無いまま公開されており、
// 環境変数の ANTHROPIC_API_KEY が生きていたため「誰でも従量課金を発生させられる」状態だった。
// 本サービスは Search Console 28日で表示0＝実ユーザーゼロのため、機能を守る価値より
// 課金リスクの方が大きい。よって **既定で停止**し、再開したいときだけ環境変数で開ける。
// 再開手順：Cloudflare Pages → Settings → Variables → TORIMESHI_API_ENABLED = 1 を追加して再デプロイ。
// ⚠️ 再開する前に、必ずレート制限か Origin 制限を入れること（無認証のまま開け直さない）。
export function apiEnabled(env) {
  return String((env && env.TORIMESHI_API_ENABLED) || "") === "1";
}

export function disabledResponse() {
  return json({ error: "service_disabled", message: "AI機能は現在停止中です" }, 503);
}

export function extractJson(text) {
  let t = (text || "").trim().replace(/^```(?:json)?/m, "").replace(/```$/m, "").trim();
  const m = t.match(/\{[\s\S]*\}/);
  return JSON.parse(m ? m[0] : t);
}

// Anthropic Messages API 呼び出し。失敗時は {code} を投げる
export async function callAnthropic(env, body) {
  // 二重の安全装置：新しいエンドポイントがキルスイッチの確認を忘れても、ここで必ず止まる
  if (!apiEnabled(env)) throw { code: "service_disabled" };
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
