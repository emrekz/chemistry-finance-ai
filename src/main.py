import os
import threading
import tkinter as tk
import customtkinter as ctk
import requests
import time
import xml.etree.ElementTree as ET
import yfinance as yf
import pandas as pd
from markdown_pdf import MarkdownPdf, Section

# from dotenv import load_dotenv
from google import genai

keywords = [
    "polyurethane raw material prices",
    "housing market trends eurostat",
    "global freight rate index",
    "chemical supply chain",
]

# Load environment variables from .env file
# load_dotenv()

# Configure CustomTkinter design settings
ctk.set_appearance_mode("System")  # Options: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"


class AssistantApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Settings
        self.title("X KİMYA - Finans Risk Asistanı")
        self.geometry("700x500")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Label area takes fixed space
        self.grid_rowconfigure(1, weight=0)  # Key Input area takes fixed space
        self.grid_rowconfigure(2, weight=1)  # Chat box area takes full space

        self.styled_label = ctk.CTkLabel(
            master=self,
            text="X KİMYA | Finans Risk Asistanı",
            font=("Helvetica", 16, "bold"),
            text_color="white",
            fg_color="#364a58",  # Blue background color
            corner_radius=8,  # Rounded corners
            width=150,
            height=40,
        )
        self.styled_label.grid(row=0, column=0, padx=20, pady=(10, 20), sticky="ew")

        # UI Element API Key Input Layout Frame:
        self.api_input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.api_input_frame.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.api_input_frame.grid_columnconfigure(0, weight=1)

        # UI Element API Key Input Field:
        self.api_input = ctk.CTkEntry(
            self.api_input_frame,
            placeholder_text="Gemini API Key giriniz...",
            font=("Arial", 12),
        )
        self.api_input.grid(row=0, column=0, padx=(0, 0), sticky="ew")
        self.api_input.bind("<Return>", lambda event: self.start_chat_thread())

        # UI Element 1: Chat History Display (Scrollable)
        self.chat_display = ctk.CTkTextbox(
            self, state="disabled", wrap="word", font=("Arial", 12)
        )
        self.chat_display.grid(row=2, column=0, padx=20, pady=(20, 10), sticky="nsew")
        self.chat_display.tag_config("green_line", foreground="#15f800")
        self.chat_display.tag_config("yellow_line", foreground="#ffd900")
        self.chat_display.tag_config("red_line", foreground="#ff0000")
        self.chat_display.tag_config("white_line", foreground="#ffffff")

        # UI Element 4: Send Button
        self.send_button = ctk.CTkButton(
            self,
            text="Rapor Oluştur",
            command=self.start_chat_thread,
            font=("Arial", 12, "bold"),
        )
        self.send_button.grid(
            row=1, column=0, padx=20, pady=(10, 20), sticky="e"
        )  # Placed on grid right edge
        # self.input_frame.grid_columnconfigure(1, weight=0)
        # self.send_button.master = self.input_frame
        self.send_button.grid(row=0, column=1)

        # Core System Message Appending
        self.append_message(
            "Sistem",
            "Finans Risk Asistanı başlatıldı!\n" + "─" * 30 + "\n",
        )

    def append_message(self, sender: str, text: str, color: str = "white_line"):
        """Helper function to safely unlock, write, and re-lock the Textbox UI."""
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"[{sender}]: {text}", color)
        self.chat_display.see("end")  # Auto-scrolls to the bottom
        self.chat_display.configure(state="disabled")

    def connect_to_gemini(self):
        # Initialize the modern Google GenAI Client
        # It automatically picks up the GEMINI_API_KEY environment variable
        KEY = self.api_input.get().strip()
        try:
            self.ai_client = genai.Client(api_key=KEY)
            # self.append_message("Sistem", f"Gemini API bağlandı.\n")
        except Exception as e:
            print(
                f"Warning: Could not initialize Gemini Client. Check your API key. Error: {e}"
            )
            self.ai_client = None
            self.append_message("Sistem", f"Gemini API bağlantısı başarısız.\n\n")

    def start_chat_thread(self):
        self.connect_to_gemini()
        threading.Thread(target=self.get_news, args=(), daemon=True).start()

        self.send_button.configure(
            state="disabled"
        )  # Disable button to prevent spamming

        # Offload the network call to a background thread
        # threading.Thread(
        #     target=self.get_gemini_response, args=(prompt,), daemon=True
        # ).start()

    def get_gemini_response(self, prompt: str):
        """Backend worker loop executed strictly out-of-thread."""
        if not self.ai_client:
            self.after(
                0,
                lambda: self.append_message(
                    "System",
                    "Error: Gemini client not initialized. Check your .env API Key.\n\n",
                ),
            )
            self.after(0, lambda: self.send_button.configure(state="normal"))
            return

        try:
            self.append_message(
                "Sistem", f"Gemini AI verileri işliyor. Lütfen bekleyin...\n\n"
            )
            # Use 'after(0, ...)' to safely push text updates back onto the Main Tkinter UI Thread
            self.after(0, lambda: self.chat_display.configure(state="normal"))
            # self.after(0, lambda: self.chat_display.insert("end", "[Gemini]: "))

            # Use modern gemini-3.6-flash with streaming tokens
            self.response = self.ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )

            self.append_message(
                "Sistem", f"Gemini AI verileri işledi. Rapor hazırlanıyor...\n\n"
            )
            self.create_report()

            # for chunk in response_stream:
            #     if chunk.text:
            #         # Stream tokens straight into the text widget smoothly
            #         self.after(
            #             0, lambda text=chunk.text: self.chat_display.insert("end", text)
            #         )
            #         self.after(0, lambda: self.chat_display.see("end"))

            # # Stream complete; clean up breaks
            # self.after(
            #     0, lambda: self.chat_display.insert("end", "\n\n" + "─" * 30 + "\n\n")
            # )
            # self.after(0, lambda: self.chat_display.configure(state="disabled"))

        except Exception as e:
            self.after(
                0,
                lambda: self.append_message(
                    "Sistem", f"API Error: {e}\n\n", "red_line"
                ),
            )
            self.after(
                0,
                lambda: self.append_message(
                    "Sistem", f"Doğru API Key girdiğinizden emin olun.\n\n", "red_line"
                ),
            )

        finally:
            # Re-enable the send button when done
            self.after(0, lambda: self.send_button.configure(state="normal"))

    def get_news(self):
        self.append_message(
            "Sistem", f"Güncel haberler araştırılıyor. Lütfen bekleyin...\n\n"
        )
        self.news_list = f""
        for key in keywords:
            try:
                # print(f"\nNews for: {key}:")
                # self.append_message("İçerik:", f"{key}")
                url = (
                    "https://news.google.com/rss/search?hl=en&gl=US&ceid=US%3Aen&q="
                    + key
                )

                # Make the GET request (with a timeout safety net)
                response = requests.get(url, timeout=5)

                # Check if the request was successful (status code 200)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    for item in root.findall(".//item")[:5]:
                        baslik = item.find("title").text
                        self.news_list += f"- {baslik}\n"
                        # self.append_message("Haber:", f"- {baslik}")
                        # print(f"- {baslik}")

                else:
                    print(f"Failed with status code: {response.status_code}\n")

            except requests.exceptions.RequestException as e:
                # Handle connection errors, timeouts, etc.
                print(f"An error occurred: {e}\n")
                self.append_message(
                    "Sistem", f"Güncel haberler araştırılırken hata.\n\n", "red_line"
                )
                return

            # 3. Pause for 1 second before the next request (Politeness/Rate limiting)
            time.sleep(1)
        self.append_message("Sistem", f"Güncel haberler kaydedildi.\n\n", "yellow_line")
        threading.Thread(target=self.get_prices, args=(), daemon=True).start()

    def get_prices(self):
        self.append_message(
            "Sistem", f"Güncel fiyatlar araştırılıyor. Lütfen bekleyin...\n\n"
        )
        self.prices = ""
        # 1. OTOMASYON: Takip etmek istediğimiz finansal varlıkların Yahoo Finance sembolleri
        # BZ=F -> Brent Petrol, NG=F -> Doğalgaz, USDTRY=X -> Dolar Kuru
        semboller = {
            "Brent Petrol (Varil)": "BZ=F",
            "Doğalgaz (Henry Hub)": "NG=F",
            "Dolar Kuru (USD/TRY)": "USDTRY=X",
            "Euro Kuru (EUR/TRY)": "EURTRY=X",
            "Alüminyum (Metalik Pigment & Ambalaj)": "ALI=F",
            "Dow Inc. (Reçine & Polimer Trendi)": "DOW",
        }

        for isim, sembol in semboller.items():
            # Son 5 günlük veriyi çekiyoruz (Hafta sonu boşluklarını ve dünü yakalamak için)
            ticker = yf.Ticker(sembol)
            gecmis_veri = ticker.history(period="5d")

            if len(gecmis_veri) >= 2:
                # VERİ ANALİZİ: Son kapanış fiyatı ve bir önceki günün kapanış fiyatı
                guncel_fiyat = gecmis_veri["Close"].iloc[-1]
                onceki_fiyat = gecmis_veri["Close"].iloc[-2]

                # Yüzde değişimi hesaplama
                yuzde_degisim = ((guncel_fiyat - onceki_fiyat) / onceki_fiyat) * 100

                self.prices += f"- {isim}, Güncel Fiyat: {round(guncel_fiyat, 2)}, Önceki Kapanış: {round(onceki_fiyat, 2)}, Günlük Değişim (%): {round(yuzde_degisim, 2)}\n"
            else:
                print(f"Hata: {isim} için yeterli veri alınamadı.")
                self.append_message(
                    "Sistem", f"Güncel fiyatlar araştırılırken hata.\n\n", "red_line"
                )
                return

        self.append_message("Sistem", f"Güncel fiyatlar kaydedildi.\n\n", "yellow_line")

        self.PROMPT = f"""
        Sen kimya boya üretim sektöründe 20 yıllık deneyime sahip kıdemli bir Tedarik Zinciri ve Satın Alma Stratejistisin.
        Türkiye'de bir kimyasal boya üretim tesisinde çalışıyorsun.
        Aşağıda, internetten otomatik olarak toplanmış güncel sektörel haber başlıkları ve piyasa fiyatları yer almaktadır.

        Bu verileri inceleyerek, bir "Satın Alma Müdürü"nün haftalık/günlük operasyonel ve stratejik kararlarında kullanabileceği, profesyonel bir **"Yönetici Özet Raporu"** hazırla.

        Raporda şu kurallara kesinlikle uy:
        1. Dil tamamen kurumsal ve akıcı bir Türkçe olmalıdır.
        2. Sadece genel bir özet geçme; haberlerin satın alma maliyetlerine, tedarik sürelerine, lojistiğe veya hammadde bulunabilirliğine (polimerler, petrokimya, özel kimyasallar vb.) olası etkilerini yorumla.
        3. Varsa kritik riskleri (grevler, fabrika kapanmaları, kota/regülasyon değişiklikleri, navlun krizleri) "KRİTİK UYARI" başlığı altında en başa koy.
        4. Okumayı kolaylaştırmak için markdown formatı (kalın yazılar, listeler, kısa paragraflar) kullan.
        5. Haberler eski tarihli olabilir, güncel verilere ve günün şartlarına göre cevap ver.

        Analiz Edilecek Haber ve Fiyat Verileri:
        {self.news_list}
        {self.prices}

        Rapor Formatı:
        # 🚨 Kritik Satın Alma Uyarıları (Varsa)
        # 📈 Hammadde ve Tedarik Zinciri Analizi
        # ⚡ Stratejik Aksiyon Önerileri (Satın alma müdürünün ne yapması gerektiğine dair net tavsiyeler)
        """

        # Offload the network call to a background thread
        threading.Thread(
            target=self.get_gemini_response, args=(self.PROMPT,), daemon=True
        ).start()

    def create_report(self):
        # 2. Correct way: Pass toc_level when creating the MarkdownPdf instance
        pdf = MarkdownPdf(toc_level=2)

        # 3. Pass only the string into Section
        pdf.add_section(Section(self.response.text))

        # 4. Save the compiled content to a file
        pdf.save("günlük_risk_raporu.pdf")

        self.append_message(
            "Sistem", f"Rapor 'günlük_risk_raporu.pdf' oluşturuldu.\n\n", "green_line"
        )


if __name__ == "__main__":
    app = AssistantApp()
    app.mainloop()
