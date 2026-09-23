"""An in-memory stand-in for the MediaWiki API used by the tests."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from adminhelperbot.api import APIError
from adminhelperbot.timeutil import UTC


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeWiki:
    """Holds the state of the fake wiki (bnwiki + meta)."""

    def __init__(self, page_title: str, text: str, now: datetime):
        self.page_title = page_title
        self.text = text
        self.revid = 1000
        self.rev_ts = now
        self.clock = now
        self.blocks: List[dict] = []          # list=blocks rows
        self.global_blocks: List[dict] = []   # list=globalblocks rows
        self.locked: Dict[str, dict] = {}     # name -> {"by":..,"ts":..}
        self.contribs: Dict[str, datetime] = {}
        self.edits: List[dict] = []
        self.conflict_next_edit = False
        self.subst_output = "<!-- সংগ্রহশালাভুক্তির জন্য প্রস্তুত -->"

    # helpers used by tests ---------------------------------------------
    def block(self, user, by, ts, partial=False, expiry="infinity"):
        self.blocks.append({"id": len(self.blocks) + 1, "user": user, "by": by,
                            "timestamp": iso(ts), "expiry": expiry,
                            "partial": partial})

    def gblock(self, target, by, ts):
        self.global_blocks.append({"id": len(self.global_blocks) + 1, "target": target,
                                   "by": by, "timestamp": iso(ts), "expiry": "infinity"})

    def lock(self, user, by, ts):
        self.locked[user] = {"by": by, "ts": ts}


class FakeAPI:
    def __init__(self, wiki: FakeWiki, meta: bool = False):
        self.wiki = wiki
        self.is_meta = meta
        self.logged_in_as: Optional[str] = None

    def now(self):
        return self.wiki.clock

    def login(self, username, password):
        self.logged_in_as = username

    def csrf_token(self):
        return "token+\\"

    def post(self, **params):
        return self.get(**params)

    def get(self, **p):
        w = self.wiki
        base = {"curtimestamp": iso(w.clock)}
        if self.is_meta:
            assert p["list"] == "logevents"
            name = p["letitle"][len("User:"):-len("@global")]
            rows = []
            if name in w.locked:
                rows.append({"type": "globalauth", "action": "setstatus",
                             "user": w.locked[name]["by"],
                             "timestamp": iso(w.locked[name]["ts"]),
                             "params": {"added": ["locked"], "removed": []}})
            return {**base, "query": {"logevents": rows}}

        action = p.get("action")
        if action == "edit":
            if w.conflict_next_edit:
                w.conflict_next_edit = False
                raise APIError("editconflict", "Edit conflict.")
            assert p["basetimestamp"] == iso(w.rev_ts)
            assert p["title"] == w.page_title
            w.text = p["text"]
            w.revid += 1
            w.rev_ts = w.clock
            w.edits.append(p)
            return {**base, "edit": {"result": "Success", "newrevid": w.revid}}
        if action == "parse":
            return {**base, "parse": {"text": w.subst_output}}
        if action != "query":
            raise AssertionError(f"unexpected action {action}")

        if p.get("prop") == "revisions":
            if p["titles"] != w.page_title:
                return {**base, "query": {"pages": [{"title": p["titles"], "missing": True}]}}
            return {**base, "query": {"pages": [{"title": w.page_title, "revisions": [{
                "revid": w.revid, "timestamp": iso(w.rev_ts),
                "slots": {"main": {"content": w.text}}}]}]}}
        if p.get("prop") == "redirects":
            return {**base, "query": {"pages": [
                {"title": "টেমপ্লেট:করা হয়েছে",
                 "redirects": [{"title": "টেমপ্লেট:Done"}, {"title": "টেমপ্লেট:হয়েছে"}]},
                {"title": "টেমপ্লেট:সহঅ", "redirects": []},
            ]}}
        if p.get("list") == "blocks":
            wanted = set(p["bkusers"].split("|")) if "bkusers" in p else {p["bkip"]}
            return {**base, "query": {"blocks": [b for b in w.blocks if b["user"] in wanted]}}
        if p.get("list") == "globalblocks":
            wanted = set(p["bgtargets"].split("|"))
            return {**base, "query": {"globalblocks": [
                b for b in w.global_blocks if b["target"] in wanted]}}
        if p.get("meta") == "globaluserinfo":
            name = p["guiuser"]
            info = {"name": name, "id": 1}
            if name in w.locked:
                info["locked"] = True
            return {**base, "query": {"globaluserinfo": info}}
        if p.get("list") == "usercontribs":
            ts = w.contribs.get(p["ucuser"])
            rows = [{"timestamp": iso(ts)}] if ts else []
            return {**base, "query": {"usercontribs": rows}}
        raise AssertionError(f"unexpected query {p}")
