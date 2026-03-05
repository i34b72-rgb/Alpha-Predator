import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı buraya yaz!
BIST_TARAMA = ["THYAO.IS", "EREGL.IS", "ASELS.IS", "SASA.IS", "KCHOL.IS"]

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def grafik_gonder(bot, sembol, df):
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(df.index[-30:], df['Close'][-30:], label='Fiyat', color='blue')
        plt.title(f"{sembol} Analiz")
        plt.grid(True)
        dosya = f"{sembol}.png"
        plt.savefig(dosya)
        plt.close()
        with open(dosya, 'rb') as p:
            await bot.send_photo(chat_id=MY_ID, photo=p, caption=f"📊 {sembol} Grafiği")
        os.remove(dosya)
    except Exception as e:
        print(f"Grafik hatası: {e}")

async def analiz_et(bot, sembol):
    try:
        hisse = yf.Ticker(sembol)
        df = hisse.history(period="60d")
        if len(df) < 20: return
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        
        # Test amaçlı sinyal aralığını geniş tutuyoruz (RSI < 50)
        if son['RSI'] < 50:
            msg = f"🎯 <b>{sembol} Sinyali!</b>\nFiyat: {son['Close']:.2f}\nRSI: {son['RSI']:.1f}"
            await bot.send_message(chat_id=MY_ID, text=msg, parse_mode='HTML')
            await grafik_gonder(bot, sembol, df)
    except Exception as e:
        print(f"{sembol} hatası: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=MY_ID, text="🚀 Borsa Tarama Başlatıldı...")
    tasks = [analiz_et(bot, s) for s in BIST_TARAMA]
    await asyncio.gather(*tasks)

# DÜZELTME: 'await' hatasını bu blok çözer
if __name__ == "__main__":
    asyncio.run(ana_islem())
