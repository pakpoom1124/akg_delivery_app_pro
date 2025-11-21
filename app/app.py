from flask import Flask, render_template, render_template_string, request, redirect, flash, url_for, send_file, send_from_directory
import pandas as pd
import pymysql
import os
import imghdr
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

# Jinja filter & helper: generate download URL for an attached file (used in receipts.html & Excel export)
def build_file_url(value, external: bool = False) -> str:
    """Build a download URL for an attached file.

    - Accepts either a bare filename ("2025-11-18_AKG-SKV38_Received_1001_20251118053120.jpg")
      or a path-like string ("/app/uploads/2025-...jpg").
    - Returns empty string when there is no file.
    - If external=True, generate an absolute URL (for use in Excel export).
    - Also normalizes legacy names that were saved as "..._jpg" (no dot extension)
      or without any extension at all, so that the URL always uses a proper
      ".jpg" / ".png" / etc. while the download route still knows how to
      find the real file on disk.
    """
    if not value:
        return ''

    safe_name = os.path.basename(str(value).strip())
    if not safe_name:
        return ''

    # --- 1) Handle legacy pattern: "..._jpg" / "..._png" (underscore instead of dot)
    lower = safe_name.lower()
    for ext in ("jpg", "jpeg", "png", "pdf", "xlsx", "xls", "csv"):
        suffix = "_" + ext
        if lower.endswith(suffix) and not lower.endswith("." + ext):
            # Convert "..._jpg" -> "....jpg" for URL
            safe_name = safe_name[: -len(suffix)] + "." + ext
            lower = safe_name.lower()
            break

    # --- 2) Handle legacy pattern: value ใน DB ไม่มีจุดนามสกุลเลย ---
    # ตัวอย่างเช่น "2025-11-20_AKG-Pinklao_Received_1001_20251120111124"
    # ให้ลองตรวจในโฟลเดอร์ UPLOAD_DIR เพื่อเดาว่าน่าจะเป็นไฟล์ชนิดใด
    if "." not in safe_name:
        # พยายามหาไฟล์จริงในโฟลเดอร์ uploads ทั้งแบบ ".ext" และ "_ext"
        for ext in sorted(ALLOWED_EXT):
            ext = ext.lower()
            # candidate แบบมีจุดนามสกุล
            cand_dot = f"{safe_name}.{ext}"
            # candidate แบบ legacy ที่เซฟเป็น "_ext"
            cand_underscore = f"{safe_name}_{ext}"

            if os.path.isfile(os.path.join(UPLOAD_DIR, cand_dot)):
                # มีไฟล์แบบ .ext จริง ๆ ก็ใช้ชื่อนี้เป็น URL ไปเลย
                safe_name = cand_dot
                break
            if os.path.isfile(os.path.join(UPLOAD_DIR, cand_underscore)):
                # มีไฟล์แบบ _ext แต่เพื่อให้ดาวน์โหลดเป็น .ext สวย ๆ
                # ให้ URL ใช้ชื่อแบบมีจุดนามสกุล แล้วให้ download_file
                # จัดการ map ไปหาไฟล์จริงอีกที
                safe_name = cand_dot
                break

    return url_for('download_file', fname=safe_name, _external=external)


@app.template_filter('file_url')
def file_url(fname):
    """Template filter wrapper that always returns a relative URL."""
    return build_file_url(fname, external=False)

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
    return render_template('home_akg.html', year=datetime.now().year)

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
                        # ใช้ extension เดิมจากไฟล์ต้นฉบับ และบันทึกในรูปแบบ .jpg / .png / ฯลฯ ปกติ
                        original = secure_filename(fileobj.filename)
                        base, ext = os.path.splitext(original)  # ext เช่น ".jpg"
                        ext = ext.lower()
                        ts = datetime.now().strftime('%Y%m%d%H%M%S')
                        # ตั้งชื่อไฟล์: วันที่_สาขา_กิจกรรม_รหัสวัตถุดิบ_เวลา.นามสกุล
                        fname = secure_filename(f"{date_str}_{branch}_{activity}_{code_str}_{ts}{ext}")
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
    activity_labels = {'Received':'รับเข้า (Received)','Wasted':'บันทึกของเสีย (Wasted)','Ending':'บันทึกสิ้นวัน (Ending)'}
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
                        # ใช้ extension เดิมจากไฟล์ต้นฉบับ และบันทึกในรูปแบบ .jpg / .png / ฯลฯ ปกติ
                        original = secure_filename(fileobj.filename)
                        base, ext = os.path.splitext(original)
                        ext = ext.lower()
                        ts = datetime.now().strftime('%Y%m%d%H%M%S')
                        fname = secure_filename(f"{date_str}_{branch}_{activity}_{code_str}_{ts}{ext}")
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

