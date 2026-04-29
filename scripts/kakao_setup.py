#!/usr/bin/env python3
"""
카카오 OAuth 토큰 발급 - 최초 1회만 실행하면 됨
실행 후 출력된 KAKAO_REFRESH_TOKEN을 GitHub Secret에 저장
"""

import requests
import webbrowser
from urllib.parse import urlencode

# IODAY 앱 키 or 새 앱 키
# developers.kakao.com → 내 애플리케이션 → 앱 키 → REST API 키
KAKAO_REST_API_KEY = input("카카오 REST API 키 입력: ").strip()
REDIRECT_URI = "https://localhost"  # 앱 설정에서 이 URI 등록 필요

# 1단계: 인증 URL로 이동
params = {
    "client_id": KAKAO_REST_API_KEY,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "talk_message",
}
auth_url = "https://kauth.kakao.com/oauth/authorize?" + urlencode(params)

print("\n브라우저에서 카카오 로그인 후 리다이렉트된 URL을 복사해줘")
print("(https://localhost?code=XXXX 형태)")
webbrowser.open(auth_url)

code = input("\n리다이렉트 URL 붙여넣기: ").strip()
if "code=" in code:
    code = code.split("code=")[1].split("&")[0]

# 2단계: 토큰 발급
resp = requests.post("https://kauth.kakao.com/oauth/token", data={
    "grant_type": "authorization_code",
    "client_id": KAKAO_REST_API_KEY,
    "redirect_uri": REDIRECT_URI,
    "code": code,
})
data = resp.json()

if "refresh_token" not in data:
    print("오류:", data)
else:
    print("\n===== GitHub Secrets에 저장할 값 =====")
    print(f"KAKAO_REST_API_KEY = {KAKAO_REST_API_KEY}")
    print(f"KAKAO_REFRESH_TOKEN = {data['refresh_token']}")
    print("======================================")
    print("\ndevelopers.kakao.com → 내 앱 → 설정 → Redirect URI에")
    print(f"  {REDIRECT_URI}  추가 필요!")
