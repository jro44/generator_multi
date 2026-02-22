import os
import re
import random
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

import streamlit as st

# Optional but recommended for more robust PDF parsing
# pdfplumber works on many PDFs; PyMuPDF (fitz) is a good fallback.
import pdfplumber

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    PYMUPDF_AVAILABLE = False


# =========================================================
# CONFIG
# =========================================================
APP_TITLE = "🔷 Multi-Multi — Blue Lucky Generator"
PDF_FILENAME = "wyniki.pdf"
NUM_MIN = 1
NUM_MAX = 80
PICK_COUNT = 10

# For "hot/cold" grouping defaults
DEFAULT_HOT_GROUP_SIZE = 25   # top 25 most frequent numbers
DEFAULT_COLD_GROUP_SIZE = 25  # bottom 25 least frequent numbers

# For weighted picking defaults (you can tweak)
HOT_SHARE_DEFAULT = 0.70
COLD_SHARE_DEFAULT = 0.20
MIX_SHARE_DEFAULT = 0.10


# =========================================================
# UI STYLE (light + blue)
# =========================================================
LIGHT_BLUE_CSS = """
<style>
/* App background */
.stApp {
    background: radial-gradient(1200px 800px at 10% 10%, #f2f8ff 0%, #ffffff 50%, #f5fbff 100%);
    color: #0b1b2b;
}

/* Main container padding */
.block-container { padding-top: 2.0rem; padding-bottom: 2.5rem; }

/* Headers */
h1, h2, h3, h4 {
    letter-spacing: 0.3px;
}

/* Cards */
.mm-card {
    background: rgba(255,255,255,0.92);
    border: 1px solid rgba(0, 123, 255, 0.18);
    box-shadow: 0 10px 30px rgba(0, 40, 120, 0.08);
    border-radius: 16px;
    padding: 16px 16px 12px 16px;
}

/* Pills */
.mm-pill {
    display: inline-block;
    padding: 6px 10px;
    margin: 3px 4px 0 0;
    border-radius: 999px;
    border: 1px solid rgba(0, 123, 255, 0.24);
    background: rgba(0, 123, 255, 0.06);
    font-weight: 600;
    color: #0a2a4a;
}

/* Buttons - primary */
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #0b66ff 0%, #19a2ff 100%) !important;
    color: white !important;
    border: 0 !important;
    border-radius: 14px !important;
    padding: 0.75rem 1.1rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.4px !important;
    box-shadow: 0 10px 22px rgba(0, 88, 255, 0.18) !important;
}
div.stButton > button[kind="primary"]:hover {
    filter: brightness(1.03);
    transform: translateY(-1px);
}

/* Inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
    border-radius: 14px !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(11,102,255,0.08) 0%, rgba(25,162,255,0.03) 100%);
    border-right: 1px solid rgba(0, 123, 255, 0.10);
}

/* Small text */
.mm-muted {
    opacity: 0.75;
    font-size: 0.92rem;
}

/* Table style */
.mm-table {
    border-collapse: separate;
    border-spacing: 0 8px;
}
.mm-row {
    background: rgba(255,255,255,0.9);
    border: 1px solid rgba(0, 123, 255, 0.18);
    border-radius: 14px;
    padding: 10px 12px;
}

/* Mobile tweaks */
@media (max-width: 640px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    div.stButton > button[kind="primary"] { width: 100% !important; }
}
</style>
"""


# =========================================================
# DATA STRUCTURES
# =========================================================
@dataclass
class Draw:
    draw_id: int
    numbers: List[int]


# =========================================================
# PDF PARSING
# =========================================================
def _extract_text_pdfplumber(pdf_path: str) -> str:
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                texts.append(t)
    return "\n".join(texts)


def _extract_text_pymupdf(pdf_path: str) -> str:
    if not PYMUPDF_AVAILABLE:
        return ""
    texts = []
    doc = fitz.open(pdf_path)
    for page in doc:
        t = page.get_text("text") or ""
        if t.strip():
            texts.append(t)
    doc.close()
    return "\n".join(texts)


