import json
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import urlopen

from ..config import AUTH_PROVIDER, WECHAT_APP_ID, WECHAT_APP_SECRET


def resolve_wechat_session(code: str) -> Dict[str, Any]:
    if AUTH_PROVIDER != "wechat":
        user_id = "demo_user" if not code else f"wx_{abs(hash(code)) % 100000000}"
        return {"userId": user_id, "openid": user_id, "provider": "mock"}

    if not WECHAT_APP_ID or not WECHAT_APP_SECRET:
        raise RuntimeError("微信登录未配置 WECHAT_APP_ID 或 WECHAT_APP_SECRET")
    if not code:
        raise RuntimeError("缺少 wx.login 返回的 code")

    query = urlencode(
        {
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    with urlopen(f"https://api.weixin.qq.com/sns/jscode2session?{query}", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("errcode"):
        raise RuntimeError(payload.get("errmsg") or "微信登录失败")

    openid = payload.get("openid", "")
    if not openid:
        raise RuntimeError("微信登录未返回 openid")

    return {
        "userId": f"wx_{openid}",
        "openid": openid,
        "unionid": payload.get("unionid", ""),
        "sessionKey": payload.get("session_key", ""),
        "provider": "wechat",
    }
