import time

import cv2
import keyboard
import mss
import numpy as np
import pygetwindow as gw
import win32api
import win32con


class Logger:
    def __init__(self, prefix=None):
        self.prefix = prefix

    def log(self, data: str):
        if self.prefix:
            print(f"{self.prefix} {data}")
        else:
            print(data)


class AutoClicker:
    def __init__(self, window_title, target_colors_hex, logger):
        self.window_title = window_title
        self.target_colors_hex = target_colors_hex
        self.logger = logger
        self.running = False

    @staticmethod
    def hex_to_hsv(hex_color):
        hex_color = hex_color.lstrip('#')
        h_len = len(hex_color)
        rgb = tuple(int(hex_color[i:i + h_len // 3], 16) for i in range(0, h_len, h_len // 3))
        rgb_normalized = np.array([[rgb]], dtype=np.uint8)
        hsv = cv2.cvtColor(rgb_normalized, cv2.COLOR_RGB2HSV)
        return hsv[0][0]

    @staticmethod
    def click_at(x, y):
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

    def toggle_script(self):
        self.running = not self.running
        r_text = "вкл" if self.running else "выкл"
        self.logger.log(f'Статус изменен: {r_text}')

    def click_color_areas(self):
        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            self.logger.log(
                f"Не найдено окна с заголовком: {self.window_title}. Откройте Веб-приложение Blum и откройте скрипт заново")
            return

        window = windows[0]
        window.activate()
        target_hsvs = [self.hex_to_hsv(color) for color in self.target_colors_hex]

        with mss.mss() as sct:
            grave_key_code = 41
            keyboard.add_hotkey(grave_key_code, self.toggle_script)

            while True:
                if self.running:
                    monitor = {
                        "top": window.top,
                        "left": window.left,
                        "width": window.width,
                        "height": window.height
                    }
                    img = np.array(sct.grab(monitor))
                    img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

                    for target_hsv in target_hsvs:
                        lower_bound = np.array([max(0, target_hsv[0] - 1), 30, 30])
                        upper_bound = np.array([min(179, target_hsv[0] + 1), 255, 255])
                        mask = cv2.inRange(hsv, lower_bound, upper_bound)
                        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                        for contour in contours:
                            if cv2.contourArea(contour) < 1:
                                continue

                            M = cv2.moments(contour)
                            if M["m00"] == 0:
                                continue
                            cX = int(M["m10"] / M["m00"]) + monitor["left"]
                            cY = int(M["m01"] / M["m00"]) + monitor["top"]

                            click_offset_y = 0
                            self.click_at(cX, cY + click_offset_y)
                            self.logger.log(f'Нажал: {cX} {cY + click_offset_y}')

                    time.sleep(0.4)


if __name__ == "__main__":
    logger = Logger("[https://t.me/scriptblum]")
    logger.log("Вас приветствует бесплатный скрипт - автокликер для игры Blum")
    logger.log('После запуска мини игры нажимайте клавишу "ё" (`) на клавиатуре')
    target_colors_hex = ["#c8e000"]
    auto_clicker = AutoClicker("TelegramDesktop", target_colors_hex, logger)
    try:
        auto_clicker.click_color_areas()
    except Exception as e:
        logger.log(f"Произошла ошибка: {e}")
    for i in reversed(range(5)):
        i += 1
        print(f"Скрипт завершит работу через {i}")
        time.sleep(1)
