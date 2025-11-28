
import streamlit as st
import datetime

st.set_page_config(page_title="Cenotvorba nafty", page_icon="⛽", layout="centered")

# Inicializácia jednoduchého "CRM" a cenníkovej histórie v pamäti
if "clients" not in st.session_state:
    st.session_state["clients"] = []

if "price_history" not in st.session_state:
    st.session_state["price_history"] = []  # zoznam dictov: {"date": date, "price": float}

# Logo (súbor ftc_logo.png musí byť v rovnakom priečinku ako app.py)
try:
    st.image("ftc_logo.png", width=230)
except Exception:
    pass

st.title("⛽ Cenotvorba nafty – FTC pricing & mini CRM")

st.markdown(
    """
Táto aplikácia:
- eviduje **klientov** (splatnosť, logistika, zľava z cenníka, kontakty)
- spravuje **základnú cenníkovú cenu** podľa dátumu
- podľa zvoleného klienta a zľavy vypočíta jeho **klientsku cenu**
- spočíta **náklad na klienta** (nákup, logistika, financovanie, factoring) a maržu
"""
)

# ==========================
# 0️⃣ Základná cenníková cena (história)
# ==========================
st.header("0️⃣ Základná cenníková cena")

col_p1, col_p2 = st.columns(2)

with col_p1:
    price_date = st.date_input(
        "Dátum cenníkovej ceny",
        value=datetime.date.today(),
        help="Dátum, od ktorého platí táto cenníková cena."
    )

with col_p2:
    base_list_price_input = st.number_input(
        "Cenníková cena (EUR/l)",
        min_value=0.0,
        value=1.500,
        step=0.001,
        format="%.4f",
        help="Základná predajná cenníková cena bez zľavy."
    )

if st.button("💾 Uložiť cenníkovú cenu"):
    # ak existuje záznam pre tento dátum, prepíšeme; inak pridáme
    found = False
    for entry in st.session_state["price_history"]:
        if entry["date"] == price_date:
            entry["price"] = base_list_price_input
            found = True
            break
    if not found:
        st.session_state["price_history"].append(
            {"date": price_date, "price": base_list_price_input}
        )
    st.success(f"Cenníková cena k {price_date.strftime('%d.%m.%Y')} bola uložená.")

# zistíme aktuálnu cenníkovú cenu = posledná podľa dátumu
current_list_price = None
if st.session_state["price_history"]:
    latest = max(st.session_state["price_history"], key=lambda x: x["date"])
    current_list_price = latest["price"]
    st.info(
        f"Aktuálna cenníková cena podľa posledného záznamu "
        f"({latest['date'].strftime('%d.%m.%Y')}): **{current_list_price:.4f} EUR/l**"
    )
else:
    st.warning("Zatiaľ nemáš uloženú žiadnu cenníkovú cenu. Použi blok vyššie.")

with st.expander("História cenníkových cien"):
    if st.session_state["price_history"]:
        st.table(
            [
                {
                    "Dátum": entry["date"].strftime("%d.%m.%Y"),
                    "Cenníková cena (EUR/l)": f"{entry['price']:.4f}",
                }
                for entry in sorted(st.session_state["price_history"], key=lambda x: x["date"])
            ]
        )
    else:
        st.write("Zatiaľ žiadne záznamy.")

st.markdown("---")

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
                    "Logistika (EUR/l)": f"{c['logistics_eur']:.4f}",
                    "Zľava (EUR/m³)": f"{c['discount_eur_m3']:.2f}",
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
    default_logistics_eur = st.number_input(
        "Štandardná logistika (EUR/l)",
        min_value=0.0,
        value=0.030,
        step=0.001,
        format="%.4f",
        help="Priemerný logistický náklad na tohto klienta."
    )
    default_discount_eur_m3 = st.number_input(
        "Štandardná zľava z cenníkovej ceny (EUR/m³)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f",
        help="Zľava v EUR na m³ oproti základnej cenníkovej cene."
    )

