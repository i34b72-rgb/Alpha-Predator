import yfinance as yf
import pandas as pd
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # KESİNLİKLE KENDİ ID'Nİ YAZ
HISSELER = ["THYAO.IS", "EREGL.IS", "ASELS.IS", "BTC-USD"]

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

async def analiz_et(bot, sembol):
    try:
        hisse = yf.Ticker(sembol)
        df = hisse.history(period="100d")
        if len(df) < 30: return

        df['RSI'] = rsi_hesapla(df['Close'])
        df['SMA20'] = df['Close'].rolling(window=20).mean()

        son_fiyat = df['Close'].iloc[-1]
        son_rsi = df['RSI'].iloc[-1]
        
        # TEST İÇİN: Her zaman mesaj atması için kriteri çok genişletiyoruz
        if son_rsi > 0: # Bu her zaman doğrudur, yani mutlaka mesaj atmalı
            mesaj = f"✅ <b>{sembol} Aktif Takipte</b>\nFiyat: {son_fiyat:.2f}\nRSI: {son_rsi:.1f}"
            await bot.send_message(chat_id=MY_ID, text=mesaj, parse_mode='HTML')
            
    except Exception as e:
        print(f"Hata {sembol}: {e}")

async def ana_islem():
    if not TOKEN:
        print("TOKEN EKSİK!")
        return
    bot = Bot(token=TOKEN)
    # Sistem testi mesajı
    await bot.send_message(chat_id=MY_ID, text="🚀 Borsa Botu Testi Başlatıldı!")
    
    tasks = [analiz_et(bot, s) for s in HISSELER]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(ana_islem())
