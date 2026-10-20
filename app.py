from datetime import datetime, timedelta
import hashlib
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# הגדרת נתיב התיקייה שבה נמצא קובץ ה-app.py הנוכחי
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# הגדרת דף ותקני אבטחה בסיסיים
st.set_page_config(
    page_title="מערכת ניהול אבטחה ובקרה מחוזית",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
    <style>
    html, body, [class*="css"] {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stApp {
        background: #ffffff;
        color: #1e293b;
    }
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        color: #0f172a;
        border-left: 1px solid #e2e8f0;
        z-index: 999999;
    }
    h1 {
        color: #0f172a !important;
        font-weight: 900;
        border-bottom: 4px solid #3b82f6;
        padding-bottom: 10px;
        font-size: 2rem !important;
    }
    h2, h3 {
        color: #334155 !important;
        font-weight: 800;
        font-size: 1.4rem !important;
    }
    p, span, label {
        color: #334155;
        font-size: 1.05rem;
    }
    div[data-testid="InputInstructions"] {
        display: none !important;
    }
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-radius: 10px;
        font-weight: 700;
        border: none;
        padding: 0.6rem 1.2rem;
        width: 100%;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        transition: all 0.3s ease;
    }
    </style>
""", unsafe_allow_html=True)


# תקן OWASP: הצפנת סיסמאות חזקה (SHA-256) למניעת שמירת סיסמאות בטקסט חופשי
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def safe_int(val):
    """OWASP: מניעת שגיאות הזרקה וטיפול בערכים ריקים או שגויים (NaN)"""
    try:
        if pd.isna(val):
            return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0


# תקן OWASP: ניהול הרשאות ובקרת גישה (RBAC)
if "users" not in st.session_state:
    st.session_state.users = {
        "chendudu": {
            "password_hash": hash_password("chen1234"),
            "role": "admin",
            "managed_district": None,
        }
    }

# טעינה אוטומטית של קבצי האקסל לפי נתיב מלא מדויק
if "df_data" not in st.session_state:
    excel_files = {
        "צפון": os.path.join(BASE_DIR, "צפון.xlsx"),
        "חוף": os.path.join(BASE_DIR, "חוף.xlsx"),
        "מרכז": os.path.join(BASE_DIR, "מרכז.xlsx"),
        "תל אביב": os.path.join(BASE_DIR, "תל אביב.xlsx"),
        "ים": os.path.join(BASE_DIR, "ים.xlsx"),
        "שי": os.path.join(BASE_DIR, "שי.xlsx"),
        "דרום": os.path.join(BASE_DIR, "דרום.xlsx"),
    }

    all_rows = []
    for dist_key, filepath in excel_files.items():
        if os.path.exists(filepath):
            try:
                xls = pd.ExcelFile(filepath)
                for sheet_name in xls.sheet_names:
                    df_excel = pd.read_excel(xls, sheet_name=sheet_name)
                    for idx, row in df_excel.iterrows():
                        dist_name = str(row.get("מחוז", dist_key)).strip()
                        city_name = str(
                            row.get("שם רשום מקומית", row.get("שם ישוב בחירות", "אחר"))
                        ).strip()
                        place_name = str(
                            row.get("מקום קלפי", row.get("כתובת קלפי", "קלפי מרכזית"))
                        ).strip()
                        sec_comp = str(row.get("חברת אבטחה", "לא ידוע")).strip()

                        exp_g = safe_int(row.get("מס' מאבטחים", 0))
                        exp_a = safe_int(row.get("מס' חמושים", 0))
                        exp_c = safe_int(row.get("מס' בודקים", 0))

                        all_rows.append({
                            "m_id": f"{dist_key}_{idx}",
                            "מחוז": dist_name,
                            "עיר": city_name,
                            "מקום": place_name,
                            "חברה": sec_comp,
                            "תקן_מאבטחים": exp_g,
                            "בפועל_מאבטחים": 0,
                            "תקן_חמושים": exp_a,
                            "בפועל_חמושים": 0,
                            "תקן_בודקים": exp_c,
                            "בפועל_בודקים": 0,
                        })
            except Exception as e:
                print(f"שגיאה בקריאת הקובץ {filepath}: {e}")

    st.session_state.df_data = pd.DataFrame(all_rows)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.managed_district = None

# ==========================================
# מסך התחברות (אבטחת אימות משתמשים)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown(
            "<h2 style='text-align: center;'>🔐 התחברות למערכת ניהול אבטחה</h2>",
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<b>שם משתמש:</b>", unsafe_allow_html=True)
        username_input = st.text_input(
            "שם משתמש", label_visibility="collapsed", key="login_user"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<b>סיסמה:</b>", unsafe_allow_html=True)
        password_input = st.text_input(
            "סיסמה",
            type="password",
            label_visibility="collapsed",
            key="login_pass",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("התחבר למערכת"):
            users = st.session_state.users
            if (
                    username_input in users
                    and users[username_input]["password_hash"]
                    == hash_password(password_input)
            ):
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = users[username_input]["role"]
                st.session_state.managed_district = users[username_input][
                    "managed_district"
                ]
                st.success("התחברת בהצלחה!")
                st.rerun()
            else:
                st.error("⚠️ שם משתמש או סיסמה שגויים. נסה שוב.")
    st.stop()

# ==========================================
# אזור הניהול לאחר התחברות
# ==========================================
current_user = st.session_state.username
current_role = st.session_state.role

st.sidebar.markdown("### 🛡️ אזור אישי")
st.sidebar.markdown(f"""
    <div style="background: rgba(59, 130, 246, 0.1); padding: 14px 16px; border-radius: 12px; border: 1px solid rgb(191, 219, 254); margin-bottom: 20px;">
        <span style="font-size: 0.85rem; color: rgb(30, 64, 175);">מחובר כעת:</span><br>
        <strong style="color: rgb(30, 58, 138); font-size: 1.15rem;">{current_user}</strong><br>
        <span style="font-size: 0.85rem; color: rgb(71, 85, 105);">תפקיד: <code>{current_role}</code></span>
    </div>
