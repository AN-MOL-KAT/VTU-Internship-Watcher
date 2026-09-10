import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output stream on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.monitoring.monitor import InternshipMonitor
from src.notifications.telegram import TelegramNotifier
from src.utils.logger import setup_logger

logger = setup_logger(log_file="logs/watcher.log")

BANNER = """
========================================================
             VTU INTERNSHIP WATCHER
========================================================
"""


def print_banner():
    print(BANNER)


def handle_stats(monitor: InternshipMonitor):
    stats = monitor.db.get_stats()
    print("\n--- DATABASE SUMMARY ---")
    print(f"Total Internships Tracked: {stats['total_internships']}")
    print(f"Total Alerts Dispatched:   {stats['notifications_sent']}")
    print("\nBreakdown by Priority Level:")
    for level, count in stats["priority_counts"].items():
        print(f"  - {level:<12}: {count}")
    print("------------------------\n")


def handle_list(monitor: InternshipMonitor):
    items = monitor.db.get_all_internships()
    if not items:
        print("\nNo internships stored in database yet. Run 'python run.py --once' to fetch.\n")
        return

    print("\n" + "=" * 80)
    print(f"{'PRIORITY':<12} | {'MATCH':<6} | {'TYPE/FEE':<14} | {'MODE':<8} | {'TITLE & COMPANY'}")
    print("=" * 80)
    for item in items[:25]:
        stipend_fee = item.stipend if item.stipend else (f"₹{item.fee}" if item.fee > 0 else "Free")
        print(
            f"{item.priority_level:<12} | {item.technical_score:>5.0f}% | {stipend_fee:<14} | {item.mode:<8} | {item.title[:35]} ({item.company[:20]})"
        )
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="VTU Internship Watcher")
    parser.add_argument(
        "--once", action="store_true", default=True, help="Run a single check and exit (default)"
    )
    parser.add_argument(
        "--loop", action="store_true", help="Run in continuous monitoring loop"
    )
    parser.add_argument(
        "--interval", type=int, default=30, help="Polling interval in minutes for --loop (default: 30)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate check without altering database or sending alerts"
    )
    parser.add_argument(
        "--test-telegram", action="store_true", help="Send a test message to verify Telegram bot credentials"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Display database statistics and priority breakdown"
    )
    parser.add_argument(
        "--list", action="store_true", help="Display all stored internships sorted by priority"
    )

    args = parser.parse_args()
    print_banner()

    monitor = InternshipMonitor()

    if args.test_telegram:
        print("Testing Telegram Bot connection...")
        telegram = TelegramNotifier()
        if not telegram.is_configured():
            print("❌ Telegram credentials missing in .env! (Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
            return
        success = telegram.send_test_message()
        if success:
            print("✓ Telegram test message delivered successfully!")
        else:
            print("❌ Failed to deliver Telegram test message. Check logs/watcher.log for details.")
        return

    if args.stats:
        handle_stats(monitor)
        return

    if args.list:
        handle_list(monitor)
        return

    if args.loop:
        monitor.start_loop(interval_minutes=args.interval)
        return

    # Default: Run once
    print("Starting monitor...\n")
    summary = monitor.run_check(dry_run=args.dry_run)

    print("\n✓ Portal connection successful")
    print(f"✓ Found {summary['total_found']} internships")
    print(f"✓ {summary['new_count']} new internships")
    print(f"✓ {summary['relevant_count']} relevant internships")
    print(f"✓ {summary['high_priority_count']} high-priority internships")
    print(f"✓ {summary['alerts_sent']} alert{'s' if summary['alerts_sent'] != 1 else ''} sent")
    print("\n" + "=" * 56)


if __name__ == "__main__":
    main()
