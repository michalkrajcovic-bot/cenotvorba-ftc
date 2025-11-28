import streamlit as st
import datetime

st.set_page_config(page_title="Cenotvorba nafty", page_icon="⛽", layout="centered")

# Inicializácia jednoduchého "CRM" v pamäti
if "clients" not in st.session_state:
    st.session_state["clients"] = []

# Logo (súbor ftc_logo.png musí byť v rovnakom priečinku ako app.py)
try:
    st.image("ftc_logo.png", width=230)
except Exception:
    pass

st.title("⛽ Cenotvorba nafty – FTC pricing & mini CRM")

st.markdown(
    """
Táto aplikácia:
- eviduje **klientov** (splatnosť, marža, logistika, kontakty)
- podľa zvoleného klienta **predvyplní parametre cenotvorby**
- spočíta **predajnú cenu nafty (EUR/l)** vrátane:
    - nákupnej ceny
    - logistiky
    - úroku (EURIBOR + marža)
    - factoring fee
    - tvojej obchodnej marže
"""
)

# ==========================
# 1️⃣ CRM – Klienti
# ==========================

st.header("1️⃣ CRM – Klienti")

with st.expander("Zoznam klientov"):
    if st.session_state["clients"]:
        st.table(
            [
                {
                    "Klient": c["name"],
                    "Kontakt": c["contact_name"],
                    "Email": c["email"],
                    "Telefón": c["phone"],
                    "Splatnosť (dní)": c["payment_days"],
                    "Marža (EUR/l)": c["margin_eur"],
                    "Logistika (EUR/l)": c["logistics_eur"],
                }
                for c in st.session_state["clients"]
            ]
        )
    else:
        st.info("Zatiaľ nemáš žiadnych klientov. Pridaj prvého nižšie.")

st.subheader("Pridať / upraviť klienta")

col_c1, col_c2 = st.columns(2)

with col_c1:
    client_name_form = st.text_input("Názov klienta *", placeholder="Napr. RD TRANS s. r. o.")
    contact_name = st.text_input("Kontaktná osoba", placeholder="Napr. p. Novák")
    email = st.text_input("Email", placeholder="obchod@klient.sk")
    phone = st.text_input("Telefón", placeholder="+421 900 000 000")

with col_c2:
    payment_days = st.number_input("Štandardná splatnosť (dni)", min_value=0, value=28, step=1)
    default_margin_eur = st.number_input(
        "Štandardná marža (EUR/l)",
        min_value=0.0,
        value=0.030,
        step=0.001,
        format="%.4f",
    )
    default_logistics_eur = st.number_input(
        "Štandardná logistika (EUR/l)",
        min_value=0.0,
        value=0.030,
        step=0.001,
        format="%.4f",
    )

if st.button("💾 Uložiť klienta"):
    if not client_name_form.strip():
        st.error("Názov klienta je povinný.")
    else:
        # ak klient existuje, upravíme ho; inak pridáme
        updated = False
        for c in st.session_state["clients"]:
            if c["name"].lower() == client_name_form.strip().lower():
                c.update(
                    {
                        "contact_name": contact_name,
                        "email": email,
                        "phone": phone,
                        "payment_days": payment_days,
                        "margin_eur": default_margin_eur,
                        "logistics_eur": default_logistics_eur,
                    }
                )
                updated = True
                break
        if not updated:
            st.session_state["clients"].append(
                {
                    "name": client_name_form.strip(),
                    "contact_name": contact_name,
                    "email": email,
                    "phone": phone,
                    "payment_days": payment_days,
                    "margin_eur": default_margin_eur,
                    "logistics_eur": default_logistics_eur,
                }
            )
        st.success(f"Klient '{client_name_form}' bol uložený.")

st.markdown("---")

# Výber klienta pre cenotvorbu
st.subheader("Vyber klienta pre výpočet ceny")

client_names = ["(ručne bez CRM)"] + [c["name"] for c in st.session_state["clients"]]

selected_client_name = st.selectbox("Klient", options=client_names)

selected_client = None
if selected_client_name != "(ručne bez CRM)":
    selected_client = next(
        (c for c in st.session_state["clients"] if c["name"] == selected_client_name),
        None,
    )

# ==========================
# 2️⃣ Vstupné parametre ceny
# ==========================

st.header("2️⃣ Vstupné parametre ceny")

col1, col2 = st.columns(2)

