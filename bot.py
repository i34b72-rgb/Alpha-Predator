import yfinance as yf
import gspread
import os
import json
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
import asyncio
from datetime import datetime

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı yaz
SHEET_JSON = os.environ.get('GSPREAD_SERVICE_ACCOUNT')

# Google Sheets Bağlantısı
def tabloya_baglan():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(SHEET_JSON)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("Borsa_Sinyal_Takip").sheet1

async def analiz_ve_tabloya_yaz(bot, sheet, sembol, sektor):
    try:
        hisse = yf.Ticker(sembol)
        df = hisse.history(period="60d")
        if len(df) < 20: return
        
        # Basit RSI Hesaplama
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        son_fiyat = df['Close'].iloc[-1]

        if rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            # Google Sheets'e yeni satır ekle
            sheet.append_row([tarih, sektor, sembol, round(son_fiyat, 2), round(rsi, 1), "FIRSAT"])
            
            # Telegram Mesajı
            await bot.send_message(chat_id=MY_ID, text=f"✅ {sembol} Tabloya Kaydedildi!\nFiyat: {son_fiyat:.2f}\nRSI: {rsi:.1f}")
    except Exception as e:
        print(f"Hata {sembol}: {e}")

async def ana_islem():
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    
    hisseler = {"HAVACILIK": ["THYAO.IS"], "ENERJI": ["ASTOR.IS"]} # Listeni buraya ekle
    
    for sektor, liste in hisseler.items():
        for s in liste:
            await analiz_ve_tabloya_yaz(bot, sheet, s, sektor)

if __name__ == "__main__":
    asyncio.run(ana_islem())
