import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
import json
import gspread
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from datetime import datetime

# --- AYARLAR ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
MY_ID = 750480616  # Kendi ID numaranı yazmayı unutma!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

def guncel_bist100_cek():
    """BIST 100 listesini çekmek için çoklu kaynak denemesi yapar."""
    # 1. Kaynak: Wikipedia (Geliştirilmiş Header ile)
    try:
        url = "https://tr.wikipedia.org/wiki/BIST_100"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        tablo = soup.find('table', {'class': 'wikitable'})
        df = pd.read_html(str(tablo))[0]
        kodlar = [str(kod).strip() + ".IS" for kod in df['Kod'].tolist() if len(str(kod)) <= 6]
        if len(kodlar) > 50: return kodlar
    except: pass

    # 2. Kaynak: Eğer yukarıdaki başarısız olursa alternatif liste (En popüler 100)
    print("⚠️ Dinamik liste çekilemedi, manuel geniş liste yükleniyor...")
    return [
        "THYAO.IS", "EREGL.IS", "TUPRS.IS", "AKBNK.IS", "SISE.IS", "KCHOL.IS", "SASA.IS", "ASTOR.IS",
        "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "BIMAS.IS", "SAHOL.IS", "ASELS.IS", "TCELL.IS", "PETKM.IS",
        "HEKTS.IS", "KOZAL.IS", "PGSUS.IS", "ARCLK.IS", "ENKAI.IS", "GUBRF.IS", "FROTO.IS", "TOASO.IS",
        "EUPWR.IS", "KONTR.IS", "MIATK.IS", "YEOTK.IS", "REEDR.IS", "ODAS.IS", "ZOREN.IS" # Bu listeyi 100'e tamamlayabilirsin
    ]

# --- TABLO VE RSI FONKSİYONLARI AYNI KALIYOR ---
def tabloya_baglan():
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

async def ai_yorumla(sembol, fiyat, rsi):
    if not GEMINI_KEY: return "AI Devre Dışı."
    try:
        await asyncio.sleep(4) # Rate limit koruması
        res = ai_model.generate_content(f"{sembol} {fiyat} TL, RSI {rsi}. 1 cümlelik analiz yap.")
        return res.text
    except: return "AI yoğun."

async def analiz_et(bot, sheet, sembol):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 20: return
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        fiyat, rsi = round(son['Close'], 2), round(son['RSI'], 1)

        # TEST İÇİN: Gerçek kullanımda rsi <= 35 yap
        if rsi <= 35:
            yorum = await ai_yorumla(sembol, fiyat, rsi)
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([tarih, "BIST100", sembol, fiyat, rsi, "BEKLEMEDE"])
            
            # Grafik ve Telegram gönderimi (Önceki kodla aynı)
            plt.style.use('dark_background')
            plt.figure(figsize=(8, 4))
            plt.plot(df.index[-20:], df['Close'][-20:], color='#00ff00', marker='o')
            plt.title(f"{sembol} - {fiyat} TL")
            plt.savefig(f"{sembol}.png")
            plt.close()

            with open(f"{sembol}.png", 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=f"🎯 {sembol}\nFiyat: {fiyat}\nRSI: {rsi}\n🤖 {yorum}", parse_mode='HTML')
            os.remove(f"{sembol}.png")
    except: pass

async def ana_islem():
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    hisseler = guncel_bist100_cek()
    
    await bot.send_message(chat_id=MY_ID, text=f"🚀 <b>{len(hisseler)} Hisse Taranıyor...</b>", parse_mode='HTML')
    
    for s in hisseler:
        await analiz_et(bot, sheet, s)
        await asyncio.sleep(1.5) # yfinance ban koruması

if __name__ == "__main__":
    asyncio.run(ana_islem())
