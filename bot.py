import yfinance as yf
import pandas as pd
import pandas_ta as ta
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616  # BURAYA KENDİ ID NUMARANI YAZ!
HISSELER = ["THYAO.IS", "EREGL.IS", "ASELS.IS", "SASA.IS", "BTC-USD"]

async def alpha_analiz(bot, sembol):
    """Her hisseyi tek tek analiz eden ve sinyal varsa mesaj atan fonksiyon."""
    try:
        hisse = yf.Ticker(sembol)
        # Analiz için yeterli veri (100 gün) çekiyoruz
        df = hisse.history(period="100d")
        
        if len(df) < 30:
            print(f"⚠️ {sembol} için yeterli veri yok.")
            return

        # Teknik Göstergeler (RSI ve Hareketli Ortalama)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['SMA20'] = ta.sma(df['Close'], length=20)
        
        son_fiyat = df['Close'].iloc[-1]
        son_rsi = df['RSI'].iloc[-1]
        son_sma = df['SMA20'].iloc[-1]
        onceki_fiyat = df['Close'].iloc[-2]
        onceki_sma = df['SMA20'].iloc[-2]

        mesaj = ""
        # STRATEJİ 1: RSI 35 Altı (Aşırı Ucuz/Fırsat)
        if son_rsi <= 35:
            mesaj = f"🚨 <b>{sembol} - FIRSAT BÖLGESİ</b>\n💰 Fiyat: {son_fiyat:.2f}\n📉 RSI: {son_rsi:.1f} (Aşırı Satım)"

        # STRATEJİ 2: Golden Cross / SMA Kırılımı
        elif son_fiyat > son_sma and onceki_fiyat <= onceki_sma:
            mesaj = f"🚀 <b>{sembol} - TREND BAŞLADI</b>\n💰 Fiyat: {son_fiyat:.2f}\n📈 20 Günlük Ortalama Yukarı Kırıldı!"

        if mesaj:
            await bot.send_message(chat_id=MY_ID, text=mesaj, parse_mode='HTML')
            print(f"✅ {sembol} için sinyal gönderildi.")
            
    except Exception as e:
        print(f"❌ {sembol} hatası: {str(e)}")

async def ana_islem():
    """Botun ana döngüsü."""
    if not TOKEN:
        print("🔴 HATA: TELEGRAM_TOKEN GitHub Secrets içinde bulunamadı!")
        return

    bot = Bot(token=TOKEN)
    print("🚀 Borsa analizi başlatılıyor...")
    
    # Tüm hisseleri aynı anda (paralel) tara
    tasks = [alpha_analiz(bot, s) for s in HISSELER]
    await asyncio.gather(*tasks)
    print("🏁 Analiz tamamlandı.")

# --- DÜZELTİLEN KISIM: AWAIT HATASI ÇÖZÜMÜ ---
if __name__ == "__main__":
    # GitHub ve yerel bilgisayar için en güvenli çalıştırma yöntemi
    import asyncio
    asyncio.run(ana_islem())
