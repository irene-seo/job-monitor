#!/usr/bin/env python3
"""채용공고 모니터링 봇 - 네이버/카카오/SK 계열"""

import json, os, sys, time, traceback
from dataclasses import dataclass
from typing import List, Dict
import requests
from bs4 import BeautifulSoup

# ── 문과 직무 키워드 ────────────────────────────────────────
INCLUDE_KW = [
    "기획", "마케팅", "브랜드", "광고", "SNS", "퍼포먼스", "CRM", "그로스",
    "PM", "PO", "프로덕트", "Product",
    "AI 기획", "AI기획", "AI 서비스", "AI서비스", "AI PM",
    "운영", "고객", "CS ", "CX",
    "사업개발", "비즈니스", "제휴", "파트너십", " BD",
    "UX", "리서치", "사용자",
    "홍보", "PR", "커뮤니케이션",
    "MD", "머천다이저",
    "HR", "채용", "인사",
    "법무", "법률",
    "콘텐츠", "에디터", "카피",
    "데이터 분석", "데이터분석", "인사이트",
    "경영", "전략",
]

EXCLUDE_KW = [
    "개발자", "엔지니어", "engineer", "developer",
    "프론트엔드", "백엔드", "풀스택", "안드로이드", "ios 개발",
    "devops", "sre", "인프라",
    "데이터사이언티스트", "data scientist",
    "머신러닝", "딥러닝", "mlops",
    "디자이너", "designer",
    "qa ", "테스터",
]


@dataclass
class Job:
    company: str
    title: str
    url: str
    job_id: str
    department: str = ""

    def is_humanities(self) -> bool:
        text = f"{self.title} {self.department}".lower()
        for kw in EXCLUDE_KW:
            if kw in text:
                return False
        for kw in INCLUDE_KW:
            if kw.lower() in text:
                return True
        return False

    def to_message(self) -> str:
        dept = f"\n📁 {self.department}" if self.department else ""
        return f"📢 새 채용공고!\n🏢 {self.company}\n💼 {self.title}{dept}\n🔗 {self.url}"


# ── ntfy 알림 ────────────────────────────────────────────────
def send_ntfy(topic: str, text: str):
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=text.encode("utf-8"),
        headers={"Title": "새 채용공고!", "Priority": "high"},
        timeout=10,
    )


# ── seen_jobs 저장/로드 ──────────────────────────────────────
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/seen_jobs.json")

def load_seen() -> Dict[str, List[str]]:
    try:
        with open(DATA_PATH) as f:
            return json.load(f)
    except Exception:
        return {}

def save_seen(seen: Dict[str, List[str]]):
    with open(DATA_PATH, "w") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


# ── 스크래퍼 ─────────────────────────────────────────────────

