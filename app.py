import streamlit as st
import pypdf
import re
import random
import os
import pandas as pd
from collections import Counter

# --- KONFIGURACJA DLA MULTI MULTI ---
st.set_page_config(
    page_title="Multi Smart System",
    page_icon="🟣",
    layout="centered"
)

# --- STYL (FIOLETOWY) ---
st.markdown("""
    <style>
    .stApp { background-color: #1a0526; color: white; } /* Ciemny fiolet */
    .big-number {
        font-size: 20px; font-weight: bold; color: white;
        background-color: #8e44ad; /* Fiolet Multi */
        border-radius: 50%;
        width: 45px; height: 45px; display: inline-flex;
        justify-content: center; align-items: center;
        margin: 4px; box-shadow: 2px 2px 8px rgba(0,0,0,0.6);
        border: 2px solid #9b59b6;
    }
    .metric-box {
        background-color: #2c0e3a; padding: 12px; border-radius: 8px;
        text-align: center; border: 1px solid #4a148c; margin-bottom: 10px;
        color: #e0e0e0;
    }
    h1 { color: #d1c4e9 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE ---
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return []
    draws = []
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text() or ""
            tokens = re.findall(r'\d+', text)
            i = 0
            while i < len(tokens):
                candidates = []
                offset = 0
                # Szukamy ciągu 20 liczb (wyniki losowania Multi to 20 kul)
                # Ale my będziemy wybierać z nich statystykę dla 80 liczb
                while len(candidates) < 20 and (i + offset) < len(tokens):
                    try:
                        val = int(tokens[i+offset])
                        if 1 <= val <= 80:
                            candidates.append(val)
                        else:
                            # Jeśli liczba > 80 (np. ID losowania), przerywamy
                            if candidates: break
                    except: break
                    offset += 1
                
                # Jeśli znaleźliśmy przynajmniej 10 liczb w ciągu, uznajemy to za losowanie
                # (Czasem PDF dzieli wyniki na linie, więc 20 może nie być w jednym ciągu)
                if len(candidates) >= 10:
                    draws.append(candidates)
                    i += offset
                else:
                    i += 1
    except:
        return []
    return draws

def get_hot_numbers(draws):
    flat_data = [num for sublist in draws for num in sublist]
    counts = Counter(flat_data)
    # Wagi dla liczb 1-80
    weights = [counts.get(i, 1) for i in range(1, 81)]
    return weights

# --- SMART ALGORYTM MULTI (DLA 10 SKREŚLEŃ) ---
def smart_generate_multi(weights):
    population = list(range(1, 81))
    
    # Próbujemy max 3000 razy (trudniejsze filtry przy 10 liczbach)
    for _ in range(3000):
        # 1. Losowanie ważone (Hot Numbers)
        stronger_weights = [w**1.3 for w in weights] # Nieco mniejszy mnożnik niż w Lotto, żeby nie zawęzić za mocno
        
        candidates = set()
        while len(candidates) < 10: # Celujemy w 10 liczb (Max wygrana)
            c = random.choices(population, weights=stronger_weights, k=1)[0]
            candidates.add(c)
        
        nums = sorted(list(candidates))
        
        # --- FILTRY MULTI (10 liczb z 80) ---
        
        # 1. Suma (Średnia dla 10 liczb to ~405. Margines bezpieczny: 320-490)
        total_sum = sum(nums)
        if not (320 <= total_sum <= 490):
            continue 
            
        # 2. Parzystość (Balans dla 10 liczb: od 4 do 6 parzystych)
        even_count = sum(1 for n in nums if n % 2 == 0)
        if even_count < 4 or even_count > 6:
            continue
            
        # 3. Niskie/Wysokie (Podział 1-40 i 41-80. Też szukamy balansu 4-6)
        low_count = sum(1 for n in nums if n <= 40)
        if low_count < 4 or low_count > 6:
            continue
            
        # 4. Ciągi (Unikamy np. 4,5,6 obok siebie. Pary 4,5 są OK)
        consecutive = 0
        max_consecutive = 0
        for i in range(len(nums)-1):
            if nums[i+1] == nums[i] + 1:
                consecutive += 1
            else:
                consecutive = 0
            max_consecutive = max(max_consecutive, consecutive)
        
        if max_consecutive >= 2: # Odrzucamy trójki (x, x+1, x+2)
            continue
            
        return nums, total_sum, even_count, low_count

    # Fallback
    return nums, sum(nums), 0, 0

# --- INTERFEJS ---
def main():
    st.title("🟣 Multi Smart System")
    st.markdown("Algorytm generujący 10 liczb o najwyższym potencjale statystycznym.")
    
    # Pamiętaj o wgraniu pliku z wynikami Multi Multi!
    FILE_NAME = "tablica999.pdf" # ZMIEŃ NA NAZWĘ SWOJEGO PLIKU!
    
    # Próba wczytania (obsługa błędu nazwy pliku)
    if not os.path.exists(FILE_NAME):
        # Fallback na nazwę uniwersalną, jeśli użytkownik nie zmienił
        if os.path.exists("tablica999.pdf"):
            FILE_NAME = "tablica999.pdf"

    draws = load_data(FILE_NAME)
    
    if not draws:
        st.warning(f"⚠️ Nie widzę pliku bazy danych. Sprawdź nazwę pliku w kodzie!")
        weights = [1] * 80
    else:
        st.success(f"Analiza bazy: {len(draws)} losowań Multi Multi.")
        weights = get_hot_numbers(draws)

    if st.button("WYGENERUJ TYP NA 10", use_container_width=True):
        with st.spinner("Analiza rozkładu Gaussa dla 80 liczb..."):
            result, s_sum, s_even, s_low = smart_generate_multi(weights)
            
        # Kule (W dwóch rzędach po 5 dla estetyki)
        row1 = st.columns(5)
        row2 = st.columns(5)
        
        for i, n in enumerate(result[:5]):
            row1[i].markdown(f"<div class='big-number'>{n}</div>", unsafe_allow_html=True)
        for i, n in enumerate(result[5:]):
            row2[i].markdown(f"<div class='big-number'>{n}</div>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Statystyki
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"<div class='metric-box'>📐 Suma: <b>{s_sum}</b><br><small>(Norma: 320-490)</small></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='metric-box'>⚖️ Parzyste: <b>{s_even}/10</b><br><small>(Balans 4-6)</small></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='metric-box'>🌓 Niskie: <b>{s_low}/10</b><br><small>(Zakres 1-40)</small></div>", unsafe_allow_html=True)
        
        st.caption("System generuje zestaw 10 liczb. Aby wygrać, musisz trafić przynajmniej ułamek z nich, ale ten rozkład maksymalizuje szansę przy grze na 10 skreśleń.")

if __name__ == "__main__":
    main()