# 4.2) บันทึกวัตถุดิบสิ้นวัน (Ending)
@app.route('/item_ending', methods=['GET','POST'])
def item_ending():
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
        # Normalize activity ให้เป็น 'Ending' เสมอ (รองรับ alias เผื่อมีการส่งค่ามาแตกต่างกัน)
        raw_activity = (request.form.get('activity') or 'Ending').strip()
        aliases = {
            'ending': 'Ending',
            'end': 'Ending',
            'สิ้นวัน': 'Ending',
            'ending (closing)': 'Ending',
        }
        activity = aliases.get(raw_activity.lower(), 'Ending')

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
                        # ใช้ extension เดิมจากไฟล์ต้นฉบับ และบันทึกในรูปแบบ .jpg / .png / ฯลฯ ปกติ
                        original = secure_filename(fileobj.filename)
                        base, ext = os.path.splitext(original)
                        ext = ext.lower()
                        ts = datetime.now().strftime('%Y%m%d%H%M%S')
                        fname = secure_filename(f"{date_str}_{branch}_{activity}_{code_str}_{ts}{ext}")
                        fileobj.save(os.path.join(UPLOAD_DIR, fname))
                        saved_filename = fname
                    else:
                        flash(f'ไฟล์แนบของรหัส {code_str} ไม่รองรับนามสกุล', 'warning')

                # บันทึกลงตาราง item_ending
                cur.execute("""
                    INSERT INTO item_ending
                      (receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (date_str, branch, activity, code_str, name, q_val, unit, note, saved_filename))
                inserted += 1

            db.commit()
            flash(f'บันทึกสิ้นวัน {inserted} แถวเรียบร้อย')
        except Exception as e:
            db.rollback()
            flash(f'เกิดข้อผิดพลาด: {e}')
        finally:
            db.close()
        return redirect(url_for('item_ending'))

    # GET
    selected_activity = 'Ending'
    activity_labels = {'Ending':'สิ้นวัน (Ending)'}
    return render_template(
        'item_ending.html',
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

    sql = """
        SELECT id, src_table, receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
        FROM (
            SELECT id, 'item_receipts' AS src_table,
                   receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
            FROM item_receipts
            UNION ALL
            SELECT id, 'item_wasted' AS src_table,
                   receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
            FROM item_wasted
            UNION ALL
            SELECT id, 'item_ending' AS src_table,
                   receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
            FROM item_ending
        ) AS all_moves
        WHERE 1=1
    """
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

@app.route('/receipt_edit', methods=['GET', 'POST'])
def receipt_edit():
    """
    แก้ไขรายการเคลื่อนไหวเดียว (รองรับทั้ง item_receipts, item_wasted, item_ending)
    - GET: แสดงฟอร์มแก้ไข quantity / note
    - POST: บันทึกการแก้ไขแล้ว redirect กลับไปหน้ารายงาน receipts พร้อมตัวกรองเดิม
    """
    allowed_tables = {'item_receipts', 'item_wasted', 'item_ending'}

    if request.method == 'POST':
        src_table = (request.form.get('src_table') or '').strip()
        rec_id_str = (request.form.get('rec_id') or '').strip()
        if src_table not in allowed_tables:
            flash('ตารางที่ต้องการแก้ไขไม่ถูกต้อง', 'danger')
            return redirect(url_for('receipts'))

        try:
            rec_id = int(rec_id_str)
        except ValueError:
            flash('รหัสรายการไม่ถูกต้อง', 'danger')
            return redirect(url_for('receipts'))

        qty_str = (request.form.get('quantity') or '').strip()
        note = (request.form.get('note') or '').strip()

        q_val = None
        if qty_str != '':
            try:
                q_val = float(qty_str)
            except ValueError:
                flash('จำนวนที่กรอกไม่ถูกต้อง ระบบจะไม่เปลี่ยนค่า quantity', 'warning')
                q_val = None

        db = get_db(); cur = db.cursor()
        try:
            if q_val is None:
                # แก้ไขเฉพาะหมายเหตุ
                cur.execute(f"UPDATE {src_table} SET note=%s WHERE id=%s", (note, rec_id))
            else:
                cur.execute(f"UPDATE {src_table} SET quantity=%s, note=%s WHERE id=%s", (q_val, note, rec_id))
            db.commit()
            flash('บันทึกการแก้ไขเรียบร้อยแล้ว', 'success')
        except Exception as e:
            db.rollback()
            flash(f'ไม่สามารถบันทึกการแก้ไขได้: {e}', 'danger')
        finally:
            db.close()

        # นำตัวกรองเดิมกลับไปใช้ที่หน้า receipts
        date_from = request.form.get('date_from') or ''
        date_to   = request.form.get('date_to') or ''
        branch    = request.form.get('branch') or ''
        activity  = request.form.get('activity') or ''
        return redirect(url_for('receipts',
                                date_from=date_from,
                                date_to=date_to,
                                branch=branch,
                                activity=activity))

    # GET: โหลดข้อมูลรายการที่ต้องการแก้ไข
    src_table = (request.args.get('src_table') or '').strip()
    rec_id = request.args.get('rec_id', type=int)
    date_from = request.args.get('date_from','')
    date_to   = request.args.get('date_to','')
    branch    = request.args.get('branch','')
    activity  = request.args.get('activity','')

    if src_table not in allowed_tables or not rec_id:
        flash('ข้อมูลที่ต้องการแก้ไขไม่ครบถ้วน', 'danger')
        return redirect(url_for('receipts'))

    db = get_db(); cur = db.cursor()
    cur.execute(
        f"""
        SELECT id, receipt_date, branch, activity, item_code, item_name,
               quantity, unit, note, attached_file
        FROM {src_table}
        WHERE id = %s
        """,
        (rec_id,)
    )
    row = cur.fetchone()
    db.close()

    if not row:
        flash('ไม่พบรายการที่ต้องการแก้ไข', 'danger')
        return redirect(url_for('receipts'))

    # map row -> dict เพื่อใช้ใน template
    rec = {
        'id':           row[0],
        'receipt_date': row[1],
        'branch':       row[2],
        'activity':     row[3],
        'item_code':    row[4],
        'item_name':    row[5],
        'quantity':     row[6],
        'unit':         row[7],
        'note':         row[8],
        'attached_file':row[9],
    }

    # แปลงวันที่ให้เป็น string สำหรับแสดงผล
    if hasattr(rec['receipt_date'], 'strftime'):
        rec['receipt_date_str'] = rec['receipt_date'].strftime('%Y-%m-%d')
    else:
        rec['receipt_date_str'] = str(rec['receipt_date'])

    # ใช้ template แยกไฟล์ templates/edit_receipts.html
    return render_template(
        'edit_receipts.html',
        rec=rec,
        src_table=src_table,
        date_from=date_from,
        date_to=date_to,
        branch=branch,
        activity=activity
    )

# 6) เส้นทางส่งออกข้อมูล item_receipts เป็น Excel
@app.route('/export_item_receipts')
def export_item_receipts():
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    branch    = request.args.get('branch','').strip()
    activity  = request.args.get('activity','').strip()
    sql = """
        SELECT id, src_table, receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
        FROM (
            SELECT id, 'item_receipts' AS src_table,
                   receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
            FROM item_receipts
            UNION ALL
            SELECT id, 'item_wasted' AS src_table,
                   receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
            FROM item_wasted
            UNION ALL
            SELECT id, 'item_ending' AS src_table,
                   receipt_date, branch, activity, item_code, item_name, quantity, unit, note, attached_file, created_at
            FROM item_ending
        ) AS all_moves
        WHERE 1=1
    """
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
        if 'attached_file' in df.columns:
            # Use the same URL-building logic as the Jinja filter, but with absolute URLs
            df['file_url'] = df['attached_file'].apply(lambda x: build_file_url(x, external=True))
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
    """Serve an attached file from the uploads directory as a binary download.

    - ป้องกัน path แปลก ๆ ด้วยการใช้ basename เสมอ
    - รองรับชื่อไฟล์ legacy หลายรูปแบบ เช่น
      * บันทึกเป็น "..._jpg" แทน "....jpg"
      * ค่าใน DB ไม่มีนามสกุล แต่ไฟล์จริงเป็น `.jpg` หรือ `_jpg`
    - พยายามตั้งชื่อไฟล์ที่ดาวน์โหลดให้มีนามสกุลที่ถูกต้องเสมอ
    """
    # ตัดให้เหลือเฉพาะชื่อไฟล์ ป้องกัน path traversal
    safe_name = os.path.basename((fname or '').strip())
    full_path = os.path.join(UPLOAD_DIR, safe_name)

    # 1) กรณีที่ชื่อไฟล์ตรงกับไฟล์จริงในโฟลเดอร์ uploads
    if os.path.isfile(full_path):
        # ถ้าเป็นไฟล์เก่า ๆ ที่ไม่มีนามสกุล ให้พยายามเดาประเภทไฟล์จากเนื้อไฟล์
        download_basename = safe_name
        if '.' not in download_basename:
            kind = imghdr.what(full_path)
            if kind in ('jpeg', 'jpg'):
                download_basename = safe_name + '.jpg'
            elif kind == 'png':
                download_basename = safe_name + '.png'
            elif kind == 'gif':
                download_basename = safe_name + '.gif'
            # ถ้าเดาไม่ได้ก็ปล่อยให้เป็นชื่อเดิม (ไม่มีนามสกุล)

        return send_file(full_path, as_attachment=True, download_name=download_basename)

    # 2) Compatibility / legacy fallback
    root, ext = os.path.splitext(safe_name)  # ext เช่น ".jpg"
    candidates = []

    if ext:
        # กรณีมี .ext แล้ว แต่อาจมีไฟล์เก่าที่ใช้รูปแบบ "_ext" แทน
        # เช่น ขอ "....jpg" แต่ไฟล์จริงคือ "...._jpg"
        candidates.append(f"{root}_{ext[1:]}")
    else:
        # กรณีไม่มีจุดนามสกุล ให้ลอง map หลายแบบ
        lower_name = safe_name.lower()

        # 2.1 ถ้าลงท้ายด้วย _jpg / _png / ฯลฯ แล้วไม่มีจุด ให้ลองแปลงเป็น .ext
        for e in sorted(ALLOWED_EXT):
            e = e.lower()
            suffix = "_" + e
            if lower_name.endswith(suffix):
                candidates.append(safe_name[: -len(suffix)] + "." + e)

        # 2.2 กรณีค่าใน DB เป็น base ล้วน ๆ (ไม่มีทั้ง .ext และ _ext)
        # ให้ลองต่อ .ext และ _ext แล้วค้นหาไฟล์จริง
        if not candidates:
            for e in sorted(ALLOWED_EXT):
                e = e.lower()
                candidates.append(f"{safe_name}.{e}")
                candidates.append(f"{safe_name}_{e}")

    # ลองตรวจทุก candidate ว่ามีไฟล์จริงอยู่หรือไม่
    for cand in candidates:
        cand_path = os.path.join(UPLOAD_DIR, cand)
        if os.path.isfile(cand_path):
            # กำหนดชื่อไฟล์สำหรับดาวน์โหลด
            download_basename = safe_name
            if '.' not in download_basename:
                # ถ้า original ไม่มีนามสกุล ให้ใช้ส่วนขยายของไฟล์จริง
                _, real_ext = os.path.splitext(cand)
                if real_ext:
                    download_basename = safe_name + real_ext

            app.logger.info("download_file fallback: '%s' -> '%s' (download as '%s')", safe_name, cand, download_basename)
            return send_file(cand_path, as_attachment=True, download_name=download_basename)

    # ไม่พบไฟล์จริงในโฟลเดอร์ uploads
    app.logger.warning("download_file: file not found for '%s'", safe_name)
    return f"File not found: {safe_name}", 404

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)