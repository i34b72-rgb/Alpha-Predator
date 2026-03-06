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
MY_ID = 750480616 # Kendi ID'ni yaz!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

def guncel_bist100_cek():
    """Wikipedia üzerinden güncel BIST 100 listesini otomatik çeker."""
    try:
        url = "https://tr.wikipedia.org/wiki/BIST_100"
        tablolar = pd.read_html(url)
        # Wikipedia'daki hisse listesi tablosunu alıyoruz
        df = tablolar[0]
        hisse_kodlari = df['Kod'].tolist()
        # Kodların sonuna .IS ekleyerek yfinance formatına getiriyoruz
        return [str(kod) + ".IS" for kod in hisse_kodlari if len(str(kod)) <= 5]
    except Exception as e:
        print(f"Liste çekilemedi, yedek liste kullanılıyor: {e}")
        return ["THYAO.IS", "EREGL.IS", "TUPRS.IS", "AKBNK.IS", "SISE.IS"]

def tabloya_baglan():
    if not SHEET_JSON: raise ValueError("Secret eksik!")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(SHEET_JSON.strip())
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Borsa_Sinyal_Takip").sheet1

def rsi_hesapla(series):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def ai_analiz(sembol, fiyat, rsi):
    if not GEMINI_KEY: return "Analiz yapılamadı."
    prompt = f"{sembol} {fiyat} TL ve RSI {rsi}. Kısa teknik yorum yap."
    try:
        res = ai_model.generate_content(prompt)
        return res.text
    except: return "AI şu an meşgul."

async def analiz_et(bot, sheet, sembol):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 30: return
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        fiyat, rsi = round(son['Close'], 2), round(son['RSI'], 1)

        # STRATEJİ: RSI 35 altı (Gerçek sinyal)
        if rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([tarih, "BIST100", sembol, fiyat, rsi, "BEKLEMEDE"])
            yorum = await ai_analiz(sembol, fiyat, rsi)

            plt.style.use('dark_background')
            plt.figure(figsize=(8, 4))
            plt.plot(df.index[-20:], df['Close'][-20:], color='#00ff00', marker='o')
            plt.title(f"{sembol} Analiz")
            plt.savefig(f"{sembol}.png")
            plt.close()

            cap = f"🎯 <b>{sembol} SİNYAL!</b>\nFiyat: {fiyat} TL | RSI: {rsi}\n\n🤖 <b>AI:</b> {yorum}"
            with open(f"{sembol}.png", 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=cap, parse_mode='HTML')
            os.remove(f"{sembol}.png")
    except Exception as e: print(f"{sembol} Hatası: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    hisseler = guncel_bist100_cek() # OTOMATİK LİSTE BURADA DEVREYE GİRİYOR
    
    await bot.send_message(chat_id=MY_ID, text=f"🔎 <b>BIST 100 Otomatik Tarama Başladı...</b>\nToplam {len(hisseler)} hisse inceleniyor.")
    
    for s in hisseler:
        await analiz_et(bot, sheet, s)
        await asyncio.sleep(1) # Rate limit koruması

if __name__ == "__main__":
    asyncio.run(ana_islem())
