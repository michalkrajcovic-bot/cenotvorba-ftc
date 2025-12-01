import streamlit as st
import datetime
import gspread


st.set_page_config(page_title="Cenotvorba nafty", page_icon="⛽", layout="centered")

# Inicializácia jednoduchého "CRM" v pamäti
if "clients" not in st.session_state:
    st.session_state["clients"] = []

# ---------- Google Sheets helpery pre cenníkovú cenu ----------

def get_cennik_worksheet():
    """Vráti worksheet 'cennik' z Google Sheets podľa ID v secrets."""
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    spreadsheet_id = st.secrets["pricing"]["spreadsheet_id"]
    sh = gc.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet("cennik")
    except Exception:
        ws = sh.add_worksheet(title="cennik", rows=1000, cols=2)
        ws.update("A1:B1", [["date", "price"]])
    return ws
def normalize_price(val):
    """
    Prevedie hodnotu ceny na float:
    - nahradí čiarku za bodku
    - ak je cena > 5, delí ju 10, kým nie je v rozumnom rozsahu
      (očakávame 0–5 EUR/l, takže opravíme 19 → 1.9, 116399 → 1.16399)
    """
    try:
        v = float(str(val).replace(",", "."))
    except Exception:
        return None

    while v > 5:
        v /= 10.0

    return v


def load_price_history():
    """Načíta históriu cenníkových cien z Google Sheets."""
    ws = get_cennik_worksheet()
    rows = ws.get_all_records()
    history = []

    for r in rows:
        raw_date = str(r.get("date", "")).strip()
        raw_price = r.get("price", "")

        if not raw_date or raw_price == "":
            continue

        # dátum – najprv ISO (2025-12-03), potom dd.mm.yyyy
        try:
            d = datetime.date.fromisoformat(raw_date)
        except Exception:
            try:
                d = datetime.datetime.strptime(raw_date, "%d.%m.%Y").date()
            except Exception:
                continue

        price = normalize_price(raw_price)
        if price is None:
            continue

        history.append({"date": d, "price": price})

    return history


def save_price_entry(date, price):
    """Uloží/aktualizuje cenníkovú cenu k dátumu v Google Sheets."""
    ws = get_cennik_worksheet()
    str_date = date.isoformat()
    norm_price = normalize_price(price)
    if norm_price is None:
        return

    try:
        cell = ws.find(str_date)
        ws.update_cell(cell.row, 2, norm_price)
    except Exception:
        ws.append_row([str_date, norm_price])

# Logo
try:
    st.image("ftc_logo.png", width=230)
except Exception:
    pass

st.title("⛽ Cenotvorba nafty – FTC pricing & mini CRM")

st.markdown(
    """
Táto aplikácia:
- eviduje **klientov**
- pracuje s **cenníkovou cenou uloženou v Google Sheets**
- z cenníka + zľavy spočíta **klientsku cenu**
- dopočíta **náklady** (nákup, logistika, financovanie, factoring)
- ukáže tvoju **maržu**
"""
)

# ==========================
# 0️⃣ Základná cenníková cena (Google Sheets)
# ==========================

st.header("0️⃣ Základná cenníková cena")

cennik_error = None
price_history = []

try:
    price_history = load_price_history()
except Exception as e:
    cennik_error = e
    st.warning("Nepodarilo sa načítať cenníkovú históriu z Google Sheets. Skontroluj secrets.")

col_p1, col_p2 = st.columns(2)

with col_p1:
    price_date = st.date_input(
        "Dátum cenníkovej ceny",
        value=datetime.date.today()
    )

with col_p2:
    base_list_price_input = st.number_input(
        "Cenníková cena (EUR/l)",
        min_value=0.0,
        value=1.500,
        step=0.001,
        format="%.4f",
    )

if st.button("💾 Uložiť cenníkovú cenu"):
    if cennik_error:
        st.error("Cenník nie je prepojený s Google Sheets – nedá sa uložiť.")
    else:
        save_price_entry(price_date, base_list_price_input)
        st.success(f"Uložené k {price_date.strftime('%d.%m.%Y')}")
        price_history = load_price_history()

current_list_price = None
if price_history:
    latest = max(price_history, key=lambda x: x["date"])
    current_list_price = latest["price"]
    st.info(
        f"Aktuálna cenníková cena "
        f"({latest['date'].strftime('%d.%m.%Y')}): **{current_list_price:.4f} EUR/l**"
    )
else:
    st.warning("Zatiaľ nemáš žiadnu cenu v Google Sheets.")

with st.expander("História cenníkových cien"):
    if price_history:
        st.table(
            [
                {
                    "Dátum": entry["date"].strftime("%d.%m.%Y"),
                    "Cenníková cena (EUR/l)": f"{entry['price']:.4f}",
                }
                for entry in sorted(price_history, key=lambda x: x["date"])
            ]
        )
    else:
        st.write("Žiadne záznamy.")


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
        st.info("Zatiaľ nemáš klientov.")

st.subheader("Pridať / upraviť klienta")

col_c1, col_c2 = st.columns(2)

with col_c1:
    client_name_form = st.text_input("Názov klienta *")
    contact_name = st.text_input("Kontaktná osoba")
    email = st.text_input("Email")
    phone = st.text_input("Telefón")

