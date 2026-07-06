import streamlit as st
import psycopg2
import pandas as pd

# 1. الاتصال بقاعدة بيانات Neon
def get_db_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

# 2. تهيئة قاعدة البيانات
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS units (id SERIAL PRIMARY KEY, unit_name TEXT, location TEXT, unit_type TEXT, price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS contracts (id SERIAL PRIMARY KEY, unit_id INTEGER, client_name TEXT, start_date TEXT, end_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects (id SERIAL PRIMARY KEY, project_name TEXT, location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, project_id INTEGER, category TEXT, description TEXT, supplier TEXT, amount REAL, expense_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS rent_payments (id SERIAL PRIMARY KEY, contract_id INTEGER, amount_paid REAL, payment_date DATE, due_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, unit_id INTEGER, buyer_name TEXT, buyer_phone TEXT, sale_price REAL, paid_amount REAL, remaining_amount REAL, sale_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales_installments (id SERIAL PRIMARY KEY, sale_id INTEGER, amount REAL, installment_date DATE)''')
    conn.commit(); conn.close()

init_db()

# 3. الواجهة الرئيسية
st.set_page_config(page_title="نظام الإدارة العقارية والمقاولات", layout="wide")
st.title("🏢 نظام الإدارة العقارية والمقاولات السحابي")

menu = ["الرئيسية", "إدارة العقارات", "أرشيف المقاولات"]
choice = st.sidebar.selectbox("القائمة", menu)

if choice == "الرئيسية":
    st.subheader("📊 لوحة التحكم")
    st.info("مرحباً بك في النظام. يمكنك التنقل بين الصفحات من القائمة الجانبية.")

elif choice == "إدارة العقارات":
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["إضافة وحدة", "تسجيل إيجار", "عرض البيانات", "تحصيل إيجار", "عقد بيع", "سداد أقساط", "إحصائيات"])
    
    with tab1:
        with st.form("u_form"):
            n = st.text_input("اسم الوحدة"); l = st.text_input("الموقع"); t = st.selectbox("النوع", ["سكني", "تجاري"]); p = st.number_input("السعر")
            if st.form_submit_button("حفظ"):
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute('INSERT INTO units (unit_name, location, unit_type, price) VALUES (%s, %s, %s, %s)', (n, l, t, p))
                conn.commit(); conn.close(); st.rerun()
    
    with tab2:
        st.write("صفحة تسجيل الإيجار")
    with tab3:
        st.write("صفحة عرض البيانات")
    with tab4:
        st.write("صفحة تحصيل الإيجار")
    with tab5:
        st.write("صفحة عقد البيع")
    with tab6:
        st.write("صفحة الأقساط")
    with tab7:
        st.write("صفحة الإحصائيات")

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
                
    with tab2:
        st.write("صفحة تسجيل المصروفات")
    with tab3:
        st.write("صفحة التقرير المالي")
