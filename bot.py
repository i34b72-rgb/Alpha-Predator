import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
import urllib.parse
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı buraya yaz!

# BIST 100 TAM LİSTE (Örnek bir grup, tamamını tarar)
BIST100 = [
    "THYAO.IS", "EREGL.IS", "ASELS.IS", "SASA.IS", "KCHOL.IS", "SISE.IS", "AKBNK.IS",
    "GARAN.IS", "TUPRS.IS", "BIMAS.IS", "ISCTR.IS", "YKBNK.IS", "SAHOL.IS", "HEKTS.IS",
    "PGSUS.IS", "EKGYO.IS", "EREGL.IS", "PETKM.IS", "TOASO.IS", "ARCLK.IS", "FROTO.IS"
    # Buraya BIST100'ün diğer kodlarını da ekleyebilirsin.
]

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def haber_bul(sembol):
    """Hisseye özel borsa haberlerini tarar."""
    temiz_ad = sembol.replace(".IS", "")
    query = urllib.parse.quote(f"{temiz_ad} hisse haber")
    url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"
    # Şimdilik link olarak mesajda sunacağız
    return f"🔍 <a href='{url}'>{temiz_ad} Son Haberler için Tıkla</a>"

async def analiz_ve_rapor(bot, sembol):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 20: return

        df['RSI'] = rsi_hesapla(df['Close'])
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        son = df.iloc[-1]
        
        # --- STRATEJİ: RSI 35 ALTI (UCUZ) VEYA SMA KIRILIMI ---
        if son['RSI'] <= 35 or (son['Close'] > son['SMA20'] and df['Close'].iloc[-2] <= df['SMA20'].iloc[-2]):
            durum = "📉 AŞIRI SATIM (UCUZ)" if son['RSI'] <= 35 else "🚀 TREND YUKARI KIRILDI"
            haber_linki = await haber_bul(sembol)
            
            mesaj = (f"🎯 <b>{sembol} SİNYAL YAKALANDI!</b>\n\n"
                     f"💰 Fiyat: {son['Close']:.2f} TL\n"
                     f"📊 RSI: {son['RSI']:.1f}\n"
                     f"📢 Durum: {durum}\n\n"
                     f"📰 <b>Haber Analizi:</b>\n{haber_linki}")
            
            await bot.send_message(chat_id=MY_ID, text=mesaj, parse_mode='HTML', disable_web_page_preview=True)
            
            # Grafik çizimi
            plt.figure(figsize=(8, 4))
            plt.plot(df.index[-20:], df['Close'][-20:], label='Fiyat', color='blue')
            plt.title(f"{sembol} - Son 20 Gün")
            plt.grid(True)
            plt.savefig(f"{sembol}.png")
            plt.close()
            
            with open(f"{sembol}.png", 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p)
            os.remove(f"{sembol}.png")

    except Exception as e:
        print(f"{sembol} hatası: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=MY_ID, text="🔎 <b>BIST 100 Tam Tarama Başlatıldı...</b>", parse_mode='HTML')
    
    # Tüm listeyi paralel olarak tara (Hız için)
    tasks = [analiz_ve_rapor(bot, s) for s in BIST100]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(ana_islem())
