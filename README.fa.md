# میلی‌کانفیگ (MILICONFIG)

پلتفرم سازمانی و بازنویسی کامل پایتونی برای زیرساخت پروکسی و تولید هوشمند سابسکریپشن.  
نسخه بازنویسی‌شده، مستقل و مدرن پروژه [`byjoey/cfnew`](https://github.com/byjoey/cfnew) با تمرکز بر استقرار در **Railway** و **Docker**.

---

## ۱. ویژگی‌های کلیدی

- **حذف کامل وابستگی به کلودفلر**: تمام منطق پروکسی و شبکه با پایتون ناهمگام (FastAPI + Asyncio) بازنویسی شده و به هیچ ورکر کلودفلر یا کتابخانه‌های اختصاصی وابسته نیست.
- **سیستم چندکاربره واقعی (Multi-User)**:
  - هر کاربر دارای UUID اختصاصی، توکن سابسکریپشن مستقل، محدودیت ترافیک (آپلود/دانلود)، تاریخ انقضا و وضعیت فعالیت است.
- **پروتکل‌های پیاده‌سازی‌شده**:
  - **VLESS**: تجزیه باینری بسته VLESS، احراز هویت با UUID، پشتیبانی از استریم TCP و UDP.
  - **Trojan**: اعتبارسنجی هش SHA224 کلمه عبور و رله فریم‌های تروجان.
  - **xHTTP**: انتقال استریمینگ HTTP POST با هدرها و پارامترهای پدینگ تصادفی ضد DPI.
  - **ShadowSocks واقعی**: سرور بومی پایتون بر پایه الگوریتم‌های استاندارد AEAD (`chacha20-ietf-poly1305`, `aes-256-gcm`, `aes-128-gcm`) با پورت و رمز اختصاصی برای هر کاربر.
- **الزام نام‌گذاری نودها**: تمامی نودهای خروجی برای کلاینت با پیشوند اجباری `miliconfig` نام‌گذاری می‌شوند (مثلاً `miliconfig-01 • US Premium`، `miliconfig • VLESS`).
- **موتور تولید سابسکریپشن**:
  - تشخیص خودکار نرم‌افزار کلاینت از روی `User-Agent` (نرم‌افزارهای Clash, Sing-box, V2RayNG, Shadowrocket, Surge, Loon).
  - تولید خروجی‌های استاندارد Base64, Clash/Mihomo YAML و Sing-box JSON (سازگار با نسخه 1.12+).
- **پنل مدیریت Dark Glassmorphism**:
  - طراحی نئون سبز تیره با داشبورد زنده، بدون داده‌های ساختگی یا فیک.
- **آماده استقرار در Railway و Docker**:
  - با داکر ایمیج امن (Non-root user)، سلامت‌سنجی خودکار و بدون پورت هاردکد شده.

---

## ۲. راه‌اندازی و توسعه محلی (Local Development)

```bash
# کلون کردن مخزن
git clone https://github.com/your-username/miliconfig.git
cd miliconfig

# ایجاد و فعال‌سازی محیط مجازی
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای سرور توسعه
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

سپس مرورگر خود را باز کرده و به نشانی [http://localhost:8000](http://localhost:8000) بروید.
اطلاعات پیش‌فرض ورود مدیر:
- **نام کاربری**: `admin`
- **رمز عبور**: `miliconfig_admin_2026`

---

## ۳. استقرار با Docker و Docker Compose

برای اجرای کامل سرویس به همراه پایگاه‌داده PostgreSQL:

```bash
# اجرای سرویس‌ها در پس‌زمینه
docker compose up -d

# مشاهده لاگ‌ها
docker compose logs -f miliconfig
```

پس از بالا آمدن کانتینر، پنل روی پورت `8000` و سرور شدوساکس روی پورت `8388` در دسترس خواهد بود.

---

## ۴. استقرار روی Railway

این پروژه برای استقرار با یک کلیک در Railway کاملاً بهینه‌سازی شده است:
1. در پنل [Railway.app](https://railway.app) وارد شوید.
2. گزینه **New Project** و سپس **Deploy from GitHub repo** را انتخاب کرده و مخزن `miliconfig` را متصل کنید.
3. در همان پروژه یک سرویس **PostgreSQL** اضافه کنید.
4. Railway به صورت خودکار فایل `Dockerfile` و `railway.toml` را شناسایی می‌کند و متغیر `$PORT` را تنظیم می‌نماید.
5. متغیرهای محیطی زیر را در تب Variables تنظیم کنید:
   - `DATABASE_URL`: آدرس اتصال به دیتابیس پستگرس
   - `SECRET_KEY`: یک کلید امن تصادفی
   - `JWT_SECRET`: کلید امضای سشن‌های JWT
   - `ADMIN_PASSWORD`: رمز عبور دلخواه برای اکانت ادمین
6. پروژه شما به صورت خودکار بیلد و با دامین امن HTTPS در دسترس قرار می‌گیرد.

---

## ۵. متغیرهای محیطی (Environment Variables)

| نام متغیر | توضیحات | مقدار پیش‌فرض |
| :--- | :--- | :--- |
| `PORT` | پورت وب و رله ورودی | `8000` |
| `DATABASE_URL` | نشانی پایگاه‌داده (SQLite یا PostgreSQL) | `sqlite:///./miliconfig.db` |
| `SECRET_KEY` | کلید رمزنگاری داخلی | مقدار پیش‌فرض امن |
| `JWT_SECRET` | کلید امضای توکن سشن ادمین | مقدار پیش‌فرض |
| `ADMIN_USERNAME` | نام کاربری مدیر کل | `admin` |
| `ADMIN_PASSWORD` | رمز عبور مدیر کل | `miliconfig_admin_2026` |
| `PUBLIC_BASE_URL` | نشانی دامنه عمومی سرویس | `http://localhost:8000` |
| `DEFAULT_DOMAIN` | دامنه پیش‌فرض SNI و هاست | `localhost` |
| `ENABLE_SHADOWSOCKS` | فعال‌سازی سرور شدوساکس | `true` |
| `SS_PORT` | پورت شدوساکس | `8388` |
| `SS_DEFAULT_METHOD`| روش رمزنگاری پیش‌فرض شدوساکس | `chacha20-ietf-poly1305` |
| `OUTBOUND_MODE` | حالت خروجی ترافیک (`""`, `no`, `only`) | `""` |
| `OUTBOUND_PROXY` | آدرس پروکسی آپ‌استریم (`socks5://...`) | `""` |
| `DNS_SERVERS` | آدرس سرورهای DNS و DoH | `1.1.1.1,8.8.8.8,https://223.5.5.5/dns-query` |

---

## ۶. مهاجرت از `byjoey/cfnew`

اگر از پروژه قبلی `cfnew` استفاده می‌کردید و فایل JSON کانفیگ KV را دارید، با اسکریپت زیر می‌توانید تمام اطلاعات را به دیتابیس میلی‌کانفیگ منتقل کنید:

```bash
# مهاجرت از فایل بک‌آپ KV
python -m app.migrate_cfnew --file cfnew_kv_export.json

# یا مهاجرت از متغیرهای محیطی
python -m app.migrate_cfnew --from-env
```

این ابزار خودکار:
- کاربر مرتبط با UUID قبلی را می‌سازد.
- تمام ProxyIPها و تنظیمات DoH را منتقل می‌کند.
- نودهای مربوط به آدرس‌های ترجیحی را با پیشوند `miliconfig • ` ذخیره می‌نماید.

---

## ۷. تست‌ها و ارزیابی کیفیت

اجرای مجموعه کامل تست‌های خودکار:

```bash
python scripts/run_tests.py
```

تست‌های موجود شامل:
- `test_auth.py`: تست احراز هویت، هشینگ رمزها و توکن‌های JWT.
- `test_users.py`: چرخه حیات کاربر، ریست UUID، سهمیه ترافیک.
- `test_vless.py`: پارسر باینری پکت‌های VLESS و هدر پاسخ.
- `test_trojan.py`: هش SHA224 و پارسر تروجان.
- `test_shadowsocks.py`: رمزنگاری و تست یکپارچگی سرور شدوساکس.
- `test_subscription.py`: فرمت‌های کلش، سینگ‌باکس، بیس۶۴ و نام‌گذاری نودها.
- `test_dns.py`: تست رزولور DoH و کش DNS.
- `test_routing.py`: بررسی قوانین مسیریابی دامنه و CIDR.
- `test_proxyip.py`: مدیریت و سنجش تاخیر ProxyIP.
- `test_migration.py`: مهاجرت کامل کانفیگ‌های cfnew به دیتابیس جدید.

---

## ۸. لایسنس

این پروژه تحت لایسنس MIT منتشر شده است.
