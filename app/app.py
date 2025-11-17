from flask import Flask, render_template, render_template_string, request, redirect, flash, url_for, send_file, send_from_directory
import pandas as pd
import pymysql
import os
#from datetime import datetime
from datetime import datetime, timedelta   # เดิมมีแต่ datetime
from urllib.parse import urlencode
from pymysql.err import IntegrityError

from werkzeug.utils import secure_filename

# === File upload configuration ===
# Avoid referencing `app` before it's defined; base on this file's directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {'pdf', 'jpg', 'jpeg', 'png', 'xlsx', 'xls', 'csv'}
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

pymysql.install_as_MySQLdb()
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

app.secret_key = "akgsecret"

# Jinja filter: generate download URL for an attached file (used in receipts.html)
@app.template_filter('file_url')
def file_url(fname):
    """
    Build a download URL for an attached file (used in receipts.html).
    Returns empty string if no filename.
    """
    if not fname:
        return ''
    return url_for('download_file', fname=fname)

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
            flash(f'เกิดข้อผิดพลาด: {e}')
        finally:
            db.close()
        return redirect(url_for('form_THG'))
    return render_template('form_THG.html', menu_items=menu_items)

@app.route('/qsr', methods=['GET', 'POST'])
def qsr_form():
    if request.method == 'POST':
        name = request.form.get('name')
        department = request.form.get('department')
        detail = request.form.get('detail')
        flash("บันทึกข้อมูล QSR เรียบร้อย!")
        return redirect(url_for('qsr_form'))
    return render_template('qsr_form.html')  
 
@app.route('/sales', methods=['GET', 'POST'])
def sales_form():
    if request.method == 'POST':
        data = {}
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

@app.route('/export_delivery_amo')
def export_delivery_amo():
    db = get_db()
    df = pd.read_sql("SELECT * FROM akg_orders", db)
    db.close()
    output_path = "delivery_amo_export.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True, download_name="delivery_amo_export.xlsx")

@app.route('/export_delivery_thg')
def export_delivery_thg():
    db = get_db()
    df = pd.read_sql("SELECT * FROM akg_orders_thg", db)
    db.close()
    output_path = "delivery_thg_export.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True, download_name="delivery_thg_export.xlsx")

@app.route('/export_sales')
def export_sales():
    db = get_db()
    df = pd.read_sql("SELECT * FROM sales", db)
    db.close()
    output_path = "sales_export.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True, download_name="sales_export.xlsx")

#add items here

@app.route('/items', methods=['GET','POST'])
def items_list():
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        item_code = request.form.get('item_code','').strip()
        item_name = request.form.get('item_name','').strip()
        default_unit = request.form.get('default_unit','').strip() or 'PCS'
        if not item_code or not item_name:
            flash('กรุณากรอกรหัสและชื่อวัตถุดิบ')
        else:
            try:
                cur.execute(
                    "INSERT INTO items (item_code, item_name, default_unit) VALUES (%s, %s, %s)",
                    (item_code, item_name, default_unit)
                )
                db.commit()
                flash('เพิ่มรายการวัตถุดิบเรียบร้อย')
            except Exception as e:
                db.rollback()
                flash(f'เกิดข้อผิดพลาด: {e}')
    cur.execute("SELECT id, item_code, item_name, default_unit, is_active FROM items ORDER BY item_code")
    rows = cur.fetchall()
    db.close()
    return render_template('items.html', rows=rows)

@app.route('/items/<int:item_id>/edit', methods=['GET','POST'])
def items_edit(item_id):
    db = get_db()
    cur = db.cursor()
    if request.method == 'POST':
        item_code   = request.form.get('item_code','').strip()
        item_name   = request.form.get('item_name','').strip()
        default_unit= request.form.get('default_unit','').strip() or 'PCS'
        is_active   = 1 if request.form.get('is_active')=='on' else 0
        try:
            cur.execute(
                "UPDATE items SET item_code=%s,item_name=%s,default_unit=%s,is_active=%s WHERE id=%s",
                (item_code, item_name, default_unit, is_active, item_id)
            )
            db.commit()
            flash('บันทึกการแก้ไขแล้ว')
            return redirect(url_for('items_list'))
        except Exception as e:
            db.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}')
    cur.execute("SELECT id, item_code, item_name, default_unit, is_active FROM items WHERE id=%s", (item_id,))
    r = cur.fetchone()
    db.close()
    # คุณควรสร้างไฟล์ templates/item_edit.html สำหรับหน้าแก้ไขนี้
    return render_template('item_edit.html', r=r)

