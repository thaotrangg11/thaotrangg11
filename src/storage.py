"""KV-backed storage — thay SQLite."""
from js import Object
from pyodide.ffi import to_js
import json

async def kv_get(env, key: str, default=None):
    raw = await env.BOT_KV.get(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return raw

async def kv_put(env, key: str, value) -> None:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    await env.BOT_KV.put(key, str(value))

async def kv_delete(env, key: str) -> None:
    await env.BOT_KV.delete(key)

# ---------- user ----------
async def touch_user(env, uid: int, username: str | None, first: str | None):
    key = f"user:{uid}"
    u = await kv_get(env, key, {"user_id": uid})
    u["username"] = username or ""
    u["first_name"] = first or ""
    u["last_seen"] = __import__("time").time()
    await kv_put(env, key, u)

async def get_user(env, uid: int) -> dict:
    return await kv_get(env, f"user:{uid}", {})

async def is_banned(env, uid: int) -> bool:
    return (await get_user(env, uid)).get("banned", False)

async def ban(env, uid: int, b: bool = True):
    u = await get_user(env, uid)
    u["banned"] = b
    await kv_put(env, f"user:{uid}", u)

# ---------- vip ----------
async def vip_until(env, uid: int) -> int | None:
    import time
    rec = await kv_get(env, f"vip:{uid}")
    if not rec:
        return None
    exp = rec.get("expires_at", 0)
    return exp if exp > time.time() else None

async def activate_vip(env, uid: int, days: int) -> int:
    import time
    now = int(time.time())
    rec = await kv_get(env, f"vip:{uid}", {"expires_at": 0})
    base = max(rec.get("expires_at", 0), now)
    new_exp = 4102444800 if days == -1 else base + days * 86400
    await kv_put(env, f"vip:{uid}", {"expires_at": new_exp, "activated_at": now})
    return new_exp

# ---------- usage (free quota) ----------
async def today_usage(env, uid: int, day: str) -> int:
    rec = await kv_get(env, f"usage:{uid}:{day}", {})
    return rec.get("rounds", 0)

async def bump_usage(env, uid: int, day: str, n: int):
    key = f"usage:{uid}:{day}"
    rec = await kv_get(env, key, {"rounds": 0})
    rec["rounds"] = rec.get("rounds", 0) + n
    await kv_put(env, key, rec)

# ---------- jobs history ----------
async def push_job(env, uid: int, job: dict):
    key = f"jobs:{uid}"
    lst = await kv_get(env, key, [])
    lst.insert(0, job)
    lst = lst[:20]
    await kv_put(env, key, lst)

async def list_jobs(env, uid: int) -> list[dict]:
    return await kv_get(env, f"jobs:{uid}", [])

# ---------- stats (global counters) ----------
async def bump_counter(env, name: str, n: int = 1):
    cur = await kv_get(env, f"counter:{name}", 0)
    await kv_put(env, f"counter:{name}", int(cur) + n)

async def get_counter(env, name: str) -> int:
    return int(await kv_get(env, f"counter:{name}", 0))