def _parse_draws_from_text(text: str) -> List[Draw]:
    """
    Expected pattern (from your uploaded PDF):
    16616 04 05 10 13 ... 79   (draw_id + 20 numbers for 20/80)
    We only need to read the numbers 1..80 and treat each line as a draw.
    """
    draws: List[Draw] = []

    # Normalize spaces
    text = text.replace("\t", " ")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # A draw line usually starts with 4-6 digits draw id, followed by many 2-digit numbers
    # We'll capture all ints and then validate.
    for ln in lines:
        if not re.match(r"^\d{4,6}\s+", ln):
            continue

        ints = [int(x) for x in re.findall(r"\d+", ln)]
        if len(ints) < 5:
            continue

        draw_id = ints[0]
        nums = ints[1:]

        # Keep only valid range numbers
        nums = [n for n in nums if NUM_MIN <= n <= NUM_MAX]

        # Multi Multi 20/80 lines typically have 20 numbers
        # but some PDFs might split lines—still, we accept >=10.
        if len(nums) >= 10:
            # Remove duplicates while keeping order
            seen = set()
            uniq = []
            for n in nums:
                if n not in seen:
                    uniq.append(n)
                    seen.add(n)
            draws.append(Draw(draw_id=draw_id, numbers=uniq))

    # Deduplicate by draw_id, keep first occurrence
    uniq_by_id: Dict[int, Draw] = {}
    for d in draws:
        if d.draw_id not in uniq_by_id:
            uniq_by_id[d.draw_id] = d

    # Sort by draw_id descending if it looks incremental; else preserve
    final_draws = list(uniq_by_id.values())
    final_draws.sort(key=lambda d: d.draw_id, reverse=True)
    return final_draws


@st.cache_data(show_spinner=False)
def load_draws_from_local_pdf(pdf_path: str) -> List[Draw]:
    # Try pdfplumber first
    text = ""
    try:
        text = _extract_text_pdfplumber(pdf_path)
    except Exception:
        text = ""

    # Fallback to PyMuPDF if pdfplumber failed or returned too little
    if len(text.strip()) < 100 and PYMUPDF_AVAILABLE:
        try:
            text2 = _extract_text_pymupdf(pdf_path)
            if len(text2.strip()) > len(text.strip()):
                text = text2
        except Exception:
            pass

    if not text.strip():
        raise RuntimeError("Nie udało się odczytać tekstu z PDF (pdfplumber / PyMuPDF).")

    draws = _parse_draws_from_text(text)
    if not draws:
        raise RuntimeError("Nie znaleziono poprawnych losowań w PDF. Sprawdź format pliku wyniki.pdf.")
    return draws


# =========================================================
# ANALYTICS: HOT / COLD / OVERDUE
# =========================================================
def compute_frequency(draws: List[Draw]) -> Counter:
    c = Counter()
    for d in draws:
        c.update([n for n in d.numbers if NUM_MIN <= n <= NUM_MAX])
    return c


def compute_last_seen(draws: List[Draw]) -> Dict[int, int]:
    """
    Return map number -> index of last occurrence in draws list (0 = most recent).
    If never seen, value = big number.
    """
    last = {n: 10**9 for n in range(NUM_MIN, NUM_MAX + 1)}
    for idx, d in enumerate(draws):
        for n in d.numbers:
            if last.get(n, 10**9) == 10**9:
                last[n] = idx
    return last


def build_groups(freq: Counter, hot_size: int, cold_size: int) -> Tuple[List[int], List[int]]:
    all_nums = list(range(NUM_MIN, NUM_MAX + 1))
    # Sort by frequency descending for hot
    hot_sorted = sorted(all_nums, key=lambda n: (freq.get(n, 0), n), reverse=True)
    cold_sorted = sorted(all_nums, key=lambda n: (freq.get(n, 0), n))

    hot = hot_sorted[:max(1, min(hot_size, len(all_nums)))]
    cold = cold_sorted[:max(1, min(cold_size, len(all_nums)))]

    return hot, cold


# =========================================================
# GENERATION LOGIC
# =========================================================
def _weighted_pick(pool: List[int], weights: Dict[int, float], k: int) -> List[int]:
    """
    Weighted sampling without replacement.
    """
    pool = list(dict.fromkeys(pool))  # unique preserve order
    if k >= len(pool):
        return sorted(pool)

    chosen = []
    local_pool = pool[:]
    for _ in range(k):
        w = [max(0.000001, weights.get(n, 1.0)) for n in local_pool]
        total = sum(w)
        r = random.random() * total
        acc = 0.0
        pick_idx = 0
        for i, ww in enumerate(w):
            acc += ww
            if acc >= r:
                pick_idx = i
                break
        chosen_num = local_pool.pop(pick_idx)
        chosen.append(chosen_num)
    return sorted(chosen)