@app.route('/items/<int:item_id>/delete', methods=['POST'])
def items_delete(item_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM items WHERE id=%s", (item_id,))
        db.commit()
        flash('ลบรายการสำเร็จ')
    except IntegrityError:
        db.rollback()
        flash('ไม่สามารถลบได้: มีรายการเคลื่อนไหวอ้างถึงวัตถุดิบนี้')
    except Exception as e:
        db.rollback()
        flash(f'ลบไม่สำเร็จ: {e}')
    finally:
        db.close()
    return redirect(url_for('items_list'))

# 4) เส้นทางสำหรับบันทึกการรับเข้าหรือปรับ/เบิก
@app.route('/item_received', methods=['GET','POST'])
def item_received():
    db = get_db(); cur = db.cursor()

    # 1) วัตถุดิบที่ยัง active
    cur.execute("""
        SELECT item_code, item_name, default_unit
        FROM items
        WHERE is_active=1
        ORDER BY item_code
    """)
    items = cur.fetchall()

    # 2) สาขาสำหรับ dropdown
    cur.execute("""
        SELECT branch_id, branch_name
        FROM AKG_Branches
        WHERE is_active=1
        ORDER BY branch_id
    """)
    branches = cur.fetchall()

    if request.method == 'POST':
        date_str  = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
        branch    = request.form.get('branch','').strip() or 'MAIN'  # เก็บเป็นชื่อสาขา
        activity  = request.form.get('activity','Received')

        try:
            inserted = 0
            for code, name, unit in items:
                code_str = str(code)

                qty_str = (request.form.get(f'qty_{code_str}','') or '').strip()
                note    = (request.form.get(f'note_{code_str}','') or '').strip()
                fileobj = request.files.get(f'file_{code_str}')

                # ข้ามถ้าไม่มีข้อมูลอะไรเลยในแถวนี้
                if qty_str == '' and note == '' and not (fileobj and fileobj.filename):
                    continue

                # แปลงจำนวน (อนุญาตว่างได้)
                q_val = None
                if qty_str != '':
                    try:
                        q_val = float(qty_str)
                    except ValueError:
                        q_val = 0.0

                # จัดการไฟล์แนบต่อแถว
                saved_filename = None
                if fileobj and fileobj.filename:
                    if allowed_file(fileobj.filename):
                        original = secure_filename(fileobj.filename)
                        ts = datetime.now().strftime('%Y%m%d%H%M%S')
                        # ใส่รายละเอียดเพื่อให้ไม่ชนกัน และดูย้อนหลังได้ง่าย
                        composed = f"{date_str}_{branch}_{activity}_{code_str}_{ts}_{original}"
                        fname = secure_filename(composed)
                        fileobj.save(os.path.join(UPLOAD_DIR, fname))
                        saved_filename = fname
                    else:
                        flash(f'ไฟล์แนบของรหัส {code_str} ไม่รองรับนามสกุล', 'warning')

                # บันทึกลงตาราง item_receipts; จะบันทึกเมื่อมีอย่างน้อยหนึ่งฟิลด์ถูกกรอก
                cur.execute("""
                    INSERT INTO item_receipts
                      (receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date_str, branch, activity, code_str, name, q_val, unit, note, saved_filename))
                inserted += 1

            db.commit()
            flash(f'บันทึกการเคลื่อนไหว {inserted} แถวเรียบร้อย')
        except Exception as e:
            db.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}')
        finally:
            db.close()
        return redirect(url_for('item_received'))

    # GET
    selected_activity = 'Received'
    activity_labels = {'Received':'รับเข้า (Received)','Wasted':'ปรับ (Wasted)','Issued':'เบิก (Issued)'}
    return render_template(
        'item_received.html',
        items=items,
        branches=branches,
        nowdate=datetime.now().strftime('%Y-%m-%d'),
        selected_activity=selected_activity,
        selected_activity_label=activity_labels[selected_activity]
    )

# 4.1) บันทึกวัตถุดิบของเสีย (Wasted)
@app.route('/item_wasted', methods=['GET','POST'])
def item_wasted():
    db = get_db(); cur = db.cursor()

    # 1) วัตถุดิบที่ยัง active
    cur.execute("""
        SELECT item_code, item_name, default_unit
        FROM items
        WHERE is_active=1
        ORDER BY item_code
    """)
    items = cur.fetchall()

    # 2) สาขาสำหรับ dropdown
    cur.execute("""
        SELECT branch_id, branch_name
        FROM AKG_Branches
        WHERE is_active=1
        ORDER BY branch_id
    """)
    branches = cur.fetchall()

    if request.method == 'POST':
        date_str  = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
        branch    = request.form.get('branch','').strip() or 'MAIN'
        # Normalize activity to exactly 'Wasted' (accept various user/form variants)
        raw_activity = (request.form.get('activity') or 'Wasted').strip()
        aliases = {
            'wasted': 'Wasted',
            'waste': 'Wasted',
            'ของเสีย': 'Wasted',
            'ปรับ (wasted)': 'Wasted',
            'ปรับ(wasted)': 'Wasted'
        }
        activity = aliases.get(raw_activity.lower(), 'Wasted')

        try:
            inserted = 0
            for code, name, unit in items:
                code_str = str(code)

                qty_str = (request.form.get(f'qty_{code_str}','') or '').strip()
                note    = (request.form.get(f'note_{code_str}','') or '').strip()
                fileobj = request.files.get(f'file_{code_str}')

                # ถ้าไม่ได้ใส่อะไรเลยในแถวนี้ ให้ข้าม
                if qty_str == '' and note == '' and not (fileobj and fileobj.filename):
                    continue

                q_val = None
                if qty_str != '':
                    try:
                        q_val = float(qty_str)
                    except ValueError:
                        q_val = 0.0

                saved_filename = None
                if fileobj and fileobj.filename:
                    if allowed_file(fileobj.filename):
                        original = secure_filename(fileobj.filename)
                        ts = datetime.now().strftime('%Y%m%d%H%M%S')
                        composed = f"{date_str}_{branch}_{activity}_{code_str}_{ts}_{original}"
                        fname = secure_filename(composed)
                        fileobj.save(os.path.join(UPLOAD_DIR, fname))
                        saved_filename = fname
                    else:
                        flash(f'ไฟล์แนบของรหัส {code_str} ไม่รองรับนามสกุล', 'warning')

                # บันทึกลงตาราง item_wasted
                cur.execute("""
                    INSERT INTO item_wasted
                      (receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date_str, branch, activity, code_str, name, q_val, unit, note, saved_filename))
                inserted += 1

            db.commit()
            flash(f'บันทึกของเสีย {inserted} แถวเรียบร้อย')
        except Exception as e:
            db.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}')
        finally:
            db.close()
        return redirect(url_for('item_wasted'))

    # GET
    selected_activity = 'Wasted'
    activity_labels = {'Wasted':'ของเสีย (Wasted)'}
    return render_template(
        'item_wasted.html',
        items=items,
        branches=branches,
        nowdate=datetime.now().strftime('%Y-%m-%d'),
        selected_activity=selected_activity,
        selected_activity_label=activity_labels.get(selected_activity, selected_activity)
    )

