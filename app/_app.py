from flask import Flask, render_template, request, redirect, flash, url_for, send_file
import pandas as pd
import pymysql
import os
from datetime import datetime

pymysql.install_as_MySQLdb()
app = Flask(__name__)
app.secret_key = "akgsecret"

MYSQL_HOST = os.environ.get('MYSQL_HOST', 'db')
MYSQL_USER = os.environ.get('MYSQL_USER', 'akg_user')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'akg_pass')
MYSQL_DB = os.environ.get('MYSQL_DB', 'akg_db')

def get_db():
    return pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, passwd=MYSQL_PASSWORD, db=MYSQL_DB, charset='utf8')

menu_df = pd.read_excel("AKG_Delivery.xlsx")
menu_items = menu_df["รายการอาหาร"].tolist()

@app.route('/')
def home():
    return render_template('home.html', year=datetime.now().year)

@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        selected = request.form.getlist('menu')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db = get_db()
        cursor = db.cursor()
        n_saved = 0
        for idx, item in enumerate(menu_items):
            if str(idx) in selected:
                qty_str = request.form.get(f'quantity{idx}', '0')
                try:
                    qty = int(qty_str)
                except ValueError:
                    qty = 0
                if qty > 0:
                    cursor.execute(
                        "INSERT INTO akg_orders (order_datetime, item_name, quantity) VALUES (%s, %s, %s)",
                        (now, item, qty)
                    )
                    n_saved += 1
        db.commit()
        db.close()
        flash(f'บันทึกข้อมูล {n_saved} รายการเรียบร้อย!')
        return redirect(url_for('form'))
    return render_template('form.html', menu_items=menu_items)

@app.route('/form_THG', methods=['GET', 'POST'])
def form_THG():
    if request.method == 'POST':
        selected = request.form.getlist('menu')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db = get_db()
        cursor = db.cursor()
        n_saved = 0
        try:
            for idx, item in enumerate(menu_items):
                if str(idx) in selected:
                    qty_str = request.form.get(f'quantity{idx}', '0')
                    try:
                        qty = int(qty_str)
                    except ValueError:
                        qty = 0
                    if qty > 0:
                        cursor.execute(
                            "INSERT INTO akg_orders_thg (order_datetime, item_name, quantity) VALUES (%s, %s, %s)",
                            (now, item, qty)
                        )
                        n_saved += 1
            db.commit()
            flash(f'บันทึกข้อมูล {n_saved} รายการเรียบร้อย!')
        except Exception as e:
            db.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}')   # <-- ดู error ที่นี่
        finally:
            db.close()
        flash(f'บันทึกข้อมูล {n_saved} รายการเรียบร้อย!')
        return redirect(url_for('form_THG'))
    return render_template('form_THG.html', menu_items=menu_items)

@app.route('/qsr', methods=['GET', 'POST'])
def qsr_form():
    if request.method == 'POST':
        # ตัวอย่าง: รับค่าจากฟอร์ม (แก้ชื่อ field ตามที่มีใน template)
        name = request.form.get('name')
        department = request.form.get('department')
        detail = request.form.get('detail')
        # -- ใส่ logic เก็บข้อมูลลง MySQL (หรืออื่นๆ) ได้เลย --
        flash("บันทึกข้อมูล QSR เรียบร้อย!")
        return redirect(url_for('qsr_form'))
    return render_template('qsr_form.html')  
 

@app.route('/sales', methods=['GET', 'POST'])
def sales_form():
    if request.method == 'POST':
        data = {}
        # ดึงค่าทุก field จาก form
        for field in [
            "Date", "Branch", "TargetSales", "BaseSales", "NoOfGuest", "AvgCheck",
            "StaffMorningShift", "StaffAfternoonShift", "Overtime", "Absence",
            "AreaManager2", "ManagerOnDuty",
            "L_Reservation", "L_FnBUnavaliable", "L_ComplainComment", "L_BaseSales", "L_AvgCheck", "L_Guest", "L_DineIn", "L_TakeAway", "L_GrabFood", "L_LineMan", "L_Catering",
            "D_Reservation", "D_FnBUnavaliable", "D_Complain_Comment", "D_BaseSales", "D_AvgCheck", "D_Guest", "D_DineIn", "D_TakeAway", "D_GrabFood", "D_LineMan", "D_Catering"
        ]:
            data[field] = request.form.get(field)

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("""
                INSERT INTO sales (
                    Date, Branch, TargetSales, BaseSales, NoOfGuest, AvgCheck,
                    StaffMorningShift, StaffAfternoonShift, Overtime, Absence,
                    AreaManager2, ManagerOnDuty,
                    L_Reservation, L_FnBUnavaliable, L_ComplainComment, L_BaseSales, L_AvgCheck, L_Guest, L_DineIn, L_TakeAway, L_GrabFood, L_LineMan, L_Catering,
                    D_Reservation, D_FnBUnavaliable, D_Complain_Comment, D_BaseSales, D_AvgCheck, D_Guest, D_DineIn, D_TakeAway, D_GrabFood, D_LineMan, D_Catering
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, tuple(data.values()))
            db.commit()
            flash("บันทึกข้อมูล Sales ครบทุกคอลัมน์เรียบร้อย!")
        except Exception as e:
            db.rollback()
            flash("เกิดข้อผิดพลาดในการบันทึกข้อมูล: " + str(e))
        finally:
            db.close()
        return redirect(url_for('sales_form'))
    return render_template('sales_form.html')

@app.route('/export_delivery')
def export_delivery():
    db = get_db()
    df = pd.read_sql("SELECT * FROM akg_orders", db)
    db.close()
    output_path = "delivery_export.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True, download_name="delivery_export.xlsx")

@app.route('/export_sales')
def export_sales():
    db = get_db()
    df = pd.read_sql("SELECT * FROM sales", db)
    db.close()
    output_path = "sales_export.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True, download_name="sales_export.xlsx")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)