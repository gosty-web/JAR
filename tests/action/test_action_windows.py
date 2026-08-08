"""Test script for the Action Layer on Windows."""

import sys
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, ".")

from core.action import ActionService

def main():
    print("=" * 60)
    print("JAR Action Layer - Live Windows Test")
    print("=" * 60)
    
    # 1. Initialize Action Service
    print("\n[1/4] Initializing ActionService...")
    try:
        action = ActionService()
        print("  [OK] ActionService initialized successfully")
    except Exception as e:
        print(f"  [FAIL] Initialization failed: {e}")
        sys.exit(1)
        
    # 2. Open Notepad
    print("\n[2/4] Opening Notepad for test...")
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(2) # Wait for it to open and gain focus
    
    try:
        # 3. Test typing
        print("\n[3/4] Testing keyboard input (type_text and hotkey)...")
        action.type_text("Hello from JAR Action Layer!\n")
        time.sleep(0.5)
        action.type_text("This was typed using pyautogui.")
        time.sleep(1)
        
        # Test hotkey (Ctrl+A to select all)
        print("  Testing hotkey (ctrl+a)...")
        action.hotkey("ctrl", "a")
        time.sleep(1)
        
        # 4. Close Notepad
        print("\n[4/4] Closing Notepad...")
        action.hotkey("alt", "f4")
        time.sleep(1)
        
        # Notepad asks to save. Press Tab to go to "Don't Save" and press Enter
        print("  Dismissing save dialog...")
        # Note: On Windows 11, the hotkey to not save is usually 'n', or tab to "Don't save".
        # Let's try native click_element for "Don't Save" instead!
        print("  Attempting native click_element on 'Don't Save' button...")
        # The button name might be "Don't Save" or "Don't save" depending on locale/OS version
        success = action.click_element(name="Don't Save", control_type="button", automation_id="CommandButton_7")
        if not success:
            success = action.click_element(name="Don't save", control_type="button")
            
        if not success:
            print("  [WARN] Native click failed. Using physical key fallback (n).")
            action.press_key("n")
            
        # Ensure it closed or kill it
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        print("\nRESULT: [PASS] - Action Layer tests completed.")
        
    except Exception as e:
        print(f"\nRESULT: [FAIL] - Exception during test: {e}")
        proc.kill()
        sys.exit(1)

if __name__ == "__main__":
    main()
