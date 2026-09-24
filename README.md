# AdminHelperBot

[![tests](https://github.com/shakil-mdshosen/AdminHelperBOT/actions/workflows/tests.yml/badge.svg)](https://github.com/shakil-mdshosen/AdminHelperBOT/actions/workflows/tests.yml)

A maintenance bot for the Bangla Wikipedia administrators' noticeboard, **[উইকিপিডিয়া:প্রশাসকদের আলোচনাসভা](https://bn.wikipedia.org/wiki/উইকিপিডিয়া:প্রশাসকদের_আলোচনাসভা)**. That page is where editors ask administrators to act, for example to block a registered or temporary account.

Administrators and global stewards often handle a request but forget to mark it as done and tag it for archiving. The bot fills that gap:

1. **Marks handled requests as done.** It checks whether each reported account has been blocked, globally locked or globally blocked, and records who did it.
2. **Closes stale requests** about temporary accounts that nobody acted on and that have stopped editing.
3. **Adds the archive tag** to requests an administrator already closed without it.

The bot edits **only that one page**. Every edit is marked as automated and carries a detailed Bangla edit summary.

| Document | Contents |
|---|---|
| **[docs/how-it-works.md](docs/how-it-works.md)** | Every step, decision rule and timing detail, with examples from the real page *(Bangla)* |
| **[docs/deployment.md](docs/deployment.md)** | Bot account, BotPassword, Toolforge, monitoring, troubleshooting *(Bangla)* |
| **[docs/texts.md](docs/texts.md)** | How to edit the bot's Bangla wording in `texts.toml` *(Bangla)* |

---

## What the bot does

The bot checks every request (every section) on the page every 5 minutes.

### 1. Handled but not marked as done

The bot acts when **every** account reported in a section (registered, temporary or IP) has been:

* **blocked** locally by an administrator, **or**
* **globally locked** by a steward, **or**
* **globally blocked** by a steward.

If nobody has marked the request **10 minutes after the last action**, the bot appends:

```
:Ferdous কর্তৃক {{করা হয়েছে}} <small>(স্বয়ংক্রিয় বার্তা)</small> --~~~~
{{subst:সহঅ}}
```

The first line reads "Done by Ferdous (automated message)". It is indented with `:` because `reply_indent` is `":"` in `config.json`. The name is the administrator or steward who acted. If several people acted, all their names appear, e.g. `Steward X ও Yahya কর্তৃক …` ("by Steward X and Yahya"). `{{subst:সহঅ}}` tags the request for archiving.

### 2. Stale temporary-account reports

The bot closes a report about a temporary account when **both** of these hold:

* no administrator or steward acted within **72 hours** of the report, **and**
* the account has not edited for **60 hours**.

It writes:

```
:বাধা দেওয়ার প্রয়োজন নেই, অস্থায়ী অ্যাকাউন্ট থেকে সর্বশেষ সম্পাদনা ২১ জুন ২০২৬, ১১:৫০ (ইউটিসি) টায় হয়েছে। <small>(স্বয়ংক্রিয় বার্তা)</small> --~~~~
{{subst:সহঅ}}
```

This means "No block needed; the temporary account last edited at 21 June 2026, 11:50 (UTC)."

### 3. Decided but not tagged for archiving

An administrator may close a request with `{{করা হয়েছে}}` (done), `{{করা হয়নি}}` (not done) or `{{done}}`, but forget `{{subst:সহঅ}}`. The bot then adds **only** the archive tag, **10 minutes after the last comment** in the section:

```
{{subst:সহঅ}}
```

This applies to every request on the page, not only block requests. If the decision template is unsigned, the 10 minutes count from when the bot first saw it.

### Edit summaries

Every edit links to its section and explains exactly what happened, in Bangla. For example:

> /\* বাধাদানের অনুরোধ: Swarup Das Official \*/ বট: অনুরোধটি সম্পন্ন হিসেবে চিহ্নিত ও সংগ্রহশালাভুক্তির জন্য প্রস্তুত করা হলো — Swarup Das Official-কে প্রশাসক Ferdous স্থানীয়ভাবে বাধা দিয়েছেন (২৩ সেপ্টেম্বর ২০২৬, ০৫:৫০ (ইউটিসি))। পদক্ষেপ নেওয়ার ১০ মিনিট পরেও কেউ চিহ্নিত না করায় স্বয়ংক্রিয়ভাবে {{করা হয়েছে}} ও {{সহঅ}} যোগ করা হয়েছে। (স্বয়ংক্রিয় সম্পাদনা)

*In English:* "Bot: request marked as done and ready for archiving: administrator Ferdous blocked Swarup Das Official locally (23 September 2026, 05:50 UTC). Nobody marked it within 10 minutes of the action, so {{করা হয়েছে}} and {{সহঅ}} were added automatically. (automated edit)"

---

## Timing rules

| Rule | The bot acts at |
|---|---|
| Done | `max(report time, time of the last block/lock) + 10 minutes` |
| Stale | `max(report time + 72 hours, last edit + 60 hours)` |
| Archive tag only | `time of the last comment + 10 minutes` |

* All times use the **wiki server's clock** (from the API), in UTC, never the host machine's clock.
* The bot checks every 5 minutes. When a request becomes due between two checks, the bot wakes up exactly then (+5 seconds), so "10 minutes" means 10 minutes, not up to 15.
* The report time is the reporter's own signature (the first signature in the section).
* Every limit is tested to the second: at 9:59 nothing happens, at exactly 10:00 the bot acts.

## When the bot does nothing

The bot deliberately leaves a request alone when any of these apply:

* The section already carries an archive marker (`{{সমাধান হওয়া অনুচ্ছেদ}}`, `{{সহঅ}}` or a redirect to one).
* An administrator used `{{Doing}}`, meaning the work is in progress.
* It is not a block request (e.g. template creation, undeletion, a deletion dispute).
* Only some of the reported accounts were handled.
* The block was placed long before the report (more than 60 minutes earlier).
* A registered account was not actioned; the stale rule applies to temporary accounts only.
* The emergency stop page (`run_page`) does not say `চালু` ("on").

When in doubt, the bot leaves the decision to humans. All of these rules are tested against a copy of the real noticeboard ([tests/test_real_page.py](tests/test_real_page.py)).

### How requests are read

* **Reported accounts** come from the section heading and the first comment only. That includes contribution links, user links, report templates such as `{{userlinks}}`, temporary-account names, and plain names in headings like `বাধাদানের অনুরোধ: A ও B` ("Block request: A and B").
* **Plain-text names in a heading** are used only after the wiki confirms that every one of them is an existing account.
* **Signatures** (the reporter's and in replies) are never treated as reported accounts. That covers decorated signatures and tool links such as XReport.
* **Block requests** are recognised by keywords (বাধা, ব্লক, lock, vandal, …) matched on visible text at the start of a word. That way, "লক" inside "পুলক" does not count, and "block" inside a URL does not count either.

---

## Quick start

Requirements: **Python 3.11+**.

```bash
git clone https://github.com/shakil-mdshosen/AdminHelperBOT.git
cd AdminHelperBOT
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Credentials from Special:BotPasswords (never put them in a file)
export ADMINHELPERBOT_USERNAME='AdminHelperBot@AdminHelperBot'
export ADMINHELPERBOT_PASSWORD='…'

venv/bin/python -m adminhelperbot --once --dry-run   # show what it would do, no edits
venv/bin/python -m adminhelperbot                    # run continuously
```

| Command-line option | Meaning |
|---|---|
| `--once` | Check the page once and exit (for cron) |
| `--dry-run` | Log what would be written, with summaries, without editing; works without logging in |
| `-c FILE` | Use a different config file (default: `config.json` in the repository root) |
| `-v` | Verbose logging |

Before the account has the bot flag, set `"assert_mode": "user"` in `config.json` for supervised test edits.

For the full deployment steps (bot account, bot flag, Toolforge), see **[docs/deployment.md](docs/deployment.md)**.

## Stopping the bot

| Situation | What to do |
|---|---|
| **Pause from the wiki** (no server access) | Edit the stop page set as `run_page` in `config.json` (currently `ব্যবহারকারী:MdsShakil/খেলাঘর_২`) and replace `চালু` with anything else, e.g. `বন্ধ`. Editing stops within about 5 minutes. Change it back to resume. |
| **Kill the Toolforge job** | `toolforge jobs delete adminhelperbot` (a continuous job restarts itself if only the process dies). Start again with `toolforge jobs load jobs.yaml`. |
| **Restart after a config/text change** | `toolforge jobs restart adminhelperbot` |
| **Local run** | Press `Ctrl+C`, or run `pkill -f adminhelperbot` |
| **Emergency** | Any administrator can block the bot account, or the operator can revoke its BotPassword. |

---

## Configuration

### Technical settings: `config.json`

All technical settings live in **[`config.json`](config.json)** in the repository root, next to this README. The bot reads it automatically at startup and logs the path it used (`Config: …`).

* Keys starting with `_` are explanatory comments (in Bangla) and are ignored.
* An unknown or misspelled key stops the bot with an error naming the key.
* Missing keys fall back to the defaults in [`adminhelperbot/config.py`](adminhelperbot/config.py).
* Relative paths in the file (`state_file`, `texts_file`) are resolved from the file's own folder.
* **Never store credentials in this file.** It is committed to GitHub; use the environment variables above.

| Key | Value in `config.json` | Meaning |
|---|---|---|
| `check_interval_minutes` | `5` | How often the page is checked |
| `done_grace_minutes` | `10` | Wait after a block/lock before marking as done |
| `archive_grace_minutes` | `10` | Wait after the last comment before adding the archive tag to a decided request |
| `stale_no_action_hours` | `72` | Hours without action before a temporary-account report is stale |
| `stale_inactivity_hours` | `60` | Hours without edits from the temporary account |
| `action_before_report_tolerance_minutes` | `60` | A block placed up to this long before the report still counts as the answer |
| `count_partial_blocks` | `true` | Treat partial blocks as an action |
| `archive_decided_requests` | `true` | Add `{{subst:সহঅ}}` to decided but untagged requests |
| `stale_add_archive_template` | `true` | Add `{{subst:সহঅ}}` to stale requests |
| `reply_indent` | `":"` | Indentation of the bot's comment line, e.g. `":"` or `"::"` (the `{{subst:সহঅ}}` line is never indented) |
| `display_tz_offset_minutes` | `0` | Time zone offset for times the bot writes (`360` = Bangladesh; the label is in `texts.toml`) |
| `require_block_keywords` | `true` | Act on block requests only |
| `temp_account_regex` | `~\d{4}-\d+(?:-\d+)*` | Pattern of temporary account names |
| `assert_mode` | `"bot"` | `"user"` until the account has the bot flag |
| `maxlag` | `5` | MediaWiki `maxlag` value |
| `max_edits_per_run` | `25` | Safety limit per check |
| `run_page` | `"ব্যবহারকারী:MdsShakil/খেলাঘর_২"` | Emergency stop page; the bot edits only while this page contains `চালু`. **The page must exist and contain `চালু` before the first run**; set `null` to disable the feature. |
| `texts_file` | `null` | Use a different Bangla texts file (`null` = `adminhelperbot/texts.toml`) |
| `state_file` | `"state.json"` | Small file where the bot remembers when it first saw things |
| `dry_run` | `false` | Never edit, only log |
| `api_url`, `meta_api_url`, `user_agent` | bnwiki / metawiki | API endpoints and User-Agent |

### Bangla wording: `adminhelperbot/texts.toml`

Every Bangla string the bot uses lives in one file: **[`adminhelperbot/texts.toml`](adminhelperbot/texts.toml)**. That includes:

* the lines it writes on the page and the edit summaries;
* month names and the date format;
* namespace and template names;
* the keywords and heading rule used to read requests.

To change the wording, edit that file and restart the bot. No code changes are needed.

* Words like `$actors` or `$last_edit` are placeholders that the bot fills in. Write `$$` for a literal dollar sign.
* The file is validated at startup. A mistake stops the bot before any edit, with a message saying exactly what is wrong, e.g. `page.done_line: unknown placeholder $actor (allowed: $actors)`.
* A test fails if Bangla text ever reappears in the Python code, so this single-file rule holds.

The full guide, in Bangla, is in [docs/texts.md](docs/texts.md).

---

## How it works (overview)

On every check, the bot:

1. Reads the latest revision of the page (keeping the revision ID and timestamp for edit-conflict detection).
2. Splits the page into sections and, for each one, finds the report time, the reported accounts, and any decision or archive markers.
3. Looks up every reported account through the API:
   * local blocks (`list=blocks`);
   * global blocks (`list=globalblocks`);
   * global locks (`meta=globaluserinfo`, plus the actor from the metawiki `globalauth` log);
   * the last edit of temporary accounts (`list=usercontribs`).
4. Decides for each request: `DONE`, `STALE`, `ARCHIVE` (tag only), `WAIT` (with the exact due time) or `SKIP` (with the reason).
5. Makes one edit per request, re-reading the page after each edit.
   * The reply is appended at the end of its section, and nothing else on the page changes.
   * Edits use `bot=1`, `assert=bot`, `maxlag`, `nocreate` and edit-conflict protection; on a conflict the bot re-reads the page and decides again.
6. Sleeps until the next 5-minute check, or until the earliest due request if that comes sooner.

At startup the bot also **calibrates itself** from the wiki. It learns every redirect of `{{করা হয়েছে}}` and `{{সহঅ}}`, and what `{{subst:সহঅ}}` expands to (currently `{{সমাধান হওয়া অনুচ্ছেদ|…}}`). That way, template renames on the wiki don't break detection.

Every decision and its reason are logged, so you can always see why the bot did or did not act on a request.

The detailed description, in Bangla, is in [docs/how-it-works.md](docs/how-it-works.md).

---

## Testing

```bash
pip install -r requirements-dev.txt
python -m pyflakes adminhelperbot tests
python -m pytest -q
```

The suite runs against an in-memory fake wiki ([`tests/fakewiki.py`](tests/fakewiki.py)), with no network access needed. GitHub Actions runs it on every push.

| File | What it covers |
|---|---|
| `tests/test_real_page.py` | A copy of the real noticeboard: every section's interpretation, blocks, locks, global blocks, stale reports, duplicate section titles, names in headings, non-block requests, no duplicate edits |
| `tests/test_logic.py` | Every timing limit, to the second |
| `tests/test_bot.py` | Full runs: edit conflicts, dry run, stop page, exact wake-up scheduling, archive-only rule |
| `tests/test_parser.py` | Signatures, dates, keywords, account detection |
| `tests/test_texts.py` | `texts.toml` changes the output, mistakes are reported, no Bangla text in the code, `config.json` is complete |

## Project layout

```
AdminHelperBOT/
├── config.json            technical settings (read automatically)
├── jobs.yaml              Toolforge continuous job
├── requirements.txt       runtime dependencies (requests, mwparserfromhell)
├── requirements-dev.txt   test dependencies
├── docs/                  detailed documentation (Bangla)
├── tests/                 test suite and a copy of the real noticeboard
└── adminhelperbot/
    ├── texts.toml         all Bangla text
    ├── texts.py           loads and validates texts.toml
    ├── config.py          loads config.json
    ├── api.py             MediaWiki API client (login, maxlag, retries, server clock)
    ├── parser.py          sections, reported accounts, closing markers
    ├── status.py          blocks, global blocks, global locks, last edits
    ├── logic.py           decisions: DONE / STALE / ARCHIVE / WAIT / SKIP
    ├── messages.py        page text and edit summaries
    ├── timeutil.py        Bangla digits and dates, signature timestamps
    ├── bot.py             main loop, calibration, safe editing, scheduling
    └── __main__.py        command-line entry point
```

## Known limitations

* A registered account named in plain text (no link or template) is only detected in headings of the form `বাধাদানের অনুরোধ: …`.
* When several sections share a title, MediaWiki links the edit summary's `/* … */` to the first one. The edit itself always goes to the correct section, and the summary names the accounts.
* A temporary account's last edit is taken from visible edits on Bangla Wikipedia only (deleted edits are not visible).
