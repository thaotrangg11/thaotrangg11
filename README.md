# TG Bomber Bot — Cloudflare Worker

## Setup

1. Tạo repo GitHub mới, push toàn bộ file.
2. Cloudflare Dashboard → Workers & Pages → KV → Create namespace `BOT_KV`.
3. Copy KV namespace ID, dán vào `wrangler.toml` mục `id`.
4. Cloudflare → My Profile → API Tokens → Create Token → template "Edit Cloudflare Workers".
5. GitHub repo → Settings → Secrets → Actions:
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
6. Push lên `main` → GitHub Actions tự deploy.
7. Set biến môi trường (Cloudflare Dashboard → Worker → Settings → Variables):
   - `BOT_TOKEN` = token từ BotFather
   - `ADMIN_IDS` = ID Telegram của mày
8. Set webhook:
