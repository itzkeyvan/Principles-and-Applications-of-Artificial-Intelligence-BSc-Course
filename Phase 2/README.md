# PlanForge — پروژه ارضای قید برای تولید پلان آپارتمان

در این پروژه شما هسته‌ی یک حل‌کننده‌ی CSP را برای چیدن اتاق‌های یک آپارتمان پیاده‌سازی می‌کنید. بخش‌های رابط گرافیکی، خواندن فایل‌های JSON، ساخت دامنه‌ها، اعتبارسنجی نهایی و نمایش پلان آماده است. شما فقط باید فایل‌های داخل پوشه‌ی `student/` را کامل کنید.

## اجرای برنامه

```bash
python run_app.py
```

در ویندوز می‌توانید روی `run_windows.bat` دابل‌کلیک کنید.

## اجرای public self-check

```bash
python run_public_grade.py
```

این public grader فقط برای بازخورد گرفتن است و نمره‌ی نهایی نیست. نمره‌ی نهایی با private grader و تست‌های مخفی محاسبه می‌شود.

## فایل‌هایی که باید کامل کنید

فقط این فایل‌ها را تغییر دهید:

- `student/solver.py`
- `student/consistency.py`
- `student/heuristics.py`
- `student/inference.py`
- `student/scoring.py`

## بخش‌های اجباری

بخش اجباری از ۱۰۰ نمره است و شامل این موارد می‌شود:

- پیاده‌سازی `solve`، `backtrack` و `is_complete` با backtracking بازگشتی.
- استفاده از `ctx` برای ثبت آمار اجرای الگوریتم، مثل `ctx.on_node()` و `ctx.on_solution(...)`.
- پیاده‌سازی `is_consistent` برای بررسی قیود سخت.
- پیاده‌سازی MRV در `select_unassigned_variable`.
- پیاده‌سازی LCV در `order_domain_values`.
- تولید جواب معتبر برای نمونه‌های ساده و متوسط.
- تشخیص مسئله‌ی بدون جواب.

## بخش‌های اختیاری و امتیازی

بخش اختیاری ۳۰ نمره دارد و برای دانشجویانی است که می‌خواهند solver قوی‌تری بسازند:

- پیاده‌سازی `forward_check`.
- پیاده‌سازی `AC-3`.
- پیاده‌سازی `score_assignment` برای انتخاب پلان بهتر بین چند جواب معتبر.
- جست‌وجوی چند جواب معتبر و انتخاب بهترین جواب.
- تولید پلان‌هایی با کیفیت بالاتر، coverage بهتر و دسترسی منطقی‌تر فضاها.

## نکته مهم درباره تحویل

در زمان نمره‌دهی، فقط پوشه‌ی `student/` شما روی یک نسخه‌ی تمیز از پروژه تست می‌شود. بنابراین تغییر دادن فایل‌های `planforge/`، فایل‌های example یا grader در نمره‌ی نهایی اثری ندارد و ممکن است تخلف محسوب شود.


## Bonus challenge case

The public self-check includes `planforge/examples/bonus_challenge_apartment.json` as a visible optional stress test. It is designed to reward strong optimization, pruning, and soft scoring under finite search limits. Passing the required cases is not enough for full optional credit.

## Visual solve mode

The desktop app includes a separate **Visual solve** button. This mode runs your real solver with tracing enabled, then replays the recorded backtracking steps on the apartment canvas. The delay box controls the pause between animation steps in milliseconds.

For the animation to show your actual search path, call these optional tracing hooks in `student/solver.py`:

- `ctx.on_select_variable(variable, assignment)` after choosing the next variable.
- `ctx.on_assign(variable, value, assignment)` right after assigning a value.
- `ctx.on_unassign(variable, assignment)` after removing a value during backtracking.

These hooks do not change correctness or grading by themselves, but they make the visualizer accurately show how your own algorithm explores the search tree.