with col1:
    base_price = st.number_input(
        "Nákupná cena nafty (EUR/l)",
        min_value=0.0,
        value=1.20,
        step=0.001,
        format="%.4f",
        help="Tvoja nákupná cena (napr. prepočítaná z Platts/cenníka na EUR/l).",
    )

    logistics = st.number_input(
        "Logistické náklady (EUR/l)",
        min_value=0.0,
        value=(selected_client["logistics_eur"] if selected_client else 0.030),
        step=0.001,
        format="%.4f",
        help="Doprava, skladovanie, prečerpávanie, poplatky…",
    )

    margin_eur = st.number_input(
        "Tvoja obchodná marža (EUR/l)",
        min_value=0.0,
        value=(selected_client["margin_eur"] if selected_client else 0.030),
        step=0.001,
        format="%.4f",
        help="Koľko chceš zarobiť na litri (čistá marža).",
    )

with col2:
    days_credit = st.number_input(
        "Dni úverovania (napr. 28 pri 14+14)",
        min_value=0,
        value=(selected_client["payment_days"] if selected_client else 28),
        step=1,
        help="Celkový počet dní od nákupu po inkaso od klienta.",
    )

    euribor_1m = st.number_input(
        "EURIBOR 1M (%)",
        min_value=-5.0,
        value=3.80,
        step=0.01,
        format="%.2f",
        help="Aktuálna hodnota 1M EURIBOR v percentách.",
    )

    bank_margin = st.number_input(
        "Marža banky nad EURIBOR (%)",
        min_value=0.0,
        value=1.80,
        step=0.01,
        format="%.2f",
        help="Tvoja marža banky – napr. EURIBOR + 1,8 %",
    )

    factoring_fee = st.number_input(
        "Factoring fee z faktúry (%)",
        min_value=0.0,
        value=0.30,
        step=0.01,
        format="%.2f",
        help="Poplatok za factoring ako % z fakturovanej sumy (napr. 0,3 %).",
    )

# ==========================
# 3️⃣ Údaje k ponuke
# ==========================

st.header("3️⃣ Údaje k ponuke")

client_name = st.text_input(
    "Názov klienta v ponuke",
    value=(selected_client["name"] if selected_client else ""),
)

volume_l = st.number_input(
    "Objem dodávky (l)",
    min_value=0.0,
    value=30000.0,
    step=1000.0,
    format="%.0f",
)

valid_until = st.date_input(
    "Platnosť ponuky do",
    value=datetime.date.today() + datetime.timedelta(days=3),
)

# ==========================
# 4️⃣ Výpočet ceny
# ==========================

st.header("4️⃣ Výpočet ceny")

if st.button("Vypočítať cenu a vytvoriť ponuku"):
    # Základný náklad (nákup + logistika)
    base_cost = base_price + logistics

    # Ročná úroková sadzba
    annual_rate = (euribor_1m + bank_margin) / 100.0

    # Úrok za obdobie
    interest_l = base_cost * annual_rate * (days_credit / 365.0)

    # Predbežná cena pred factoringom
    preliminary_price = base_cost + interest_l + margin_eur

    # Factoring fee
    factoring_l = preliminary_price * (factoring_fee / 100.0)

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

        contact_line = ""
        if selected_client:
            if selected_client.get("contact_name"):
                contact_line += f"Kontaktná osoba: {selected_client['contact_name']}\n"
            if selected_client.get("email"):
                contact_line += f"Email: {selected_client['email']}\n"
            if selected_client.get("phone"):
                contact_line += f"Telefón: {selected_client['phone']}\n"

        offer_text = f"""CENOVÁ PONUKA – motorová nafta

Klient: {client_name}
Objem: {volume_l:,.0f} l
Jednotková cena: {final_price:.4f} EUR/l
Celková hodnota: {total_price:,.2f} EUR

Finančné podmienky:
- splatnosť: {days_credit} dní
- financovanie: EURIBOR 1M {euribor_1m:.2f} % + {bank_margin:.2f} %
- náklad na financovanie: {interest_l:.4f} EUR/l
- factoring fee: {factoring_fee:.2f} %

Cena zahŕňa:
- nákupnú cenu a logistiku
- financovanie {days_credit} dní
- factoring
- obchodnú maržu dodávateľa

{contact_line if contact_line else ""}Platnosť ponuky do: {valid_until.strftime('%d.%m.%Y')}

V Bratislave, dňa {datetime.date.today().strftime('%d.%m.%Y')}

Fuel Traders Corporation s. r. o.
"""

        st.markdown("---")
        st.subheader("📄 Text cenovej ponuky")
        st.text_area("Ponuka", offer_text, height=260)

        st.download_button(
            "⬇️ Stiahnuť ponuku ako .txt",
            data=offer_text,
            file_name="cenova_ponuka_nafta.txt",
            mime="text/plain",
        )

        st.info("Ak chceš PDF, otvor túto stránku v prehliadači → Print → Save as PDF.")
    else:
        st.warning("Vyplň názov klienta a objem dodávky, aby sa vytvoril text ponuky.")

