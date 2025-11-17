# AKG Delivery App (Docker Compose + Web + phpMyAdmin)

## วิธีใช้งาน
1. แตก zip ไฟล์
2. สร้าง table ใน mysql (หลังระบบ MySQL ใน docker compose รันแล้ว):
```
CREATE TABLE akg_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_datetime DATETIME NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL
);
```
3. เปิด terminal ที่ root ของโปรเจกต์
4. รัน
```
docker compose up --build
```
5. เข้าหน้า Home: [http://localhost:5000](http://localhost:5000)
6. เข้าหน้า Form: [http://localhost:5000/form](http://localhost:5000/form)
7. phpMyAdmin: [http://localhost:8080](http://localhost:8080) (user: akg_user, pass: akg_pass)

---
> รองรับ Mac M1, M2, Windows, Linux  
> สามารถแก้ไข logo และปรับแต่งได้ในไฟล์ home.html
> เวลาที่ทำการแก้ไข Code ไม่ต้อง Stop Docker แต่ให้ใช้คำสั่ง docker compose restart web แทน
> เวลาที่ต้องการ build docker ให้ใช้คำสั่ง docker compose up --build
