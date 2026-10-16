# 오늘 환율을 Frankfurter에서 가져온다. 가입·키가 필요 없는 공개 API다.
# 환율 데이터: Frankfurter (유럽중앙은행 기준 환율, 영업일마다 하루 한 번 갱신) — 쓰는 곳에 출처를 밝힌다
import requests

URL = "https://api.frankfurter.dev/v1/latest"
CURRENCIES = ["KRW", "JPY", "EUR", "CNY"]  # 달러 기준으로 한 번에 받아 온다


def get_rates():
    """{'date': '2026-10-15', 'KRW': 1345.9, 'JPY': 157.98, ...} — 1달러가 각 돈으로 얼마인지. 실패하면 None"""
    params = {"base": "USD", "symbols": ",".join(CURRENCIES)}
    try:
        # timeout: 환율 서버가 느려도 봇 전체가 멈춰 있지 않게 5초만 기다린다
        response = requests.get(URL, params=params, timeout=5)
        response.raise_for_status()  # 200이 아니면 에러로
        data = response.json()  # JSON → 파이썬 dict
        rates = {"date": data["date"], **data["rates"]}
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"[환율 오류] {e}")
        return None
    return rates


def exchange_text():
    rates = get_rates()
    # 받아 온 것에 원하는 돈이 하나라도 빠졌으면 계산할 수 없다
    if rates is None or any(code not in rates for code in CURRENCIES):
        return "지금은 환율을 가져오지 못했어요."

    # 서비스는 "1달러 = ○○"만 준다 → 원화를 각 돈으로 나눠서 "그 돈 1개 = 몇 원"을 구한다
    krw = rates["KRW"]
    dollar = krw
    yen_100 = krw / rates["JPY"] * 100  # 엔은 값이 작아서 100엔 기준
    euro = krw / rates["EUR"]
    yuan = krw / rates["CNY"]

    return (
        f"오늘 환율 ({rates['date']} 기준)\n"
        f"1달러 = {dollar:,.0f}원\n"
        f"100엔 = {yen_100:,.0f}원\n"
        f"1유로 = {euro:,.0f}원\n"
        f"1위안 = {yuan:,.0f}원\n"
        "(유럽중앙은행 기준 환율이라 은행 고시 환율과 조금 다를 수 있어요. 데이터: Frankfurter)"
    )
