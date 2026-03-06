import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
import json
import gspread
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from datetime import datetime

# --- AYARLAR ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
# DİKKAT: Buraya kendi sayısal ID'ni yaz (Örn: 12345678)
MY_ID = 750480616 
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

# BIST 100 GENİŞ LİSTE
SEKTORLER = {
    "LOKOMOTIF": ["THYAO.IS", "EREGL.IS", "TUPRS.IS", "BIMAS.IS"],
    "BANKA": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS"],
    "ENERJI": ["ASTOR.IS", "SASA.IS", "EUPWR.IS"]
}

def tabloya_baglan():
    if not SHEET_JSON:
        raise ValueError("HATA: GSPREAD_SERVICE_ACCOUNT bulunamadı!")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(SHEET_JSON.strip())
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Borsa_Sinyal_Takip").sheet1

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def analiz_et(bot, sheet, sembol, sektor):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 30: return
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        fiyat, rsi = round(son['Close'], 2), round(son['RSI'], 1)

        # TEST İÇİN: Sinyal gelsin diye RSI > 0 yaptık
        if rsi > 0:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([tarih, sektor, sembol, fiyat, rsi, "TEST"])
            
            plt.style.use('dark_background')
            plt.figure(figsize=(8, 4))
            plt.plot(df.index[-20:], df['Close'][-20:], color='#00ff00', marker='o')
            plt.title(f"{sembol} - {fiyat} TL")
            plt.savefig(f"{sembol}.png")
            plt.close()

            cap = f"🎯 <b>{sembol} SİNYAL!</b>\nFiyat: {fiyat} TL | RSI: {rsi}"
            with open(f"{sembol}.png", 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=cap, parse_mode='HTML')
            os.remove(f"{sembol}.png")
    except Exception as e:
        print(f"Hata {sembol}: {e}")

async def ana_islem():
    if not TOKEN or not SHEET_JSON:
        print("Eksik Ayar!")
        return
    bot = Bot(token=TOKEN)
    try:
        sheet = tabloya_baglan()
        for sektor, liste in SEKTORLER.items():
            tasks = [analiz_et(bot, sheet, s, sektor) for s in liste]
            await asyncio.gather(*tasks)
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

if __name__ == "__main__":
    asyncio.run(ana_islem())
