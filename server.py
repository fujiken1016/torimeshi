#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
トレ飯相棒 バックエンド（標準ライブラリのみ / 追加依存は anthropic のみ）

起動:
    export ANTHROPIC_API_KEY="sk-ant-..."     # console.anthropic.com で発行
    python3 server.py
    → ブラウザで http://localhost:8787 を開く

エンドポイント:
    GET  /                … フロント(index.html)
    POST /api/analyze     … 写真(base64) → Claude Vision で料理とPFCを推定
    POST /api/coach       … 状況＋会話 → 相棒AI「ゲイン」の返答
"""

import json
import os
import re
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("TORIMESHI_MODEL", "claude-opus-4-8")  # 最上位。安くしたいなら claude-sonnet-5 / claude-haiku-4-5
PORT = int(os.environ.get("PORT", "8787"))
HERE = os.path.dirname(os.path.abspath(__file__))

try:
    import anthropic
    _client = anthropic.Anthropic() if os.environ.get("ANTHROPIC_API_KEY") else None
except Exception:                    # anthropic 未インストール等
    anthropic = None
    _client = None


# ---------- Claude 呼び出し ----------
def _extract_json(text):
    """モデル出力から最初のJSONオブジェクトを取り出す。"""
    text = text.strip()
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
    # data URL -> media_type, base64
    m = re.match(r"data:(image/[a-zA-Z.+-]+);base64,(.*)$", data_url, re.DOTALL)
    if not m:
        raise ValueError("bad_image")
    media_type, b64 = m.group(1), m.group(2)
    # 正規化（png/jpeg/webp/gif のみ許可）
    if media_type not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        media_type = "image/jpeg"

    resp = _client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=ANALYZE_SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": f"目標モード: {mode}。この食事のPFCを推定してJSONで返して。"},
            ],
        }],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    data = _extract_json(text)
    P = max(0, round(float(data.get("P", 0))))
    F = max(0, round(float(data.get("F", 0))))
    C = max(0, round(float(data.get("C", 0))))
    return {
        "name": str(data.get("name", "料理"))[:40],
        "P": P, "F": F, "C": C,
        "kcal": P * 4 + F * 9 + C * 4,
        "confidence": float(data.get("confidence", 0.6)),
        "note": str(data.get("note", ""))[:40],
    }


def coach_reply(ctx):
    """ctx: {buddy, mode, targets{P,F,C,kcal}, today{P,F,C,kcal}, streak, meals[], history[], message}"""
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

    resp = _client.messages.create(
        model=MODEL, max_tokens=200, system=system, messages=messages)
    text = next((b.text for b in resp.content if b.type == "text"), "").strip()
    return {"reply": text or "…（うまく言葉が出ないわ、もう一回言って）"}


# ---------- HTTP ----------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_OPTIONS(self):
        self._send(204, b"")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            try:
                with open(os.path.join(HERE, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "index.html not found", "text/plain; charset=utf-8")
        elif path == "/api/health":
            self._json(200, {"ok": True, "model": MODEL, "has_key": _client is not None})
        else:
            # 静的ファイル（manifest.json / アイコン等）。Vercelでは自動配信される分をローカルでも再現
            name = os.path.basename(path)
            types = {".png": "image/png", ".json": "application/json; charset=utf-8",
                     ".ico": "image/x-icon", ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json"}
            ext = os.path.splitext(name)[1]
            target = os.path.join(HERE, name)
            if ext in types and os.path.isfile(target):
                with open(target, "rb") as f:
                    self._send(200, f.read(), types[ext])
            else:
                self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "bad_json"})

        try:
            if path == "/api/analyze":
                out = analyze_image(payload.get("image", ""), payload.get("mode", "cut"))
                return self._json(200, out)
            if path == "/api/coach":
                return self._json(200, coach_reply(payload))
            return self._json(404, {"error": "not_found"})
        except RuntimeError as e:
            if str(e) == "no_api_key":
                return self._json(503, {"error": "no_api_key",
                                        "message": "サーバにANTHROPIC_API_KEYが設定されていません"})
            return self._json(500, {"error": "server_error", "message": str(e)})
        except Exception as e:
            return self._json(500, {"error": "server_error", "message": str(e)})

    def log_message(self, *args):
        pass  # 静かに


def main():
    key = "✓ 設定済み" if _client else "✗ 未設定（写真解析・相棒会話は動きません）"
    print("=" * 48)
    print("  トレ飯相棒 サーバ起動")
    print(f"  URL     : http://localhost:{PORT}")
    print(f"  モデル  : {MODEL}")
    print(f"  APIキー : {key}")
    print("  停止    : Ctrl+C")
    print("=" * 48)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
