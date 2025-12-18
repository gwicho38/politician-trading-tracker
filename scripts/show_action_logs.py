#!/usr/bin/env python3
"""
Quick script to display recent action logs from the database
"""

from politician_trading.utils.action_logger import get_action_logger

def main():
    print("📊 Recent Action Logs from Database:")
    print("=" * 40)

    try:
        logger = get_action_logger()
        actions = logger.get_recent_actions(limit=10)

        if actions:
            for action in actions:
                print(f'🕒 {action["created_at"][:19]}')
                print(f'📝 {action["action_type"]}: {action["action_name"] or "N/A"}')
                print(f'📊 Status: {action["status"]}')

                if action.get('result_message'):
                    print(f'✅ Result: {action["result_message"]}')
                if action.get('error_message'):
                    print(f'❌ Error: {action["error_message"]}')

                print('-' * 40)
        else:
            print("No action logs found")

    except Exception as e:
        print(f"❌ Error retrieving action logs: {e}")

if __name__ == "__main__":
    main()