def generate_ticket_base(
    mode: str,
    hot: List[int],
    cold: List[int],
    freq: Counter,
    last_seen: Dict[int, int],
    hot_share: float,
    cold_share: float,
    mix_share: float,
) -> List[int]:
    """
    Base behavior (when NOT using smart mode constraints):
    - HOT: pick 10 from hot, weighted by frequency + slight overdue
    - COLD: pick 10 from cold, weighted by overdue more
    - MIX: mixture (by shares), remainder filled by hot
    """
    all_nums = list(range(NUM_MIN, NUM_MAX + 1))

    # Build weights
    # freq_weight: emphasize frequent numbers
    # overdue_weight: emphasize numbers not seen recently (bigger index)
    max_freq = max(freq.values()) if freq else 1
    max_last = max([v for v in last_seen.values() if v < 10**9] + [1])

    weights_hot = {}
    weights_cold = {}
    weights_all = {}

    for n in all_nums:
        f = freq.get(n, 0)
        f_norm = (f / max_freq) if max_freq else 0.0
        ls = last_seen.get(n, 10**9)
        if ls >= 10**9:
            overdue_norm = 1.0
        else:
            overdue_norm = min(1.0, (ls / max_last) if max_last else 0.0)

        # Hot: mainly frequency, a touch of overdue so it doesn't pick only the same
        weights_hot[n] = 0.80 * (0.20 + f_norm) + 0.20 * (0.20 + overdue_norm)

        # Cold: mainly overdue (rare / not seen), a bit of frequency
        weights_cold[n] = 0.30 * (0.20 + f_norm) + 0.70 * (0.20 + overdue_norm)

        # All: balanced
        weights_all[n] = 0.55 * (0.20 + f_norm) + 0.45 * (0.20 + overdue_norm)

    if mode == "Gorące (Hot)":
        return _weighted_pick(hot, weights_hot, PICK_COUNT)

    if mode == "Zimne (Cold)":
        return _weighted_pick(cold, weights_cold, PICK_COUNT)

    if mode == "Mix (Hot+Cold)":
        hot_k = int(round(PICK_COUNT * hot_share))
        cold_k = int(round(PICK_COUNT * cold_share))
        mix_k = max(0, PICK_COUNT - hot_k - cold_k)

        chosen = []
        if hot_k > 0:
            chosen += _weighted_pick(hot, weights_hot, min(hot_k, len(hot)))
        if cold_k > 0:
            # prevent duplicates
            cold_pool = [n for n in cold if n not in chosen]
            chosen += _weighted_pick(cold_pool, weights_cold, min(cold_k, len(cold_pool)))
        if mix_k > 0:
            all_pool = [n for n in all_nums if n not in chosen]
            chosen += _weighted_pick(all_pool, weights_all, min(mix_k, len(all_pool)))

        # If still short, fill from hot then all
        if len(chosen) < PICK_COUNT:
            fill_pool = [n for n in hot if n not in chosen] + [n for n in all_nums if n not in chosen]
            chosen += _weighted_pick(fill_pool, weights_all, PICK_COUNT - len(chosen))

        return sorted(set(chosen))[:PICK_COUNT]

    # Fallback
    return sorted(random.sample(all_nums, PICK_COUNT))


def count_consecutive_pairs(nums_sorted: List[int]) -> int:
    """
    Counts how many consecutive pairs exist in a sorted list.
    Example: [2,3,4,10] has pairs (2,3) and (3,4) -> 2 pairs
    """
    pairs = 0
    for a, b in zip(nums_sorted, nums_sorted[1:]):
        if b == a + 1:
            pairs += 1
    return pairs


def has_run_length(nums_sorted: List[int], run_len: int) -> bool:
    """
    True if there exists a consecutive run of length >= run_len.
    """
    if run_len <= 1:
        return True
    run = 1
    for a, b in zip(nums_sorted, nums_sorted[1:]):
        if b == a + 1:
            run += 1
            if run >= run_len:
                return True
        else:
            run = 1
    return False


