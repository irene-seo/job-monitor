#!/usr/bin/env python3
"""카카오 OAuth 토큰 발급 - 최초 1회만 실행"""

import requests
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs

# IODAY 앱에 등록된 Redirect URI
REDIRECT_URI = "https://irene-seo.github.io/job-monitor/callback.html"


def main():
    api_key = input("IODAY REST API 키 입력: ").strip()

    auth_url = "https://kauth.kakao.com/oauth/authorize?" + urlencode({
        "client_id": api_key,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "talk_message",
    })

    print("\n아래 URL을 복사해서 시크릿 창에 붙여넣어줘!")
    print("(로그인 후 주소창이 https://localhost?code=XXXX 로 바뀔 거야)\n")
    print(f"👉 {auth_url}\n")

    url_or_code = input("주소창 URL 붙여넣기: ").strip()

    # URL에서 code 추출
    if "code=" in url_or_code:
        code = parse_qs(urlparse(url_or_code).query).get("code", [url_or_code])[0]
    else:
        code = url_or_code

    print(f"\n[확인] 사용 중인 키: {api_key[:6]}...{api_key[-4:]}")
    print(f"[확인] 코드: {code[:10]}...")

    # 토큰 발급
    resp = requests.post("https://kauth.kakao.com/oauth/token", data={
        "grant_type": "authorization_code",
        "client_id": api_key,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    })
    data = resp.json()
    print(f"[응답] {data}")

    if "refresh_token" not in data:
        print("❌ 토큰 발급 실패:", data)
        return

    print("\n====== GitHub Secrets에 저장할 값 ======")
    print(f"KAKAO_REST_API_KEY  = {api_key}")
    print(f"KAKAO_REFRESH_TOKEN = {data['refresh_token']}")
    print("=========================================")


if __name__ == "__main__":
    main()