""", unsafe_allow_html=True)

menu_options = ["עדכון נתונים והזנה"]
if current_role == "admin":
    menu_options.insert(0, "🖥️ מסך שליטה ארצי ודשבורד")
    menu_options.append("👥 ניהול משתמשים (Admin)")

choice = st.sidebar.radio("ניווט במערכת:", menu_options)

if st.sidebar.button("🚪 התנתק מהמערכת"):
    st.session_state.logged_in = False
    st.rerun()

df_main = st.session_state.df_data

# ==========================================
# 1. דשבורד ארצי
# ==========================================
if choice == "🖥️ מסך שליטה ארצי ודשבורד" and current_role == "admin":
    st.title("🖥️ מסך שליטה ובקרה ארצי - אבטחת קלפיות")

    if df_main.empty:
        st.error(
            "❌ שגיאה: לא נמצאו קבצי אקסל בתיקייה או שהם ריקים. בדוק שהם באותו נתיב"
            f" כמו app.py ({BASE_DIR})"
        )
    else:
        tot_exp_g = df_main["תקן_מאבטחים"].sum()
        tot_act_g = df_main["בפועל_מאבטחים"].sum()
        tot_exp_a = df_main["תקן_חמושים"].sum()
        tot_act_a = df_main["בפועל_חמושים"].sum()
        tot_exp_c = df_main["תקן_בודקים"].sum()
        tot_act_c = df_main["בפועל_בודקים"].sum()

        tot_exp_all = tot_exp_g + tot_exp_a + tot_exp_c
        tot_act_all = tot_act_g + tot_act_a + tot_act_c
        overall_pct = (tot_act_all / tot_exp_all * 100) if tot_exp_all > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("📌 מחוזות", df_main["מחוז"].nunique())
        with c2:
            st.metric("👥 סה״כ תקן ארצי", f"{tot_exp_all:,}")
        with c3:
            st.metric(
                "✨ סה״כ התייצבו בפועל",
                f"{tot_act_all:,}",
                f"{overall_pct:.1f}% ביצוע",
            )
        with c4:
            st.metric("🏢 חברות אבטחה", df_main["חברה"].nunique())

        st.markdown("---")
        st.subheader("📊 סיכום נתונים לפי מחוזות")

        dist_summary = (
            df_main.groupby("מחוז")[[
                "תקן_מאבטחים",
                "בפועל_מאבטחים",
                "תקן_חמושים",
                "בפועל_חמושים",
                "תקן_בודקים",
                "בפועל_בודקים",
            ]]
                .sum()
                .reset_index()
        )
        dist_summary["סה\"כ תקן"] = (
                dist_summary["תקן_מאבטחים"]
                + dist_summary["תקן_חמושים"]
                + dist_summary["תקן_בודקים"]
        )
        dist_summary["סה\"כ בפועל"] = (
                dist_summary["בפועל_מאבטחים"]
                + dist_summary["בפועל_חמושים"]
                + dist_summary["בפועל_בודקים"]
        )
        dist_summary["אחוז התייצבות (%)"] = (
                dist_summary["סה\"כ בפועל"] / dist_summary["סה\"כ תקן"] * 100
        ).round(1)

        st.dataframe(dist_summary, use_container_width=True, hide_index=True)

        st.subheader("🏢 סיכום לפי חברות אבטחה (ארצי)")
        comp_summary = (
            df_main.groupby("חברה")[[
                "תקן_מאבטחים",
                "בפועל_מאבטחים",
                "תקן_חמושים",
                "בפועל_חמושים",
                "תקן_בודקים",
                "בפועל_בודקים",
            ]]
                .sum()
                .reset_index()
        )
        comp_summary["סה\"כ תקן"] = (
                comp_summary["תקן_מאבטחים"]
                + comp_summary["תקן_חמושים"]
                + comp_summary["תקן_בודקים"]
        )
        comp_summary["סה\"כ בפועל"] = (
                comp_summary["בפועל_מאבטחים"]
                + comp_summary["בפועל_חמושים"]
                + comp_summary["בפועל_בודקים"]
        )
        comp_summary["עמידה בתקן (%)"] = (
                comp_summary["סה\"כ בפועל"] / comp_summary["סה\"כ תקן"] * 100
        ).round(1)
        st.dataframe(
            comp_summary.sort_values(by="עמידה בתקן (%)", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

# ==========================================
# 2. עדכון נתונים והזנה (סינון מחוזות וערים)
# ==========================================
elif choice == "עדכון נתונים והזנה":
    st.title("📋 הזנת נתוני התייצבות בשטח")

    df_filtered = df_main
    if current_role == "district_manager" and st.session_state.managed_district:
        df_filtered = df_main[
            df_main["מחוז"] == st.session_state.managed_district
            ]
        st.info(f"📌 מציג נתונים למחוז מנוהל: **{st.session_state.managed_district}**")

        # סינון נוסף לפי עיר במחוז המנוהל
        cities_in_dist = sorted(df_filtered["עיר"].unique().tolist())
        selected_city_filter = st.selectbox("🏙️ סינון לפי עיר:", ["הצג הכל"] + cities_in_dist)
        if selected_city_filter != "הצג הכל":
            df_filtered = df_filtered[df_filtered["עיר"] == selected_city_filter]

    else:
        # שלב א': בחירת מחוז
        all_districts = sorted(df_main["מחוז"].unique().tolist())
        selected_district_filter = st.selectbox(
            "🔍 סינון לפי מחוז:", ["הצג הכל"] + all_districts
        )

        if selected_district_filter != "הצג הכל":
            df_filtered = df_main[df_main["מחוז"] == selected_district_filter]

            # שלב ב': בחירת עיר מתוך המחוז הנבחר
            cities_in_dist = sorted(df_filtered["עיר"].unique().tolist())
            selected_city_filter = st.selectbox("🏙️ סינון לפי עיר:", ["הצג הכל"] + cities_in_dist)
            if selected_city_filter != "הצג הכל":
                df_filtered = df_filtered[df_filtered["עיר"] == selected_city_filter]
        else:
            # אם מוצג הכל, ניתן לאפשר גם פילטור כללי לפי עיר או להשאיר פתוח
            pass

    if df_filtered.empty:
        st.warning("⚠️ אין נתונים להצגה.")
    else:
        st.subheader("✏️ הזנת נתוני התייצבות בפועל לפי קלפי")
        st.markdown(
            "👆 **הקלק על התאים בעמודות 'בפועל' כדי לעדכן את כמות המתייצבים:**"
        )

        view_cols = [
            "m_id",
            "מחוז",
            "עיר",
            "מקום",
            "חברה",
            "תקן_מאבטחים",
            "בפועל_מאבטחים",
            "תקן_חמושים",
            "בפועל_חמושים",
            "תקן_בודקים",
            "בפועל_בודקים",
        ]
        df_editable = df_filtered[view_cols].copy()

        edited_df = st.data_editor(
            df_editable,
            hide_index=True,
            use_container_width=True,
            column_config={
                "m_id": None,
                "בפועל_מאבטחים": st.column_config.NumberColumn(
                    "בפועל מאבטחים", min_value=0, step=1, required=True
                ),
                "בפועל_חמושים": st.column_config.NumberColumn(
                    "בפועל חמושים", min_value=0, step=1, required=True
                ),
                "בפועל_בודקים": st.column_config.NumberColumn(
                    "בפועל בודקים", min_value=0, step=1, required=True
                ),
            },
            disabled=[
                "m_id",
                "מחוז",
                "עיר",
                "מקום",
                "חברה",
                "תקן_מאבטחים",
                "תקן_חמושים",
                "תקן_בודקים",
            ],
        )

        if st.button("💾 שמור נתונים ובדוק תקינות תקן"):
            has_error = False
            error_msg = ""

            for _, row in edited_df.iterrows():
                ag = safe_int(row["בפועל_מאבטחים"])
                aa = safe_int(row["בפועל_חמושים"])
                ac = safe_int(row["בפועל_בודקים"])

                eg = safe_int(row["תקן_מאבטחים"])
                ea = safe_int(row["תקן_חמושים"])
                ec = safe_int(row["תקן_בודקים"])

                # OWASP: בדיקת ולדידציה קשיחה למניעת חריגה מהתקן
                if ag > eg or aa > ea or ac > ec:
                    error_msg = (
                        f"❌ שגיאת תקן בקלפי '{row['m_id']}': כמות בפועל חורגת מהתקן המותר!"
                    )
                    has_error = True
                    break

            if has_error:
                st.error(error_msg)
            else:
                for _, row in edited_df.iterrows():
                    m_id = row["m_id"]
                    idx = st.session_state.df_data[
                        st.session_state.df_data["m_id"] == m_id
                        ].index
                    if not idx.empty:
                        st.session_state.df_data.loc[idx, "בפועל_מאבטחים"] = safe_int(
                            row["בפועל_מאבטחים"]
                        )
                        st.session_state.df_data.loc[idx, "בפועל_חמושים"] = safe_int(
                            row["בפועל_חמושים"]
                        )
                        st.session_state.df_data.loc[idx, "בפועל_בודקים"] = safe_int(
                            row["בפועל_בודקים"]
                        )

                st.success("הנתונים נשמרו בהצלחה ועמדו בכל בדיקות התקן!")
                st.rerun()

# ==========================================
# 3. ניהול משתמשים (כולל שינוי סיסמה למשתמשים)
# ==========================================
elif choice == "👥 ניהול משתמשים (Admin)" and current_role == "admin":
    st.title("👥 ניהול משתמשים והרשאות מחוזיות")

    col_add, col_edit = st.columns(2)

    with col_add:
        with st.form("add_user_form"):
            st.subheader("➕ הוספת משתמש חדש")
            new_user = st.text_input("שם משתמש")
            new_pass = st.text_input("סיסמה", type="password")
            new_role = st.selectbox(
                "תפקיד",
                ["admin", "district_manager"],
                format_func=lambda x: (
                    "מנהל מערכת ראשי (Admin)" if x == "admin" else "מפקח מחוז"
                ),
            )
            districts_list = df_main["מחוז"].unique().tolist()
            new_dist = st.selectbox("מחוז מנוהל", [""] + districts_list)

            if st.form_submit_button("צור משתמש"):
                if not new_user or not new_pass:
                    st.error("חובה להזין שם משתמש וסיסמה.")
                elif new_user in st.session_state.users:
                    st.error("שם המשתמש כבר קיים.")
                else:
                    st.session_state.users[new_user] = {
                        "password_hash": hash_password(new_pass),
                        "role": new_role,
                        "managed_district": new_dist if new_dist else None,
                    }
                    st.success(f"המשתמש {new_user} נוצר בהצלחה!")
                    st.rerun()

    with col_edit:
        with st.form("edit_pass_form"):
            st.subheader("🔑 שינוי סיסמה למשתמש קיים")
            users_list = list(st.session_state.users.keys())
            target_user = st.selectbox("בחר משתמש לעדכון", users_list)
            updated_pass = st.text_input("סיסמה חדשה", type="password")

            if st.form_submit_button("עדכן סיסמה"):
                if not updated_pass:
                    st.error("חובה להזין סיסמה חדשה.")
                else:
                    st.session_state.users[target_user]["password_hash"] = hash_password(updated_pass)
                    st.success(f"הסיסמה עבור המשתמש {target_user} עודכנה בהצלחה!")
                    st.rerun()

    st.markdown("---")
    st.subheader("📋 רשימת משתמשים קיימים")
    users_data = []
    for u, info in st.session_state.users.items():
        users_data.append({
            "שם משתמש": u,
            "תפקיד": info["role"],
            "מחוז מנוהל": info["managed_district"] or "הכל (Admin)",
        })
    st.dataframe(pd.DataFrame(users_data), use_container_width=True, hide_index=True)