# AdminHelperBot

[![tests](https://github.com/shakil-mdshosen/AdminHelperBOT/actions/workflows/tests.yml/badge.svg)](https://github.com/shakil-mdshosen/AdminHelperBOT/actions/workflows/tests.yml)

বাংলা উইকিপিডিয়ার **[উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা](https://bn.wikipedia.org/wiki/উইকিপিডিয়া:প্রশাসকদের_আলোচনাসভা)** পাতার জন্য একটি সহায়ক বট। বাধাদানের যেসব অনুরোধে প্রশাসক বা স্টুয়ার্ড ইতিমধ্যে পদক্ষেপ নিয়েছেন কিন্তু অনুরোধটি চিহ্নিত করা হয়নি, সেগুলো বট সম্পন্ন হিসেবে চিহ্নিত করে। অস্থায়ী অ্যাকাউন্টের বিরুদ্ধে যেসব অনুরোধ বাসি হয়ে গেছে, সেগুলোও বন্ধ করে। বট শুধু এই একটি পাতাতেই সম্পাদনা করে।

*A helper bot for the Bangla Wikipedia administrators' noticeboard. [English summary below](#english).*

| নথি | বিষয়বস্তু |
|---|---|
| **[docs/how-it-works.md](docs/how-it-works.md)** | বট কীভাবে কাজ করে: প্রতিটি ধাপ, নিয়ম, সময়ের হিসাব, আসল পাতায় আচরণ |
| **[docs/deployment.md](docs/deployment.md)** | বট অ্যাকাউন্ট, বট পাসওয়ার্ড, Toolforge, পর্যবেক্ষণ, সমস্যা সমাধান |

## বট কী করে

বট প্রতি ৫ মিনিটে পাতার প্রতিটি অনুরোধ পরীক্ষা করে।

### ১. সম্পন্ন কিন্তু চিহ্নিত নয়

রিপোর্ট করা **সব** অ্যাকাউন্ট (নিবন্ধিত, অস্থায়ী বা আইপি) যদি স্থানীয় প্রশাসক কর্তৃক **বাধাপ্রাপ্ত**, স্টুয়ার্ড কর্তৃক **বৈশ্বিকভাবে লক** বা **বৈশ্বিকভাবে বাধাপ্রাপ্ত** হয়, এবং শেষ পদক্ষেপের **১০ মিনিট** পরেও কেউ অনুরোধটি চিহ্নিত না করেন, তাহলে বট লেখে:

```
Ferdous কর্তৃক {{করা হয়েছে}} <small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~
{{subst:সহঅ}}
```

নামটি হলো যিনি পদক্ষেপ নিয়েছেন সেই প্রশাসক বা স্টুয়ার্ড। একাধিক জন হলে `Steward X ও Yahya কর্তৃক …`।

### ২. বাসি অস্থায়ী অ্যাকাউন্ট

রিপোর্ট করা অস্থায়ী অ্যাকাউন্টের বিরুদ্ধে রিপোর্টের **৭২ ঘণ্টায়** কোনো পদক্ষেপ না নেওয়া হলে **এবং** অ্যাকাউন্টটি থেকে **৬০ ঘণ্টা** ধরে কোনো সম্পাদনা না হলে বট লেখে:

```
বাধা দেওয়ার প্রয়োজন নেই, অস্থায়ী অ্যাকাউন্ট থেকে সর্বশেষ সম্পাদনা ২১ জুন ২০২৬, ১১:৫০ (ইউটিসি) টায় হয়েছে। <small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~
{{subst:সহঅ}}
```

### প্রতিটি সম্পাদনার সারাংশ (উদাহরণ)

> /\* বাধাদানের অনুরোধ: Swarup Das Official \*/ বট: অনুরোধটি সম্পন্ন হিসেবে চিহ্নিত ও সংগ্রহশালাভুক্তির জন্য প্রস্তুত করা হলো — Swarup Das Official-কে প্রশাসক Ferdous স্থানীয়ভাবে বাধা দিয়েছেন (২৩ সেপ্টেম্বর ২০২৬, ০৫:৫০ (ইউটিসি))। পদক্ষেপ নেওয়ার ১০ মিনিট পরেও কেউ চিহ্নিত না করায় স্বয়ংক্রিয়ভাবে {{করা হয়েছে}} ও {{সহঅ}} যোগ করা হয়েছে। (স্বয়ংক্রিয় সম্পাদনা)

## সময়ের নিয়ম

| নিয়ম | কখন কাজ করে |
|---|---|
| সম্পন্ন | `max(রিপোর্টের সময়, শেষ পদক্ষেপের সময়) + ১০ মিনিট` |
| বাসি | `max(রিপোর্টের সময় + ৭২ ঘণ্টা, শেষ সম্পাদনা + ৬০ ঘণ্টা)` |

* সব হিসাব **উইকি সার্ভারের ঘড়ি** ধরে, UTC-তে।
* বট প্রতি ৫ মিনিটে দেখে, তবে কোনো অনুরোধের সময় তার আগেই পূর্ণ হলে বট ঠিক সেই মুহূর্তে (+৫ সেকেন্ড) জেগে কাজ করে। তাই ১০ মিনিট মানে ১০ মিনিটই।
* রিপোর্টের সময় = রিপোর্টকারীর স্বাক্ষরের সময়।
* প্রতিটি সীমা সেকেন্ড পর্যন্ত পরীক্ষিত (৯:৫৯-এ কিছু না, ১০:০০-এ কাজ)।

## বট কখন কিছু করে না

* অনুচ্ছেদে আগে থেকেই `{{সমাধান হওয়া অনুচ্ছেদ}}`, `{{করা হয়েছে}}`, `{{করা হয়নি}}`, `{{done}}` ইত্যাদি বা এদের পুনর্নির্দেশ থাকলে।
* অনুরোধটি বাধাদানের না হলে (যেমন টেমপ্লেট তৈরি, পাতা পুনরুদ্ধার, অপসারণ প্রস্তাবনা নিয়ে অভিযোগ)।
* রিপোর্ট করা অ্যাকাউন্টের কিছুতে পদক্ষেপ হয়েছে, কিছুতে হয়নি।
* বাধাটি রিপোর্টের অনেক আগের হলে (৬০ মিনিটের বেশি)।
* নিবন্ধিত অ্যাকাউন্টে কোনো পদক্ষেপ না হলে (বাসি নিয়ম শুধু অস্থায়ী অ্যাকাউন্টের জন্য)।
* জরুরি বন্ধের পাতায় "চালু" না থাকলে।

বট উপরের সব নিয়ম আলোচনাসভার আসল পাতার অনুলিপিতে পরীক্ষা করে ([tests/test_real_page.py](tests/test_real_page.py))।

## দ্রুত শুরু

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp config.example.json config.json

export ADMINHELPERBOT_USERNAME='AdminHelperBot@AdminHelperBot'   # বিশেষ:BotPasswords
export ADMINHELPERBOT_PASSWORD='…'

venv/bin/python -m adminhelperbot -c config.json --once --dry-run   # শুধু দেখায়, সম্পাদনা করে না
venv/bin/python -m adminhelperbot -c config.json                    # নিরবচ্ছিন্নভাবে চলে
```

বিস্তারিত (বট ফ্ল্যাগ, Toolforge, সমস্যা সমাধান): **[docs/deployment.md](docs/deployment.md)**।

## কনফিগারেশন

সব মান [`adminhelperbot/config.py`](adminhelperbot/config.py)-এ আছে; JSON ফাইল (`-c config.json`) দিয়ে যেকোনোটি বদলানো যায়। অজানা কী দিলে বট চালু হয় না, তাই বানান ভুল ধরা পড়ে।

| কী | ডিফল্ট | অর্থ |
|---|---|---|
| `check_interval_minutes` | 5 | কত মিনিট পরপর পাতা দেখা হবে |
| `done_grace_minutes` | 10 | পদক্ষেপের পর কত মিনিট অপেক্ষা |
| `stale_no_action_hours` | 72 | রিপোর্টের পর কত ঘণ্টা পদক্ষেপহীন থাকলে বাসি |
| `stale_inactivity_hours` | 60 | অস্থায়ী অ্যাকাউন্ট কত ঘণ্টা নিষ্ক্রিয় থাকলে বাসি |
| `stale_add_archive_template` | true | বাসি অনুরোধেও `{{subst:সহঅ}}` যোগ হবে |
| `action_before_report_tolerance_minutes` | 60 | রিপোর্টের কত মিনিট আগের বাধাও উত্তর হিসেবে গণ্য |
| `count_partial_blocks` | true | আংশিক বাধাও পদক্ষেপ হিসেবে গণ্য |
| `reply_indent` | `""` | উত্তরের শুরুতে `:` চাইলে |
| `automated_note` | `<small>(স্বয়ংক্রিয় বট বার্তা)</small>` | পাতায় স্বয়ংক্রিয় কার্যক্রমের উল্লেখ |
| `display_tz_offset_minutes` / `display_tz_label` | 0 / ইউটিসি | শেষ সম্পাদনার সময় কোন সময়-অঞ্চলে লেখা হবে (বাংলাদেশ সময়: 360 / বাংলাদেশ সময়) |
| `assert_mode` | bot | বট ফ্ল্যাগের আগে `user` |
| `run_page` | null | জরুরি বন্ধের পাতা |
| `resolved_templates`, `block_keywords`, `report_templates`, `heading_account_regex` | — | শনাক্তকরণের তালিকা ও নিয়ম ([বিস্তারিত](docs/how-it-works.md)) |

## পরীক্ষা

```bash
pip install -r requirements-dev.txt
python -m pytest -q        # ৬৭টি পরীক্ষা
```

* `tests/test_real_page.py`: আসল আলোচনাসভার প্রতিটি অনুচ্ছেদে বাস্তব পরিস্থিতি (বাধা, লক, বৈশ্বিক বাধা, বাসি, একই নামের অনুচ্ছেদ, শিরোনামে নাম, অ-বাধাদান অনুরোধ, একই কাজ দুবার না করা)।
* `tests/test_logic.py`: প্রতিটি সময়-সীমা সেকেন্ড পর্যন্ত।
* `tests/test_bot.py`: সম্পূর্ণ রান, সম্পাদনা-দ্বন্দ্ব, dry-run, জরুরি বন্ধ, সঠিক মুহূর্তে জাগা।
* `tests/test_parser.py`: স্বাক্ষর, তারিখ, মূলশব্দ, নাম শনাক্তকরণ।

## কোড কাঠামো

```
adminhelperbot/
  api.py        MediaWiki API ক্লায়েন্ট (লগইন, maxlag, সার্ভারের ঘড়ি)
  parser.py     অনুচ্ছেদ, রিপোর্ট করা অ্যাকাউন্ট, বন্ধের চিহ্ন
  status.py     বাধা / বৈশ্বিক বাধা / লক / শেষ সম্পাদনা
  logic.py      সিদ্ধান্ত: DONE / STALE / WAIT / SKIP
  messages.py   পাতার লেখা ও বাংলা সম্পাদনা সারাংশ
  bot.py        মূল লুপ ও নিরাপদ সম্পাদনা
  timeutil.py   বাংলা তারিখ ও সংখ্যা
  config.py     সেটিং
```

---

## English

**What it does.** The bot runs only on `উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা` and checks it every 5 minutes.

* **Done rule.** All accounts reported in a section must be locally blocked, globally locked or globally blocked. If nobody closes the section within 10 minutes of the last action, the bot appends `ACTOR কর্তৃক {{করা হয়েছে}} … --~~~~` plus `{{subst:সহঅ}}`. ACTOR is the admin or steward who acted, read from the block list, the global block list or the meta global lock log.
* **Stale rule.** Temporary accounts with no action at all get the "no block needed" message plus `{{subst:সহঅ}}`. This happens once 72 h have passed since the report and 60 h since the account's last edit.

**Timing.** Server time is used everywhere, in UTC. The scheduler wakes exactly when a request becomes due.

**Safety.** The bot skips:

* already closed sections (`{{সমাধান হওয়া অনুচ্ছেদ}}`, `{{করা হয়েছে}}`, redirects learned at startup);
* non-block requests (keyword match on visible text at word starts);
* partially handled requests and blocks made long before the report.

Accounts are taken only from the heading and the first comment, and signatures are excluded. Plain-text names in `বাধাদানের অনুরোধ: A ও B` headings are used only after the wiki confirms that all of them exist. Edit conflicts are detected and retried. An optional run page acts as a kill switch.

**Docs.** How it works: [docs/how-it-works.md](docs/how-it-works.md). Deployment: [docs/deployment.md](docs/deployment.md).
