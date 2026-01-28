from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timedelta, timezone
import random
import re

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException


app = FastAPI(title="Yandex Weather API")

CACHE_TTL = timedelta(minutes=15)
_cache: Dict[Tuple[str, float, float], Dict[str, Any]] = {}
_UA_POOL = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


def make_headers() -> Dict[str, str]:
    return {
        "User-Agent": random.choice(_UA_POOL),
        "Accept-Language": "ru-RU,ru;q=0.9",
    }


def _get_cached(scope: str, lat: float, lon: float) -> Optional[Dict[str, Any]]:
    key = (scope, lat, lon)
    entry = _cache.get(key)
    if not entry:
        return None
    if datetime.now(timezone.utc) - entry["ts"] > CACHE_TTL:
        return None
    return entry["data"]


def _set_cached(scope: str, lat: float, lon: float, data: Dict[str, Any]) -> None:
    key = (scope, lat, lon)
    _cache[key] = {"ts": datetime.now(timezone.utc), "data": data}


def _extract_temperature(text: Optional[str]) -> Optional[str]:
    """Extract temperature value from text like 'Ощущается как +3°' -> '+3°'"""
    if not text:
        return None
    match = re.search(r'[+-]?\d+°', text)
    return match.group(0) if match else None


def _extract_wind(text: Optional[str]) -> Optional[str]:
    """Extract wind value from text like 'СЗ 3 м/с' -> 'СЗ 3 м/с' (already clean)"""
    if not text:
        return None
    return text.strip()


def _extract_pressure(text: Optional[str]) -> Optional[str]:
    """Extract pressure value from text like '758 мм рт. ст.' -> '758'"""
    if not text:
        return None
    match = re.search(r'\d+', text)
    return match.group(0) if match else None


def _extract_humidity(text: Optional[str]) -> Optional[str]:
    """Extract humidity value from text like '65%' -> '65'"""
    if not text:
        return None
    match = re.search(r'\d+', text)
    return match.group(0) if match else None


def _map_condition_to_code(condition_text: Optional[str]) -> Optional[str]:
    """Map Russian weather condition text to standardized code for frontend translation"""
    if not condition_text:
        return None
    
    text = condition_text.lower()
    
    # Mapping based on common Yandex weather conditions
    if "ясно" in text:
        return "clear"
    elif "малооблачно" in text or "переменная облачность" in text:
        return "partly-cloudy"
    elif "облачно с прояснениями" in text:
        return "cloudy-and-clear"
    elif "облачно" in text:
        return "cloudy"
    elif "пасмурно" in text:
        return "overcast"
    elif "небольшой дождь" in text or "слабый дождь" in text:
        return "light-rain"
    elif "дождь" in text:
        return "rain"
    elif "ливень" in text or "сильный дождь" in text:
        return "heavy-rain"
    elif "гроза" in text:
        return "thunderstorm"
    elif "небольшой снег" in text or "слабый снег" in text:
        return "light-snow"
    elif "снег" in text:
        return "snow"
    elif "метель" in text or "сильный снег" in text:
        return "heavy-snow"
    elif "туман" in text:
        return "fog"
    elif "мгла" in text or "дымка" in text:
        return "haze"
    elif "морось" in text:
        return "drizzle"
    elif "град" in text:
        return "hail"
    else:
        return "unknown"


def parse_weather(html: str) -> Dict[str, Optional[str]]:
    """
    Parse the Yandex weather HTML fragment and return the main metrics.
    """
    soup = BeautifulSoup(html, "html.parser")
    wrap = soup.select_one("div.AppFact_wrap__N4SYB")
    if not wrap:
        wrap = soup.find("div", class_=lambda c: isinstance(c, str) and "AppFact_wrap__" in c)
    if not wrap:
        value_span = soup.find("span", class_=lambda c: isinstance(c, str) and "AppFactTemperature_value" in c)
        wrap = value_span.find_parent("div") if value_span else None
    if not wrap:
        raise ValueError("Weather block not found in the page")

    temperature_block = wrap.select_one("p.AppFactTemperature_content__Lx4p9")
    sign = temperature_block.select_one("span.AppFactTemperature_sign__1MeN4") if temperature_block else None
    value = temperature_block.select_one("span.AppFactTemperature_value__2qhsG") if temperature_block else None
    degree = temperature_block.select_one("span.AppFactTemperature_degree__LL_2v") if temperature_block else None
    temperature = "".join(
        filter(
            None,
            [
                sign.text if sign else "",
                value.text if value else "",
                degree.text if degree else "",
            ],
        )
    ).strip() or None

    condition_warning = wrap.select_one("p.AppFact_warning__8kUUn")
    feels_like = wrap.select_one("span.AppFact_feels__IJoel")
    yesterday_full = wrap.select_one("span.AppFact_yesterday__zTK7e")
    yesterday_short = wrap.select_one("span.AppFact_yesterdayShort__DB943")

    details_items = wrap.select("ul.AppFact_details__OYahy li.AppFact_details__item__QFIXI")

    def detail_at(index: int) -> Optional[str]:
        try:
            return details_items[index].get_text(strip=True)
        except (IndexError, AttributeError):
            return None

    condition_text = condition_warning.text.strip() if condition_warning else None
    
    return {
        "temperature": temperature,
        "condition": _map_condition_to_code(condition_text),
        "condition_text": condition_text,
        "feels_like": _extract_temperature(feels_like.text.strip() if feels_like else None),
        "yesterday_full": _extract_temperature(yesterday_full.text.strip() if yesterday_full else None),
        "yesterday_short": _extract_temperature(yesterday_short.text.strip() if yesterday_short else None),
        "wind": _extract_wind(detail_at(0)),
        "pressure": _extract_pressure(detail_at(1)),
        "humidity": _extract_humidity(detail_at(2)),
        "water_temperature": detail_at(3),
    }


