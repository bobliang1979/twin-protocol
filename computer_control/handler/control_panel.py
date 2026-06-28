"""control_panel_handler.py — 专用 Windows Control Panel 交互模块

解决 OSWorld #3.3 Control Panel 超时问题。
Win32 对话框用 ctypes 直接交互，绕过 UIA 树。

Usage:
    from control_panel_handler import ControlPanelHandler
    handler = ControlPanelHandler()
    result = await handler.find_and_click("Advanced system settings")
"""

import ctypes
import ctypes.wintypes
import time
import re
from typing import Optional, List, Tuple

# Windows API constants
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
BM_CLICK = 0x00F5
SW_SHOW = 5
SW_MINIMIZE = 6
SW_RESTORE = 9

# Window class names for Control Panel
CONTROL_PANEL_CLASSES = ("#32770", "CabinetWClass", "ControlPanelWindow")

user32 = ctypes.windll.user32

class ControlPanelHandler:
    """Direct Win32 interaction for Control Panel dialogs.
    
    Bypasses UIA entirely — uses ctypes win32 API for:
    - Window enumeration
    - Button/control detection by text
    - Click simulation via BM_CLICK / SendInput
    """

    @staticmethod
    def _get_window_text(hwnd: int) -> str:
        length = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
        if not length:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, buf)
        return buf.value

    @staticmethod
    def _enum_windows_callback(hwnd: int, lparam: tuple) -> bool:
        """Callback for EnumWindows. Collects matching windows."""
        results, class_pattern, text_pattern = lparam
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        
        # Match class
        if class_pattern and class_pattern not in class_name.value:
            return True
        
        # Match text
        win_text = ControlPanelHandler._get_window_text(hwnd)
        if text_pattern:
            if isinstance(text_pattern, re.Pattern):
                if not text_pattern.search(win_text):
                    return True
            elif text_pattern.lower() not in win_text.lower():
                return True
        
        results.append((hwnd, class_name.value, win_text))
        return True

    @classmethod
    def find_windows(cls, class_pattern: str = None, 
                     text_pattern: str = None) -> List[Tuple]:
        """Find windows by class and/or text pattern."""
        results = []
        if text_pattern:
            text_pattern = re.compile(text_pattern, re.IGNORECASE) if isinstance(text_pattern, str) else text_pattern
        callback = ctypes.WINFUNCTYPE(
            ctypes.c_bool, 
            ctypes.c_int, 
            ctypes.py_object
        )(cls._enum_windows_callback)
        user32.EnumWindows(callback, (results, class_pattern, text_pattern))
        return results

    @classmethod
    def find_control_panel_dialogs(cls) -> List[Tuple]:
        """Find all open Control Panel dialogs."""
        results = []
        for cp_class in CONTROL_PANEL_CLASSES:
            results.extend(cls.find_windows(class_pattern=cp_class))
        return results

    @classmethod
    def find_child_button(cls, parent_hwnd: int, button_text: str) -> Optional[int]:
        """Find a button child control by text."""
        buttons = []
        def enum_child(hwnd, lparam):
            class_name = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_name, 256)
            if "Button" in class_name.value:
                text = cls._get_window_text(hwnd)
                if button_text.lower() in text.lower():
                    buttons.append(hwnd)
            return True
        
        callback = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.py_object)(enum_child)
        user32.EnumChildWindows(parent_hwnd, callback, None)
        return buttons[0] if buttons else None

    @classmethod
    def click_button(cls, hwnd: int) -> bool:
        """Click a button via BM_CLICK message."""
        try:
            user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
            return True
        except Exception:
            return False

    @classmethod
    def bring_to_foreground(cls, hwnd: int) -> bool:
        """Bring window to foreground."""
        try:
            user32.ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.2)
            user32.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    @classmethod
    async def find_and_click(cls, target_text: str, 
                              timeout: float = 60.0) -> bool:
        """High-level: Find Control Panel item and click it.
        
        Args:
            target_text: Text to search for in button/control
            timeout: Max seconds to wait
            
        Returns:
            True if clicked successfully
        """
        deadline = time.time() + timeout
        last_error = ""
        
        while time.time() < deadline:
            try:
                # Find control panel dialogs
                dialogs = cls.find_control_panel_dialogs()
                for hwnd, cls_name, win_text in dialogs:
                    cls.bring_to_foreground(hwnd)
                    time.sleep(0.3)
                    
                    # Find matching button
                    btn = cls.find_child_button(hwnd, target_text)
                    if btn:
                        cls.click_button(btn)
                        time.sleep(0.5)
                        return True
                    
                    # Also search all child controls for text match
                    all_controls = []
                    def enum_all(h, _):
                        t = cls._get_window_text(h)
                        if target_text.lower() in t.lower():
                            all_controls.append(h)
                        return True
                    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.py_object)(enum_all)
                    user32.EnumChildWindows(hwnd, cb, None)
                    
                    if all_controls:
                        # Try to click the first match
                        for ctrl in all_controls[:3]:
                            try:
                                user32.SendMessageW(ctrl, BM_CLICK, 0, 0)
                            except:
                                pass
                        time.sleep(0.5)
                        return True
                    
                    last_error = f"No control with text '{target_text}' found"
                    
            except Exception as e:
                last_error = str(e)
            
            time.sleep(1.0)
        
        raise TimeoutError(
            f"Control Panel: '{target_text}' not found after {timeout}s. "
            f"Last error: {last_error}"
        )
