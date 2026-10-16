# 어제의 일별 박스오피스(1~10위)를 영화진흥위원회(KOBIS) 오픈API에서 가져온다.
# 인증키가 필요하다: KOBIS 오픈API에서 무료로 발급받아 .env에 KOBIS_API_KEY=... 로 넣는다
# 박스오피스 데이터: 영화진흥위원회 (KOBIS) — 쓰는 곳에 출처를 밝힌다
import os
from datetime import datetime, timedelta, timezone

import requests

URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"


def yesterday():
    """한국 시간 기준 어제를 "20261015" 모양 글자로. 박스오피스는 전날 집계가 나온다."""
    kst = timezone(timedelta(hours=9))
    return (datetime.now(kst) - timedelta(days=1)).strftime("%Y%m%d")


def get_boxoffice():
    """{'date': '20261015', 'movies': [{'rank': '1', 'title': '…', 'open': '2026-10-01'}, …]} — 실패하면 None"""
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
            {"rank": item["rank"], "title": item["movieNm"], "open": item.get("openDt", "")}
            for item in items
        ]
    except (requests.RequestException, ValueError, KeyError) as e:
        # e 전체를 찍으면 주소(키가 들어 있다)까지 나올 수 있어서 에러 종류만 찍는다
        print(f"[영화 오류] {type(e).__name__}")
        return None
    return {"date": date, "movies": movies}


def boxoffice_text():
    result = get_boxoffice()
    if result is None or not result["movies"]:
        return "지금은 박스오피스를 가져오지 못했어요."

    d = result["date"]
    lines = [f"어제({d[:4]}-{d[4:6]}-{d[6:]}) 박스오피스"]
    for movie in result["movies"]:
        open_date = movie["open"].strip() or "미정"  # 개봉일이 비어 있어도 멈추지 않게
        lines.append(f"{movie['rank']}위 {movie['title']} (개봉 {open_date})")
    lines.append("(데이터: 영화진흥위원회)")
    return "\n".join(lines)