def parse_month(html: str) -> List[Dict[str, Optional[str]]]:
    """
    Parse the Yandex month view and return a list of day forecasts.
    """
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.AppMonth_month__CunyE")
    if not article:
        raise ValueError("Month block not found in the page")

    days: List[Dict[str, Optional[str]]] = []

    for day_block in article.select("div.AppMonthCalendarDay_day__GjOhu"):
        li = day_block.find_parent("li")
        classes = li.get("class", []) if li else []
        if any("climateStart" in cls for cls in classes):
            continue

        link = day_block.select_one("a.AppMonthCalendarDay_day__date__QDruE")
        title = link.get("aria-label") if link else None
        date_text = link.get_text(" ", strip=True) if link else None

        temp_spans = day_block.select("p.AppMonthCalendarDay_temperature__4x_Yx span.AppMonthCalendarDay_temperature__number__VSntF")
        day_temp = temp_spans[0].text.strip() if len(temp_spans) > 0 else None
        night_temp = None
        for span in temp_spans:
            if "AppMonthCalendarDay_temperature__number_night__ggkzj" in span.get("class", []):
                night_temp = span.text.strip()
                break

        details = (li or day_block).select_one("div.AppMonthCalendarDayDetailedInfo_details__Z6kgi")
        feels = details.select_one("p.AppMonthCalendarDayDetailedInfo_details__feelsLike__nXzvQ") if details else None
        params = details.select("ul.AppMonthCalendarDayDetailedInfo_params__7Z8Yt li") if details else []

        def param_at(index: int) -> Optional[str]:
            try:
                return params[index].get_text(" ", strip=True)
            except (IndexError, AttributeError):
                return None

        days.append(
            {
                "title": title or date_text,
                "label": date_text,
                "day_temp": day_temp,
                "night_temp": night_temp,
                "feels_like": _extract_temperature(feels.text.strip() if feels else None),
                "pressure": _extract_pressure(param_at(0)),
                "humidity": _extract_humidity(param_at(1)),
                "wind": _extract_wind(param_at(2)),
                "water_temperature": param_at(3),
            }
        )

    if not days:
        raise ValueError("No day entries found in month view")

    return days


@app.get("/api/weather/total")
def get_weather_total(lat: float, lon: float):
    """
    Fetch and parse weather data from Yandex for the given coordinates.
    """
    url = f"https://yandex.ru/pogoda/ru?lat={lat}&lon={lon}"
    scope = "current"
    cached = _get_cached(scope, lat, lon)
    if cached:
        return {"lat": lat, "lon": lon, "source": url, "data": cached, "cached": True}
    try:
        response = requests.get(url, timeout=10, headers=make_headers())
        response.raise_for_status()
    except requests.RequestException as exc:
        cached = _get_cached(scope, lat, lon)
        if cached:
            return {"lat": lat, "lon": lon, "source": url, "data": cached, "cached": True}
        raise HTTPException(status_code=502, detail=f"Failed to fetch source page: {exc}") from exc

    try:
        data = parse_weather(response.text)
    except ValueError as exc:
        cached = _get_cached(scope, lat, lon)
        if cached:
            return {"lat": lat, "lon": lon, "source": url, "data": cached, "cached": True}
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _set_cached(scope, lat, lon, data)
    return {"lat": lat, "lon": lon, "source": url, "data": data, "cached": False}


@app.get("/api/weather/month")
def get_weather_month(lat: float, lon: float):
    """
    Fetch and parse month weather data from Yandex for the given coordinates.
    """
    scope = "month"
    url = f"https://yandex.ru/pogoda/ru/month?lat={lat}&lon={lon}"
    cached = _get_cached(scope, lat, lon)
    if cached:
        return {"lat": lat, "lon": lon, "source": url, "data": cached, "cached": True}

    try:
        response = requests.get(url, timeout=10, headers=make_headers())
        response.raise_for_status()
    except requests.RequestException as exc:
        cached = _get_cached(scope, lat, lon)
        if cached:
            return {"lat": lat, "lon": lon, "source": url, "data": cached, "cached": True}
        raise HTTPException(status_code=502, detail=f"Failed to fetch source page: {exc}") from exc

    try:
        data = parse_month(response.text)
    except ValueError as exc:
        cached = _get_cached(scope, lat, lon)
        if cached:
            return {"lat": lat, "lon": lon, "source": url, "data": cached, "cached": True}
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    _set_cached(scope, lat, lon, data)
    return {"lat": lat, "lon": lon, "source": url, "data": data, "cached": False}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

