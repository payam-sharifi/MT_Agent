# 🤖 Hermes Agent Skill - راهنمای فارسی

## ✨ چی ساخته شد؟

یک **Skill کامل برای Cursor Agent** به نام **Hermes** که می‌تونه:

1. با کاربر به **زبان ساده فارسی/انگلیسی** حرف بزنه
2. منظور کاربر رو **درک کنه** (NLP)
3. APIهای **easyWebBuilder** رو بشناسه و **call کنه**
4. **Preview workflow** رو مدیریت کنه
5. پاسخ‌های **فارسی روان** بده

---

## 📍 مکان Skill

```
/Users/negin-payam/.cursor/skills/hermes-easyweb-chat/SKILL.md
```

---

## 🎯 قابلیت‌های Skill

### ۱. درک زبان طبیعی (NLP)

Agent می‌تونه این جورایی حرف‌ها رو بفهمه:

```
✅ "عنوان سایتم رو به فروشگاه من تغییر بده"
✅ "متن صفحه اصلی رو عوض کن"
✅ "لوگوی جدید: https://example.com/logo.png"
✅ "وضعیت سایتم چطوره؟"
✅ "تایید"
✅ "لغو"
```

### ۲. API Integration

Skill شامل اطلاعات کامل همه APIهای backend:

#### Content Management:
- `POST /api/agent/update-site` - ایجاد تغییرات
- `GET /api/agent/site-data` - دریافت محتوا
- `POST /api/agent/read-site` - خواندن یک key خاص

#### Preview Management:
- `GET /api/agent/pending-changes` - لیست تغییرات در انتظار
- `POST /api/agent/pending-changes/:id/approve` - تایید
- `POST /api/agent/pending-changes/:id/reject` - رد

### ۳. Key Mappings (فارسی → انگلیسی)

```typescript
'عنوان' → 'site_title'
'متن صفحه اصلی' → 'homepage_text'
'لوگو' → 'logo'
'ایمیل' → 'contact_email'
'تلفن' → 'contact_phone'
...
```

### ۴. Response Templates

پیام‌های آماده به فارسی:

```
🔍 پیش‌نمایش آماده شد!
✅ تغییرات منتشر شد!
❌ تغییرات لغو شد.
📊 وضعیت سایت شما:
```

---

## 💬 مثال‌های مکالمه

### مثال ۱: تغییر ساده

```
👤 کاربر: "سلام hermes"
🤖 Agent: "سلام! چطور می‌تونم کمکتون کنم؟ 😊"

👤 کاربر: "عنوان سایتم رو عوض کن"
🤖 Agent: "حتما! عنوان جدید رو بهم بگید."

👤 کاربر: "فروشگاه آنلاین من"
🤖 Agent: 
    [Call API: POST /api/agent/update-site]
    "🔍 پیش‌نمایش آماده شد!
    
    عنوان سایت → فروشگاه آنلاین من
    
    پیش‌نمایش: http://localhost:3000/preview/mysite/123
    
    برای انتشار بگید: تایید"

👤 کاربر: "تایید"
🤖 Agent:
    [Call API: POST /api/agent/pending-changes/{id}/approve]
    "✅ تغییرات منتشر شد!
    سایت شما به‌روزرسانی شد. 🎉"
```

### مثال ۲: چک وضعیت

```
👤 کاربر: "سایتم چطوره؟"
🤖 Agent:
    [Call API: GET /api/agent/site-data]
    [Call API: GET /api/agent/pending-changes]
    
    "📊 وضعیت سایت شما:
    
    🌐 آدرس: mysite.easyweb.builder
    ✅ وضعیت: فعال
    📝 عنوان فعلی: فروشگاه آنلاین من
    ⏳ تغییرات در انتظار: 0
    
    چیز دیگه‌ای می‌خواید؟"
```

### مثال ۳: تغییرات چندگانه

```
👤 کاربر: "می‌خوام چند تا چیز رو عوض کنم"
🤖 Agent: "بفرمایید، چه تغییراتی می‌خواید؟"

👤 کاربر: "اول عنوان: فروشگاه من
           بعد متن صفحه اصلی: به فروشگاه خوش اومدید
           و ایمیل: info@myshop.com"

🤖 Agent: "فهمیدم! سه تغییر:
          1. عنوان → فروشگاه من
          2. متن صفحه اصلی → به فروشگاه...
          3. ایمیل → info@myshop.com
          
          می‌خواید همه رو با هم اعمال کنم؟"

👤 کاربر: "آره"
🤖 Agent: [Process 3 updates + send previews]
```

---

## 🔧 ساختار Skill

### ۱. API Reference کامل

تمام endpoint ها با:
- متد HTTP
- URL
- Headers
- Body مثال
- Response مثال
- زمان استفاده

### ۲. Natural Language Processing

راهنمای پردازش جملات فارسی:
- تشخیص intent (update, approve, reject, status)
- استخراج key و value
- مدیریت ambiguity

### ۳. Conversation Flow Examples

سناریوهای واقعی مکالمه با:
- پیام‌های کاربر
- API calls
- پاسخ‌های agent

### ۴. Error Handling

