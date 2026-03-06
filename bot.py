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
MY_ID = 750480616  # Kendi ID numaranı buraya yaz!
SHEET_JSON = os.getenv('GSPREAD_SERVICE_ACCOUNT')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

# --- BIST 100 SABİT VE TAM LİSTE ---
BIST100_HİSSELERİ = [
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
    if not SHEET_JSON: raise ValueError("Secrets eksik!")
    creds_dict = json.loads(SHEET_JSON.strip())
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds).open("Borsa_Sinyal_Takip").sheet1

def rsi_hesapla(series):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def ai_yorum_al(sembol, fiyat, rsi):
    if not GEMINI_KEY: return "AI Kapalı."
    try:
        await asyncio.sleep(4) # Kotayı korumak için bekleme
        res = ai_model.generate_content(f"{sembol} {fiyat} TL ve RSI {rsi}. 1 cümlelik çok kısa analiz yap.")
        return res.text
    except: return "AI yoğun."

async def analiz_et(bot, sheet, sembol):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 20: return
        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        fiyat, rsi = round(son['Close'], 2), round(son['RSI'], 1)

        # STRATEJİ: RSI 35 ve altı
        if rsi <= 35:
            tarih = datetime.now().strftime("%d/%m/%Y %H:%M")
            yorum = await ai_yorum_al(sembol, fiyat, rsi)
            sheet.append_row([tarih, "BIST100", sembol, fiyat, rsi, "BEKLEMEDE"])
            
            plt.style.use('dark_background')
            plt.figure(figsize=(8, 4))
            plt.plot(df.index[-20:], df['Close'][-20:], color='#00ff00', marker='o')
            plt.title(f"{sembol} - {fiyat} TL")
            plt.savefig(f"{sembol}.png")
            plt.close()

            with open(f"{sembol}.png", 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=f"🎯 <b>{sembol}</b>\nFiyat: {fiyat}\nRSI: {rsi}\n🤖 {yorum}", parse_mode='HTML')
            os.remove(f"{sembol}.png")
    except: pass

async def ana_islem():
    bot = Bot(token=TOKEN)
    sheet = tabloya_baglan()
    
    # Bilgi mesajı
    await bot.send_message(chat_id=MY_ID, text=f"🚀 <b>BIST 100 Taraması Başladı</b>\nToplam {len(BIST100_HİSSELERİ)} hisse inceleniyor...", parse_mode='HTML')
    
    for s in BIST100_HİSSELERİ:
        await analiz_et(bot, sheet, s)
        await asyncio.sleep(1.2) # Banlanma koruması

if __name__ == "__main__":
    asyncio.run(ana_islem())
