import yfinance as yf
import pandas as pd
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı yaz
HISSELER = ["THYAO.IS", "EREGL.IS", "ASELS.IS", "BTC-USD"]

def rsi_hesapla(series, period=14):
    """Pandas-ta olmadan manuel RSI hesaplar."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (10 + rs)) # Basit RSI formülü

async def analiz_et(bot, sembol):
    try:
        hisse = yf.Ticker(sembol)
        df = hisse.history(period="100d")
        if len(df) < 30: return

        # RSI Hesapla (Kendi fonksiyonumuzla)
        df['RSI'] = rsi_hesapla(df['Close'])
        # 20 Günlük Ortalama
        df['SMA20'] = df['Close'].rolling(window=20).mean()

        son_fiyat = df['Close'].iloc[-1]
        son_rsi = df['RSI'].iloc[-1]
        son_sma = df['SMA20'].iloc[-1]
        onceki_fiyat = df['Close'].iloc[-2]
        onceki_sma = df['SMA20'].iloc[-2]

        mesaj = ""
        if son_rsi <= 35:
            mesaj = f"🚨 <b>{sembol} - FIRSAT</b>\nFiyat: {son_fiyat:.2f}\nRSI: {son_rsi:.1f}"
        elif son_fiyat > son_sma and onceki_fiyat <= onceki_sma:
            mesaj = f"🚀 <b>{sembol} - YÜKSELİŞ</b>\nFiyat: {son_fiyat:.2f}\nSMA20 yukarı kırıldı!"

        if mesaj:
            await bot.send_message(chat_id=MY_ID, text=mesaj, parse_mode='HTML')
    except Exception as e:
        print(f"Hata {sembol}: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    tasks = [analiz_et(bot, s) for s in HISSELER]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(ana_islem())
