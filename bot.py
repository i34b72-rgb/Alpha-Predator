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
MY_ID = 12345678  # Kendi ID numaranı yaz!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# AI Yapılandırması
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

SEKTORLER = {
    "HAVACILIK": ["THYAO.IS", "PGSUS.IS"],
    "BANKA": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS"],
    "ENERJI": ["ASTOR.IS", "SASA.IS", "EUPWR.IS"],
    "DEMIR-CELIK": ["EREGL.IS", "KRDMD.IS"]
}

def tabloya_baglan():
    if not SHEET_JSON:
        raise ValueError("GSPREAD_SERVICE_ACCOUNT kasada bulunamadı!")
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

async def ai_yorum_al(sembol, fiyat, rsi):
    if not GEMINI_KEY: return "AI yorumu devre dışı."
    prompt = f"{sembol} hissesi {fiyat} TL fiyatta ve RSI {rsi} seviyesinde. Kısa bir teknik yorum yap ve bir risk belirt."
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except: return "Analiz yapılamadı."

async def analiz_ve_islem(bot, sheet, sembol, sektor):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 30: return
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        fiyat, rsi = round(son['Close'], 2), round(son['RSI'], 1)

        # Sinyal Filtresi (RSI 35 Altı)
        if rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([tarih, sektor, sembol, fiyat, rsi, "BEKLEMEDE"])
            
            # AI Yorumu Al
            yorum = await ai_yorum_al(sembol, fiyat, rsi)

            # Grafik
            plt.style.use('dark_background')
            plt.figure(figsize=(10, 5))
            plt.plot(df.index[-25:], df['Close'][-25:], color='#00ff00', marker='o')
            plt.title(f"{sembol} - {fiyat} TL")
            plt.savefig(f"{sembol}.png")
            plt.close()

            caption = (f"🎯 <b>{sembol} ({sektor}) SİNYAL!</b>\n"
                       f"💰 Fiyat: {fiyat} TL | RSI: {rsi}\n\n"
                       f"🤖 <b>AI ANALİZİ:</b>\n{yorum}")
            
            with open(f"{sembol}.png", 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=caption, parse_mode='HTML')
            os.remove(f"{sembol}.png")
    except Exception as e: print(f"Hata {sembol}: {e}")

async def ana_islem():
    if not TOKEN or not SHEET_JSON: return
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    await bot.send_message(chat_id=MY_ID, text="🚀 <b>AI Destekli Borsa Analizi Başladı!</b>")
    for sektor, liste in SEKTORLER.items():
        tasks = [analiz_ve_islem(bot, sheet, s, sektor) for s in liste]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1)

if __name__ == "__main__":
