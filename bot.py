import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import asyncio
import os
from telegram import Bot

# --- AYARLAR ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
MY_ID = 750480616 # Kendi ID numaranı yaz

# SEKTÖREL GRUPLANDIRMA (Adım 1)
SEKTORLER = {
    "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS"],
    "BANKA": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS"],
    "ENERJI": ["ASTOR.IS", "EUPWR.IS", "ALFAS.IS", "ENJSA.IS", "SASA.IS"],
    "DEMIR-CELIK": ["EREGL.IS", "KRDMD.IS"],
    "PERAKENDE": ["BIMAS.IS", "MGROS.IS", "SOKM.IS"],
    "HOLDING": ["KCHOL.IS", "SAHOL.IS", "DOHOL.IS"]
}

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def analiz_ve_kaydet(bot, sembol, sektor_adi):
    try:
        df = yf.Ticker(sembol).history(period="60d")
        if len(df) < 30: return

        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        
        # STRATEJİ: RSI 35 Altı (Adım 2 için kayıt tetikleyici)
        if son['RSI'] <= 35:
            # 1. Kayıt (Performans Ölçümü İçin - Adım 2)
            yeni_kayit = pd.DataFrame([{
                'Tarih': son.name, 'Hisse': sembol, 'Fiyat': son['Close'], 'RSI': son['RSI'], 'Sektor': sektor_adi
            }])
            yeni_kayit.to_csv('sinyal_kayitlari.csv', mode='a', index=False, header=not os.path.exists('sinyal_kayitlari.csv'))

            # 2. Grafik ve Mesaj (Adım 1 & 3)
            plt.style.use('dark_background')
            plt.figure(figsize=(10, 5))
            plt.plot(df.index[-20:], df['Close'][-20:], color='#00ff00', marker='o')
            plt.title(f"{sembol} ({sektor_adi}) - Sinyal: RSI {son['RSI']:.1f}")
            
            # AI Yorumu Hazırlığı (Adım 3)
            ai_notu = "🤖 AI Analizi: RSI dipte, hacim kontrol edilmeli. Tepki alımı muhtemel."
            
            caption = (f"🎯 <b>{sembol} [{sektor_adi}]</b>\n\n"
                       f"💰 Fiyat: {son['Close']:.2f} TL\n"
                       f"📊 RSI: {son['RSI']:.1f}\n\n"
                       f"{ai_notu}\n"
                       f"📈 <i>Bu sinyal kâr/zarar takibi için kaydedildi.</i>")

            dosya = f"{sembol}.png"
            plt.savefig(dosya)
            plt.close()
            with open(dosya, 'rb') as p:
                await bot.send_photo(chat_id=MY_ID, photo=p, caption=caption, parse_mode='HTML')
            os.remove(dosya)

    except Exception as e:
        print(f"{sembol} hatası: {e}")

async def ana_islem():
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=MY_ID, text="🐺 <b>Alpha Predator V3: Sektörel Tarama Başladı</b>", parse_mode='HTML')
    
    for sektor, hisseler in SEKTORLER.items():
        tasks = [analiz_ve_kaydet(bot, s, sektor) for s in hisseler]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(ana_islem())
