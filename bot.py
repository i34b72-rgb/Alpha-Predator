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

# BIST 100 GENİŞLETİLMİŞ TARAMA LİSTESİ
BIST100 = [
    "THYAO.IS", "EREGL.IS", "ASELS.IS", "SASA.IS", "KCHOL.IS", "SISE.IS", "AKBNK.IS",
    "GARAN.IS", "TUPRS.IS", "BIMAS.IS", "ISCTR.IS", "YKBNK.IS", "SAHOL.IS", "HEKTS.IS",
    "PGSUS.IS", "EKGYO.IS", "PETKM.IS", "TOASO.IS", "ARCLK.IS", "FROTO.IS", "TCELL.IS",
    "TKFEN.IS", "TTKOM.IS", "KOZAL.IS", "GUBRF.IS", "HALKB.IS", "VAKBN.IS", "DOHOL.IS",
    "SKBNK.IS", "TSKB.IS", "ALARK.IS", "ARDYZ.IS", "BERA.IS", "CANTE.IS", "CIMSA.IS",
    "DOAS.IS", "ECILC.IS", "EGEEN.IS", "ENJSA.IS", "ENKAI.IS", "GESAN.IS", "GLYHO.IS",
    "GSDHO.IS", "IPEKE.IS", "ISGYO.IS", "JANTS.IS", "KARSN.IS", "KONTR.IS", "KORDS.IS",
    "KRDMD.IS", "MGROS.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "QUAGR.IS", "REEDR.IS",
    "SMRTG.IS", "SOKM.IS", "TAVHL.IS", "TKNSA.IS", "TMSN.IS", "TRGYO.IS", "TURSG.IS",
    "ULKER.IS", "VESBE.IS", "VESTL.IS", "ZOREN.IS", "EUPWR.IS", "ASTOR.IS", "ALFAS.IS"
]

def rsi_hesapla(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))

async def rapor_olustur_ve_gonder(bot, sembol, df):
    try:
        son = df.iloc[-1]
        temiz_ad = sembol.replace(".IS", "")
        
        # Grafik Çizimi
        plt.style.use('dark_background') # Daha profesyonel görünüm
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df.index[-25:], df['Close'][-25:], marker='o', linestyle='-', color='#00ff00', label='Fiyat')
        
        # Grafik üzerine fiyat etiketleri ve başlık
        plt.title(f"{temiz_ad} - Teknik Analiz Raporu", fontsize=14, color='white')
        plt.grid(True, color='gray', linestyle='--', alpha=0.5)
        
        # Sağ üst köşeye fiyat bilgisini yazdır (Grafik içinde)
        info_text = f"Son Fiyat: {son['Close']:.2f} TL\nRSI: {son['RSI']:.1f}"
        plt.text(0.02, 0.95, info_text, transform=ax.transAxes, fontsize=12, 
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='black', alpha=0.5))

        dosya_adi = f"{temiz_ad}.png"
        plt.savefig(dosya_adi, bbox_inches='tight')
        plt.close()

        # Haber linki
        query = urllib.parse.quote(f"{temiz_ad} hisse haber")
        haber_url = f"https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"

        caption = (f"🎯 <b>{temiz_ad} Sinyal Analizi</b>\n\n"
                   f"💰 Güncel Fiyat: {son['Close']:.2f} TL\n"
                   f"📊 RSI Seviyesi: {son['RSI']:.1f}\n"
                   f"📢 Durum: <b>{'Uzatılmış Alım Fırsatı' if son['RSI'] < 35 else 'Trend Takibi'}</b>\n\n"
                   f"📰 <a href='{haber_url}'>Son Dakika Haberleri İçin Tıkla</a>")

        with open(dosya_adi, 'rb') as photo:
            await bot.send_photo(chat_id=MY_ID, photo=photo, caption=caption, parse_mode='HTML')
        
        os.remove(dosya_adi)
    except Exception as e:
        print(f"Rapor hatası ({sembol}): {e}")

async def analiz_et(bot, sembol):
    try:
        hisse = yf.Ticker(sembol)
        df = hisse.history(period="60d")
        if len(df) < 25: return

        df['RSI'] = rsi_hesapla(df['Close'])
        son = df.iloc[-1]
        
        # Filtre: RSI 40'ın altındaysa (Toparlanma beklenen bölge)
        if son['RSI'] <= 40:
            await rapor_olustur_ve_gonder(bot, sembol, df)
            
    except Exception as e:
        print(f"{sembol} tarama hatası: {e}")

async def ana_islem():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=MY_ID, text="🔎 <b>BIST 100 Tam Tarama Başladı...</b>\n<i>Fırsatlar raporlanıyor.</i>", parse_mode='HTML')
    
    # 10'arlı gruplar halinde tara (Sistem kilitlenmesin diye)
    for i in range(0, len(BIST100), 10):
        grup = BIST100[i:i+10]
        tasks = [analiz_et(bot, s) for s in grup]
        await asyncio.gather(*tasks)
        await asyncio.sleep(1) # Yahoo Finance banlanmaması için kısa ara

if __name__ == "__main__":
    asyncio.run(ana_islem())
