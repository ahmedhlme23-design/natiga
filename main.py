import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# -------------------------------------------------------------
# البيانات والتهيئات الخاصة بالمشروع
# -------------------------------------------------------------
BOT_TOKEN = "8703972510:AAH0ttSDYJD0mMZlxgxiuPF7mzgdBbNCn7k"
SUPABASE_URL = "https://zaycmrniwffsakzbvesb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpheWNtcm5pd2Zmc2FremJ2ZXNiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODUyNjk0NTgsImV4cCI6MjEwMDg0NTQ1OH0.jW37BJ9cRZWk3OSo27GpFco-4urM0gY8t-azJ5uRzDs"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -------------------------------------------------------------
# الدوال المساعدة للربط مع Supabase
# -------------------------------------------------------------
def search_by_seating_no(seating_no: int):
    """البحث بواسطة رقم الجلوس"""
    url = f"{SUPABASE_URL}/rest/v1/student_results?seating_no=eq.{seating_no}&select=*"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data if data else None
    return None

def search_by_name(name_query: str):
    """البحث بواسطة الاسم (يحتوي على الكلمة)"""
    url = f"{SUPABASE_URL}/rest/v1/student_results?arabic_name=ilike.*{name_query}*&select=*&limit=10"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    return []

def get_student_by_id(student_id: int):
    """جلب بيانات طالب محدد بواسطة ID الخاص به"""
    url = f"{SUPABASE_URL}/rest/v1/student_results?id=eq.{student_id}&select=*"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        return data[0] if data else None
    return None

def format_result_message(student: dict) -> str:
    """تنسيق رسالة عرض النتيجة بالهيكل المطلوب"""
    name = student.get("arabic_name", "غير محدد")
    seating_no = student.get("seating_no", "غير محدد")
    total_degree = float(student.get("total_degree", 0))
    case_desc = student.get("student_case_desc", "غير محدد")
    
    # حساب النسبة المئوية من المجموع الكلي (320)
    percentage = (total_degree / 320.0) * 100

    msg = (
        f"📊 **نتيجة الثانوية العامة 2026**\n\n"
        f"👤 **الاسم:** {name}\n"
        f"🔢 **رقم الجلوس:** `{seating_no}`\n"
        f"📈 **الدرجة الكلية:** {total_degree} / 320\n"
        f"💯 **النسبة المئوية:** {percentage:.2f}%\n"
        f"📌 **الحالة:** {case_desc}\n"
    )
    return msg

# -------------------------------------------------------------
# معالجة أوامر البوت والأحداث
# -------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عند ضغط زر ابدأ أو كتابة /start"""
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت نتائج الثانوية العامة 2026! 🎓\n\n"
        f"من فضلك أرسل **رقم الجلوس** (مكون من 7 أرقام) أو **اسم الطالب** للبحث عن النتيجة."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة كافة النصوص المدخلة من المستخدم"""
    text = update.message.text.strip()

    # 1. التحقق إذا كان المدخل رقم جلوس (أرقام فقط)
    if text.isdigit():
        if len(text) != 7:
            await update.message.reply_text("⚠️ يجب أن يكون رقم الجلوس مكوناً من 7 أرقام بالضبط.")
            return

        # البحث برقم الجلوس
        results = search_by_seating_no(int(text))
        if results:
            student = results[0]
            msg = format_result_message(student)
            keyboard = [[InlineKeyboardButton("🔍 بحث عن نتيجة أخرى", callback_data="search_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                "❌ هذه النتيجة غير موجودة حالياً في قاعدة البيانات أو أن رقم الجلوس خطأ. من فضلك أعد إدخال البيانات صحيحة."
            )

    # 2. إذا كان المدخل اسماً
    else:
        words = text.split()
        if len(words) < 2:
            await update.message.reply_text("⚠️ لا يمكن البحث باسم أقل من اسمين، يرجى كتابة اسم الطالب ثنائياً على الأقل.")
            return

        results = search_by_name(text)
        if not results:
            await update.message.reply_text(
                "❌ هذه النتيجة غير موجودة حالياً في قاعدة البيانات أو أن الاسم خطأ. من فضلك أعد إدخال البيانات صحيحة."
            )
            return

        # إذا كانت هناك نتائج، يتم عرضها على هيئة أزرار
        keyboard = []
        for student in results:
            btn_text = f"👤 {student['arabic_name']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"show_std_{student['id']}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🔎 وجدنا النتائج التالية، اختر الاسم المطلوب لمشاهدة التفاصيل:", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغطات الأزرار التفاعلية"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "search_again":
        await query.message.reply_text("يرجى إرسال **اسم الطالب** (اسمين على الأقل) أو **رقم الجلوس** (7 أرقام):", parse_mode="Markdown")

    elif data.startswith("show_std_"):
        student_id = int(data.split("_")[-1])
        student = get_student_by_id(student_id)

        if student:
            msg = format_result_message(student)
            keyboard = [[InlineKeyboardButton("🔍 بحث عن نتيجة أخرى", callback_data="search_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ حدث خطأ، تعذر جلب بيانات الطالب.")

# -------------------------------------------------------------
# تشغيل التطبيق
# -------------------------------------------------------------
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()