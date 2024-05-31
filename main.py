import time
import cv2
import keyboard
import mss
import numpy as np
import pygetwindow as gw
import win32api
import win32con
import math


class Logger:
    def __init__(self, prefix=None):
        self.prefix = prefix

    def log(self, data: str):
        if self.prefix:
            print(f"{self.prefix} {data}")
        else:
            print(data)


class AutoClicker:
    def __init__(self, window_title, target_colors_hex, nearby_colors_hex, logger):
        self.window_title = window_title
        self.target_colors_hex = target_colors_hex
        self.nearby_colors_hex = nearby_colors_hex
        self.logger = logger
        self.running = False
        self.clicked_points = []

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

    def is_near_color(self, hsv_img, center, target_hsvs, radius=8):
        x, y = center
        height, width = hsv_img.shape[:2]
        for i in range(max(0, x - radius), min(width, x + radius + 1)):
            for j in range(max(0, y - radius), min(height, y + radius + 1)):
                distance = math.sqrt((x - i) ** 2 + (y - j) ** 2)
                if distance <= radius:
                    pixel_hsv = hsv_img[j, i]
                    for target_hsv in target_hsvs:
                        if np.allclose(pixel_hsv, target_hsv, atol=[1, 50, 50]):
                            return True
        return False

    def click_color_areas(self):
        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            self.logger.log(
                f"Не найдено окна с заголовком: {self.window_title}. Откройте Веб-приложение Blum и откройте скрипт заново")
            return

        window = windows[0]
        window.activate()
        target_hsvs = [self.hex_to_hsv(color) for color in self.target_colors_hex]
        nearby_hsvs = [self.hex_to_hsv(color) for color in self.nearby_colors_hex]

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

                            if not self.is_near_color(hsv, (cX - monitor["left"], cY - monitor["top"]), nearby_hsvs):
                                continue

                            if any(math.sqrt((cX - px) ** 2 + (cY - py) ** 2) < 20 for px, py in self.clicked_points):
                                continue

                            self.click_at(cX, cY)
                            self.logger.log(f'Нажал: {cX} {cY}')
                            self.clicked_points.append((cX, cY))

                    time.sleep(0.4)
                    self.clicked_points.clear()


if __name__ == "__main__":
    logger = Logger("[https://t.me/scriptblum]")
    logger.log("Вас приветствует бесплатный скрипт - автокликер для игры Blum")
    logger.log('После запуска мини игры нажимайте клавишу "ё" (`) на клавиатуре')
    target_colors_hex = ["#c9e100", "#bae70e"]
    nearby_colors_hex = ["#abff61", "#87ff27"]
    auto_clicker = AutoClicker("TelegramDesktop", target_colors_hex, nearby_colors_hex, logger)
    try:
        auto_clicker.click_color_areas()
    except Exception as e:
        logger.log(f"Произошла ошибка: {e}")
    for i in reversed(range(5)):
        i += 1
        print(f"Скрипт завершит работу через {i}")
        time.sleep(1)
