import json
import os

# مسیر دقیق فایل کانفیگ سایت روی مک شما
SITE_DATA_PATH = "/Users/negin-payam/projects/jarbezan/Ads_client/site_data.json"

def update_site_data(key: str, value: str) -> str:
    """
    این ابزار اطلاعات سایت مثل شماره تماس، ایمیل یا آدرس را ویرایش می‌کند.
    
    :param key: نام کلید برای تغییر (مثلاً phone, email, address)
    :param value: مقدار جدید
    """
    if not os.path.exists(SITE_DATA_PATH):
        return f"خطا: فایل داده‌های سایت در مسیر {SITE_DATA_PATH} پیدا نشد."

    try:
        with open(SITE_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        data[key] = value

        with open(SITE_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return f"تغییر انجام شد: {key} به '{value}' تغییر یافت."
    except Exception as e:
        return f"خطا در ویرایش: {str(e)}"