# -*- coding: utf-8 -*-
"""analyze / coach 共通ロジック（Vercel Python サーバーレス関数から利用）"""
import json
import os
import re

MODEL = os.environ.get("TORIMESHI_MODEL", "claude-haiku-4-5")  # 最安。精度上げたいなら env で claude-sonnet-5 / claude-opus-4-8

try:
    import anthropic
    _client = anthropic.Anthropic() if os.environ.get("ANTHROPIC_API_KEY") else None
except Exception:
    anthropic = None
    _client = None


def has_key():
    return _client is not None


def _extract_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0)) if m else json.loads(text)


ANALYZE_SYSTEM = (
    "あなたはトレーニー向け食事記録アプリの栄養推定エンジン。"
    "写真に写っている料理を推定し、写っている量（1食分）のタンパク質(P)・脂質(F)・炭水化物(C)を"
    "グラム単位で見積もる。ボディメイクの実用に足る、現実的で控えめすぎない推定を出す。"
    "必ず次のJSONだけを返す（前置き・説明・コードフェンス禁止）:\n"
    '{"name":"料理名(日本語,簡潔)","P":数値,"F":数値,"C":数値,'
    '"confidence":0〜1,"note":"一言メモ(日本語,20字以内)"}'
)


def analyze_image(data_url, mode="cut"):
    if _client is None:
        raise RuntimeError("no_api_key")
    m = re.match(r"data:(image/[a-zA-Z.+-]+);base64,(.*)$", data_url or "", re.DOTALL)
    if not m:
        raise ValueError("bad_image")
    media_type, b64 = m.group(1), m.group(2)
    if media_type not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        media_type = "image/jpeg"
    resp = _client.messages.create(
        model=MODEL, max_tokens=400, system=ANALYZE_SYSTEM,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": f"目標モード: {mode}。この食事のPFCを推定してJSONで返して。"},
        ]}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    data = _extract_json(text)
    P = max(0, round(float(data.get("P", 0))))
    F = max(0, round(float(data.get("F", 0))))
    C = max(0, round(float(data.get("C", 0))))
    return {"name": str(data.get("name", "料理"))[:40], "P": P, "F": F, "C": C,
            "kcal": P * 4 + F * 9 + C * 4,
            "confidence": float(data.get("confidence", 0.6)),
            "note": str(data.get("note", ""))[:40]}


def coach_reply(ctx):
    if _client is None:
        raise RuntimeError("no_api_key")
    name = ctx.get("buddy", "ゲイン")
    system = (
        f"あなたはトレーニー向け食事アプリの相棒AI「{name}」。ユーザーと同じ沼にいる筋トレ仲間として話す。"
        "栄養士のような説教はしない。タメ口で、短く(2文以内)、熱く、でも押しつけない。"
        "減量期でもチートを責めない。増量期は食えと励ます。タンパク質(P)の残りを一番気にする。"
        "絵文字は0〜1個。相手の今日の数値を踏まえて具体的に言う。"
    )
    t = ctx.get("targets", {})
    d = ctx.get("today", {})
    facts = (
        f"目標: P{t.get('P')}g F{t.get('F')}g C{t.get('C')}g {t.get('kcal')}kcal / "
        f"今日: P{d.get('P')}g F{d.get('F')}g C{d.get('C')}g {d.get('kcal')}kcal / "
        f"モード:{ctx.get('mode')} / P達成連続:{ctx.get('streak')}日 / "
        f"今日の食事:{', '.join(ctx.get('meals', [])) or 'まだ無し'}"
    )
    messages = [{"role": "user", "content": f"【今日の状況】{facts}\n\n上の状況を踏まえて、相棒として一言。"}]
    for h in ctx.get("history", [])[-6:]:
        role = "assistant" if h.get("role") == "buddy" else "user"
        messages.append({"role": role, "content": str(h.get("text", ""))[:500]})
    if ctx.get("message"):
        messages.append({"role": "user", "content": str(ctx["message"])[:500]})
    resp = _client.messages.create(model=MODEL, max_tokens=200, system=system, messages=messages)
    text = next((b.text for b in resp.content if b.type == "text"), "").strip()
    return {"reply": text or "…（うまく言葉が出ないわ、もう一回言って）"}
