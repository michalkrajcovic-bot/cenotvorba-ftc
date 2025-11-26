import streamlit as st
import datetime

st.image("ftc_logo.png", width=230)


st.set_page_config(page_title="Cenotvorba nafty", page_icon="⛽", layout="centered")

st.title("⛽ Cenotvorba nafty – FTC verzia 1.1")

st.markdown(
    """
Táto aplikácia vypočíta **predajnú cenu nafty (EUR/l)** vrátane:
- nákupnej ceny
- logistiky
- úroku (EURIBOR + marža)
- factoring fee
- tvojej obchodnej marže

Všetky ceny zadávaj **v EUR/liter**.
"""
)

st.header("1️⃣ Vstupné parametre ceny")

col1, col2 = st.columns(2)

with col1:
    base_price = st.number_input(
        "Nákupná cena nafty (EUR/l)",
        min_value=0.0,
        value=1.20,
        step=0.001,
        format="%.4f"
    )

    logistics = st.number_input(
        "Logistické náklady (EUR/l)",
        min_value=0.0,
        value=0.030,
        step=0.001,
        format="%.4f"
    )

    margin_eur = st.number_input(
        "Tvoja obchodná marža (EUR/l)",
        min_value=0.0,
        value=0.030,
        step=0.001,
        format="%.4f"
    )

with col2:
    days_credit = st.number_input(
        "Dni úverovania (napr. 28 pri 14+14)",
        min_value=0,
        value=28,
        step=1
    )

    euribor_1m = st.number_input(
        "EURIBOR 1M (%)",
        min_value=-5.0,
        value=3.80,
        step=0.01,
        format="%.2f"
    )

    bank_margin = st.number_input(
        "Marža banky nad EURIBOR (%)",
        min_value=0.0,
        value=1.80,
        step=0.01,
        format="%.2f"
    )

    factoring_fee = st.number_input(
        "Factoring fee z faktúry (%)",
        min_value=0.0,
        value=0.30,
        step=0.01,
        format="%.2f"
    )

st.header("2️⃣ Údaje k ponuke")

client_name = st.text_input("Názov klienta (napr. RD TRANS s.r.o.)")
volume_l = st.number_input(
    "Objem dodávky (l)",
    min_value=0.0,
    value=30000.0,
    step=1000.0,
    format="%.0f"
)
valid_until = st.date_input("Platnosť ponuky do", value=datetime.date.today() + datetime.timedelta(days=3))

st.header("3️⃣ Výpočet ceny")

if st.button("Vypočítať cenu a vytvoriť ponuku"):
    # Základné náklady
    base_cost = base_price + logistics

    # Úrok
    annual_rate = (euribor_1m + bank_margin) / 100
    interest_l = base_cost * annual_rate * (days_credit / 365)

    # Predbežná cena pred factoringom
    preliminary_price = base_cost + interest_l + margin_eur

    # Factoring fee
    factoring_l = preliminary_price * (factoring_fee / 100)

    # Celkový náklad
    total_cost = base_cost + interest_l + factoring_l

    # Finálna predajná cena
    final_price = total_cost + margin_eur

    st.subheader("📊 Rozpis nákladov (EUR/l)")
    st.write(f"**Nákup + logistika:** {base_cost:.4f} EUR/l")
    st.write(f"**Úrok za {days_credit} dní:** {interest_l:.4f} EUR/l")
    st.write(f"**Factoring:** {factoring_l:.4f} EUR/l")
    st.write(f"**Tvoja marža:** {margin_eur:.4f} EUR/l")

    st.markdown("---")
    st.write(f"### 🟢 Predajná cena pre klienta: **{final_price:.4f} EUR/l**")

    if client_name and volume_l > 0:
        total_price = final_price * volume_l

        offer_text = f"""CENOVÁ PONUKA – motorová nafta

Klient: {client_name}
Objem: {volume_l:,.0f} l
Jednotková cena: {final_price:.4f} EUR/l
Celková hodnota: {total_price:,.2f} EUR

Cena zahŕňa:
- nákupnú cenu a logistiku
- financovanie {days_credit} dní (EURIBOR 1M {euribor_1m:.2f} % + {bank_margin:.2f} %)
- factoring fee {factoring_fee:.2f} %
- obchodnú maržu dodávateľa

Platnosť ponuky do: {valid_until.strftime('%d.%m.%Y')}

V Bratislave, dňa {datetime.date.today().strftime('%d.%m.%Y')}

Fuel Traders Corporation s.r.o.
"""

        st.markdown("---")
        st.subheader("📄 Text cenovej ponuky")
        st.text_area("Ponuka", offer_text, height=220)

        st.download_button(
            "⬇️ Stiahnuť ponuku ako .txt",
            data=offer_text,
            file_name="cenova_ponuka_nafta.txt",
            mime="text/plain",
        )

        st.info("Ak chceš PDF, otvor túto stránku v prehliadači → Print → Save as PDF.")
    else:
        st.warning("Vyplň názov klienta a objem dodávky, aby sa vytvoril text ponuky.")
