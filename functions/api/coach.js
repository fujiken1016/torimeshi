// POST /api/coach — 状況＋会話 → 相棒AI「ゲイン」の返答
import { callAnthropic, json } from "./_lib.js";

export async function onRequestPost({ request, env }) {
  try {
    const ctx = await request.json();
    const name = ctx.buddy || "ゲイン";
    const system =
      `あなたはトレーニー向け食事アプリの相棒AI「${name}」。ユーザーと同じ沼にいる筋トレ仲間として話す。` +
      "栄養士のような説教はしない。タメ口で、短く(2文以内)、熱く、でも押しつけない。" +
      "減量期でもチートを責めない。増量期は食えと励ます。タンパク質(P)の残りを一番気にする。" +
      "絵文字は0〜1個。相手の今日の数値を踏まえて具体的に言う。";

    const t = ctx.targets || {};
    const d = ctx.today || {};
    const meals = (ctx.meals || []).join(", ") || "まだ無し";
    const facts =
      `目標: P${t.P}g F${t.F}g C${t.C}g ${t.kcal}kcal / ` +
      `今日: P${d.P}g F${d.F}g C${d.C}g ${d.kcal}kcal / ` +
      `モード:${ctx.mode} / P達成連続:${ctx.streak}日 / 今日の食事:${meals}`;

    const messages = [{ role: "user", content: `【今日の状況】${facts}\n\n上の状況を踏まえて、相棒として一言。` }];
    for (const h of (ctx.history || []).slice(-6)) {
      messages.push({ role: h.role === "buddy" ? "assistant" : "user", content: String(h.text || "").slice(0, 500) });
    }
    if (ctx.message) messages.push({ role: "user", content: String(ctx.message).slice(0, 500) });

    const { text } = await callAnthropic(env, { max_tokens: 200, system, messages });
    return json({ reply: text.trim() || "…（うまく言葉が出ないわ、もう一回言って）" });
  } catch (e) {
    if (e && e.code === "no_api_key")
      return json({ error: "no_api_key", message: "ANTHROPIC_API_KEY 未設定" }, 503);
    return json({ error: "server_error", message: (e && e.message) || String(e) }, 500);
  }
}
