import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı yaz
# BIST 100 hisselerinin bir listesini (Örn: THYAO, EREGL...) buraya ekleyebiliriz.
# Test için şimdilik ana hisseleri koyuyorum, listeyi genişletebilirsin.
BIST_TARAMA = ["THYAO.IS", "EREGL.IS", "ASELS.IS", "SASA.IS", "KCHOL.IS", "SISE.IS", "AKBNK.IS"]

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def grafik_olustur_ve_gonder(bot, sembol, df):
    """Sinyal veren hissenin son 30 günlük grafiğini çizer."""
    plt.figure(figsize=(10, 6))
    plt.plot(df.index[-30:], df['Close'][-30:], label='Fiyat', color='blue', linewidth=2)
    plt.title(f"{sembol} - Teknik Analiz Grafiği")
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    dosya_adi = f"{sembol}_grafik.png"
    plt.savefig(dosya_adi)
    plt.close()
    
    with open(dosya_adi, 'rb') as photo:
        await bot.send_photo(chat_id=MY_ID, photo=photo, caption=f"📊 {sembol} için detaylı teknik grafik hazır.")
    os.remove(dosya_adi)

async def analiz_et(bot, sembol):
    try:
        df = yf.Ticker(sembol).history(period="100d")
        if len(df) < 30: return

        df['RSI'] = rsi_hesapla(df['Close'])
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['Vol_Avg'] = df['Volume'].rolling(window=10).mean()

        son = df.iloc[-1]
        
        # --- KRİTİK SÜZGEÇ (FIRSAT YAKALAMA) ---
        if son['RSI'] <= 35 and son['Volume'] > son['Vol_Avg']:
            mesaj = (f"🎯 <b>{sembol} SÜZGECE TAKILDI!</b>\n\n"
                     f"💰 Fiyat: {son['Close']:.2f}\n"
                     f"📉 RSI: {son['RSI']:.1f}\n"
                     f"📈 Hacim: Güçlü Artış!\n"
                     f"🤖 <b>AI Yorumu:</b> Aşırı satım bölgesinde hacimli toparlanma emaresi. Teknik olarak 'Tepki Alımı' beklenebilir.")
            
            await bot.send_message(chat_id=MY_ID, text=mesaj, parse_mode='HTML')
            await grafik_olustur_ve_gonder(bot, sembol, df)

    except Exception as e:
        print(f"{sembol} hatası: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    # Tüm BIST Tarama listesini asenkron (hızlı) tara
    tasks = [analiz_et(bot, s) for s in BIST_TARAMA]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(ana_islem())
