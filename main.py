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
    
    # 1. تنبيه العقود المنتهية
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
                conn = get_db_connection()
                cur = conn.cursor()  # تعديل: إنشاء المؤشر
                cur.execute('INSERT INTO units (unit_name, location, unit_type, price) VALUES (%s, %s, %s, %s)', (n, l, t, p))
                conn.commit(); conn.close(); st.rerun()

    with tab2:
        st.subheader("تسجيل عقد إيجار جديد")
        df_u = pd.read_sql("SELECT id, unit_name, location FROM units", get_db_connection())
        if not df_u.empty:
            df_u['display_name'] = df_u['unit_name'] + " - " + df_u['location']
            with st.form("c_form"):
                sel = st.selectbox("الوحدة (الموقع):", df_u['display_name'])
                u_id = df_u[df_u['display_name'] == sel]['id'].iloc[0]
                c = st.text_input("المستأجر"); s = st.date_input("البداية"); e = st.date_input("النهاية")
                if st.form_submit_button("حفظ العقد"):
                    conn = get_db_connection()
                    cur = conn.cursor()  # تعديل: إنشاء المؤشر
                    cur.execute('INSERT INTO contracts (unit_id, client_name, start_date, end_date) VALUES (%s, %s, %s, %s)', (int(u_id), c, str(s), str(e)))
                    conn.commit(); conn.close(); st.success("تم حفظ العقد بنجاح!"); st.rerun()
        else: 
            st.warning("لا توجد وحدات مسجلة لإضافة عقود.")
    with tab3:
        st.subheader("🔍 إدارة وتصفية العقود والتحصيلات")
        
        # 1. الفلترة الموحدة
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            locations = ["الكل"] + pd.read_sql("SELECT DISTINCT location FROM units", get_db_connection())['location'].tolist()
            sel_loc = st.selectbox("اختر الموقع:", locations)
        with col_f2:
            start_date = st.date_input("من تاريخ:", value=pd.to_datetime("2026-01-01"))
        with col_f3:
            end_date = st.date_input("إلى تاريخ:", value=pd.to_datetime("2026-12-31"))

        filter_sql = f" AND u.location = '{sel_loc}'" if sel_loc != "الكل" else ""
        
        # 2. سجل العقود
        st.write("---"); st.subheader("📋 سجل العقود")
        sql_c = f"""SELECT c.id, u.unit_name AS "الوحدة", u.unit_type AS "النوع", 
                           c.client_name AS "المستأجر", c.start_date AS "البداية", c.end_date AS "النهاية" 
                    FROM contracts c JOIN units u ON c.unit_id = u.id 
                    WHERE 1=1 {filter_sql} AND c.start_date::date BETWEEN '{start_date}' AND '{end_date}'"""
        
        df_contracts = pd.read_sql(sql_c, get_db_connection())
        st.table(df_contracts)
        
        if not df_contracts.empty:
            c_id = st.selectbox("اختر عقد للتعامل معه:", df_contracts['id'].tolist(), key="c_sel")
            rec = df_contracts[df_contracts['id'] == c_id].iloc[0]
            with st.form("edit_contract"):
                n_c = st.text_input("المستأجر:", value=rec['المستأجر'])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 تحديث"): 
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("UPDATE contracts SET client_name=%s WHERE id=%s", (n_c, int(c_id)))
                    conn.commit(); conn.close(); st.rerun()
                if c2.form_submit_button("🗑 حذف"): 
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("DELETE FROM contracts WHERE id=%s", (int(c_id),))
                    conn.commit(); conn.close(); st.rerun()

        # 3. سجل التحصيلات (إيجار)
        st.write("---"); st.subheader("💰 سجل تحصيلات الإيجار")
        query_pay = f"""
            SELECT r.id, u.unit_name AS "الوحدة", r.amount_paid AS "المبلغ", r.due_date AS "يخص شهر" 
            FROM rent_payments r 
            JOIN contracts c ON r.contract_id = c.id 
            JOIN units u ON c.unit_id = u.id 
            WHERE 1=1 {filter_sql.replace('WHERE', 'AND') if filter_sql else ''} 
            AND r.due_date::date BETWEEN '{start_date}' AND '{end_date}'
        """
        df_pay = pd.read_sql(query_pay, get_db_connection())
        st.table(df_pay)
        
        if not df_pay.empty:
            p_id = st.selectbox("اختر دفعة إيجار:", df_pay['id'].tolist(), key="p_sel")
            rec = df_pay[df_pay['id'] == p_id].iloc[0]
            with st.form("edit_pay"):
                n_amt = st.number_input("المبلغ:", value=float(rec['المبلغ']))
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 تحديث الدفعة"): 
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("UPDATE rent_payments SET amount_paid=%s WHERE id=%s", (n_amt, int(p_id)))
                    conn.commit(); conn.close(); st.rerun()
                if c2.form_submit_button("🗑 حذف الدفعة"): 
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("DELETE FROM rent_payments WHERE id=%s", (int(p_id),))
                    conn.commit(); conn.close(); st.rerun()

        # 4. سجل المبيعات
        st.write("---"); st.subheader("🛒 سجل مبيعات الوحدات")
        query_sales = f"""
            SELECT s.id, u.unit_name AS "الوحدة", s.buyer_name AS "المشتري", 
                   s.sale_price AS "السعر", s.paid_amount AS "المدفوع", s.sale_date AS "التاريخ" 
            FROM sales s 
            JOIN units u ON s.unit_id = u.id 
            WHERE 1=1 {filter_sql.replace('WHERE', 'AND') if filter_sql else ''} 
            AND s.sale_date::date BETWEEN '{start_date}' AND '{end_date}'
        """
        df_sales = pd.read_sql(query_sales, get_db_connection())
        st.table(df_sales)
        
        if not df_sales.empty:
            s_id = st.selectbox("اختر عملية بيع للتعامل معها:", df_sales['id'].tolist(), key="s_sel")
            rec_s = df_sales[df_sales['id'] == s_id].iloc[0]
            with st.form("edit_sale"):
                new_buyer = st.text_input("اسم المشتري:", value=rec_s['المشتري'])
                new_price = st.number_input("تعديل السعر:", value=float(rec_s['السعر']))
                if st.form_submit_button("💾 تحديث البيع"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("UPDATE sales SET buyer_name=%s, sale_price=%s WHERE id=%s", (new_buyer, new_price, int(s_id)))
                    conn.commit(); conn.close(); st.rerun()
        # 5. سجل الأقساط مع التعديل والحذف
        st.write("---")
        st.subheader("📅 سجل الأقساط المدفوعة")
        
        query_inst = f"""
            SELECT i.id, u.unit_name AS "الوحدة", s.buyer_name AS "المشتري", 
                   i.amount AS "المبلغ", i.installment_date AS "تاريخ القسط" 
            FROM sales_installments i 
            JOIN sales s ON i.sale_id = s.id 
            JOIN units u ON s.unit_id = u.id 
            WHERE 1=1 {filter_sql.replace('WHERE', 'AND') if filter_sql else ''} 
            AND i.installment_date::date BETWEEN '{start_date}' AND '{end_date}'
        """
        df_inst = pd.read_sql(query_inst, get_db_connection())
        
        if not df_inst.empty:
            st.table(df_inst)
            inst_id = st.selectbox("اختر قسطاً للتعامل معه:", df_inst['id'].tolist(), key="inst_sel")
            rec_inst = df_inst[df_inst['id'] == inst_id].iloc[0]
            
            with st.form("edit_inst"):
                new_amt = st.number_input("تعديل المبلغ:", value=float(rec_inst['المبلغ']))
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 تحديث القسط"):
                    diff = new_amt - float(rec_inst['المبلغ'])
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("UPDATE sales_installments SET amount=%s WHERE id=%s", (new_amt, int(inst_id)))
                    cur.execute("""UPDATE sales SET remaining_amount = remaining_amount - %s, paid_amount = paid_amount + %s 
                                   WHERE id = (SELECT sale_id FROM sales_installments WHERE id=%s)""", (diff, diff, int(inst_id)))
                    conn.commit(); conn.close(); st.success("تم التحديث"); st.rerun()
                    
                if c2.form_submit_button("🗑 حذف القسط"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("""UPDATE sales SET remaining_amount = remaining_amount + %s, paid_amount = paid_amount - %s 
                                   WHERE id = (SELECT sale_id FROM sales_installments WHERE id=%s)""", (float(rec_inst['المبلغ']), float(rec_inst['المبلغ']), int(inst_id)))
                    cur.execute("DELETE FROM sales_installments WHERE id=%s", (int(inst_id),))
                    conn.commit(); conn.close(); st.warning("تم الحذف"); st.rerun()
        else:
            st.info("لا توجد أقساط في هذا النطاق الزمني.")  

    with tab4:
        st.subheader("💰 تسجيل دفعة إيجار")
        df_c = pd.read_sql("SELECT c.id, u.unit_name, c.client_name FROM contracts c JOIN units u ON c.unit_id = u.id", get_db_connection())
        if not df_c.empty:
            with st.form("pay_form"):
                sel_c = st.selectbox("اختر العقد:", df_c['unit_name'] + " - " + df_c['client_name'])
                c_id = df_c[df_c['unit_name'] + " - " + df_c['client_name'] == sel_c]['id'].iloc[0]
                amount = st.number_input("المبلغ المحصل"); due = st.date_input("يخص شهر")
                if st.form_submit_button("تسجيل الدفعة"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("INSERT INTO rent_payments (contract_id, amount_paid, payment_date, due_date) VALUES (%s, %s, CURRENT_DATE, %s)", (int(c_id), amount, str(due)))
                    conn.commit(); conn.close(); st.success("تم التسجيل!"); st.rerun()
    with tab5:
        st.subheader("🛒 تسجيل عملية بيع جديدة")
        df_u = pd.read_sql("SELECT id, unit_name, location, price FROM units", get_db_connection())
        if not df_u.empty:
            df_u['display'] = df_u['unit_name'] + " - " + df_u['location']
            with st.form("sale_form"):
                sel = st.selectbox("اختر الوحدة:", df_u['display'])
                u_id = df_u[df_u['display'] == sel]['id'].iloc[0]
                price = st.number_input("سعر البيع النهائي", value=float(df_u[df_u['display'] == sel]['price'].iloc[0]))
                buyer = st.text_input("اسم المشتري"); phone = st.text_input("رقم الهاتف"); paid = st.number_input("المبلغ المدفوع (مقدم)"); sale_date = st.date_input("تاريخ البيع")
                if st.form_submit_button("إتمام عملية البيع"):
                    remaining = price - paid
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute('INSERT INTO sales (unit_id, buyer_name, buyer_phone, sale_price, paid_amount, remaining_amount, sale_date) VALUES (%s, %s, %s, %s, %s, %s, %s)', 
                                (int(u_id), buyer, phone, price, paid, remaining, str(sale_date)))
                    conn.commit(); conn.close(); st.success("تمت عملية البيع بنجاح!"); st.rerun()
        else: st.warning("يجب إضافة وحدات أولاً.")

    with tab6:
        st.subheader("💳 تسجيل قسط جديد لعملية بيع")
        df_sales = pd.read_sql("SELECT s.id, u.unit_name, s.buyer_name, s.remaining_amount FROM sales s JOIN units u ON s.unit_id = u.id WHERE s.remaining_amount > 0", get_db_connection())
        if not df_sales.empty:
            df_sales['display'] = df_sales['unit_name'] + " - " + df_sales['buyer_name'] + " (المتبقي: " + df_sales['remaining_amount'].astype(str) + ")"
            with st.form("inst_form"):
                sel = st.selectbox("اختر عملية البيع:", df_sales['display'])
                sale_id = int(df_sales[df_sales['display'] == sel]['id'].iloc[0])
                amount = st.number_input("مبلغ القسط"); date = st.date_input("تاريخ الدفع")
                if st.form_submit_button("إضافة القسط"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute('INSERT INTO sales_installments (sale_id, amount, installment_date) VALUES (%s, %s, %s)', (sale_id, amount, str(date)))
                    cur.execute('UPDATE sales SET remaining_amount = remaining_amount - %s, paid_amount = paid_amount + %s WHERE id = %s', (amount, amount, sale_id))
                    conn.commit(); conn.close(); st.success("تم إضافة القسط!"); st.rerun()
        else: st.info("لا توجد مبيعات بها أقساط متبقية.")

    with tab7:
        st.subheader("📊 إحصائيات العقارات")
        col_f1, col_f2 = st.columns(2)
        start = col_f1.date_input("من:", value=pd.to_datetime("2026-01-01")); end = col_f2.date_input("إلى:", value=pd.to_datetime("2026-12-31"))
        conn = get_db_connection()
        query_sales_sum = f"SELECT SUM(sale_price) as \"الإجمالي\", SUM(paid_amount) as \"المحصل\", SUM(remaining_amount) as \"المتبقي\" FROM sales WHERE sale_date::date BETWEEN '{start}' AND '{end}'"
        df_stats = pd.read_sql(query_sales_sum, conn)
        st.table(df_stats)
        conn.close()

elif choice == "أرشيف المقاولات":
    st.subheader("أرشيف أعمال المقاولات")
    tab1, tab2, tab3 = st.tabs(["إضافة مشروع", "تسجيل مصروفات", "التقرير المالي"])
    
    with tab1:
        with st.form("p_form"):
            n = st.text_input("اسم المشروع"); l = st.text_input("الموقع")
            if st.form_submit_button("إنشاء"):
                conn = get_db_connection(); cur = conn.cursor()
                cur.execute("INSERT INTO projects (project_name, location) VALUES (%s, %s)", (n, l))
                conn.commit(); conn.close(); st.success("تم إضافة المشروع!"); st.rerun()

    with tab2:
        df_p = pd.read_sql("SELECT id, project_name FROM projects", get_db_connection())
        if not df_p.empty:
            with st.form("e_form"):
                sel = st.selectbox("🔍 ابحث عن المشروع:", df_p['project_name'])
                p_id = int(df_p[df_p['project_name'] == sel]['id'].iloc[0])
                cat = st.selectbox("البند", ["كهرباء", "سباكة", "دهانات", "عمالة"])
                desc = st.text_input("الوصف"); sup = st.text_input("المورد"); amt = st.number_input("المبلغ", min_value=0.0)
                if st.form_submit_button("تسجيل المصروف"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("INSERT INTO expenses (project_id, category, description, supplier, amount, expense_date) VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)", 
                                (p_id, cat, desc, sup, amt))
                    conn.commit(); conn.close(); st.success("تم تسجيل المصروف!"); st.rerun()
            
            st.write("---")
            search_query = st.text_input("🔍 بحث سريع في مصروفات المشروع المختار:", key="search_tab2")
            # استخدام f-string آمن للـ project_id فقط لأنه رقم صحيح
            df_exp = pd.read_sql(f'SELECT category AS "البند", description AS "الوصف", supplier AS "المورد", amount AS "المبلغ", expense_date AS "التاريخ" FROM expenses WHERE project_id = {p_id}', get_db_connection())
            
            if search_query:
                df_exp = df_exp[df_exp["الوصف"].str.contains(search_query, case=False, na=False) | 
                                df_exp["المورد"].str.contains(search_query, case=False, na=False)]
            if not df_exp.empty: st.table(df_exp)
        else: 
            st.warning("يجب إضافة مشروع أولاً.")
    with tab3:
        st.subheader("🔍 إدارة وتصفية المصروفات")
        col1, col2 = st.columns(2)
        with col1:
            df_p = pd.read_sql("SELECT id, project_name FROM projects", get_db_connection())
            sel_p = st.selectbox("اختر المشروع:", ["الكل"] + df_p['project_name'].tolist())
            start_date = st.date_input("من تاريخ:", value=pd.to_datetime("2026-01-01"))
            end_date = st.date_input("إلى تاريخ:", value=pd.to_datetime("2026-12-31"))
        with col2:
            cat = st.selectbox("اختر البند:", ["الكل", "كهرباء", "سباكة", "دهانات", "عمالة"])
            search_query = st.text_input("بحث بالوصف أو المورد:")
            min_amt = st.number_input("أقل مبلغ:", value=0.0)
        
        # بناء استعلام SQL الديناميكي
        sql = """SELECT e.id, e.category, e.description, e.supplier, e.amount, e.expense_date, p.project_name 
                 FROM expenses e JOIN projects p ON e.project_id = p.id WHERE 1=1"""
        
        if sel_p != "الكل":
            p_id = int(df_p[df_p['project_name'] == sel_p]['id'].iloc[0])
            sql += f" AND e.project_id = {p_id}"
        
        sql += f" AND e.expense_date::date BETWEEN '{start_date}' AND '{end_date}'"
        if cat != "الكل": sql += f" AND e.category = '{cat}'"
        if min_amt > 0: sql += f" AND e.amount >= {min_amt}"
        
        df_exp = pd.read_sql(sql, get_db_connection())
        
        if search_query:
            df_exp = df_exp[df_exp['description'].str.contains(search_query, case=False, na=False) | 
                            df_exp['supplier'].str.contains(search_query, case=False, na=False)]
            
        if not df_exp.empty:
            df_display = df_exp.rename(columns={
                'project_name': 'اسم المشروع', 'category': 'البند',
                'description': 'الوصف', 'supplier': 'المورد',
                'amount': 'المبلغ', 'expense_date': 'تاريخ المصروف'
            })
            st.write(f"### 💰 إجمالي التكلفة: {df_exp['amount'].sum():,.2f} ج.م")
            st.table(df_display[['اسم المشروع', 'البند', 'الوصف', 'المورد', 'المبلغ', 'تاريخ المصروف']])
            
            st.write("---")
            st.write("### 🛠 تعديل أو حذف مصروف")
            selected_id = st.selectbox("اختر رقم المصروف للتعامل معه:", df_exp['id'].tolist())
            record = df_exp[df_exp['id'] == selected_id].iloc[0]
            
            with st.form("edit_form"):
                n_cat = st.selectbox("البند", ["كهرباء", "سباكة", "دهانات", "عمالة"], 
                                     index=["كهرباء", "سباكة", "دهانات", "عمالة"].index(record['category']))
                n_desc = st.text_input("الوصف", value=record['description'])
                n_sup = st.text_input("المورد", value=record['supplier'])
                n_amt = st.number_input("المبلغ", value=float(record['amount']))
                
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 حفظ التعديل"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("UPDATE expenses SET category=%s, description=%s, supplier=%s, amount=%s WHERE id=%s", 
                                (n_cat, n_desc, n_sup, n_amt, int(selected_id)))
                    conn.commit(); conn.close(); st.rerun()
                if c2.form_submit_button("🗑 حذف المصروف"):
                    conn = get_db_connection(); cur = conn.cursor()
                    cur.execute("DELETE FROM expenses WHERE id=%s", (int(selected_id),))
                    conn.commit(); conn.close(); st.rerun()
        else:
            st.info("لا توجد مصروفات تطابق الفلتر الحالي.")