if st.button("💾 Uložiť klienta"):
    if not client_name_form.strip():
        st.error("Názov klienta je povinný.")
    else:
        updated = False
        for c in st.session_state["clients"]:
            if c["name"].lower() == client_name_form.strip().lower():
                c.update(
                    {
                        "contact_name": contact_name,
                        "email": email,
                        "phone": phone,
                        "payment_days": payment_days,
                        "logistics_eur": default_logistics_eur,
                        "discount_eur_m3": default_discount_eur_m3,
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
                    "logistics_eur": default_logistics_eur,
                    "discount_eur_m3": default_discount_eur_m3,
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

st.header("2️⃣ Vstupné parametre ceny a financovania")

col1, col2 = st.columns(2)

with col1:
    base_purchase_price = st.number_input(
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

# Vypočítame klientsku cenu podľa cenníka a zľavy
client_discount_eur_m3 = selected_client["discount_eur_m3"] if selected_client else 0.0
client_discount_eur_l = client_discount_eur_m3 / 1000.0

client_price_per_l = None
if current_list_price is not None:
    client_price_per_l = current_list_price - client_discount_eur_l

st.markdown("---")
st.subheader("3️⃣ Cenníková a klientská cena")

if current_list_price is None:
    st.error("Nemáš definovanú cenníkovú cenu. Najprv ju nastav v bloku 0️⃣.")
else:
    st.write(f"**Základná cenníková cena:** {current_list_price:.4f} EUR/l")
    if selected_client:
        st.write(
            f"**Zľava klienta {selected_client['name']}:** "
            f"{client_discount_eur_m3:.2f} EUR/m³ "
            f"(= {client_discount_eur_l:.4f} EUR/l)"
        )
        st.write(
            f"➡️ **Klientská cena (po zľave): {client_price_per_l:.4f} EUR/l**"
        )
    else:
        st.info(
            "Nie je zvolený klient z CRM. Môžeš ho vybrať hore alebo pracovať len s cenníkovou cenou."
        )

# ==========================
# 4️⃣ Údaje k ponuke
# ==========================

st.header("4️⃣ Údaje k ponuke")

client_name_for_offer = st.text_input(
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
# 5️⃣ Výpočet ceny
# ==========================

st.header("5️⃣ Výpočet nákladu a marže")

if st.button("Vypočítať cenu a vytvoriť ponuku"):
    if current_list_price is None or client_price_per_l is None:
        st.error("Chýba cenníková cena alebo klientská cena. Skontroluj blok 0️⃣ a výber klienta.")
    else:
        # Základný náklad (nákup + logistika)
        base_cost = base_purchase_price + logistics

        # Ročná úroková sadzba
        annual_rate = (euribor_1m + bank_margin) / 100.0

        # Úrok za obdobie
        interest_l = base_cost * annual_rate * (days_credit / 365.0)

        # Factoring fee – % z klientovej ceny
        factoring_l = client_price_per_l * (factoring_fee / 100.0)

        # Celkový náklad
        total_cost = base_cost + interest_l + factoring_l

        # Marža na liter
        margin_eur_per_l = client_price_per_l - total_cost

        st.subheader("📊 Rozpis nákladov a marže (EUR/l)")
        st.write(f"**Nákup + logistika:** {base_cost:.4f} EUR/l")
        st.write(f"**Úrok za {days_credit} dní:** {interest_l:.4f} EUR/l")
        st.write(f"**Factoring:** {factoring_l:.4f} EUR/l")
        st.write(f"**Celkový náklad:** {total_cost:.4f} EUR/l")
        st.write(f"**Klientská cena:** {client_price_per_l:.4f} EUR/l")
        st.write(f"**Marža na litri:** {margin_eur_per_l:.4f} EUR/l")

        if client_name_for_offer and volume_l > 0:
            total_revenue = client_price_per_l * volume_l
            total_cost_volume = total_cost * volume_l
            total_margin_volume = margin_eur_per_l * volume_l

            contact_line = ""
            if selected_client:
                if selected_client.get("contact_name"):
                    contact_line += f"Kontaktná osoba: {selected_client['contact_name']}\n"
                if selected_client.get("email"):
                    contact_line += f"Email: {selected_client['email']}\n"
                if selected_client.get("phone"):
                    contact_line += f"Telefón: {selected_client['phone']}\n"

            offer_text = f"""CENOVÁ PONUKA – motorová nafta

Klient: {client_name_for_offer}
Objem: {volume_l:,.0f} l

Základná cenníková cena: {current_list_price:.4f} EUR/l
Zľava klienta: {client_discount_eur_m3:.2f} EUR/m³ (= {client_discount_eur_l:.4f} EUR/l)

Jednotková klientská cena: {client_price_per_l:.4f} EUR/l
Celková hodnota dodávky: {total_revenue:,.2f} EUR

Náklad dodávateľa:
- nákup + logistika: {base_cost:.4f} EUR/l
- financovanie ({days_credit} dní, EURIBOR 1M {euribor_1m:.2f} % + {bank_margin:.2f} %): {interest_l:.4f} EUR/l
- factoring fee {factoring_fee:.2f} %: {factoring_l:.4f} EUR/l
- celkový náklad: {total_cost:.4f} EUR/l

Odhadovaná marža dodávateľa:
- marža na liter: {margin_eur_per_l:.4f} EUR/l
- celková marža z objemu: {total_margin_volume:,.2f} EUR

{contact_line if contact_line else ""}Platnosť ponuky do: {valid_until.strftime('%d.%m.%Y')}

V Bratislave, dňa {datetime.date.today().strftime('%d.%m.%Y')}

Fuel Traders Corporation s. r. o.
"""

            st.markdown("---")
            st.subheader("📄 Text cenovej ponuky")
            st.text_area("Ponuka", offer_text, height=320)

            st.download_button(
                "⬇️ Stiahnuť ponuku ako .txt",
                data=offer_text,
                file_name="cenova_ponuka_nafta.txt",
                mime="text/plain",
            )

            st.info("Ak chceš PDF, otvor túto stránku v prehliadači → Print → Save as PDF.")
        else:
            st.warning("Vyplň názov klienta a objem dodávky, aby sa vytvoril text ponuky.")
