import streamlit as st
import pypdf
import re
import random
import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import Counter
import pandas as pd

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="MultiMaster 999",
    page_icon="🟣",  # Fioletowy pasuje do Multi Multi
    layout="wide"
)

PLIK_PDF = "tablica999.pdf"


# --- 2. STYLIZACJA (FIOLETOWO-RÓŻOWA - Styl Multi Multi) ---
def local_css():
    st.markdown("""
    <style>
    .stApp {
        background-color: #F8F0FA; /* Jasny fiolet */
        color: #000000;
    }

    /* Przyciski - Fioletowe z różową ramką */
    div.stButton > button {
        background-color: #8A2BE2 !important; /* BlueViolet */
        color: #FFFFFF !important;
        border-radius: 10px;
        border: 2px solid #FF1493 !important; /* DeepPink */
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #9400D3 !important;
        transform: scale(1.02);
    }

    /* Etykiety */
    .stTextArea label, .stTextInput label, .stNumberInput label {
        color: #FFFFFF !important;
        background-color: #8A2BE2 !important;
        padding: 4px 10px !important;
        border-radius: 5px !important;
    }

    /* Nagłówki */
    h1, h2, h3 {
        color: #4B0082 !important; /* Indigo */
        font-family: 'Arial', sans-serif;
    }

    .center-text {
        text-align: center;
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)


local_css()

# --- 3. INICJALIZACJA STANU ---
if 'multi_losowania' not in st.session_state:
    st.session_state['multi_losowania'] = []
if 'powitanie_ok' not in st.session_state:
    st.session_state['powitanie_ok'] = False
if 'email_wyslany' not in st.session_state:
    st.session_state['email_wyslany'] = False
if 'captcha_a' not in st.session_state:
    st.session_state['captcha_a'] = random.randint(1, 10)
    st.session_state['captcha_b'] = random.randint(1, 10)


# --- 4. OKNO POWITALNE ---
@st.dialog("🟣 Witaj w MultiMaster!")
def okno_powitalne():
    st.markdown("""
        <div class="center-text">
            <b>Generator zestawów 10-liczbowych do Multi Multi!</b><br>
            <br>Analiza 999 ostatnich losowań (pula 80 liczb).<br>
            Pamiętaj: To tylko statystyka, nie gwarancja.<br>
            Powodzenia! A.K.
        </div>
    """, unsafe_allow_html=True)
    if st.button("Startujemy!", type="primary", use_container_width=True):
        st.session_state['powitanie_ok'] = True
        st.rerun()


# --- 5. EMAILE ---
def wyslij_email_kontaktowy(tresc_wiadomosci, email_kontaktowy):
    try:
        nadawca = st.secrets["EMAIL_USER"]
        haslo = st.secrets["EMAIL_PASSWORD"]
        odbiorca = "pracapolmar@gmail.com"

        msg = MIMEMultipart()
        msg['From'] = nadawca
        msg['To'] = odbiorca
        msg['Subject'] = "🔔 Wygrana Multi Multi - Zgłoszenie"

        body = f"Wiadomość: {tresc_wiadomosci}\nKontakt: {email_kontaktowy}"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(nadawca, haslo)
        server.sendmail(nadawca, odbiorca, msg.as_string())
        server.quit()
        return True
    except:
        return False


# --- 6. PARSER PDF DLA MULTI MULTI (1-80) ---
@st.cache_data
def wczytaj_dane_multi(sciezka):
    if not os.path.exists(sciezka): return None
    nums_flat = []

    try:
        reader = pypdf.PdfReader(sciezka)
        for strona in reader.pages:
            tekst = strona.extract_text() or ""
            # Proste tokenizowanie
            tokens = re.findall(r'\d+', tekst)

            for token in tokens:
                temp = token
                while temp:
                    # Multi Multi ma liczby do 80. ID mają 5 cyfr (np. 16566).
                    # Ignorujemy ID (powyżej 80) i wyciągamy liczby gry (1-80).

                    # Sprawdź czy to ID (duża liczba)
                    if len(temp) >= 3 and int(temp[:3]) > 80:
                        # To prawdopodobnie ID lub rok, pomijamy
                        # Ale musimy wiedzieć ile znaków uciąć.
                        # Spróbujmy znaleźć pasujące 2-cyfrowe liczby najpierw.
                        pass

                    # Logika parsowania ciągów np "3839" -> 38, 39
                    if len(temp) >= 2 and 1 <= int(temp[:2]) <= 80:
                        nums_flat.append(int(temp[:2]))
                        temp = temp[2:]
                    elif len(temp) >= 1 and 1 <= int(temp[:1]) <= 9:
                        nums_flat.append(int(temp[:1]))
                        temp = temp[1:]
                    else:
                        # Jeśli zostało coś dziwnego (np. ID > 80), ucinamy 1 znak i próbujemy dalej
                        temp = temp[1:]

    except:
        return None

    # Czyszczenie i grupowanie
    # Wiemy, że w każdym losowaniu jest 20 liczb.
    # Ucinamy ewentualne śmieci z początku, żeby liczba pasowała do wielokrotności 20
    reszta = len(nums_flat) % 20
    if reszta != 0:
        # Usuwamy 'reszta' liczb z początku (najstarsze śmieci)
        nums_flat = nums_flat[reszta:]

    # Grupujemy w losowania
    wszystkie_losowania = []
    total_draws = len(nums_flat) // 20

    for i in range(total_draws):
        # Bierzemy paczkę 20 liczb
        los = nums_flat[i * 20: (i + 1) * 20]
        # Dla pewności filtrujemy czy są w zakresie 1-80
        los = [n for n in los if 1 <= n <= 80]
        if len(los) >= 10:  # Akceptujemy jeśli udało się wyciągnąć większość
            wszystkie_losowania.append({'Liczby': los})

    # Odwracamy, żeby najnowsze były na początku (jeśli PDF idzie chronologicznie)
    # Zazwyczaj w takich PDF najnowsze są na górze strony 1.
    # Wtedy lista nums_flat ma najnowsze na początku. Zostawiamy jak jest.
    return wszystkie_losowania


# --- 7. GENERATOR 10 LICZB ---
def generuj_zestaw_multi(dane):
    # Ostatnie 3 losowania (czyli 3 * 20 = 60 liczb)
    ostatnie_3 = dane[:3]
    zakazane = set()
    for los in ostatnie_3: zakazane.update(los['Liczby'])

    # Statystyka wszystkich liczb
    wszystkie_flat = [n for los in dane for n in los['Liczby']]
    licznik = Counter(wszystkie_flat)

    # 20% szans na ZIMNY, 80% na CIEPŁY
    if random.random() < 0.20:
        typ = "❄️ ZIMNY (10 liczb)"
        # Pula: Liczby 1-80, których NIE MA w ostatnich 3 losowaniach
        pula = [n for n in range(1, 81) if n not in zakazane]
        # Sortujemy od najrzadszych
        pula_sorted = sorted(pula, key=lambda x: licznik.get(x, 0))
        # Bierzemy 20 najrzadszych i losujemy z nich 10
        kandydaci = pula_sorted[:25]
        # Zabezpieczenie gdyby kandydatów było mniej
        if len(kandydaci) < 10: kandydaci = list(range(1, 81))
        zestaw = set(random.sample(kandydaci, 10))
    else:
        typ = "🔥 GORĄCY (10 liczb)"
        populacja = list(licznik.keys())
        wagi = list(licznik.values())
        zestaw = set()
        # Losujemy 10 liczb ważonych częstotliwością
        while len(zestaw) < 10:
            kandydat = random.choices(populacja, weights=wagi, k=1)[0]
            zestaw.add(kandydat)

    return sorted(list(zestaw)), typ


def przygotuj_plik_txt(historia):
    tekst = "--- WYNIKI MULTI MASTER ---\n"
    tekst += f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    for i, wpis in enumerate(historia):
        tekst += f"#{i + 1} [{wpis['Godzina']}] {wpis['Strategia']}\n"
        tekst += f"LICZBY: {wpis['Liczby']}\n\n"
    return tekst


# --- 9. GŁÓWNA APLIKACJA ---
def main():
    if not st.session_state['powitanie_ok']:
        okno_powitalne()

    with st.sidebar:
        st.markdown("## 🟣 MultiMaster")
        st.metric("Twoje zestawy", len(st.session_state['multi_losowania']))
        st.info("Baza: 999 losowań Multi Multi")

    st.markdown("<h1 style='text-align: center; color: #4B0082;'>🟣 Generator Multi Multi</h1>", unsafe_allow_html=True)

    if not os.path.exists(PLIK_PDF):
        st.error(f"Brak pliku {PLIK_PDF}!")
        return
    dane = wczytaj_dane_multi(PLIK_PDF)
    if not dane:
        st.error("Błąd odczytu PDF.")
        return

    st.divider()
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("GENERUJ 10 LICZB 🎲", type="primary", use_container_width=True):
            with st.spinner("Analiza 80 liczb..."):
                liczby, strategia = generuj_zestaw_multi(dane)

                teraz = datetime.now()
                nowy_wpis = {
                    "Godzina": teraz.strftime("%H:%M:%S"),
                    "Strategia": strategia,
                    "Liczby": str(liczby)
                }
                st.session_state['multi_losowania'].insert(0, nowy_wpis)

                st.success(f"Wygenerowano: {strategia}")
                # Ładne wyświetlenie 10 liczb
                st.markdown(f"<h3 style='text-align: center; color: #4B0082;'>{' - '.join(map(str, liczby))}</h3>",
                            unsafe_allow_html=True)
                st.balloons()

    with col2:
        st.warning(
            "💡 **Info:**\nMulti Multi losuje 20 liczb. My typujemy najlepszą 10-tkę, aby zmaksymalizować wygraną.")

    # --- KONTAKT I HISTORIA (Skrócone dla czytelności) ---
    st.divider()
    st.markdown("### 📬 Zgłoś wygraną")

    if st.session_state['email_wyslany']:
        st.success("Wiadomość wysłana!")
    else:
        with st.form("kontakt"):
            msg = st.text_area("Wiadomość")
            mail = st.text_input(" Twój Email")

            c1, c2 = st.columns(2)
            with c1:
                st.write(f"Ile to **{st.session_state['captcha_a']} + {st.session_state['captcha_b']}**?")
            with c2:
                ans = st.number_input("Wynik", step=1)

            if st.form_submit_button("Wyślij"):
                if ans == st.session_state['captcha_a'] + st.session_state['captcha_b']:
                    if wyslij_email_kontaktowy(msg, mail):
                        st.session_state['email_wyslany'] = True
                        st.rerun()
                else:
                    st.error("Błąd matematyczny!")
                    st.session_state['captcha_a'] = random.randint(1, 10)
                    st.session_state['captcha_b'] = random.randint(1, 10)
                    time.sleep(1)
                    st.rerun()

    st.divider()
    st.markdown("### 📜 Historia sesji")
    if st.session_state['multi_losowania']:
        data = st.session_state['multi_losowania'][:20]
        st.download_button("💾 Zapisz wyniki", przygotuj_plik_txt(data), "MultiWyniki.txt")
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()