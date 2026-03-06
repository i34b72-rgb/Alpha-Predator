import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
import json
import gspread
import google.generativeai as genai
import requests
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from datetime import datetime

# --- AYARLAR ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
MY_ID = 750480616  # Kendi ID numaranı buraya yaz!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

def guncel_bist100_cek():
    """Wikipedia'dan 100 hisseyi tarayıcı gibi görünerek çeker."""
    try:
        url = "https://tr.wikipedia.org/wiki/BIST_100"
        # Wikipedia'nın botları engellememesi için tarayıcı başlığı ekliyoruz
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        tablolar = pd.read_html(response.text)
        df = tablolar[0]
        hisse_kodlari = df['Kod'].tolist()
        liste = [str(kod) + ".IS" for kod in hisse_kodlari if len(str(kod)) <= 5]
        if len(liste) > 10:
            return liste
        raise ValueError("Liste çok kısa geldi.")
    except Exception as e:
        print(f"⚠️ Wikipedia hatası: {e}. Yedek liste kullanılıyor.")
        return ["THYAO.IS", "EREGL.IS", "TUPRS.IS", "AKBNK.IS", "SISE.IS", "KCHOL.IS", "SASA.IS", "ASTOR.IS"]

def tabloya_baglan():
    if not SHEET_JSON: raise ValueError("Secrets eksik!")
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

async def ai_analiz_yap(sembol, fiyat, rsi):
    """Gemini API limitlerine takılmamak için beklemeli çalışır."""
    if not GEMINI_KEY: return "AI Anahtarı Bulunamadı."
    prompt = f"{sembol} hissesi şu an {fiyat} TL ve RSI değeri {rsi}. Kısa bir teknik analiz ve bir risk uyarısı yap (Max 2 cümle)."
    try:
        # Ücretsiz kota koruması: Her AI isteği öncesi 4 saniye bekle
        await asyncio.sleep(4)
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI Limit Hatası: {e}")
        return "AI şu an yoğun, sadece teknik veriler kaydedildi."

async def analiz_et(bot, sheet, sembol):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 20: return
        
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        fiyat, rsi = round(son['Close'], 2), round(son['RSI'], 1)

        # STRATEJİ: RSI 35 ve altı (Alım fırsatı bölgesi)
        if rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([tarih, "BIST100", sembol, fiyat, rsi, "BEKLEMEDE"])
            
            # AI Yorumu Al
            yorum = await ai_analiz_yap(sembol, fiyat, rsi)

            # Grafik Çizimi
            plt.style.use('dark_background')
            plt.figure(figsize=(10, 5))
            plt.plot(df.index[-25:], df['Close'][-25:], color='#00ff00', marker='o', linewidth=2)
            plt.title(f"{sembol} - RSI: {rsi}")
            plt.grid(True, alpha=0.2)
            
            dosya_adi = f"{sembol}.png"
            plt.savefig(dosya_adi)
            plt.close()

            mesaj = (f"🎯 <b>{sembol} SİNYAL!</b>\n\n"
                     f"💰 Fiyat: {fiyat} TL\n"
                     f"📊 RSI: {rsi}\n\n"
                     f"🤖 <b>AI ANALİZİ:</b>\n{yorum}")
            
            with open(dosya_adi, 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=mesaj, parse_mode='HTML')
            os.remove(dosya_adi)
            
    except Exception as e:
        print(f"Hata ({sembol}): {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    
    # Güncel Listeyi Çek
    hisseler = guncel_bist100_cek()
    await bot.send_message(chat_id=MY_ID, text=f"🔍 <b>BIST 100 Taraması Başladı</b>\nToplam {len(hisseler)} hisse inceleniyor...")
    
    for s in hisseler:
        await analiz_et(bot, sheet, s)
        # yfinance limitlerine takılmamak için her hisse arası 1 saniye mola
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(ana_islem())