# 5) หน้าแสดงรายงาน + ตัวกรอง
@app.route('/receipts')
def receipts():
    today = datetime.now().date()
    default_from = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    date_from = request.args.get('date_from', default_from)
    date_to   = request.args.get('date_to', today.strftime('%Y-%m-%d'))
    branch    = request.args.get('branch','').strip()
    activity  = request.args.get('activity','').strip()

    sql = ("SELECT receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at "
           "FROM item_receipts WHERE 1=1")
    params = []
    if date_from:
        sql += " AND receipt_date >= %s"; params.append(date_from)
    if date_to:
        sql += " AND receipt_date <= %s"; params.append(date_to)
    if branch:
        # Use exact match to align with dropdown values
        sql += " AND branch = %s";        params.append(branch)
    if activity:
        sql += " AND activity = %s";      params.append(activity)
    sql += " ORDER BY receipt_date DESC, item_code"
    
    db = get_db(); cur = db.cursor()
    
    # Load active branches for the dropdown
    cur.execute("SELECT branch_name FROM AKG_Branches WHERE is_active=1 ORDER BY branch_name")
    branches = [r[0] for r in cur.fetchall()]
    
    # Fetch report rows
    cur.execute(sql, params); rows = cur.fetchall()
    db.close()
    
    # Build export link with current filters
    export_qs = urlencode({'date_from': date_from, 'date_to': date_to, 'branch': branch, 'activity': activity})
    export_url = url_for('export_item_receipts') + ('?' + export_qs if export_qs else '')
    
    return render_template('receipts.html',
                           rows=rows,
                           date_from=date_from,
                           date_to=date_to,
                           branch=branch,
                           activity=activity,
                           export_url=export_url,
                           branches=branches)