مدیریت خطاهای رایج:
- Authentication failed
- Preview expired
- Invalid key
- Server error

### ۵. Key Mappings

نقشه کامل واژه‌های فارسی به keys انگلیسی

### ۶. Response Templates

قالب‌های آماده پیام‌های فارسی

---

## 📚 کلیدهای معتبر (Content Keys)

```typescript
// محتوا
site_title         // عنوان سایت
site_description   // توضیحات
homepage_text      // متن صفحه اصلی
about_text         // درباره ما
contact_email      // ایمیل
contact_phone      // تلفن

// طراحی
logo              // آدرس لوگو
primary_color     // رنگ اصلی
theme             // تم (light/dark)

// تنظیمات
language          // زبان (fa/en)
timezone          // منطقه زمانی
```

---

## 🚀 چطور استفاده کنم؟

### در Cursor Chat:

1. **بگو: "@hermes-easyweb-chat"** تا skill فعال بشه

2. **بعد بگو چی می‌خوای:**
   ```
   "یک agent بساز که با کاربر چت کنه"
   "کد پردازش پیام واتساپ رو بنویس"
   "تابع parse کردن intent رو ایجاد کن"
   ```

3. **Cursor از skill استفاده می‌کنه** و:
   - راهنماها رو می‌خونه
   - API calls درست می‌نویسه
   - Key mappings رو اعمال می‌کنه
   - Response templates رو استفاده می‌کنه

---

## 💡 مثال‌های درخواست از Cursor

### درخواست ۱: پردازش پیام
```
@hermes-easyweb-chat
یک تابع بنویس که پیام فارسی کاربر رو بگیره و intent رو تشخیص بده
```

→ Cursor کدی می‌نویسه که:
- جمله رو parse می‌کنه
- تشخیص می‌ده update/approve/reject/status
- key و value رو extract می‌کنه

### درخواست ۲: API Call
```
@hermes-easyweb-chat
کدی بنویس که عنوان سایت رو به‌روزرسانی کنه
```

→ Cursor:
```typescript
async function updateSiteTitle(title: string, token: string) {
  const response = await fetch('http://localhost:3000/api/agent/update-site', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      key: 'site_title',
      value: title,
      operation: 'set'
    })
  });
  return await response.json();
}
```

### درخواست ۳: Conversation Handler
```
@hermes-easyweb-chat
یک handler کامل برای مدیریت مکالمه با کاربر بنویس
```

→ Cursor یک handler کامل با:
- Intent detection
- API calls
- Response formatting
- Error handling
- Conversation context

---

## 🎨 ویژگی‌های خاص

### ۱. دوزبانه (Bilingual)
- پشتیبانی کامل فارسی و انگلیسی
- Key mappings برای واژه‌های فارسی
- Response templates به دو زبان

### ۲. Context-Aware
- نگه داشتن context مکالمه
- پیگیری topic های قبلی
- پاسخ به سوالات follow-up

### ۳. Error Recovery
- مدیریت خطاها
- پیام‌های راهنما
- پیشنهاد اصلاح

### ۴. User Guidance
- راهنمایی گام به گام
- مثال‌های واضح
- تایید قبل از عملیات مخرب

---

## 📖 مستندات داخل Skill

### API Endpoints (15+ endpoint)
```
✅ Authentication
✅ Content Management
✅ Preview Management
✅ Status Checking
✅ User Management
```

### NLP Patterns (20+ pattern)
```
✅ Update requests
✅ Status checks
✅ Approvals/Rejections
✅ Help requests
✅ Ambiguity handling
```

### Response Templates (30+ template)
```
✅ Success messages
✅ Error messages
✅ Confirmation prompts
✅ Status reports
✅ Help texts
```

### Conversation Flows (10+ scenario)
```
✅ New user onboarding
✅ Simple update
✅ Multiple updates
✅ Status check
✅ Error recovery
```

---

## ✅ چک‌لیست استفاده

قبل از شروع:
- [x] Skill در مسیر درست نصب شده
- [x] Backend در حال اجرا است
- [x] Database متصل است
- [ ] Agent Hermes آماده است

برای تست:
- [ ] با Cursor chat باز کن
- [ ] Skill رو mention کن: @hermes-easyweb-chat
- [ ] یک درخواست بده
- [ ] کد تولید شده رو بررسی کن

---

## 🎯 نتیجه

الان یک **راهنمای کامل ۴۰۰+ خطی** داری که به Agent Hermes می‌گه:

✅ چطور با کاربر حرف بزنه  
✅ چطور API ها رو call کنه  
✅ چطور پیام‌های فارسی رو parse کنه  
✅ چطور preview workflow رو مدیریت کنه  
✅ چطور خطاها رو handle کنه  

**همه چیز آماده است!** 🚀

---

## 🔗 لینک‌های مرتبط

- **Skill File**: `/Users/negin-payam/.cursor/skills/hermes-easyweb-chat/SKILL.md`
- **Backend API Docs**: `GIT_PREVIEW_WORKFLOW.md`
- **User Registration**: `USER_REGISTRATION_GUIDE.md`
- **Database**: `DATABASE_SETUP_COMPLETE.md`

---

