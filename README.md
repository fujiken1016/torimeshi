# トレ飯相棒

トレーニー向け食事記録アプリ。写真を撮ると **Claude Vision** が料理とPFC（タンパク質・脂質・炭水化物）を推定し、相棒AI「ゲイン」が残りタンパク質の埋め方まで一緒に考えてくれる。相棒とはチャットで会話もできる。

- **写真→本物のPFC解析**（Claude Vision）
- **体重×目標でPFC自動計算**（BMR / Mifflin-St Jeor）
- **相棒AIと会話**（今日の数値を踏まえて相談に乗る）
- **残りタンパク質の埋め方を提案**・達成演出・体重推移・日別履歴
- データはブラウザ内（localStorage）保存。サーバはAI中継のみ

## 構成（本番＝Cloudflare Pages）

| 場所 | 役割 |
|---|---|
| `index.html` / `*.html` / `manifest.json` / `icon-*.png` / `legal.css` | フロント（静的） |
| `functions/api/*.js` | **本番のAPI＝Cloudflare Pages Functions**。`analyze`=写真解析, `coach`=相棒会話, `health`。中身はAnthropic REST APIをfetchで叩くだけ |
| `privacy.html` / `contact.html` / `about.html` | プライバシーポリシー・お問い合わせ・運営者情報＋免責 |
| `api/*.py` + `server.py` + `vercel.json` | 旧Vercel/ローカル開発用。Cloudflareでは使われない（参考として残置） |

モデルの既定は `claude-opus-4-8`（Cloudflareの環境変数 `TORIMESHI_MODEL` に `claude-sonnet-5` / `claude-haiku-4-5` を設定するとコストを下げられる）。

---

## ★本番：Cloudflare Pages に公開（独自ドメイン meshi.mainichi-lab.com）

Node不要・ブラウザ操作中心。無料（Functions 10万req/日）。

### 1. Cloudflare Pages プロジェクト作成
1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. GitHub連携 → リポジトリ `fujiken1016/torimeshi` を選択
3. ビルド設定（**すべて空/なしでOK**。静的＋Functions）：
   - Framework preset: **None**
   - Build command: **（空）**
   - Build output directory: **`/`**（ルート）
4. **Save and Deploy** → `https://torimeshi.pages.dev` 系のURLが発行される

### 2. APIキーを環境変数に
プロジェクト → **Settings → Variables and Secrets** → **Add**
- `ANTHROPIC_API_KEY` = 自分の `sk-ant-...`（Secret推奨）
- （任意）`TORIMESHI_MODEL` = `claude-sonnet-5` などで節約
- 追加後 **Deployments → 最新を Retry/Redeploy** で反映

### 3. 独自ドメイン割当（meshi.mainichi-lab.com）
※ 先に `mainichi-lab.com` を Cloudflare Registrar で取得し、CloudflareのDNSに載せておくこと。
1. Pagesプロジェクト → **Custom domains** → **Set up a custom domain**
2. `meshi.mainichi-lab.com` を入力 → Cloudflare管理下のドメインなのでDNS(CNAME)は**自動追加**
3. SSL証明書が自動発行され、数分で `https://meshi.mainichi-lab.com` が有効

### 4. 仕上げ（審査要件）
- **お問い合わせフォーム有効化**：`contact.html` の `action="https://formspree.io/f/YOUR_FORM_ID"` を、[Formspree](https://formspree.io)（無料）等で作った送信先URLに置換。またはメール `contact@mainichi-lab.com` を **Cloudflare Email Routing**（無料転送）で受信できるよう設定
- **運営者情報**：`about.html` の連絡先を実際に受信できる窓口に
- GA4 / Search Console 登録（プラポリに記載済み）

> 以後 `git push` すると Cloudflare が自動で再デプロイする。

---

## A. ローカルで動かす（開発用・Python版）

`functions/`（JS）と同じ挙動を Python で確認できる。Cloudflare本番には影響しない。

```bash
cd ~/Desktop/claude/torimeshi
pip3 install anthropic                 # 未導入なら
export ANTHROPIC_API_KEY="sk-ant-..."  # console.anthropic.com で発行

---

## A. まずローカルで動かす（自分のMacだけ・確認用）

```bash
cd ~/Desktop/claude/torimeshi
pip3 install anthropic                 # 未導入なら
export ANTHROPIC_API_KEY="sk-ant-..."  # console.anthropic.com で発行
python3 server.py                      # → http://localhost:8787
```

---

## 詰まりやすいポイント

- **写真解析/会話が「未設定」と出る** → Cloudflare Pages の Settings → Variables に `ANTHROPIC_API_KEY` があるか確認。追加/変更後は **Redeploy**（環境変数は再デプロイで反映）。
- **クレジット残高エラー** → console.anthropic.com の Billing でクレジット購入が必要。**JCBは非対応**。Visa/Masterのクレジットカードを使う。
- **APIが404** → Build output directory が `/`（ルート）になっているか確認。`functions/api/*.js` がルート直下の `functions/` にある必要がある。
- **解析を安くしたい** → 環境変数 `TORIMESHI_MODEL` に `claude-haiku-4-5`（最安）or `claude-sonnet-5`。

---

## 旧Vercel構成について

`api/*.py` `server.py` `vercel.json` は Vercel/ローカル開発用の**旧実装**。Cloudflare本番では `functions/api/*.js` が使われ、これらは無視される（参考として残置）。完全に切り替わったら削除してよい。

---

## この先（本物のサービスにするなら）

- **データが端末内だけ** → 機種変で消える。複数端末同期は Cloudflare D1 / Supabase 無料枠でユーザーごとに保存。
- **他人にも使わせる** → ログイン（認証）＋APIコスト管理＋課金設計（Stripe）。
- ここから先は「個人開発Webサービスの運営」フェーズ。ロードマップ §5・§7 参照。
