import aiohttp
import yfinance as yf


async def fetch_crypto_data(coin_id: str) -> dict | None:
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()

        market = data.get("market_data", {})
        return {
            "name": data.get("name", coin_id),
            "symbol": data.get("symbol", "").upper(),
            "price": market.get("current_price", {}).get("usd", 0),
            "change_24h": market.get("price_change_percentage_24h", 0),
            "change_7d": market.get("price_change_percentage_7d", 0),
            "change_14d": market.get("price_change_percentage_14d", 0),
            "high_24h": market.get("high_24h", {}).get("usd", 0),
            "low_24h": market.get("low_24h", {}).get("usd", 0),
            "volume": market.get("total_volume", {}).get("usd", 0),
            "market_cap": market.get("market_cap", {}).get("usd", 0),
        }
    except Exception:
        return None


def fetch_stock_data(symbol: str) -> dict | None:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")

        if hist.empty:
            return None

        current = hist["Close"].iloc[-1]
        prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else current
        week_ago = hist["Close"].iloc[-5] if len(hist) >= 5 else hist["Close"].iloc[0]
        two_weeks_ago = hist["Close"].iloc[-10] if len(hist) >= 10 else hist["Close"].iloc[0]

        change_24h = ((current - prev_close) / prev_close) * 100
        change_7d = ((current - week_ago) / week_ago) * 100
        change_14d = ((current - two_weeks_ago) / two_weeks_ago) * 100

        high_24h = hist["High"].iloc[-1]
        low_24h = hist["Low"].iloc[-1]
        volume = hist["Volume"].iloc[-1]

        info = ticker.info
        market_cap = info.get("marketCap", 0)

        return {
            "name": info.get("shortName", symbol),
            "symbol": symbol,
            "price": round(current, 2),
            "change_24h": round(change_24h, 2),
            "change_7d": round(change_7d, 2),
            "change_14d": round(change_14d, 2),
            "high_24h": round(high_24h, 2),
            "low_24h": round(low_24h, 2),
            "volume": int(volume),
            "market_cap": market_cap,
        }
    except Exception:
        return None


def generate_signal(data: dict) -> dict:
    change_24h = data.get("change_24h", 0) or 0
    change_7d = data.get("change_7d", 0) or 0
    change_14d = data.get("change_14d", 0) or 0

    score = 0

    if change_24h > 3:
        score += 2
    elif change_24h > 1:
        score += 1
    elif change_24h < -3:
        score -= 2
    elif change_24h < -1:
        score -= 1

    if change_7d > 5:
        score += 2
    elif change_7d > 2:
        score += 1
    elif change_7d < -5:
        score -= 2
    elif change_7d < -2:
        score -= 1

    if change_7d > change_14d and change_7d > 0:
        score += 1
    elif change_7d < change_14d and change_7d < 0:
        score -= 1

    if score >= 3:
        signal = "STRONG BUY"
        confidence = "High"
    elif score >= 1:
        signal = "BUY"
        confidence = "Medium"
    elif score <= -3:
        signal = "STRONG SELL"
        confidence = "High"
    elif score <= -1:
        signal = "SELL"
        confidence = "Medium"
    else:
        signal = "HOLD"
        confidence = "Low"

    return {"signal": signal, "confidence": confidence, "score": score}


def format_number(n: float) -> str:
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    elif n >= 1_000:
        return f"${n / 1_000:.2f}K"
    return f"${n:.2f}"


def format_signal_message(data: dict, signal: dict, asset_type: str) -> str:
    signal_emoji = {
        "STRONG BUY": ">>",
        "BUY": ">",
        "HOLD": "=",
        "SELL": "<",
        "STRONG SELL": "<<",
    }

    emoji = signal_emoji.get(signal["signal"], "?")
    price_str = f"${data['price']:,.2f}" if data["price"] < 100_000 else format_number(data["price"])

    lines = [
        f"{data['name']} ({data['symbol']})",
        "",
        f"Price: {price_str}",
        f"24h: {data['change_24h']:+.2f}%",
        f"7d:  {data['change_7d']:+.2f}%",
        f"High: ${data['high_24h']:,.2f}",
        f"Low:  ${data['low_24h']:,.2f}",
        f"Volume: {format_number(data['volume'])}",
        f"Market Cap: {format_number(data['market_cap'])}",
        "",
        f"[{emoji}] Signal: {signal['signal']}",
        f"Confidence: {signal['confidence']}",
        "",
        "Not financial advice. Do your own research.",
    ]

    return "\n".join(lines)
