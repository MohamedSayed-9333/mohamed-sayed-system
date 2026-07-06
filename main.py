import streamlit as st
import psycopg2
import pandas as pd

# 1. الاتصال بقاعدة بيانات Neon السحابية
def get_db_connection():
    # يتم سحب الرابط من إعدادات Secrets في Streamlit Cloud
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# 2. تهيئة قاعدة البيانات (هيكل موحد لكل النظام)
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # استخدام SERIAL بدلاً من AUTOINCREMENT، واستخدام TEXT/REAL/DATE بشكل قياسي
    c.execute('''CREATE TABLE IF NOT EXISTS units (id SERIAL PRIMARY KEY, unit_name TEXT, location TEXT, unit_type TEXT, price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS contracts (id SERIAL PRIMARY KEY, unit_id INTEGER, client_name TEXT, start_date TEXT, end_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects (id SERIAL PRIMARY KEY, project_name TEXT, location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, project_id INTEGER, category TEXT, description TEXT, supplier TEXT, amount REAL, expense_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rent_payments (id SERIAL PRIMARY KEY, contract_id INTEGER, amount_paid REAL, payment_date DATE, due_date DATE, FOREIGN KEY (contract_id) REFERENCES contracts(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, unit_id INTEGER, buyer_name TEXT, buyer_phone TEXT, sale_price REAL, paid_amount REAL, remaining_amount REAL, sale_date DATE, FOREIGN KEY (unit_id) REFERENCES units(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales_installments (id SERIAL PRIMARY KEY, sale_id INTEGER, amount REAL, installment_date DATE, FOREIGN KEY (sale_id) REFERENCES sales(id))''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="نظام الإدارة العقارية والمقاولات", layout="wide")
st.title("🏢 نظام الإدارة العقارية والمقاولات (السحابي)")

menu = ["الرئيسية", "إدارة العقارات", "أرشيف المقاولات"]
choice = st.sidebar.selectbox("القائمة", menu)

# --- صفحة الرئيسية ---
if choice == "الرئيسية":
    st.subheader("📊 لوحة التحكم والتنبيهات الشهرية")
    col1, col2 = st.columns(2)
    
    conn = get_db_connection()
    
    # 1. تنبيه العقود المنتهية (استخدام CURRENT_DATE بدلاً من date('now'))
    with col1:
        st.write("### ⏳ عقود توشك على الانتهاء")
        query_alert = '''SELECT u.unit_name AS "الوحدة", c.client_name AS "المستأجر", c.end_date AS "تاريخ النهاية" 
                         FROM contracts c JOIN units u ON c.unit_id = u.id 
                         WHERE c.end_date::date BETWEEN CURRENT_DATE AND (CURRENT_DATE + INTERVAL '30 days')'''
        df_alert = pd.read_sql(query_alert, conn)
        if not df_alert.empty:
            st.error("⚠️ هناك عقود ستنتهي خلال 30 يوماً:"); st.table(df_alert)
        else:
            st.success("✅ لا توجد عقود ستنتهي قريباً.")

    # 2. تنبيه الإيجارات
    with col2:
        st.write("### 🔔 تحصيلات الإيجار الشهرية")
        query_rent = '''SELECT u.unit_name AS "الوحدة", c.client_name AS "المستأجر" 
                        FROM contracts c JOIN units u ON c.unit_id = u.id 
                        WHERE c.id NOT IN (SELECT contract_id FROM rent_payments WHERE due_date >= DATE_TRUNC('month', CURRENT_DATE))'''
        df_unpaid = pd.read_sql(query_rent, conn)
        if not df_unpaid.empty:
            st.warning("⚠️ إيجارات لم تسدد هذا الشهر:"); st.table(df_unpaid)
        else:
            st.success("✅ تم تحصيل جميع إيجارات الشهر الحالي.")

    # 3. متابعة الأقساط المتبقية
    st.write("---")
    st.subheader("💳 متابعة مبيعات الوحدات (الأقساط المتبقية)")
    query_sales_rem = '''SELECT u.unit_name AS "الوحدة", s.buyer_name AS "المشتري", s.remaining_amount AS "المبلغ المتبقي" 
                         FROM sales s JOIN units u ON s.unit_id = u.id 
                         WHERE s.remaining_amount > 0 ORDER BY s.remaining_amount DESC'''
    df_sales_rem = pd.read_sql(query_sales_rem, conn)
    
    if not df_sales_rem.empty:
        st.info("⚠️ قائمة الوحدات التي يوجد عليها مبالغ متبقية:")
        st.table(df_sales_rem)
        st.metric("إجمالي المديونيات الحالية", f"{df_sales_rem['المبلغ المتبقي'].sum():,.2f} ج.م")
    else:
        st.success("✅ تم تحصيل كامل ثمن جميع الوحدات المباعة.")
        
    conn.close()
    
    st.write("---")
    st.info("💡 نصيحة: يمكنك التنقل بين 'إدارة العقارات' و 'أرشيف المقاولات' من القائمة الجانبية لإضافة بيانات جديدة.")


elif choice == "إدارة العقارات":
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["إضافة وحدة", "تسجيل إيجار", "عرض البيانات", "تحصيل إيجار", "تسجيل عقد بيع", "سداد أقساط", "إحصائيات العقارات"])
    with tab1:
        with st.form("u_form"):
            n = st.text_input("اسم الوحدة"); l = st.text_input("الموقع"); t = st.selectbox("النوع", ["سكني", "تجاري", "إداري", "طبي"]); p = st.number_input("السعر")
            if st.form_submit_button("حفظ"):
                conn = get_db_connection(); conn.execute('INSERT INTO units (unit_name, location, unit_type, price) VALUES (?, ?, ?, ?)', (n, l, t, p))
                conn.commit(); conn.close(); st.rerun()
    with tab2: st.write("صفحة تسجيل الإيجار")
        df_u = pd.read_sql("SELECT id, unit_name, location FROM units", get_db_connection())
        if not df_u.empty:
            df_u['display_name'] = df_u['unit_name'] + " - " + df_u['location']
            with st.form("c_form"):
                sel = st.selectbox("الوحدة (الموقع):", df_u['display_name'])
                u_id = df_u[df_u['display_name'] == sel]['id'].iloc[0]
                c = st.text_input("المستأجر"); s = st.date_input("البداية"); e = st.date_input("النهاية")
                if st.form_submit_button("حفظ العقد"):
                    conn = get_db_connection(); conn.execute('INSERT INTO contracts (unit_id, client_name, start_date, end_date) VALUES (?, ?, ?, ?)', (int(u_id), c, str(s), str(e)))
                    conn.commit(); conn.close(); st.rerun()
        else: st.warning("لا توجد وحدات مسجلة.")
    with tab3: st.write("صفحة عرض البيانات")
    with tab4: st.write("صفحة تحصيل الإيجار")
    with tab5: st.write("صفحة عقد البيع")
    with tab6: st.write("صفحة الأقساط")
    with tab7: st.write("صفحة الإحصائيات")

elif choice == "أرشيف المقاولات":
    st.subheader("أرشيف أعمال المقاولات")
    tab1, tab2, tab3 = st.tabs(["إضافة مشروع", "تسجيل مصروفات", "التقرير المالي"])
    with tab1:
        with st.form("p_form"):
            n = st.text_input("اسم المشروع"); l = st.text_input("الموقع")
            if st.form_submit_button("إنشاء"):
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute("INSERT INTO projects (project_name, location) VALUES (%s, %s)", (n, l))
                conn.commit(); conn.close(); st.rerun()
    with tab2: st.write("صفحة تسجيل المصروفات")
    with tab3: st.write("صفحة التقرير المالي")
