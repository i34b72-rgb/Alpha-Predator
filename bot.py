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

# --- AYARLAR ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı yaz!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')

SEKTORLER = {
    "HAVACILIK": ["THYAO.IS", "PGSUS.IS"],
    "BANKA": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS"],
    "ENERJI": ["ASTOR.IS", "SASA.IS", "EUPWR.IS"],
    "DEMIR-CELIK": ["EREGL.IS", "KRDMD.IS"]
}

def tabloya_baglan():
    if not SHEET_JSON:
        raise ValueError("HATA: GSPREAD_SERVICE_ACCOUNT GitHub Secrets'ta bulunamadı!")
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(SHEET_JSON.strip())
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # E-Tablo adının "Borsa_Sinyal_Takip" olduğundan emin ol
    return client.open("Borsa_Sinyal_Takip").sheet1

def rsi_hesapla(series, period=14):
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
        fiyat = round(son['Close'], 2)
        rsi = round(son['RSI'], 1)

        # TEST İÇİN: Gerçek sinyal RSI <= 35'tir. 
        # Hemen veri görmek istersen burayı geçici olarak 70 yapabilirsin.
        if rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            
            # 1. GOOGLE SHEETS KAYDI (ADIM 2 PERFORMANS ALTYAPISI)
            sheet.append_row([tarih, sektor, sembol, fiyat, rsi, "BEKLEMEDE"])

            # 2. GRAFİK HAZIRLAMA
            plt.style.use('dark_background')
            plt.figure(figsize=(10, 5))
            plt.plot(df.index[-25:], df['Close'][-25:], color='#00ff00', marker='o', linewidth=2)
            plt.title(f"{sembol} - RSI: {rsi} - Fiyat: {fiyat}TL")
            plt.grid(True, alpha=0.2)
            
            dosya = f"{sembol}.png"
            plt.savefig(dosya)
            plt.close()

            # 3. TELEGRAM MESAJI
            caption = (f"🎯 <b>{sembol} ({sektor}) SİNYAL!</b>\n\n"
                       f"💰 Giriş Fiyatı: {fiyat} TL\n"
                       f"📊 RSI Seviyesi: {rsi}\n"
                       f"📝 <i>Veri performans takibi için Google Sheets'e işlendi.</i>")
            
            with open(dosya, 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=caption, parse_mode='HTML')
            os.remove(dosya)

    except Exception as e:
        print(f"Hata ({sembol}): {e}")

async def ana_islem():
    if not TOKEN or not SHEET_JSON:
        print("❌ Eksik Yapılandırma! Secrets kısmını kontrol edin.")
        return
        
    bot = Bot(token=TOKEN)
    try:
        sheet = tabloya_baglan()
        await bot.send_message(chat_id=MY_ID, text="🐺 <b>Alpha Predator V3 Aktif!</b>\nSektörel tarama ve kayıt başlıyor...")
        
        for sektor, liste in SEKTORLER.items():
            tasks = [analiz_ve_kaydet(bot, sheet, s, sektor) for s in liste]
            await asyncio.gather(*tasks)
            await asyncio.sleep(1) # Banlanmamak için kısa ara
            
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")

if __name__ == "__main__":
    asyncio.run(ana_islem())