def even_odd_split(nums: List[int]) -> Tuple[int, int]:
    ev = sum(1 for n in nums if n % 2 == 0)
    od = len(nums) - ev
    return ev, od


def generate_ticket_smart(
    base_mode: str,
    hot: List[int],
    cold: List[int],
    freq: Counter,
    last_seen: Dict[int, int],
    hot_share: float,
    cold_share: float,
    mix_share: float,
    block_run_2: bool,
    block_run_3: bool,
    max_consecutive_pairs: Optional[int],
    even_odd_choice: str,
    max_attempts: int = 250,
) -> List[int]:
    """
    Smart generation:
    - Generate candidate with the base algorithm mode, then accept only if it matches constraints.
    - If too strict, relax by returning the best candidate found.
    """
    best = None
    best_score = -10**9

    for _ in range(max_attempts):
        ticket = generate_ticket_base(
            mode=base_mode,
            hot=hot,
            cold=cold,
            freq=freq,
            last_seen=last_seen,
            hot_share=hot_share,
            cold_share=cold_share,
            mix_share=mix_share,
        )
        ticket = sorted(set(ticket))
        if len(ticket) != PICK_COUNT:
            # Fill to exact size if needed
            pool = [n for n in range(NUM_MIN, NUM_MAX + 1) if n not in ticket]
            if len(pool) >= (PICK_COUNT - len(ticket)):
                ticket += random.sample(pool, PICK_COUNT - len(ticket))
            ticket = sorted(ticket)

        # Constraints
        ok = True
        pairs = count_consecutive_pairs(ticket)

        if max_consecutive_pairs is not None and pairs > max_consecutive_pairs:
            ok = False

        if block_run_3 and has_run_length(ticket, 3):
            ok = False
        if block_run_2 and has_run_length(ticket, 2):
            ok = False

        ev, od = even_odd_split(ticket)
        if even_odd_choice != "Dowolnie":
            # choices like "5/5", "6/4", "4/6", "7/3", "3/7"
            try:
                ev_target, od_target = even_odd_choice.split("/")
                ev_t = int(ev_target.strip())
                od_t = int(od_target.strip())
                if not (ev == ev_t and od == od_t):
                    ok = False
            except Exception:
                pass

        # Score candidate (for fallback): prefer fewer pairs + balanced + higher weight sum
        weight_sum = 0.0
        max_freq = max(freq.values()) if freq else 1
        max_last = max([v for v in last_seen.values() if v < 10**9] + [1])
        for n in ticket:
            f = freq.get(n, 0) / max_freq if max_freq else 0.0
            ls = last_seen.get(n, 10**9)
            overdue = 1.0 if ls >= 10**9 else min(1.0, ls / max_last if max_last else 0.0)
            weight_sum += 0.60 * (0.20 + f) + 0.40 * (0.20 + overdue)

        balance_penalty = abs(ev - od) * 0.15
        pair_penalty = pairs * 0.25
        score = weight_sum - balance_penalty - pair_penalty

        if ok:
            return ticket

        if score > best_score:
            best_score = score
            best = ticket

    return best if best is not None else generate_ticket_base(
        mode=base_mode,
        hot=hot,
        cold=cold,
        freq=freq,
        last_seen=last_seen,
        hot_share=hot_share,
        cold_share=cold_share,
        mix_share=mix_share,
    )