# 6) เส้นทางส่งออกข้อมูล item_receipts เป็น Excel
@app.route('/export_item_receipts')
def export_item_receipts():
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    branch    = request.args.get('branch','').strip()
    activity  = request.args.get('activity','').strip()
    sql = ("SELECT receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at "
           "FROM item_receipts WHERE 1=1")
    params = []
    if date_from:
        sql += " AND receipt_date >= %s"; params.append(date_from)
    if date_to:
        sql += " AND receipt_date <= %s"; params.append(date_to)
    if branch:
        sql += " AND branch = %s";        params.append(branch)
    if activity:
        sql += " AND activity = %s";      params.append(activity)
    sql += " ORDER BY receipt_date DESC, item_code"
    db = get_db()
    df = pd.read_sql(sql, db, params=params)
    db.close()
    # Add absolute download URL for attached files so Excel users can click it
    with app.app_context():
        def _make_url(x):
            return url_for('download_file', fname=x, _external=True) if isinstance(x, str) and x.strip() else ''
        if 'attached_file' in df.columns:
            df['file_url'] = df['attached_file'].apply(_make_url)
            # Reorder columns if all expected columns are present
            desired = ['receipt_date', 'branch', 'activity', 'item_code', 'item_name',
                       'quantity', 'unit', 'note', 'attached_file', 'file_url', 'created_at']
            existing = [c for c in desired if c in df.columns]
            df = df[existing]
    output_path = "item_receipts_export.xlsx"
    df.to_excel(output_path, index=False)
    return send_file(output_path, as_attachment=True, download_name="item_receipts_export.xlsx")

# === Branches ===

@app.route('/branches', methods=['GET', 'POST'])
def branches():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        try:
            branch_id = int(request.form['branch_id'])
            branch_name = request.form['branch_name'].strip()
            is_active = 1 if request.form.get('is_active') else 0
            cur.execute(
                "INSERT INTO AKG_Branches (branch_id, branch_name, is_active) VALUES (%s,%s,%s)",
                (branch_id, branch_name, is_active)
            )
            conn.commit()
            flash('เพิ่มสาขาเรียบร้อย')
        except Exception as e:
            conn.rollback()
            flash(f'บันทึกล้มเหลว: {e}')
        return redirect(url_for('branches'))

    cur.execute("SELECT branch_id, branch_name, is_active FROM AKG_Branches ORDER BY branch_id")
    rows = cur.fetchall()
    conn.close()
    return render_template('branches.html', rows=rows)

@app.route('/branches/<int:branch_id>/delete', methods=['POST'])
def branches_delete(branch_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM AKG_Branches WHERE branch_id=%s", (branch_id,))
        conn.commit()
        flash('ลบข้อมูลเรียบร้อย')
    except IntegrityError:
        conn.rollback()
        flash('ไม่สามารถลบได้: มีข้อมูลอ้างอิงถึงสาขานี้')
    except Exception as e:
        conn.rollback()
        flash(f'ลบไม่สำเร็จ: {e}')
    finally:
        conn.close()
    return redirect(url_for('branches'))


@app.route('/branches/<int:branch_id>/edit', methods=['GET', 'POST'])
def branches_edit(branch_id):
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        try:
            branch_name = request.form['branch_name'].strip()
            is_active = 1 if request.form.get('is_active') else 0
            cur.execute(
                "UPDATE AKG_Branches SET branch_name=%s, is_active=%s WHERE branch_id=%s",
                (branch_name, is_active, branch_id)
            )
            conn.commit()
            flash('บันทึกการแก้ไขแล้ว')
            return redirect(url_for('branches'))
        except Exception as e:
            conn.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}')
            return redirect(url_for('branches_edit', branch_id=branch_id))
    # GET: โหลดข้อมูลมาแก้
    cur.execute(
        "SELECT branch_id, branch_name, is_active FROM AKG_Branches WHERE branch_id=%s",
        (branch_id,)
    )
    r = cur.fetchone()
    conn.close()
    if not r:
        flash('ไม่พบสาขานี้')
        return redirect(url_for('branches'))
    return render_template('branch_edit.html', r=r)

# === Download attached file route ===
@app.route('/download/<path:fname>')
def download_file(fname):
    return send_from_directory(UPLOAD_DIR, fname, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)