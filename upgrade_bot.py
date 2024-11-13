
from requests import Session, RequestException
from time import sleep, time
from datetime import datetime, timedelta
import random
import requests
from typing import List, Dict, Optional, Any

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    BLUE = '\033[0;34m'
    RESET = '\033[0m'

authorizations = []  
telegram_bot_token = "6751513253:AAFDosTu2MaLPa3NjAUUa0EJ8pwPjeOdMOc"  
chat_id = "6177500390"  

def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        requests.post(url, json=data)
    except RequestException as e:
        print(f"{Colors.RED}[{get_current_time()}] Failed to send Telegram message. Error: {str(e)}{Colors.RESET}")

def check_token_validity(token: str) -> bool:
    url = "https://api.hamsterkombatgame.io/interlude/upgrades-for-buy"
    headers = {'Authorization': token}
    try:
        response = requests.post(url, headers=headers, timeout=10)
        return response.status_code == 200
    except RequestException:
        return False

def get_authorizations() -> List[str]:
    if not authorizations:
        while True:
            auth_token = input(f"{Colors.GREEN}[{get_current_time()}] Enter Authorization Token (or type 'done' to finish): {Colors.RESET}")
            if auth_token.lower() == 'done':
                break
            if check_token_validity(auth_token):
                authorizations.append(auth_token)
            else:
                print(f"{Colors.RED}Invalid token. Please try again.{Colors.RESET}")
    return authorizations

def wait_for_cooldown(cooldown_seconds: int):
    end_time = datetime.now() + timedelta(seconds=cooldown_seconds)
    while cooldown_seconds > 0:
        hours, remainder = divmod(cooldown_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"{Colors.YELLOW}[{get_current_time()}] Waiting {hours}h {minutes}m {seconds}s until next upgrade...{Colors.RESET}", end='\r')
        sleep(1)
        cooldown_seconds -= 1
    print(f"\n{Colors.CYAN}[{get_current_time()}] Cooldown over. Ready for next purchase at {end_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")

def format_number(number: int) -> str:
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}m"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}k"
    else:
        return str(number)

def get_user_choice() -> str:
    print(f"{Colors.CYAN}[{get_current_time()}] Choose mode:{Colors.RESET}")
    print(f"{Colors.YELLOW}1. Buy the best card immediately (skip cooldown waiting){Colors.RESET}")
    print(f"{Colors.YELLOW}2. Buy only the best card and wait for cooldown{Colors.RESET}")
    choice = input(f"{Colors.GREEN}[{get_current_time()}] Enter your choice (1 or 2): {Colors.RESET}")
    return choice.strip()

def purchase_upgrade(session: Session, authorization: str, upgrade_id: int) -> bool:
    url = "https://api.hamsterkombatgame.io/interlude/buy-upgrade"
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization,
    }
    data = {"upgradeId": upgrade_id, "timestamp": int(time() * 1000)}
    try:
        response = session.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        print(f"{Colors.GREEN}[{get_current_time()}] Upgrade successfully purchased!{Colors.RESET}")
        send_telegram_message(f"Upgrade successfully purchased for token ending in {authorization[-6:]}.")
        return True
    except RequestException as e:
        print(f"{Colors.RED}[{get_current_time()}] Failed to purchase upgrade. Error: {str(e)}{Colors.RESET}")
        return False

def get_upgrades(session: Session, authorization: str) -> List[Dict[str, Any]]:
    url = "https://api.hamsterkombatgame.io/interlude/upgrades-for-buy"
    headers = {'Authorization': authorization}
    try:
        response = session.post(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("upgradesForBuy", [])
    except RequestException as e:
        print(f"{Colors.RED}[{get_current_time()}] Failed to retrieve upgrades. Error: {str(e)}{Colors.RESET}")
        return []

def filter_upgrades(upgrades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [u for u in upgrades if not u["isExpired"] and u["isAvailable"] and u["price"] > 0]

def get_best_upgrade(upgrades: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    valid_upgrades = filter_upgrades(upgrades)
    return max(valid_upgrades, key=lambda u: u["profitPerHourDelta"] / u["price"], default=None)

def main():
    get_authorizations()  
    if not authorizations:
        print(f"{Colors.RED}No authorization tokens entered. Exiting...{Colors.RESET}")
        return

    min_balance = float(input(f"{Colors.YELLOW}[{get_current_time()}] Set minimum balance to stop purchasing (just for reference): {Colors.RESET}"))
    user_choice = get_user_choice()

    while True: 
        with Session() as session:
            for authorization in authorizations:
                print(f"{Colors.BLUE}[{get_current_time()}] Starting process for account with token [{authorization[-6:]}] {Colors.RESET}")
                send_telegram_message(f"Starting process for account with token ending in {authorization[-6:]}.")

                while True:
                    upgrades = get_upgrades(session, authorization)
                    sorted_upgrades = sorted(filter_upgrades(upgrades), key=lambda u: u["profitPerHourDelta"] / u["price"], reverse=True)

                    purchased = False

                    for upgrade in sorted_upgrades:
                        print(f"{Colors.GREEN}[{get_current_time()}] Checking Upgrade: {Colors.YELLOW}{upgrade['name']} (ID: {upgrade['id']}, Price: {format_number(upgrade['price'])}){Colors.RESET}")

                        cooldown_seconds = upgrade.get("cooldownSeconds", 4)

                        if cooldown_seconds > 0:
                            if user_choice == "1":
                                print(f"{Colors.PURPLE}[{get_current_time()}] Upgrade {upgrade['name']} is on cooldown, skipping...{Colors.RESET}")
                                continue
                            elif user_choice == "2":
                                print(f"{Colors.YELLOW}[{get_current_time()}] Upgrade {upgrade['name']} is on cooldown. Waiting for {cooldown_seconds} seconds...{Colors.RESET}")
                                wait_for_cooldown(cooldown_seconds)

                        if purchase_upgrade(session, authorization, upgrade["id"]):
                            print(f"{Colors.GREEN}[{get_current_time()}] Successfully purchased: {upgrade['name']} (ID: {upgrade['id']}){Colors.RESET}")
                            purchased = True
                            sleep(random.randint(7, 24))  # Wait between purchases
                            break

                    if not purchased:
                        print(f"{Colors.RED}[{get_current_time()}] No valid upgrades available for account [{authorization[-6:]}...]. Moving to the next account...{Colors.RESET}")
                        break  
                wait_time = random.randint(9, 25)
                print(f"{Colors.CYAN}[{get_current_time()}] Waiting {wait_time}s before the next account...{Colors.RESET}")
                sleep(wait_time)

            print(f"{Colors.CYAN}[{get_current_time()}] Completed processing all accounts. Waiting for 2 hours before restarting...{Colors.RESET}")
            send_telegram_message("Completed processing all accounts. Waiting for 2 hours before restarting.")
            sleep(2 * 3600)  

if __name__ == "__main__":
    main()
