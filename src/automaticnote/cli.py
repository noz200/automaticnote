import argparse

from .config import ConfigError, load_settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="automaticnote")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("healthcheck", help="Check required environment variables")
    draft_parser = subparsers.add_parser("draft", help="Create draft scaffold")
    draft_parser.add_argument("topic")

    args = parser.parse_args()

    if args.command == "healthcheck":
        try:
            settings = load_settings()
            print(f"OK: NOTE_API_BASE_URL={settings.note_api_base_url}")
        except ConfigError as exc:
            print(f"NG: {exc}")
            raise SystemExit(1) from exc

    if args.command == "draft":
        print(f"# {args.topic}\n\n- 背景\n- 本文\n- まとめ")
