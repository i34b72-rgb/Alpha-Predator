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
MY_ID = 750480616  # Kendi ID numaranı yaz!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')

# --- BIST 100 TAM LİSTE ---
BIST100 = [
    "AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKFYE.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALBRK.IS",
    "ALFAS.IS", "ANSGR.IS", "ARCLK.IS", "ARDYZ.IS", "ASGYO.IS", "ASELS.IS", "ASTOR.IS", "AYDEM.IS", "BERA.IS", "BIMAS.IS",
    "BRSAN.IS", "BRYAT.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "EGEEN.IS",
    "EKGYO.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GSDHO.IS",
    "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS", "ISMEN.IS", "IZMDC.IS",
    "KAYSE.IS", "KCHOL.IS", "KCAER.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAL.IS", "KOZAA.IS", "KRDMD.IS", "MAVI.IS",
    "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", "QUAGR.IS", "REEDR.IS",
    "SAHOL.IS", "SASA.IS", "SAYAS.IS", "SDTTR.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SNGYO.IS", "SOKM.IS", "TABGD.IS",
    "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUPRS.IS", "TURSG.IS",
    "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YEOTK.IS", "YKBNK.IS", "ZOREN.IS"
]

def tabloya_baglan():
    creds_dict = json.loads(SHEET_JSON.strip())
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds).open("Borsa_Sinyal_Takip").sheet1

def teknik_analiz_yap(df):
    """Kendi teknik analiz mantığımız: RSI + SMA20 + Hacim"""
    # RSI Hesapla
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 20 Günlük Ortalama (SMA)
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    
    # Son Veriler
    son = df.iloc[-1]
    onceki = df.iloc[-2]
    
    rsi = round(son['RSI'], 1)
    fiyat = round(son['Close'], 2)
    sma20 = round(son['SMA20'], 2)
    hacim_artisi = son['Volume'] > df['Volume'].tail(5).mean() # Son hacim 5 günlük ortalamadan yüksek mi?

    # SİNYAL KARARI
    durum = "NÖTR"
    if rsi <= 35 and fiyat < sma20:
        durum = "GÜÇLÜ AL (UCUZ)"
    elif rsi >= 70:
        durum = "SATIŞ BÖLGESİ"
        
    return durum, rsi, fiyat, sma20

async def analiz_ve_gonder(bot, sheet, sembol):
    try:
        data = yf.Ticker(sembol).history(period="60d")
        if len(data) < 30: return

        durum, rsi, fiyat, sma20 = teknik_analiz_yap(data)

        # Sadece "GÜÇLÜ AL" sinyallerini bildiriyoruz
        if durum == "GÜÇLÜ AL (UCUZ)":
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            sheet.append_row([tarih, "BIST100", sembol, fiyat, rsi, durum])

            # Grafik Çizimi
            plt.style.use('dark_background')
            plt.figure(figsize=(10, 5))
            plt.plot(data.index[-30:], data['Close'][-30:], label='Fiyat', color='#00ff00')
            plt.plot(data.index[-30:], data['SMA20'][-30:], label='SMA20', color='#ff9900', linestyle='--')
            plt.title(f"{sembol} - {durum}")
            plt.legend()
            plt.grid(alpha=0.2)
            
            dosya = f"{sembol}.png"
            plt.savefig(dosya)
            plt.close()

            mesaj = (f"🚀 <b>{sembol} - ALIM FIRSATI!</b>\n\n"
                     f"💰 Fiyat: {fiyat} TL\n"
                     f"📊 RSI: {rsi}\n"
                     f"📉 20 Günlük Ort: {sma20} TL\n\n"
                     f"✅ <i>Analiz: Fiyat ortalamanın altında ve RSI aşırı satım bölgesinde.</i>")
            
            with open(dosya, 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=mesaj, parse_mode='HTML')
            os.remove(dosya)

    except Exception as e:
        print(f"{sembol} Hatası: {e}")

async def ana_islem():
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    await bot.send_message(chat_id=MY_ID, text=f"🔍 <b>Kendi Analiz Motorumuz Başladı</b>\n{len(BIST100)} hisse taranıyor...")
    
    for s in BIST100:
        await analiz_ve_gonder(bot, sheet, s)
        await asyncio.sleep(0.5) # AI olmadığı için daha hızlı tarayabiliriz

if __name__ == "__main__":
    asyncio.run(ana_islem())
