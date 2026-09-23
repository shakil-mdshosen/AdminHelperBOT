# স্থাপন ও পরিচালনা (Deployment & Operations)

## ১. বট অ্যাকাউন্ট প্রস্তুত করা

1. একটি আলাদা অ্যাকাউন্ট খুলুন, যেমন `AdminHelperBot`। ব্যবহারকারী পাতায় লিখুন যে এটি একটি বট, এর পরিচালক কে, এবং বট থামানোর উপায় কী।
2. **বট ফ্ল্যাগের আবেদন:** বাংলা উইকিপিডিয়ায় বট অনুমোদনের পাতায় আবেদন করুন। কাজের বিবরণ হিসেবে [how-it-works.md](how-it-works.md)-এর প্রথম অংশ ব্যবহার করতে পারেন।
3. **স্বাক্ষর:** বটের পছন্দসমূহে সাধারণ স্বাক্ষর রাখুন। বটের লেখা `--~~~~` এই স্বাক্ষরেই রূপ নেয়।
4. **বট পাসওয়ার্ড:** `বিশেষ:BotPasswords` থেকে একটি পাসওয়ার্ড তৈরি করুন (যেমন নাম `AdminHelperBot`)। অনুমতি দিন:
   * Basic rights
   * High-volume editing
   * Edit existing pages

   লগইন নাম হবে `AdminHelperBot@AdminHelperBot`।
5. **জরুরি বন্ধের পাতা** তৈরি করুন: `ব্যবহারকারী:AdminHelperBot/চালু`, লেখা: `চালু`। কনফিগে `"run_page": "ব্যবহারকারী:AdminHelperBot/চালু"` দিন। যেকোনো প্রশাসক লেখাটি বদলে (যেমন `বন্ধ`) বট থামাতে পারবেন। পাতাটি সুরক্ষিত রাখা ভালো।

## ২. স্থানীয়ভাবে চালানো

```bash
git clone https://github.com/shakil-mdshosen/AdminHelperBOT.git
cd AdminHelperBOT
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp config.example.json config.json

export ADMINHELPERBOT_USERNAME='AdminHelperBot@AdminHelperBot'
export ADMINHELPERBOT_PASSWORD='…'
```

**প্রথমে সবসময় dry-run:**

```bash
venv/bin/python -m adminhelperbot -c config.json --once --dry-run
```

এটি লগইন ছাড়াও চলে (পড়ার জন্য লগইন লাগে না)। প্রতিটি অনুচ্ছেদের জন্য লগে একটি লাইন আসে:

```
[বাধাদানের অনুরোধ: Swarup Das Official] Swarup Das Official -> wait (waiting for admins to mark as done), due 2026-09-23 05:50:00Z
[নিবন্ধ অপসারণ প্রস্তাবনায় …] Sàádî -> skip (does not look like a block request)
Marking [বাধাদানের অনুরোধ …] as stale
  reply: বাধা দেওয়ার প্রয়োজন নেই, … --~~~~ ⏎ {{subst:সহঅ}}
  summary: /* … */ বট: …
[DRY RUN] would save with summary: …
```

শুরুতে স্ব-সমন্বয়ের লগও দেখুন। `{{subst:সহঅ}} expands to: …` লাইনে `সমাধান হওয়া অনুচ্ছেদ` থাকা উচিত।

সব ঠিক থাকলে:

```bash
venv/bin/python -m adminhelperbot -c config.json --once   # একবার
venv/bin/python -m adminhelperbot -c config.json          # নিরবচ্ছিন্ন (প্রস্তাবিত)
```

বট ফ্ল্যাগ পাওয়ার আগে পরীক্ষামূলক সম্পাদনার জন্য `config.json`-এ `"assert_mode": "user"` দিন (অনুমোদন প্রক্রিয়ার নিয়ম মেনে)। ফ্ল্যাগ পাওয়ার পর `"bot"` করুন।

## ৩. Toolforge-এ চালানো (প্রস্তাবিত)

