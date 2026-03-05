import yfinance as yf
import pandas_ta as ta
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı buraya yaz
HISSELER = ["THYAO.IS", "EREGL.IS", "ASELS.IS", "SASA.IS", "BTC-USD", "ETH-USD"]

async def alpha_analiz(sembol):
    try:
        # Analiz için 100 günlük geniş veri seti çekiyoruz
        df = yf.Ticker(sembol).history(period="100d")
        if len(df) < 50: return None

        # --- TEKNİK HESAPLAMALAR ---
        # 1. RSI (Göreceli Güç)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        # 2. Hareketli Ortalamalar (Trend Takibi)
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        # 3. Hacim Ortalaması (Patlayıcı Güç Kontrolü)
        df['Vol_Avg'] = ta.sma(df['Volume'], length=10)

        son = df.iloc[-1]
        onceki = df.iloc[-2]

        mesaj = ""
        # STRATEJİ 1: Hacimli RSI Düşüşü (Gerçek Fırsat)
        if son['RSI'] < 30 and son['Volume'] > son['Vol_Avg']:
            mesaj = f"🚨 <b>{sembol} - HACİMLİ DİP YAKALANDI!</b>\nRSI: {son['RSI']:.1f}\nHacim: Ortalamanın %{ (son['Volume']/son['Vol_Avg'])*100:.0f} üzerinde.\n"

        # STRATEJİ 2: SMA50 Kesişmesi (Trend Dönüşü)
        elif son['Close'] > son['SMA50'] and onceki['Close'] <= onceki['SMA50']:
            mesaj = f"🚀 <b>{sembol} - 50 GÜNLÜK DİRENCİ KIRDI!</b>\nYeni bir yükseliş trendi başlayabilir.\n"

        if mesaj:
            return f"{mesaj}Fiyat: {son['Close']:.2f}\n------------------\n"
    except:
        return None
    return None

async def ana_islem():
    bot = Bot(token=TOKEN)
    
    # Tüm hisseleri aynı anda (paralel) analiz et
    gorevler = [alpha_analiz(s) for s in HISSELER]
    sonuclar = await asyncio.gather(*gorevler)
    
    final_rapor = "".join([s for s in sonuclar if s])

    if final_rapor:
        await bot.send_message(chat_id=MY_ID, text=f"<b>🐺 ALPHA PREDATOR SİNYAL</b>\n\n{final_rapor}", parse_mode='HTML')
    else:
        print("Sinyal yok, pusuya devam...")

if __name__ == "__main__":
    asyncio.run(ana_islem())