# =========================================================
# STREAMLIT APP
# =========================================================
def main():
    st.set_page_config(
        page_title="Multi-Multi Generator",
        page_icon="🔷",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.markdown(LIGHT_BLUE_CSS, unsafe_allow_html=True)

    st.title(APP_TITLE)
    st.write(
        "Czytelny generator typowań na podstawie historii losowań z pliku **wyniki.pdf** "
        f"(zakres **{NUM_MIN}–{NUM_MAX}**, wybiera **{PICK_COUNT} liczb**)."
    )
    st.caption("Źródło danych: lokalny plik `wyniki.pdf` w tym samym folderze co `app.py` (repo GitHub / Streamlit Cloud).")

    # Resolve PDF path (same folder as script OR current working directory)
    # Streamlit Cloud usually runs from repo root; safest is cwd + filename.
    pdf_path = os.path.join(os.getcwd(), PDF_FILENAME)

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Ustawienia")

        st.markdown("**Tryb typowania**")
        mode = st.selectbox(
            "Wybierz tryb",
            [
                "Gorące (Hot)",
                "Zimne (Cold)",
                "Mix (Hot+Cold)",
                "Inteligentny (Smart)",
            ],
            index=2
        )

        st.divider()

        st.markdown("**Ile kuponów wygenerować?**")
        tickets_count = st.slider("Liczba kuponów", 1, 50, 10, 1)

        st.divider()

        st.markdown("**Wielkość grup Hot/Cold**")
        hot_size = st.slider("Ile liczb w grupie Gorących", 5, 60, DEFAULT_HOT_GROUP_SIZE, 1)
        cold_size = st.slider("Ile liczb w grupie Zimnych", 5, 60, DEFAULT_COLD_GROUP_SIZE, 1)

        st.divider()

        st.markdown("**Proporcje dla trybu Mix**")
        hot_share = st.slider("Udział Gorących (Hot)", 0.0, 1.0, HOT_SHARE_DEFAULT, 0.05)
        cold_share = st.slider("Udział Zimnych (Cold)", 0.0, 1.0, COLD_SHARE_DEFAULT, 0.05)

        # keep mix_share derived to sum 1.0 (and never negative)
        mix_share = max(0.0, 1.0 - hot_share - cold_share)
        st.caption(f"Udział „Mix/Reszta” (auto): **{mix_share:.2f}**")

        st.divider()

        smart_enabled = (mode == "Inteligentny (Smart)")
        if smart_enabled:
            st.subheader("🧠 Tryb inteligentny — filtry")

            block_run_2 = st.checkbox("Blokuj układy 1–2 (kolejne liczby)", value=True)
            block_run_3 = st.checkbox("Blokuj układy 1–3 (ciąg 3 kolejnych liczb)", value=True)

            st.markdown("**Limit par (kolejne liczby)**")
            limit_pairs_on = st.checkbox("Włącz limit par", value=True)
            max_pairs = None
            if limit_pairs_on:
                max_pairs = st.slider("Maks. liczba par (np. 12–13 to 1 para)", 0, 6, 2, 1)

            st.markdown("**Parzyste / Nieparzyste** (tylko jeden wybór)")
            # Radio = single choice, zgodnie z Twoim wymogiem
            even_odd_choice = st.radio(
                "Wybierz rozkład",
                ["Dowolnie", "5/5", "6/4", "4/6", "7/3", "3/7"],
                index=1,
                help="Format: parzyste/nieparzyste"
            )
        else:
            # Defaults when smart mode off
            block_run_2 = False
            block_run_3 = False
            max_pairs = None
            even_odd_choice = "Dowolnie"

    # Load data
    colA, colB = st.columns([1.2, 0.8], gap="large")

    with colA:
        st.markdown('<div class="mm-card">', unsafe_allow_html=True)
        st.subheader("📄 Dane wejściowe")

        st.write(f"Ścieżka PDF: `{pdf_path}`")
        if not os.path.exists(pdf_path):
            st.error(
                f"Nie znaleziono pliku `{PDF_FILENAME}` w katalogu aplikacji. "
                "Upewnij się, że plik jest w repo obok `app.py`."
            )
            st.stop()

        try:
            with st.spinner("Czytam i analizuję wyniki z PDF..."):
                draws = load_draws_from_local_pdf(pdf_path)
        except Exception as e:
            st.error(f"❌ Błąd podczas czytania PDF: {e}")
            st.stop()

        st.success(f"✅ Wczytano losowania: **{len(draws)}** (najświeższe: {draws[0].draw_id}, najstarsze: {draws[-1].draw_id})")
        st.markdown('<div class="mm-muted">Wyniki w PDF mogą zawierać 20 liczb na losowanie (20/80), ale generator typuje 10 liczb (10/80).</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Analyze
    freq = compute_frequency(draws)
    last_seen = compute_last_seen(draws)
    hot, cold = build_groups(freq, hot_size=hot_size, cold_size=cold_size)

    # Right panel: show groups
    with colB:
        st.markdown('<div class="mm-card">', unsafe_allow_html=True)
        st.subheader("🔥 Gorące i ❄️ Zimne")
        st.caption("Gorące = najczęściej występujące, Zimne = najrzadziej / prawie wcale.")

        st.markdown("**Gorące (Hot)**")
        hot_html = " ".join([f'<span class="mm-pill">{n:02d}</span>' for n in sorted(hot)])
        st.markdown(hot_html, unsafe_allow_html=True)

        st.markdown("**Zimne (Cold)**")
        cold_html = " ".join([f'<span class="mm-pill">{n:02d}</span>' for n in sorted(cold)])
        st.markdown(cold_html, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # Generate tickets
    st.markdown('<div class="mm-card">', unsafe_allow_html=True)
    st.subheader("🎟️ Generator kuponów")

    btn_label = "🎯 GENERUJ KUPONY (10 liczb)"
    generate = st.button(btn_label, type="primary", use_container_width=True)

    if generate:
        results = []
        for _ in range(tickets_count):
            if mode == "Inteligentny (Smart)":
                # In smart mode, user still picks underlying base-mode behavior:
                base_mode = st.session_state.get("smart_base_mode", "Mix (Hot+Cold)")
                # But to keep UX simple: we map Smart to Mix unless user changes below.
                # We'll offer a base selector here (inline) by reading from session state,
                # but also allow default = Mix.
                ticket = generate_ticket_smart(
                    base_mode=base_mode,
                    hot=hot,
                    cold=cold,
                    freq=freq,
                    last_seen=last_seen,
                    hot_share=hot_share,
                    cold_share=cold_share,
                    mix_share=mix_share,
                    block_run_2=block_run_2,
                    block_run_3=block_run_3,
                    max_consecutive_pairs=max_pairs,
                    even_odd_choice=even_odd_choice,
                )
            else:
                ticket = generate_ticket_base(
                    mode=mode,
                    hot=hot,
                    cold=cold,
                    freq=freq,
                    last_seen=last_seen,
                    hot_share=hot_share,
                    cold_share=cold_share,
                    mix_share=mix_share,
                )
            results.append(ticket)

        # Render results
        st.markdown("### Wyniki")
        for i, t in enumerate(results, start=1):
            nums = " ".join([f"{n:02d}" for n in t])
            ev, od = even_odd_split(t)
            pairs = count_consecutive_pairs(sorted(t))
            st.markdown(
                f'<div class="mm-row"><b>Kupon #{i:02d}:</b> {nums} '
                f'<span class="mm-muted"> | parzyste/nieparzyste: {ev}/{od} | pary: {pairs}</span></div>',
                unsafe_allow_html=True
            )

        st.info("Pamiętaj: to generator oparty na analizie częstości i filtrach — nie gwarantuje wygranej.")

    # Smart base mode selector (only visible when smart mode enabled)
    if mode == "Inteligentny (Smart)":
        st.markdown("---")
        st.markdown("#### 🧩 Inteligentny: bazowy styl losowania")
        base_mode = st.selectbox(
            "Z jakiej logiki ma startować Tryb Inteligentny?",
            ["Mix (Hot+Cold)", "Gorące (Hot)", "Zimne (Cold)"],
            index=0,
            help="Najpierw losujemy wg wybranego stylu, potem odrzucamy kupony niespełniające filtrów."
        )
        st.session_state["smart_base_mode"] = base_mode

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # Diagnostics
    with st.expander("📊 Statystyki (diagnostyka)"):
        st.write("Top 15 najczęstszych liczb:")
        top15 = sorted(range(NUM_MIN, NUM_MAX + 1), key=lambda n: (freq.get(n, 0), n), reverse=True)[:15]
        st.write(", ".join([f"{n:02d} ({freq.get(n,0)})" for n in top15]))

        st.write("Top 15 najrzadszych liczb:")
        low15 = sorted(range(NUM_MIN, NUM_MAX + 1), key=lambda n: (freq.get(n, 0), n))[:15]
        st.write(", ".join([f"{n:02d} ({freq.get(n,0)})" for n in low15]))

        st.write("Liczby najbardziej 'zaległe' (dawno nie widziane w ostatnich losowaniach):")
        # biggest last_seen index means oldest occurrence (or never)
        overdue = sorted(range(NUM_MIN, NUM_MAX + 1), key=lambda n: last_seen.get(n, 10**9), reverse=True)[:15]
        st.write(", ".join([f"{n:02d} (ostatnio: {last_seen.get(n,10**9)} losowań temu)" for n in overdue]))


if __name__ == "__main__":
    main()
