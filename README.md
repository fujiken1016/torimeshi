# トレ飯相棒

トレーニー向け食事記録アプリ。写真を撮ると **Claude Vision** が料理とPFC（タンパク質・脂質・炭水化物）を推定し、相棒AI「ゲイン」が残りタンパク質の埋め方まで一緒に考えてくれる。相棒とはチャットで会話もできる。

- **写真→本物のPFC解析**（Claude Vision）
- **体重×目標でPFC自動計算**（BMR / Mifflin-St Jeor）
- **相棒AIと会話**（今日の数値を踏まえて相談に乗る）
- **残りタンパク質の埋め方を提案**・達成演出・体重推移・日別履歴
- データはブラウザ内（localStorage）保存。サーバはAI中継のみ

構成: `index.html`（フロント） / `api/`（Vercelサーバーレス関数：`analyze`=写真解析, `coach`=相棒会話, `health`） / `server.py`（ローカル開発用）。モデル `claude-opus-4-8`。

---

## A. まずローカルで動かす（自分のMacだけ・確認用）

```bash
cd ~/Desktop/claude/torimeshi
pip3 install anthropic                 # 未導入なら
export ANTHROPIC_API_KEY="sk-ant-..."  # console.anthropic.com で発行
python3 server.py                      # → http://localhost:8787
```

---

## B. スマホからいつでも使う（Vercelに公開）★本番

**Node不要・ほぼ画面クリックだけ**。所要10〜15分。無料枠(Vercel Hobby / 個人利用)で足りる。
※アカウント作成・ログイン・APIキー入力は「あなたの操作」です（こちらでは代行できません）。

### 1. Anthropic APIキーを用意
https://console.anthropic.com → API Keys → 発行（`sk-ant-...`）。従量課金（写真1枚の解析≒数円）。

### 2. コードをGitHubに置く
ローカルのgitリポジトリは初期化＆コミット済み。GitHubに上げるだけ：

1. https://github.com でアカウント作成（無料）
2. 新規リポジトリ作成（例 `torimeshi`、Private可、READMEなどは追加しない）
3. ターミナルで push（`<自分>` を自分のユーザー名に）：
   ```bash
   cd ~/Desktop/claude/torimeshi
   git remote add origin https://github.com/<自分>/torimeshi.git
   git branch -M main
   git push -u origin main
   ```
   初回pushでGitHubの認証を求められる → ブラウザ or アクセストークンで自分でログイン。

### 3. Vercelにデプロイ
1. https://vercel.com → 「Continue with GitHub」でアカウント作成（無料 Hobby）
2. **Add New → Project** → さっきの `torimeshi` リポジトリを **Import**
3. デプロイ設定画面の **Environment Variables** に1つ追加：
   - Name: `ANTHROPIC_API_KEY`　Value: `sk-ant-...`（自分のキー）
4. **Deploy** を押す → 数十秒で `https://torimeshi-xxxx.vercel.app` が発行される

### 4. スマホでアプリ化
発行URLをスマホのブラウザで開く → 共有メニュー → **「ホーム画面に追加」**。アプリのアイコンから起動できる。

> 以後、コードを直して `git push` するだけで自動で再デプロイされる。

---

## 詰まりやすいポイント

- **写真解析/会話が「未設定」と出る** → Vercelの Settings → Environment Variables に `ANTHROPIC_API_KEY` があるか確認。追加/変更後は Deployments から **Redeploy**。
- **解析が遅い/タイムアウト** → `vercel.json` の `maxDuration` を下げる、または環境変数 `TORIMESHI_MODEL=claude-sonnet-5` を足すと速く安くなる。
- **`maxDuration` でデプロイが弾かれる** → `vercel.json` の該当行を消してデプロイ（デフォルトで動く）。
- **push で認証エラー** → GitHubは今はパスワード不可。Personal Access Token（Settings→Developer settings→Tokens）を作ってパスワード欄に貼る。

---

## この先（本物のサービスにするなら）

- **データが端末内だけ** → 機種変で消える。複数端末で同期したいなら Vercel Postgres / KV などのDBを足してユーザーごとに保存。
- **他人にも使わせる** → ログイン（認証）とAPIコストの管理・課金設計が要る。Vercel Hobbyは個人/非商用まで。商用は Pro。
- ここから先は「個人開発Webサービスの運営」フェーズ。やるなら伴走する。
