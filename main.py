import streamlit as st
import psycopg2
import os

# الرابط الخاص بك
DATABASE_URL = "postgresql://neondb_owner:npg_T8zwBuoDEe2U@ep-sparkling-meadow-atb4i0jc-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # إنشاء الجداول بـ SERIAL بدلاً من AUTOINCREMENT
    c.execute('''CREATE TABLE IF NOT EXISTS units (id SERIAL PRIMARY KEY, unit_name TEXT, location TEXT, unit_type TEXT, price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS contracts (id SERIAL PRIMARY KEY, unit_id INTEGER, client_name TEXT, start_date DATE, end_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id SERIAL PRIMARY KEY, project_id INTEGER, category TEXT, description TEXT, supplier TEXT, amount REAL, expense_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id SERIAL PRIMARY KEY, unit_id INTEGER, buyer_name TEXT, sale_price REAL, paid_amount REAL, remaining_amount REAL, sale_date DATE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales_installments (id SERIAL PRIMARY KEY, sale_id INTEGER, amount REAL, installment_date DATE)''')
    conn.commit()
    c.close()
    conn.close()

# تنفيذ التهيئة
init_db()

st.title("نظام الإدارة العقارية والمقاولات")
st.write("تم الاتصال بقاعدة البيانات بنجاح وبناء الجداول!")
