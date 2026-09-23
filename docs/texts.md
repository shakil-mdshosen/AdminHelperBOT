# বাংলা লেখা বদলানো (texts.toml)

বটের **সব বাংলা লেখা** একটি ফাইলে আছে: [`adminhelperbot/texts.toml`](../adminhelperbot/texts.toml)। এর মধ্যে আছে বট পাতায় যা লেখে, সম্পাদনা সারাংশ, তারিখের ধরন, এবং পাতা পড়ার সময় বট যেসব টেমপ্লেট ও শব্দ খোঁজে। কোডে (`.py` ফাইলে) কোনো বাংলা লেখা নেই। একটি স্বয়ংক্রিয় পরীক্ষা (`test_no_bangla_strings_in_code`) ভবিষ্যতেও এটি নিশ্চিত করে।

লেখা বদলানোর নিয়ম:

1. `texts.toml` খুলে লেখাটি বদলান।
2. `python -m adminhelperbot --once --dry-run` চালিয়ে দেখুন বট এখন কী লিখবে।
3. বট আবার চালু করুন (Toolforge: `toolforge jobs restart adminhelperbot`)।

## ফাইলের অংশগুলো

| অংশ | কী আছে |
|---|---|
| `[wiki]` | পাতার নাম, `করা হয়েছে` / `সহঅ` টেমপ্লেটের নাম, নামস্থানের নাম, জরুরি-বন্ধের শব্দ |
| `[page]` | বট পাতায় যে লাইনগুলো লেখে |
| `[summary]` | সম্পাদনা সারাংশ |
| `[datetime]` | মাসের নাম, সময়ের ধরন, "ইউটিসি" লেবেল, স্বাক্ষরের বানানভেদ |
| `[detection]` | সিদ্ধান্তের টেমপ্লেট, সংগ্রহশালার টেমপ্লেট, রিপোর্ট টেমপ্লেট, মূলশব্দ, শিরোনামের নিয়ম |
| `[cli]` | কমান্ড লাইনের বর্ণনা |

## `$নাম` — বট যা নিজে বসায়

যেমন:

```toml
done_line = "$actors কর্তৃক {{করা হয়েছে}} <small>(স্বয়ংক্রিয় বট বার্তা)</small> --~~~~"
```

এখানে `$actors`-এর জায়গায় বট প্রশাসক বা স্টুয়ার্ডের নাম বসায় (যেমন `Ferdous` বা `Steward X ও Yahya`)। বাকি সব হুবহু পাতায় যায়। শব্দগুলো সাজানো বা বদলানো যায়, যেমন:

```toml
done_line = ":{{করা হয়েছে}} — $actors পদক্ষেপ নিয়েছেন। <small>(বট)</small> --~~~~"
```

প্রতিটি লেখার ঠিক উপরের মন্তব্যে বলা আছে সেখানে কোন কোন `$নাম` ব্যবহার করা যায়।

| লেখা | ব্যবহারযোগ্য `$নাম` |
|---|---|
| `page.done_line` | `$actors` |
| `page.stale_line` | `$subject`, `$last_edit` |
| `page.stale_line_no_edits` | `$subject` |
| `summary.done` | `$details`, `$grace` |
| `summary.action_*` | `$account`, `$actor`, `$when` |
| `summary.when` | `$time` |
| `summary.stale` | `$details`, `$archive_note` |
| `summary.stale_details` | `$no_action_hours`, `$inactivity_hours`, `$accounts`, `$last_edit_info` |
| `summary.stale_last_edit_info` | `$last_edit` |
| `summary.archive_only` | `$details`, `$grace` |
| `datetime.format` | `$day`, `$month`, `$year`, `$hour`, `$minute`, `$tz` |

* `$নাম`-এর পরে সরাসরি বাংলা লেখা বসানো যায়: `$account-কে`, `$accounts-এর`।
* আসল ডলার চিহ্ন লাগলে `$$` লিখুন।
* সংখ্যাগুলো (সময়, মিনিট, ঘণ্টা) বট নিজেই বাংলা অঙ্কে লেখে।

## ভুল করলে কী হয়

বট চালু হওয়ার সময় পুরো ফাইল যাচাই করে। কোনো ভুল থাকলে সম্পাদনা শুরুর **আগেই** থেমে যায় এবং ঠিক কোথায় কী ভুল তা বলে দেয়। যেমন:

```
Problems in texts.toml:
  page.done_line: unknown placeholder $actor (allowed: $actors)
  missing [page] stale_subject_one
  [datetime] months: exactly 12 names are needed
```

TOML-এর বানান-ভুল (যেমন উদ্ধৃতিচিহ্ন বন্ধ করতে ভুলে যাওয়া) হলে লাইন নম্বরসহ `TOML syntax error` দেখায়।

## খেয়াল রাখার বিষয়

* বাসি-বার্তার শুরুর অংশ (`বাধা দেওয়ার প্রয়োজন নেই`) `[detection] decision_phrases`-এও আছে, যাতে বট নিজের পুরোনো বার্তা চিনতে পারে। `page.stale_line` বদলালে এটিও বদলান।
* `[page]`/`[summary]`-এ `{{করা হয়েছে}}`, `{{সহঅ}}` সরাসরি লেখা আছে। উইকিতে টেমপ্লেটের নাম বদলালে এসব লেখা ও `[wiki]`-এর `done_template` / `archive_template` দুটোই বদলান।
* লেখা যত খুশি বদলান। তবে `[detection]`-এর তালিকা বদলালে বট কোন অনুরোধে কাজ করবে তা বদলে যায়, তাই পরে অবশ্যই `--dry-run` দিয়ে দেখে নিন।
* আলাদা ফাইল রাখতে চাইলে `config.json`-এ `"texts_file": "my-texts.toml"` দিন। তবে ফাইলটিতে সব লেখা থাকতে হবে (মূল ফাইল কপি করে বদলানো সবচেয়ে সহজ)।
