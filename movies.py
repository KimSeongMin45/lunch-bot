# 어제의 일별 박스오피스(1~10위)를 영화진흥위원회(KOBIS) 오픈API에서 가져온다.
# 인증키가 필요하다: KOBIS 오픈API에서 무료로 발급받아 .env에 KOBIS_API_KEY=... 로 넣는다
# 박스오피스 데이터: 영화진흥위원회 (KOBIS) — 쓰는 곳에 출처를 밝힌다
import os
from datetime import datetime, timedelta, timezone

import requests

URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
INFO_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"  # 영화 한 편의 상세정보
MAX_ACTORS = 3  # 주연 배우는 앞의 3명만 보여 준다 (전체는 너무 길다)

# 한 번 만든 답을 그날 동안 기억해 둔다. 영화마다 서버를 부르면 느려지고,
# 느리면 텔레그램이 같은 메시지를 다시 보내 답이 두 번 올 수 있다. 서버를 껐다 켜면 사라진다
_cache = {"date": None, "text": None}


def yesterday():
    """한국 시간 기준 어제를 "20261015" 모양 글자로. 박스오피스는 전날 집계가 나온다."""
    kst = timezone(timedelta(hours=9))
    return (datetime.now(kst) - timedelta(days=1)).strftime("%Y%m%d")


def get_boxoffice():
    """{'date': '20261015', 'movies': [{'rank': '1', 'code': '…', 'title': '…', 'open': '2026-10-01'}, …]} — 실패하면 None"""
    key = os.getenv("KOBIS_API_KEY")  # 키는 코드에 쓰지 않고 .env에서 읽는다
    if not key:
        print("[영화 오류] KOBIS_API_KEY가 .env에 없어요.")
        return None

    date = yesterday()
    try:
        # timeout: 서버가 느려도 봇 전체가 멈춰 있지 않게 5초만 기다린다
        response = requests.get(URL, params={"key": key, "targetDt": date}, timeout=5)
        response.raise_for_status()  # 200이 아니면 에러로
        data = response.json()  # JSON → 파이썬 dict
        if "faultInfo" in data:  # 키가 틀리면 에러가 아니라 이 항목에 담겨 온다
            print(f"[영화 오류] {data['faultInfo'].get('message')}")
            return None
        items = data["boxOfficeResult"]["dailyBoxOfficeList"]
        movies = [
            {
                "rank": item["rank"],
                "code": item.get("movieCd", ""),  # 영화 상세정보를 찾을 때 쓰는 번호
                "title": item["movieNm"],
                "open": item.get("openDt", ""),
            }
            for item in items
        ]
    except (requests.RequestException, ValueError, KeyError) as e:
        # e 전체를 찍으면 주소(키가 들어 있다)까지 나올 수 있어서 에러 종류만 찍는다
        print(f"[영화 오류] {type(e).__name__}")
        return None
    return {"date": date, "movies": movies}


def get_people(code):
    """{'directors': ['홍길동'], 'actors': ['김철수', '이영희', '박민수']} — 실패하면 None"""
    key = os.getenv("KOBIS_API_KEY")
    if not key or not code:
        return None

    try:
        response = requests.get(INFO_URL, params={"key": key, "movieCd": code}, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "faultInfo" in data:
            print(f"[영화 오류] {data['faultInfo'].get('message')}")
            return None
        info = data["movieInfoResult"]["movieInfo"]
        # 사람마다 peopleNm(한글 이름)이 들어 있다. 이름이 빈 항목은 건너뛴다
        directors = [p["peopleNm"] for p in info.get("directors", []) if p.get("peopleNm")]
        actors = [p["peopleNm"] for p in info.get("actors", []) if p.get("peopleNm")]
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"[영화 오류] {type(e).__name__}")  # 키가 든 주소가 안 나오게 에러 종류만
        return None
    return {"directors": directors, "actors": actors[:MAX_ACTORS]}


def boxoffice_text():
    if _cache["date"] == yesterday():  # 오늘 이미 만들어 둔 답이 있으면 바로 준다
        return _cache["text"]

    result = get_boxoffice()
    if result is None or not result["movies"]:
        return "지금은 박스오피스를 가져오지 못했어요."

    d = result["date"]
    lines = [f"어제({d[:4]}-{d[4:6]}-{d[6:]}) 박스오피스"]
    complete = True  # 영화 10편의 상세정보를 모두 가져왔는지
    for movie in result["movies"]:
        open_date = movie["open"].strip() or "미정"  # 개봉일이 비어 있어도 멈추지 않게
        lines.append(f"{movie['rank']}위 {movie['title']} (개봉 {open_date})")

        people = get_people(movie["code"])
        if people is None:
            complete = False
            people = {"directors": [], "actors": []}
        director = ", ".join(people["directors"]) or "정보 없음"
        actors = ", ".join(people["actors"]) or "정보 없음"
        lines.append(f"   감독 {director} · 주연 {actors}")
    lines.append("(데이터: 영화진흥위원회)")

    text = "\n".join(lines)
    if complete:  # 일부가 실패한 답은 기억하지 않는다 → 다음 요청에서 다시 시도한다
        _cache["date"], _cache["text"] = result["date"], text
    return text