with col_c2:
    payment_days = st.number_input("Splatnosť (dni)", min_value=0, value=28, step=1)
    default_logistics_eur = st.number_input(
        "Logistika (EUR/l)",
        min_value=0.0,
        value=0.030,
        step=0.001,
        format="%.4f"
    )
    default_discount_eur_m3 = st.number_input(
        "Zľava z cenníka (EUR/m³)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format="%.2f"
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
        st.success(f"Klient '{client_name_form}' uložený.")


st.markdown("---")

# Výber klienta
st.subheader("Vyber klienta")

client_names = ["(ručne bez CRM)"] + [c["name"] for c in st.session_state["clients"]]
selected_client_name = st.selectbox("Klient", options=client_names)

selected_client = None
if selected_client_name != "(ručne bez CRM)":
    selected_client = next(
        (c for c in st.session_state["clients"] if c["name"] == selected_client_name),
        None,
    )

# ==========================
# 2️⃣ Vstupné parametre ceny a financovania
# ==========================

st.header("2️⃣ Nákup + logistika + financovanie")

col1, col2 = st.columns(2)

with col1:
    base_purchase_price = st.number_input(
        "Nákupná cena (EUR/l)",
        min_value=0.0,
        value=1.20,
        step=0.001,
        format="%.4f",
    )

    logistics = st.number_input(
        "Logistika (EUR/l)",
        min_value=0.0,
        value=(selected_client["logistics_eur"] if selected_client else 0.030),
        step=0.001,
        format="%.4f",
    )

with col2:
    days_credit = st.number_input(
        "Dni úverovania",
        min_value=0,
        value=(selected_client["payment_days"] if selected_client else 28),
        step=1,
    )

    euribor_1m = st.number_input(
        "EURIBOR 1M (%)",
        min_value=-5.0,
        value=3.80,
        step=0.01,
        format="%.2f",
    )

    bank_margin = st.number_input(
        "Marža banky (%)",
        min_value=0.0,
        value=1.80,
        step=0.01,
        format="%.2f",
    )

    factoring_fee = st.number_input(
        "Factoring fee (%)",
        min_value=0.0,
        value=0.30,
        step=0.01,
        format="%.2f",
    )


# ==========================
# 3️⃣ Cenníková a klientská cena
# ==========================

st.header("3️⃣ Cenníková a klientská cena")

client_discount_eur_m3 = selected_client["discount_eur_m3"] if selected_client else 0.0
client_discount_eur_l = client_discount_eur_m3 / 1000.0

client_price_per_l = None
if current_list_price is not None:
    client_price_per_l = current_list_price - client_discount_eur_l

if current_list_price:
    st.write(f"**Cenníková cena:** {current_list_price:.4f} EUR/l")
else:
    st.error("Nemáš uloženú cenníkovú cenu.")

if selected_client:
    st.write(f"**Zľava klienta:** {client_discount_eur_m3:.2f} EUR/m³ "
            f"(= {client_discount_eur_l:.4f} EUR/l)")
    st.write(f"➡️ **Klientská cena:** {client_price_per_l:.4f} EUR/l")
else:
    st.info("Vyber klienta z CRM.")


# ==========================
# 4️⃣ Údaje k ponuke
# ==========================

st.header("4️⃣ Údaje k ponuke")

client_name_for_offer = st.text_input(
    "Klient v ponuke",
    value=(selected_client["name"] if selected_client else "")
)

volume_l = st.number_input(
    "Objem dodávky (l)",
    min_value=0.0,
    value=30000.0,
    step=1000.0,
)

valid_until = st.date_input(
    "Platnosť ponuky",
    value=datetime.date.today() + datetime.timedelta(days=3)
)


# ==========================
# 5️⃣ Výpočet ceny
# ==========================

st.header("5️⃣ Výpočet nákladov a marže")

if st.button("Vypočítať"):

    if current_list_price is None or client_price_per_l is None:
        st.error("Chýba cenníková alebo klientská cena.")
    else:
        base_cost = base_purchase_price + logistics
        annual_rate = (euribor_1m + bank_margin) / 100.0
        interest_l = base_cost * annual_rate * (days_credit / 365.0)
        factoring_l = client_price_per_l * (factoring_fee / 100.0)
        total_cost = base_cost + interest_l + factoring_l
        margin_eur_per_l = client_price_per_l - total_cost

        st.subheader("📊 Náklady a marža (EUR/l)")
        st.write(f"Nákup + logistika: {base_cost:.4f}")
        st.write(f"Financovanie: {interest_l:.4f}")
        st.write(f"Factoring: {factoring_l:.4f}")
        st.write(f"Celkový náklad: {total_cost:.4f}")
        st.write(f"Klientská cena: {client_price_per_l:.4f}")
        st.write(f"Marža na liter: {margin_eur_per_l:.4f}")

        total_revenue = client_price_per_l * volume_l
        total_margin_volume = margin_eur_per_l * volume_l

        st.write("---")
        st.write(f"**Celková tržba:** {total_revenue:,.2f} EUR")
        st.write(f"**Celková marža:** {total_margin_volume:,.2f} EUR")

        offer = f"""
CENOVÁ PONUKA – motorová nafta

Klient: {client_name_for_offer}
Objem: {volume_l:,.0f} l

Cenníková cena: {current_list_price:.4f} EUR/l
Zľava: {client_discount_eur_m3:.2f} EUR/m³ (= {client_discount_eur_l:.4f} EUR/l)

Klientská cena: {client_price_per_l:.4f} EUR/l
Celková hodnota dodávky: {total_revenue:,.2f} EUR

Náklady:
- nákup + logistika: {base_cost:.4f}
- financovanie ({days_credit} dní): {interest_l:.4f}
- factoring: {factoring_l:.4f}

Celkový náklad: {total_cost:.4f}
Marža: {margin_eur_per_l:.4f} EUR/l
Celková marža: {total_margin_volume:,.2f} EUR

Platnosť ponuky do: {valid_until.strftime('%d.%m.%Y')}
"""

        st.text_area("Ponuka", offer, height=300)

        st.download_button(
            "Stiahnuť ponuku",
            data=offer,
            file_name="ponuka.txt",
            mime="text/plain",
        )
