import os
from dotenv import load_dotenv
from app.browser import open_browser, screenshot_png, apply_action
from app.gemini import decide_action

load_dotenv()

START_URL = os.getenv("START_URL", "https://example.com")

def run(goal: str, max_steps: int = 8):
    p, browser, page = open_browser(START_URL)

    try:
        for step in range(max_steps):
            shot = screenshot_png(page)
            action = decide_action(goal, shot)

            print(f"\nSTEP {step+1}/{max_steps}")
            print("ACTION:", action)

            ok = apply_action(page, action)

            # If model said done, or we can't apply action, stop.
            if action.get("type") == "done":
                print("DONE.")
                break
            if not ok:
                print("Could not apply action. Stopping.")
                break

        input("\nPress ENTER to close...")
    finally:
        browser.close()
        p.stop()

if __name__ == "__main__":
    goal = input("What do you want to do? ")
    run(goal)
