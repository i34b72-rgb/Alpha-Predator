import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
from datetime import datetime

# --- GÜVENLİK AYARLARI ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616  # BURAYA KENDİ ID NUMARANI YAZ
SHEET_JSON = os.environ.get('GSPREAD_SERVICE_ACCOUNT')

# SEKTÖREL LİSTE
SEKTORLER = {
    "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "BANKA": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS"],
    "ENERJI": ["ASTOR.IS", "EUPWR.IS", "ALFAS.IS", "SASA.IS"],
    "DEMIR-CELIK": ["EREGL.IS", "KRDMD.IS"],
    "HOLDING": ["KCHOL.IS", "SAHOL.IS"]
}

def tabloya_baglan():
    """Google Sheets bağlantısını kurar."""
    if not SHEET_JSON:
        raise ValueError("GitHub Secrets: GSPREAD_SERVICE_ACCOUNT eksik!")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(SHEET_JSON.strip())
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Google Sheets'teki dosya adıyla birebir aynı olmalı
    return client.open("Borsa_Sinyal_Takip").sheet1

def rsi_hesapla(series, period=14):
    """Pandas-ta olmadan manuel RSI hesaplar."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def analiz_ve_kaydet(bot, sheet, sembol, sektor):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 30: return

        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        son_fiyat = round(son['Close'], 2)
        son_rsi = round(son['RSI'], 1)

        # STRATEJİ: RSI 35 ve altı (Alım Fırsatı)
        if son_rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # 1. Google Sheets Kaydı
            sheet.append_row([tarih, sektor, sembol, son_fiyat, son_rsi, "FIRSAT"])

            # 2. Grafik Oluşturma
            plt.style.use('dark_background')
            plt.figure(figsize=(10, 5))
            plt.plot(df.index[-25:], df['Close'][-25:], color='#00ff00', marker='o')
            plt.title(f"{sembol} - RSI: {son_rsi}")
            plt.grid(True, alpha=0.3)
            
            dosya = f"{sembol}.png"
            plt.savefig(dosya)
            plt.close()

            # 3. Telegram Mesajı
            caption = (f"🎯 <b>{sembol} ({sektor})</b>\n\n"
                       f"💰 Fiyat: {son_fiyat} TL\n"
                       f"📊 RSI: {son_rsi}\n"
                       f"✅ Veri Google Sheets'e kaydedildi.")
            
            with open(dosya, 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=caption, parse_mode='HTML')
            os.remove(dosya)

    except Exception as e:
        print(f"Hata {sembol}: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    
    await bot.send_message(chat_id=MY_ID, text="🔎 <b>Sektörel Tarama ve Tablo Kaydı Başladı...</b>", parse_mode='HTML')
    
    for sektor, liste in SEKTORLER.items():
        tasks = [analiz_ve_kaydet(bot, sheet, s, sektor) for s in liste]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(ana_islem())
