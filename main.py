import streamlit as st
import psycopg2

# الحصول على الرابط من الإعدادات الآمنة (Secrets)
DATABASE_URL = st.secrets["DATABASE_URL"]

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

st.title("🏠 نظام الإدارة العقارية والمقاولات")

# القائمة الجانبية للتنقل
menu = ["الرئيسية", "إضافة وحدة جديدة", "عرض الوحدات"]
choice = st.sidebar.selectbox("القائمة", menu)

if choice == "الرئيسية":
    st.write("مرحباً بك في لوحة تحكم النظام. اختر إجراءً من القائمة الجانبية.")

elif choice == "إضافة وحدة جديدة":
    st.subheader("إضافة عقار جديد")
    with st.form("unit_form"):
        name = st.text_input("اسم الوحدة")
        location = st.text_input("الموقع")
        u_type = st.selectbox("نوع الوحدة", ["شقة", "فيلا", "محل تجاري"])
        price = st.number_input("السعر", min_value=0.0)
        submit = st.form_submit_button("حفظ الوحدة")

        if submit:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO units (unit_name, location, unit_type, price) VALUES (%s, %s, %s, %s)", 
                      (name, location, u_type, price))
            conn.commit()
            conn.close()
            st.success(f"تم إضافة {name} بنجاح!")

elif choice == "عرض الوحدات":
    st.subheader("قائمة الوحدات المتاحة")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM units")
    data = c.fetchall()
    conn.close()
    
    if data:
        for row in data:
            st.write(f"🏢 {row[1]} - الموقع: {row[2]} - السعر: {row[4]} ج.م")
    else:
        st.write("لا توجد وحدات مضافة بعد.")
