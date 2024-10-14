import math
import os
import random
import sys
import time

import cv2
import keyboard
import mss
import numpy as np
import pygetwindow as gw
import win32api
import win32con


def resource_path(relative_path):
    """ Get the path to the image files if the application is opened via .exe """
    try:
        base_path = sys._MEIPASS
        return str(os.path.join(base_path, relative_path))
    except Exception:
        return relative_path


class Logger:
    def __init__(self, prefix=None):
        self.prefix = prefix

    def log(self, data: str):
        if self.prefix:
            print(f"{self.prefix} {data}")
        else:
            print(data)

    def input(self, text: str):
        if self.prefix:
            return input(f"{self.prefix} {text}")
        else:
            return input(text)


class AutoClicker:
    def __init__(self, window_title, target_colors_hex, nearby_colors_hex, logger, percentages: float, is_continue: bool):
        self.window_title = window_title
        self.target_colors_hex = target_colors_hex
        self.nearby_colors_hex = nearby_colors_hex
        self.logger = logger
        self.running = False
        self.clicked_points = []
        self.iteration_count = 0

        self.percentage_click = percentages
        self.is_continue = is_continue

        self.target_hsvs = [self.hex_to_hsv(color) for color in self.target_colors_hex]
        self.nearby_hsvs = [self.hex_to_hsv(color) for color in self.nearby_colors_hex]

        self.templates_plays = [
            cv2.cvtColor(cv2.imread(img, cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2GRAY) for img in CLICK_IMAGES
        ]  # images that need to be clicked on

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
        r_text = "on" if self.running else "off"
        self.logger.log(f'Status changed: {r_text}')

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

    def find_and_click_image(self, template_gray, screen, monitor):
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGRA2GRAY)

        result = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= 0.6:
            template_height, template_width = template_gray.shape
            center_x = max_loc[0] + template_width // 2 + monitor["left"]
            center_y = max_loc[1] + template_height // 2 + monitor["top"]
            self.click_at(center_x, center_y)
            return True

        return False

    def click_color_areas(self):
        windows = gw.getWindowsWithTitle(self.window_title)
        if not windows:
            self.logger.log(
                f"No window with title found: {self.window_title}. Open the Blum Web App and reopen the script")
            return

        window = windows[0]
        window.activate()

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

                    for target_hsv in self.target_hsvs:
                        lower_bound = np.array([max(0, target_hsv[0] - 1), 30, 30])
                        upper_bound = np.array([min(179, target_hsv[0] + 1), 255, 255])
                        mask = cv2.inRange(hsv, lower_bound, upper_bound)
                        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

                        for contour in reversed(contours):
                            if random.random() >= self.percentage_click:
                                continue

                            if cv2.contourArea(contour) < 8:
                                continue

                            M = cv2.moments(contour)
                            if M["m00"] == 0:
                                continue
                            cX = int(M["m10"] / M["m00"]) + monitor["left"]
                            cY = int(M["m01"] / M["m00"]) + monitor["top"]

                            if not self.is_near_color(hsv, (cX - monitor["left"], cY - monitor["top"]),
                                                      self.nearby_hsvs):
                                continue

                            if any(math.sqrt((cX - px) ** 2 + (cY - py) ** 2) < 35 for px, py in self.clicked_points):
                                continue
                            cY += 7
                            self.click_at(cX, cY)
                            self.logger.log(f'Clicked: {cX} {cY}')
                            self.clicked_points.append((cX, cY))

                    time.sleep(0.222)
                    self.iteration_count += 1
                    if self.iteration_count >= 5:
                        self.clicked_points.clear()
                        if self.is_continue:
                            for tp in self.templates_plays:
                                self.find_and_click_image(tp, img, monitor)
                        self.iteration_count = 0


if __name__ == "__main__":
    logger = Logger("[...]")
    logger.log("Welcome to the free autoclicker script for the game Blum")
    CLICK_IMAGES = [resource_path("media\\lobby-play.png"), resource_path("media\\continue-play.png")]

    PERCENTAGES = {
        "1": 0.13,  # 100
        "2": 0.17,  # 150
        "3": 0.235,  # 175
        "4": 1,
    }

    # Ask for the desired number of points
    answer = None
    while answer is None:
        points_key = logger.input(
            "Enter the desired number of points | 1 -> 90-110 | 2 -> 140-160 | 3 -> 170-180 | 4 -> MAX: ")
        answer = PERCENTAGES.get(points_key, None)
        if answer is None:
            logger.log("Invalid value")
    percentages = answer

    # Ask whether to click 'Play'
    answer = None
    answs = {
        "1": True,
        "0": False
    }
    while answer is None:
        points_key = logger.input("Does the bot continue games automatically? | 1 - yes / 0 - no: ")
        answer = answs.get(points_key, None)
        if answer is None:
            logger.log("Invalid value")
    is_continue = answer

    logger.log('To start the mini-game, press the (`) key on your keyboard and click on Blum Window.')
    target_colors_hex = ["#c9e100", "#bae70e"]
    nearby_colors_hex = ["#abff61", "#87ff27"]
    auto_clicker = AutoClicker("TelegramDesktop", target_colors_hex, nearby_colors_hex, logger, percentages=percentages,
                               is_continue=is_continue)
    try:
        auto_clicker.click_color_areas()
    except Exception as e:
        logger.log(f"An error has occurred: {e}")
    for i in reversed(range(5)):
        i += 1
        print(f"The script will exit in {i}")
        time.sleep(1)
