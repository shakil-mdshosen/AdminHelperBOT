"""Command line entry point: python -m adminhelperbot [--once] [--dry-run]."""

from __future__ import annotations

import argparse
import logging
import sys

from .bot import AdminHelperBot
from .config import Config
from .texts import default_texts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="adminhelperbot",
        description=default_texts().get("cli.description"),
    )
    ap.add_argument("-c", "--config",
                    help="JSON config file (default: config.json in the repository root)")
    ap.add_argument("--once", action="store_true",
                    help="check the page once and exit (for cron / Toolforge jobs)")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be done without editing")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = Config.load(args.config)
    logging.getLogger("adminhelperbot").info(
        "Config: %s", cfg.source or "built-in defaults (no config.json found)")
    if args.dry_run:
        cfg.dry_run = True
    bot = AdminHelperBot(cfg)
    bot.setup()
    if args.once:
        bot.run_once()
    else:
        bot.loop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