```bash
ssh login.toolforge.org
become adminhelperbot                      # আপনার tool-এর নাম
git clone https://github.com/shakil-mdshosen/AdminHelperBOT.git
cd AdminHelperBOT
toolforge jobs run setup --image python3.11 --wait \
  --command "cd ~/AdminHelperBOT && python3 -m venv venv && venv/bin/pip install -r requirements.txt"
cp config.example.json config.json         # প্রয়োজনে সম্পাদনা

toolforge envvars create ADMINHELPERBOT_USERNAME 'AdminHelperBot@AdminHelperBot'
toolforge envvars create ADMINHELPERBOT_PASSWORD '…'

toolforge jobs load jobs.yaml              # continuous job চালু
toolforge jobs list
tail -f ~/adminhelperbot.out ~/adminhelperbot.err
```

`jobs.yaml`-এ job টি `continuous: true`। বট নিজেই প্রতি ৫ মিনিটে এবং প্রয়োজনে ঠিক নির্ধারিত সময়ে জাগে। বন্ধ হয়ে গেলে Toolforge এটি আবার চালু করে। `state.json` tool-এর home ডিরেক্টরিতে থাকে।

**কেন cron নয়?** প্রতি ৫ মিনিটের cron-এ ১০ মিনিটের অপেক্ষা আসলে ১০–১৫ মিনিট হয়ে যায়। continuous মোডে বট ঠিক `due + ৫ সেকেন্ড`-এ কাজ করে। তবুও চাইলে `--once` দিয়ে cron (`*/5 * * * *`) চালানো যায়।

## ৪. হালনাগাদ

```bash
cd ~/AdminHelperBOT && git pull
venv/bin/pip install -r requirements.txt
toolforge jobs restart adminhelperbot
```

## ৫. পর্যবেক্ষণ ও সমস্যা সমাধান

| লক্ষণ | কারণ / সমাধান |
|---|---|
| `login-failed` | বট পাসওয়ার্ড ভুল বা বাতিল; নতুন তৈরি করে envvar হালনাগাদ করুন |
| `assertbotfailed` | অ্যাকাউন্টে এখনো বট ফ্ল্যাগ নেই; অনুমোদন পর্যন্ত `"assert_mode": "user"` |
| `Run page … does not allow editing` | জরুরি বন্ধের পাতায় "চালু" নেই (ইচ্ছাকৃতভাবে থামানো হয়েছে) |
| `Edit conflict, will retry` | স্বাভাবিক; কেউ একই সময়ে সম্পাদনা করছিলেন |
| `maxlag hit` | সার্ভার ব্যস্ত; বট নিজেই অপেক্ষা করে |
| কোনো অনুরোধে বট কিছু করছে না | লগে সেই অনুচ্ছেদের `-> skip (…)` কারণটি দেখুন |
| `heading names … not all existing accounts; ignored` | শিরোনামের কোনো নামের অ্যাকাউন্ট নেই, তাই শিরোনাম থেকে নাম নেওয়া হয়নি |

লগে প্রতিটি অনুচ্ছেদের সিদ্ধান্ত ও কারণ থাকে, তাই "কেন করল / কেন করল না" সবসময় বোঝা যায়। বিস্তারিত লগের জন্য `-v` দিন।

## ৬. পরীক্ষা চালানো

```bash
pip install -r requirements-dev.txt
python -m pyflakes adminhelperbot tests
python -m pytest -q
```

GitHub-এ প্রতিটি push-এ `.github/workflows/tests.yml` স্বয়ংক্রিয়ভাবে পরীক্ষা চালায়।

## ৭. নিরাপত্তা নোট

* পাসওয়ার্ড কখনো কোডে বা `config.json`-এ রাখবেন না; environment variable ব্যবহার করুন। `config.json` ও `state.json` `.gitignore`-এ আছে।
* বট শুধু `page_title`-এ দেওয়া একটি পাতাতেই সম্পাদনা করে (`nocreate=1`)।
