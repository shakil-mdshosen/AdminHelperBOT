# AdminHelperBot

বাংলা উইকিপিডিয়ার **[উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা](https://bn.wikipedia.org/wiki/উইকিপিডিয়া:প্রশাসকদের_আলোচনাসভা)** পাতার জন্য একটি সহায়ক বট। বটটি শুধু এই একটি পাতাতেই সম্পাদনা করে।

*A helper bot for the Bangla Wikipedia administrators' noticeboard. English notes are at the end.*

## বট কী করে

বটটি প্রতি ৫ মিনিট পরপর পাতার প্রতিটি অনুরোধ (প্রতিটি শিরোনাম) পরীক্ষা করে।

### ১. সম্পন্ন কিন্তু চিহ্নিত নয় এমন অনুরোধ

রিপোর্ট করা **সব** অ্যাকাউন্ট (নিবন্ধিত, অস্থায়ী বা আইপি) যদি

* স্থানীয় প্রশাসক কর্তৃক বাধাপ্রাপ্ত হয়, **অথবা**
* স্টুয়ার্ড কর্তৃক বৈশ্বিকভাবে লক (global lock) হয়, **অথবা**
* স্টুয়ার্ড কর্তৃক বৈশ্বিকভাবে বাধাপ্রাপ্ত (global block) হয়,

এবং শেষ পদক্ষেপের পর **১০ মিনিট** পেরিয়ে গেলেও কেউ অনুরোধটি চিহ্নিত না করেন, তাহলে বট অনুচ্ছেদের শেষে যোগ করে:

```
ADMINUSERNAME কর্তৃক {{করা হয়েছে}} <small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~
{{subst:সহঅ}}
```

`ADMINUSERNAME` হলো যে প্রশাসক বা স্টুয়ার্ড পদক্ষেপ নিয়েছেন তাঁর নাম। একাধিক জন হলে: `ক, খ ও গ কর্তৃক …`।

### ২. অস্থায়ী অ্যাকাউন্টের বাসি (stale) অনুরোধ

রিপোর্ট করা অস্থায়ী অ্যাকাউন্টের বিরুদ্ধে যদি রিপোর্টের **৭২ ঘণ্টার** মধ্যে কোনো প্রশাসক বা স্টুয়ার্ড পদক্ষেপ না নেন **এবং** অ্যাকাউন্টটি থেকে গত **৬০ ঘণ্টায়** কোনো সম্পাদনা না হয়, তাহলে বট লেখে:

```
বাধা দেওয়ার প্রয়োজন নেই, অস্থায়ী অ্যাকাউন্ট থেকে সর্বশেষ সম্পাদনা ২০ সেপ্টেম্বর ২০২৬, ০৯:১৫ (ইউটিসি) টায় হয়েছে। <small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~
```

### সময়ের হিসাব

| নিয়ম | কখন থেকে গোনা হয় | কখন বট কাজ করে |
|---|---|---|
| সম্পন্ন চিহ্নিতকরণ | শেষ বাধা/লকের লগ-সময় (অথবা রিপোর্টের সময়, যেটি পরে) | ঠিক +১০ মিনিটে |
| বাসি অনুরোধ | রিপোর্টের স্বাক্ষরের সময় ও অস্থায়ী অ্যাকাউন্টের শেষ সম্পাদনা | `max(রিপোর্ট + ৭২ ঘণ্টা, শেষ সম্পাদনা + ৬০ ঘণ্টা)` |

* সব সময় **উইকির সার্ভারের ঘড়ি** (API-এর `curtimestamp`) ব্যবহার করা হয়, বট যে কম্পিউটারে চলে তার ঘড়ি নয়।
* বট প্রতি ৫ মিনিটে পাতা দেখে, তবে কোনো অনুরোধের সময় ৫ মিনিটের আগেই পূর্ণ হলে বট ঠিক সেই সময়েই (+৫ সেকেন্ড) জেগে ওঠে — তাই ১০ মিনিটের অপেক্ষা ১০ মিনিটই থাকে, ১৫ মিনিট হয়ে যায় না।
* রিপোর্টের সময় = অনুচ্ছেদের প্রথম স্বাক্ষরের সময় (বাংলা/ইংরেজি দুই ধরনের স্বাক্ষরই বোঝে)।

### নিরাপত্তা

* যে অনুরোধে আগে থেকেই `{{করা হয়েছে}}`, `{{করা হয়নি}}`, `{{সহঅ}}` বা এদের যেকোনো পুনর্নির্দেশ আছে, বট সেটি ছোঁয় না। চালু হওয়ার সময় বট উইকি থেকে এই টেমপ্লেটগুলোর পুনর্নির্দেশ ও `{{subst:সহঅ}}`-এর ফলাফল নিজে শিখে নেয়।
* শুধু বাধাদান-সংক্রান্ত অনুরোধ বিবেচনা করা হয় (শিরোনাম/প্রথম মন্তব্যে "বাধা", "ব্লক", "লক", "ধ্বংসপ্রবণ" ইত্যাদি শব্দ বা `{{userlinks}}`-জাতীয় টেমপ্লেট থাকলে)।
* রিপোর্টকারীর স্বাক্ষর বা পরের উত্তরগুলোতে থাকা ব্যবহারকারী নাম "রিপোর্ট করা অ্যাকাউন্ট" হিসেবে ধরা হয় না।
* রিপোর্টের অনেক আগের (৬০ মিনিটের বেশি পুরোনো) বাধাকে এই অনুরোধের উত্তর ধরা হয় না; আংশিক পদক্ষেপ (কিছু অ্যাকাউন্ট বাধাপ্রাপ্ত, কিছু নয়) হলেও বট কিছু করে না — মানুষের সিদ্ধান্তের জন্য রেখে দেয়।
* সম্পাদনা-দ্বন্দ্ব (edit conflict) শনাক্ত করা হয় (`basetimestamp`/`starttimestamp`); দ্বন্দ্ব হলে নতুন লেখা নিয়ে আবার চেষ্টা করে।
* প্রতিটি সম্পাদনা `bot=1`, `assert=bot`, `maxlag=5` সহ হয় এবং প্রতিটির বিস্তারিত বাংলা সম্পাদনা সারাংশ থাকে, যেমন:
  > /\* ব্যবহারকারী বাধাদানের অনুরোধ \*/ বট: অনুরোধটি সম্পন্ন হিসেবে চিহ্নিত ও সংগ্রহশালাভুক্তির জন্য প্রস্তুত করা হলো — Vandal Account-কে প্রশাসক Admin A স্থানীয়ভাবে বাধা দিয়েছেন (২৩ সেপ্টেম্বর ২০২৬, ১২:৫২ (ইউটিসি))। পদক্ষেপ নেওয়ার ১০ মিনিট পরেও কেউ চিহ্নিত না করায় স্বয়ংক্রিয়ভাবে {{করা হয়েছে}} ও {{সহঅ}} যোগ করা হয়েছে। (স্বয়ংক্রিয় সম্পাদনা)
* **জরুরি বন্ধ:** `run_page` (যেমন `ব্যবহারকারী:AdminHelperBot/চালু`) পাতায় "চালু" না লেখা থাকলে বট কোনো সম্পাদনা করে না। যেকোনো প্রশাসক পাতাটি সম্পাদনা করে বট থামাতে পারেন।

## চালানোর নিয়ম

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp config.example.json config.json          # প্রয়োজনে সম্পাদনা করুন

# বিশেষ:BotPasswords থেকে পাসওয়ার্ড তৈরি করুন
# (অনুমতি: "Basic rights", "Edit existing pages", "High-volume editing")
export ADMINHELPERBOT_USERNAME='AdminHelperBot@AdminHelperBot'
export ADMINHELPERBOT_PASSWORD='...'

venv/bin/python -m adminhelperbot -c config.json --once --dry-run   # শুধু দেখায়, সম্পাদনা করে না
venv/bin/python -m adminhelperbot -c config.json --once             # একবার চালায় (cron-এর জন্য)
venv/bin/python -m adminhelperbot -c config.json                    # নিরবচ্ছিন্নভাবে চলে (প্রস্তাবিত)
```

বট ফ্ল্যাগ পাওয়ার আগে পরীক্ষামূলক চালানোর সময় `config.json`-এ `"assert_mode": "user"` দিন।

**Toolforge:** `jobs.yaml` দেখুন (`toolforge jobs load jobs.yaml`)। পরিচয়পত্র `toolforge envvars create` দিয়ে রাখুন।

### পরীক্ষা (tests)

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

টেস্টগুলো একটি নকল উইকি (`tests/fakewiki.py`) ব্যবহার করে প্রতিটি সময়-সীমা সেকেন্ড পর্যন্ত যাচাই করে (৯:৫৯ মিনিটে কিছু না করা, ঠিক ১০:০০ মিনিটে চিহ্নিত করা; ৭২ ঘণ্টা/৬০ ঘণ্টার সীমা ইত্যাদি)।

## কনফিগারেশন

সব মান `adminhelperbot/config.py`-এ আছে; JSON ফাইল দিয়ে যেকোনোটি বদলানো যায়। গুরুত্বপূর্ণ কয়েকটি:

| কী | ডিফল্ট | অর্থ |
|---|---|---|
| `done_grace_minutes` | 10 | পদক্ষেপের পর কত মিনিট অপেক্ষা |
| `stale_no_action_hours` | 72 | রিপোর্টের পর কত ঘণ্টা পদক্ষেপহীন থাকলে বাসি |
| `stale_inactivity_hours` | 60 | অস্থায়ী অ্যাকাউন্ট কত ঘণ্টা নিষ্ক্রিয় থাকলে বাসি |
| `reply_indent` | `""` | উত্তরের শুরুতে `:` চাইলে এখানে দিন |
| `automated_note` | `<small>(স্বয়ংক্রিয় বট বার্তা)</small>` | স্বয়ংক্রিয় কার্যক্রমের উল্লেখ |
| `stale_add_archive_template` | false | বাসি অনুরোধেও `{{subst:সহঅ}}` যোগ করা হবে কি না |
| `display_tz_offset_minutes` / `display_tz_label` | 0 / ইউটিসি | শেষ সম্পাদনার সময় কোন সময়-অঞ্চলে লেখা হবে (বাংলাদেশ সময়: 360 / বাংলাদেশ সময়) |
| `run_page` | null | জরুরি বন্ধের পাতা |

---

## English summary

* Runs only on `উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা`, checking every 5 minutes.
* **Done rule:** when every account reported in a section is locally blocked, globally locked or globally blocked, and nobody has marked the section 10 minutes after the last action, the bot appends `ACTOR কর্তৃক {{করা হয়েছে}} … --~~~~` and `{{subst:সহঅ}}`. ACTOR comes from the block list / global lock log (meta) / global block list.
* **Stale rule:** for temporary accounts with no block/lock at all, once 72 h have passed since the report and 60 h since the account's last edit, the bot posts the "no block needed" message with the last edit time in Bangla.
* Server time is used everywhere; the scheduler wakes up exactly when a request becomes due.
* Code layout: `parser.py` (sections, reported accounts, closed markers), `status.py` (API lookups), `logic.py` (pure timing rules), `messages.py` (Bangla texts and summaries), `bot.py` (main loop, safe edits), `api.py` (MediaWiki API client).