def scrape_kakao_main() -> List[Job]:
    """카카오 careers.kakao.com JSON API"""
    jobs, page = [], 1
    while True:
        try:
            resp = requests.get(
                "https://careers.kakao.com/api/jobs",
                params={"page": page, "size": 50},
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            data = resp.json()
            items = (
                data.get("jobList")
                or data.get("data", {}).get("list")
                or data.get("list", [])
            )
            if not items:
                break
            for item in items:
                jid = str(item.get("jobId") or item.get("id", ""))
                title = item.get("jobName") or item.get("title", "")
                dept = item.get("division") or item.get("part", "")
                url = f"https://careers.kakao.com/jobs/{jid}"
                jobs.append(Job("카카오", title, url, jid, dept))
            if len(items) < 50:
                break
            page += 1
        except Exception as e:
            print(f"  [카카오] 오류: {e}")
            break
    return jobs


def scrape_recruiter(slug: str, name: str) -> List[Job]:
    """recruiter.co.kr 공통 API - 카카오 계열사 6곳"""
    jobs, page = [], 1
    base = f"https://{slug}.recruiter.co.kr"
    while True:
        try:
            resp = requests.get(
                f"{base}/appsite/company/list",
                params={"page": page, "size": 20},
                headers={
                    "Accept": "application/json",
                    "Referer": base,
                    "User-Agent": "Mozilla/5.0",
                },
                timeout=15,
            )
            data = resp.json()
            items = (
                data.get("data", {}).get("list")
                or data.get("list", [])
            )
            if not items:
                break
            for item in items:
                jid = str(item.get("annoId", ""))
                title = item.get("annoTitle", "")
                dept = item.get("fieldNm", "")
                url = f"{base}/appsite/company/view?annoId={jid}"
                jobs.append(Job(name, title, url, jid, dept))
            if len(items) < 20:
                break
            page += 1
        except Exception as e:
            print(f"  [{name}] 오류: {e}")
            break
    return jobs


def scrape_naver() -> List[Job]:
    """네이버/네이버클라우드/네이버웹툰 recruit.navercorp.com"""
    jobs = []
    try:
        resp = requests.get(
            "https://recruit.navercorp.com/rcrt/list.do",
            params={"classId": "", "subClassId": "", "entTypeCd": "", "searchTxt": ""},
            headers={
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://recruit.navercorp.com/rcrt/list.do",
            },
            timeout=15,
        )
        try:
            data = resp.json()
            items = data.get("list") or data.get("annoList") or []
            for item in items:
                jid = str(item.get("annoId", ""))
                title = item.get("annoTitle", "")
                dept = item.get("jobGroupNm") or item.get("classNm", "")
                ent = item.get("entTypeCdNm", "")
                if "클라우드" in ent:
                    company = "네이버클라우드"
                elif "웹툰" in ent:
                    company = "네이버웹툰"
                else:
                    company = "네이버"
                url = f"https://recruit.navercorp.com/rcrt/view.do?annoId={jid}"
                jobs.append(Job(company, title, url, jid, dept))
        except Exception:
            # HTML 폴백
            soup = BeautifulSoup(resp.text, "lxml")
            for card in soup.select("li[class*='item'], div[class*='card']"):
                a = card.select_one("a[href*='annoId']")
                title_el = card.select_one("[class*='title'], h3, h4")
                if not a or not title_el:
                    continue
                href = a.get("href", "")
                jid = href.split("annoId=")[-1].split("&")[0]
                url = f"https://recruit.navercorp.com{href}" if href.startswith("/") else href
                jobs.append(Job("네이버", title_el.get_text(strip=True), url, jid))
    except Exception as e:
        print(f"  [네이버] 오류: {e}")
    return jobs


def scrape_sk_hynix() -> List[Job]:
    """SK하이닉스 recruit.skhynix.com"""
    jobs = []
    # API 엔드포인트 후보들
    api_candidates = [
        "https://recruit.skhynix.com/api/job-postings",
        "https://recruit.skhynix.com/api/jobs",
        "https://careers.skhynix.com/api/jobs",
    ]
    for api_url in api_candidates:
        try:
            resp = requests.get(
                api_url,
                params={"page": 0, "size": 50},
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = (
                data.get("content")
                or data.get("data", {}).get("list")
                or data.get("list", [])
            )
            for item in items:
                jid = str(item.get("id") or item.get("jobId", ""))
                title = item.get("title") or item.get("jobTitle", "")
                dept = item.get("department") or item.get("category", "")
                url = f"https://recruit.skhynix.com/jobs/{jid}"
                jobs.append(Job("SK하이닉스", title, url, jid, dept))
            if jobs:
                break
        except Exception:
            continue

    if not jobs:
        # HTML 폴백
        try:
            resp = requests.get(
                "https://recruit.skhynix.com",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select("a[href*='/jobs/'], a[href*='/recruit/']"):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or len(title) < 3:
                    continue
                jid = href.split("/")[-1]
                url = href if href.startswith("http") else f"https://recruit.skhynix.com{href}"
                jobs.append(Job("SK하이닉스", title, url, jid))
        except Exception as e:
            print(f"  [SK하이닉스] HTML 폴백 오류: {e}")
    return jobs


def scrape_sk_telecom() -> List[Job]:
    """SK텔레콤 (jobflex 플랫폼)"""
    jobs = []
    jobflex_candidates = [
        "https://sktnewcareers.jobflex.kr/api/v1/jobs",
        "https://sktelecom.jobflex.kr/api/v1/jobs",
    ]
    for api_url in jobflex_candidates:
        try:
            resp = requests.get(
                api_url,
                params={"page": 0, "size": 50},
                headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            items = data.get("content") or data.get("data", []) or []
            for item in items:
                jid = str(item.get("id", ""))
                title = item.get("title") or item.get("jobTitle", "")
                dept = item.get("category") or item.get("department", "")
                url = f"{api_url.replace('/api/v1/jobs', '')}/jobs/{jid}"
                jobs.append(Job("SK텔레콤", title, url, jid, dept))
            if jobs:
                break
        except Exception:
            continue

    if not jobs:
        try:
            resp = requests.get(
                "https://www.sktelecom.com/recruit/list.do",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
            soup = BeautifulSoup(resp.text, "lxml")
            for item in soup.select("[class*='recruit'] li, [class*='job'] li"):
                a = item.select_one("a")
                title_el = item.select_one("[class*='title'], h3, h4, strong")
                if not a or not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = a.get("href", "")
                jid = href.split("/")[-1].split("?")[0] or title
                url = href if href.startswith("http") else f"https://www.sktelecom.com{href}"
                jobs.append(Job("SK텔레콤", title, url, jid))
        except Exception as e:
            print(f"  [SK텔레콤] HTML 폴백 오류: {e}")
    return jobs


def scrape_sk_forest() -> List[Job]:
    """SK임업 - 사람인 검색"""
    jobs = []
    try:
        resp = requests.get(
            "https://www.saramin.co.kr/zf_user/search/recruit",
            params={"company_nm": "SK임업", "search_type": "search"},
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select(".item_recruit"):
            a = item.select_one(".job_tit a")
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href", "")
            jid = href.split("rec_idx=")[-1].split("&")[0] if "rec_idx=" in href else title
            url = f"https://www.saramin.co.kr{href}" if href.startswith("/") else href
            jobs.append(Job("SK임업", title, url, jid))
    except Exception as e:
        print(f"  [SK임업] 오류: {e}")
    return jobs


def scrape_catch(company_name: str, display_name: str) -> List[Job]:
    """캐치 - 회사명 검색"""
    jobs = []
    try:
        resp = requests.get(
            "https://www.catch.co.kr/Search/Total",
            params={"query": company_name, "searchType": "2"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a[href*='/NCS/']"):
            title = a.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            href = a.get("href", "")
            jid = f"catch_{href.split('/')[-1]}"
            url = href if href.startswith("http") else f"https://www.catch.co.kr{href}"
            jobs.append(Job(display_name, title, url, jid))
    except Exception as e:
        print(f"  [캐치/{display_name}] 오류: {e}")
    return jobs


# ── 메인 ─────────────────────────────────────────────────────
SCRAPERS = [
    ("naver",            scrape_naver),
    ("kakao",            scrape_kakao_main),
    ("kakaobank",        lambda: scrape_recruiter("kakaobank",        "카카오뱅크")),
    ("kakaopay",         lambda: scrape_recruiter("kakaopay",         "카카오페이")),
    ("kakaoent",         lambda: scrape_recruiter("kakaoent",         "카카오엔터테인먼트")),
    ("kakaomobility",    lambda: scrape_recruiter("kakaomobility",    "카카오모빌리티")),
    ("kakaogames",       lambda: scrape_recruiter("kakaogames",       "카카오게임즈")),
    ("kakaoenterprise",  lambda: scrape_recruiter("kakaoenterprise",  "카카오엔터프라이즈")),
    ("sk_hynix",         scrape_sk_hynix),
    ("sk_telecom",       scrape_sk_telecom),
    ("sk_forest",        scrape_sk_forest),
    # 캐치 보조 (회사 홈피에서 못 잡힌 공고 보완)
    ("catch_naver",      lambda: scrape_catch("네이버", "네이버(캐치)")),
    ("catch_kakao",      lambda: scrape_catch("카카오", "카카오(캐치)")),
    ("catch_sk",         lambda: scrape_catch("SK하이닉스", "SK하이닉스(캐치)")),
]


def main():
    ntfy_topic = os.environ.get("NTFY_TOPIC", "")

    if not ntfy_topic:
        print("❌ NTFY_TOPIC 환경변수 없음")
        sys.exit(1)

    print(f"[{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}] 모니터링 시작")

    seen = load_seen()
    new_count = 0

    for key, fn in SCRAPERS:
        try:
            jobs = fn()
            seen.setdefault(key, [])
            humanities = [j for j in jobs if j.is_humanities()]
            fresh = [j for j in humanities if j.job_id not in seen[key]]
            print(f"  [{key}] 전체 {len(jobs)}개 → 문과 {len(humanities)}개 → 신규 {len(fresh)}개")

            for job in fresh:
                send_ntfy(ntfy_topic, job.to_message())
                seen[key].append(job.job_id)
                new_count += 1
                time.sleep(0.5)

            # seen 목록 최대 500개 유지 (오래된 거 제거)
            if len(seen[key]) > 500:
                seen[key] = seen[key][-500:]

        except Exception as e:
            print(f"  [{key}] 예외: {e}")
            traceback.print_exc()

    save_seen(seen)
    print(f"✅ 완료 - 신규 공고 {new_count}개 알림 발송")


if __name__ == "__main__":
    main()
