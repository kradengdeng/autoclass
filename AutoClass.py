#  $$$$$$\              $$\                $$$$$$\  $$\                               
# $$  __$$\             $$ |              $$  __$$\ $$ |                              
# $$ /  $$ |$$\   $$\ $$$$$$\    $$$$$$\  $$ /  \__|$$ | $$$$$$\   $$$$$$$\  $$$$$$$\ 
# $$$$$$$$ |$$ |  $$ |\_$$  _|  $$  __$$\ $$ |      $$ | \____$$\ $$  _____|$$  _____|
# $$  __$$ |$$ |  $$ |  $$ |    $$ /  $$ |$$ |      $$ | $$$$$$$ |\$$$$$$\  \$$$$$$\  
# $$ |  $$ |$$ |  $$ |  $$ |$$\ $$ |  $$ |$$ |  $$\ $$ |$$  __$$ | \____$$\  \____$$\ 
# $$ |  $$ |\$$$$$$  |  \$$$$  |\$$$$$$  |\$$$$$$  |$$ |\$$$$$$$ |$$$$$$$  |$$$$$$$  |
# \__|  \__| \______/    \____/  \______/  \______/ \__| \_______|\_______/ \_______/ 
                                                                                    
# Made by @kradengdeng
# Notice: Please install latest python to use this program!
# Latest Update: 12/09/2026 : 9:21 PM (day-month-year)
# Visit github.com/kradengdeng/autoclass

import sys
import subprocess
import time
import random
import json
import traceback
import tempfile
import os
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_URL = "https://ssp-elective-course.web.app/"
DATA_FILE = Path(__file__).resolve().parent / "data.json"

SESSION_STARTED = datetime.now()
SESSION_ID = SESSION_STARTED.strftime("session_%m%d%Y_%H%M")
SESSION_DIR = Path(__file__).resolve().parent / "session"
SESSION_LOG_FILE = SESSION_DIR / f"{SESSION_ID}.txt"
SESSION_FINAL_STATUS = "completed"
FIRST_RUN = not DATA_FILE.exists() or not SESSION_DIR.exists()

# Console progress state.
CONSOLE_LOCK = threading.Lock()
PROGRESS_TOTAL = 0
PROGRESS_LINES = {}
PROGRESS_ACTIVE = False

# ANSI colors used before colorama is installed/imported.
ANSI_RESET = "\033[0m"
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_BLACK = "\033[90m"


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def init_session():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    SESSION_LOG_FILE.write_text(
        f"Session: {SESSION_ID}\n"
        f"Started: {SESSION_STARTED.isoformat(timespec='seconds')}\n"
        + "-" * 73
        + "\n",
        encoding="utf-8"
    )


def log_session_line(line):
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        with SESSION_LOG_FILE.open("a", encoding="utf-8") as log:
            log.write(line + "\n")
    except Exception:
        pass


def finish_session(status):
    ended = datetime.now()
    log_session_line("-" * 73)
    log_session_line(f"[ SESSION ] Status: {status}")
    log_session_line(
        f"[ SESSION ] Ended: {ended.isoformat(timespec='seconds')}"
    )


def bootstrap_notice(message, color=ANSI_CYAN, edit=False):
    line = f"[ NOTICE : {timestamp()} ] {message}"

    with CONSOLE_LOCK:
        if edit:
            print("\r\033[2K" + color + line + ANSI_RESET, end="", flush=True)
            print()
        else:
            print(color + line + ANSI_RESET, flush=True)

    log_session_line(line)


def bootstrap_separator():
    with CONSOLE_LOCK:
        print(ANSI_BLACK + "-" * 73 + ANSI_RESET, flush=True)


def install_packages():
    packages = {
        "selenium": "selenium",
        "colorama": "colorama",
    }

    missing = []

    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)

    if not missing:
        return

    bootstrap_notice("Installing package...", ANSI_YELLOW)

    for package in missing:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    bootstrap_notice("All package installed.", ANSI_YELLOW, edit=True)


# Runtime dependencies are imported after installation in __main__.

Fore = type("_Fore", (), {
    "LIGHTMAGENTA_EX": "\033[95m",
    "LIGHTYELLOW_EX": ANSI_YELLOW,
    "LIGHTGREEN_EX": ANSI_GREEN,
    "LIGHTRED_EX": ANSI_RED,
    "LIGHTCYAN_EX": ANSI_CYAN,
    "LIGHTBLACK_EX": ANSI_BLACK,
})
Style = type("_Style", (), {"RESET_ALL": ANSI_RESET})


manual_select = False


def notice(message, color=Fore.LIGHTMAGENTA_EX, write_log=True):
    line = f"[ NOTICE : {timestamp()} ] {message}"

    with CONSOLE_LOCK:
        print(f"{color}{line}{Style.RESET_ALL}", flush=True)

    if write_log:
        log_session_line(line)


def separator():
    with CONSOLE_LOCK:
        print(Fore.LIGHTBLACK_EX + "-" * 73 + Style.RESET_ALL, flush=True)


def step(message):
    notice(message, Fore.LIGHTYELLOW_EX)


def success(message):
    notice(message, Fore.LIGHTGREEN_EX)


def error(message, color=Fore.LIGHTRED_EX):
    notice(message, color)


def clear_console():
    with CONSOLE_LOCK:
        os.system("cls" if os.name == "nt" else "clear")


def student_display_name(student):
    return (
        f"{student.get('title', '')}"
        f"{student.get('name', '')} "
        f"{student.get('surname', '')}"
    ).strip()


def student_status_line(student, status):
    return (
        f"{student.get('student_id', '')} - "
        f"{student.get('title', '')}"
        f"{student.get('name', '')} "
        f"{student.get('surname', '')} : {status}"
    )


def render_working_lines(students):
    global PROGRESS_TOTAL, PROGRESS_LINES, PROGRESS_ACTIVE

    PROGRESS_TOTAL = len(students)
    PROGRESS_LINES = {}
    PROGRESS_ACTIVE = True

    with CONSOLE_LOCK:
        for index, student in enumerate(students, start=1):
            line = student_status_line(student, "Working...")
            PROGRESS_LINES[index] = line
            print(
                Fore.LIGHTYELLOW_EX +
                f"[ NOTICE : {timestamp()} ] {line}" +
                Style.RESET_ALL,
                flush=True,
            )
            log_session_line(f"[ NOTICE : {timestamp()} ] {line}")


def update_student_status(index, student, status, color):
    if not PROGRESS_ACTIVE:
        notice(student_status_line(student, status), color)
        return

    line = student_status_line(student, status)
    prefix = f"[ NOTICE : {timestamp()} ] "

    with CONSOLE_LOCK:
        rows_up = PROGRESS_TOTAL - index + 1

        print(
            f"\033[{rows_up}A",
            end="",
        )

        print(
            "\r\033[2K" +
            color +
            prefix + line +
            Style.RESET_ALL,
            end="",
            flush=True,
        )

        print(
            f"\033[{rows_up}B\r",
            end="",
            flush=True,
        )

    log_session_line(prefix + line)


def load_data():
    # First run: create the required files/folder, then stop.
    if not DATA_FILE.exists():
        sample = {
            "confirm": False,
            "randomize_next": True,
            "manual_select": False,
            "students": [
                {
                    "student_id": "",
                    "title": "",
                    "name": "",
                    "surname": "",
                    "room": "",
                    "number": "",
                    "course": "คณิตศาสตร์เสริม 6",
                    "teacher": "นายทิวัตถ์ กัลยาประสิทธิ์",
                    "year_text": "ปีการศึกษา 2569 M.3 วันพุธ"
                }
            ]
        }

        DATA_FILE.write_text(
            json.dumps(sample, ensure_ascii=False, indent=4),
            encoding="utf-8"
        )

        notice(
            "Created data.json and session folder.",
            Fore.LIGHTYELLOW_EX
        )
        notice(
            "Please fill data in data.json!",
            Fore.LIGHTRED_EX
        )
        return None

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        error("Invalid JSON in data.json.")
        return None
    except OSError:
        error("Could not read data.json.")
        return None

    if not isinstance(data, dict):
        error("Invalid data.json: root must be an object.")
        return None

    required_keys = {
        "confirm",
        "randomize_next",
        "manual_select",
        "students"
    }

    missing = required_keys - set(data.keys())
    if missing:
        error(
            "Invalid data.json: missing " +
            ", ".join(sorted(missing))
        )
        return None

    if not isinstance(data["confirm"], bool):
        error("Invalid data.json: confirm must be true or false.")
        return None

    if not isinstance(data["randomize_next"], bool):
        error("Invalid data.json: randomize_next must be true or false.")
        return None

    if not isinstance(data["manual_select"], bool):
        error("Invalid data.json: manual_select must be true or false.")
        return None

    if not isinstance(data["students"], list) or not data["students"]:
        error("Invalid data.json: students must be a non-empty list.")
        return None

    student_keys = {
        "student_id",
        "title",
        "name",
        "surname",
        "room",
        "number",
        "course",
        "teacher",
        "year_text"
    }

    for index, student in enumerate(data["students"], start=1):
        if not isinstance(student, dict):
            error(f"Invalid data.json: student {index} must be an object.")
            return None

        missing_student = student_keys - set(student.keys())
        if missing_student:
            error(
                f"Invalid data.json: student {index} missing " +
                ", ".join(sorted(missing_student))
            )
            return None

        for key in student_keys:
            if not isinstance(student[key], str):
                error(
                    f"Invalid data.json: student {index} '{key}' must be a string."
                )
                return None

        if not student["course"].strip():
            error(
                f"Invalid data.json: student {index} course cannot be empty."
            )
            return None

        if not student["teacher"].strip():
            error(
                f"Invalid data.json: student {index} teacher cannot be empty."
            )
            return None

        if not student["year_text"].strip():
            error(
                f"Invalid data.json: student {index} year_text cannot be empty."
            )
            return None

    return data


def get_screen_size():
    try:
        import ctypes

        user32 = ctypes.windll.user32
        return (
            user32.GetSystemMetrics(0),
            user32.GetSystemMetrics(1)
        )
    except Exception:
        return (1920, 1080)


def get_scale_factor(driver):
    try:
        driver.set_window_rect(
            x=0,
            y=0,
            width=300,
            height=500
        )

        actual_width = driver.get_window_size()["width"]

        if actual_width > 0:
            return actual_width / 300

    except Exception:
        pass

    return 1.0


def arrange_browser(driver, index, total):
    screen_width, screen_height = get_screen_size()

    gap = 4

    # Measure Chrome's Windows/DPI scaling so the windows tile
    # using their actual outer size instead of overlapping.
    scale = get_scale_factor(driver)

    usable_width = screen_width - (gap * max(0, total - 1))
    target_width = max(
        320,
        usable_width // max(1, total)
    )

    target_css_width = max(
        280,
        int(target_width / scale) - 8
    )

    target_css_height = max(
        500,
        int((screen_height - 40) / scale)
    )

    driver.set_window_rect(
        x=0,
        y=35,
        width=target_css_width,
        height=target_css_height
    )

    actual = driver.get_window_size()
    actual_width = actual["width"]
    actual_height = actual["height"]

    x = (index - 1) * (actual_width + gap)

    # If the measured outer width is slightly larger than expected,
    # reduce it before placing the window.
    if x + actual_width > screen_width:
        desired_width = max(
            300,
            (screen_width - (gap * max(0, total - 1))) // max(1, total)
        )

        desired_css_width = max(
            280,
            int(desired_width / scale) - 12
        )

        driver.set_window_rect(
            x=0,
            y=35,
            width=desired_css_width,
            height=target_css_height
        )

        actual = driver.get_window_size()
        actual_width = actual["width"]
        actual_height = actual["height"]

        x = (index - 1) * (actual_width + gap)

    if x + actual_width > screen_width:
        x = max(
            0,
            screen_width - actual_width
        )

    driver.set_window_position(
        x,
        35
    )



def wait_element(driver, xpath, timeout=15):
    poll = 0.05 if not randomize_next else 0.2

    return WebDriverWait(
        driver,
        timeout,
        poll_frequency=poll
    ).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )


def click_xpath(driver, xpath, timeout=15):
    element = wait_element(driver, xpath, timeout)

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: "center",
            inline: "center"
        });
        """,
        element
    )

    driver.execute_script("arguments[0].click();", element)
    return element


def click_text(driver, text, timeout=15):
    script = """
    const wanted = arguments[0].trim();

    const elements = [
        ...document.querySelectorAll(
            'button, input, a, label'
        )
    ];

    for (const el of elements) {
        const value = (
            el.innerText ||
            el.value ||
            el.textContent ||
            ""
        ).trim();

        if (value === wanted) {
            el.scrollIntoView({
                block: "center",
                inline: "center"
            });
            el.click();
            return true;
        }
    }

    return false;
    """

    end = time.time() + timeout

    while time.time() < end:
        if driver.execute_script(script, text):
            return

        time.sleep(0.01 if not randomize_next else 0.05)

    raise TimeoutException(f"Could not click: {text}")


def wait_next_delay():
    if randomize_next:
        time.sleep(random.uniform(0.100, 0.500))


def select_text(driver, xpath, text, timeout=15):
    element = wait_element(driver, xpath, timeout)

    Select(element).select_by_visible_text(text)

    driver.execute_script(
        """
        arguments[0].dispatchEvent(
            new Event("input", {bubbles: true})
        );
        arguments[0].dispatchEvent(
            new Event("change", {bubbles: true})
        );
        """,
        element
    )

    return element


def fill_input(driver, xpath, value, timeout=15):
    element = wait_element(driver, xpath, timeout)
    element.clear()
    element.send_keys(value)
    return element


def select_course(driver, course_name, teacher_name, timeout=15):
    script = """
    const wantedCourse = arguments[0]
        .trim()
        .replace(/\\s+/g, " ");

    const wantedTeacher = arguments[1]
        .trim()
        .replace(/\\s+/g, " ");

    const normalize = text =>
        (text || "").trim().replace(/\\s+/g, " ");

    const all = [...document.querySelectorAll("*")];

    // Find the smallest elements that contain the exact teacher name.
    const teacherNodes = all.filter(el => {
        const text = normalize(el.innerText || "");

        if (!text.includes(wantedTeacher)) {
            return false;
        }

        return ![...el.children].some(child =>
            normalize(child.innerText || "").includes(wantedTeacher)
        );
    });

    for (const teacherNode of teacherNodes) {
        let parent = teacherNode;

        // Walk upward until we reach the course card containing
        // exactly one checkbox.
        for (let level = 0; level < 8 && parent; level++) {
            const text = normalize(parent.innerText || "");

            if (!text.includes(wantedCourse)) {
                parent = parent.parentElement;
                continue;
            }

            const boxes = [
                ...parent.querySelectorAll(
                    'input[type="checkbox"]'
                )
            ];

            if (boxes.length === 1) {
                const box = boxes[0];

                box.scrollIntoView({
                    block: "center",
                    inline: "center"
                });

                if (!box.checked) {
                    box.click();
                }

                return box.checked;
            }

            parent = parent.parentElement;
        }
    }

    return false;
    """

    end = time.time() + timeout

    while time.time() < end:
        if driver.execute_script(
            script,
            course_name,
            teacher_name
        ):
            return

        time.sleep(0.01 if not randomize_next else 0.05)

    raise TimeoutException(
        "Exact course/teacher combination not found: "
        f"{course_name!r} / {teacher_name!r}"
    )



def fill_student_page(driver, student):
    fill_input(
        driver,
        "//input[contains(@placeholder,'เลขประจำตัวนักเรียน')]",
        student["student_id"]
    )

    select_text(driver, "//select[1]", student["title"])

    fill_input(
        driver,
        "//input[@placeholder='ชื่อ']",
        student["name"]
    )

    fill_input(
        driver,
        "//input[@placeholder='นามสกุล']",
        student["surname"]
    )

    selects = driver.find_elements(By.TAG_NAME, "select")

    if len(selects) < 2:
        raise RuntimeError("Grade selector not found.")

    grade = Select(selects[1])

    if len(grade.options) > 1:
        grade.select_by_index(1)

    fill_input(
        driver,
        "//input[contains(@placeholder,'ให้กรอกเลข')]",
        student["room"]
    )

    fill_input(
        driver,
        "//input[@placeholder='เลขที่']",
        student["number"]
    )


def select_confirmation(driver):
    script = """
    const wanted = "ข้าพเจ้ายืนยันว่าข้อมูลที่กรอกไปนั้นถูกต้องและสมบูรณ์";

    const boxes = [
        ...document.querySelectorAll('input[type="checkbox"]')
    ];

    for (const box of boxes) {
        const texts = [];

        if (box.id) {
            const label = document.querySelector(
                `label[for="${CSS.escape(box.id)}"]`
            );

            if (label) {
                texts.push(label.innerText || label.textContent || "");
            }
        }

        let parent = box.parentElement;

        for (let i = 0; i < 3 && parent; i++, parent = parent.parentElement) {
            texts.push(parent.innerText || parent.textContent || "");
        }

        if (box.nextElementSibling) {
            texts.push(
                box.nextElementSibling.innerText ||
                box.nextElementSibling.textContent ||
                ""
            );
        }

        if (box.previousElementSibling) {
            texts.push(
                box.previousElementSibling.innerText ||
                box.previousElementSibling.textContent ||
                ""
            );
        }

        const combined = texts
            .join(" ")
            .replace(/\\s+/g, " ")
            .trim();

        if (combined.includes(wanted)) {
            box.scrollIntoView({
                block: "center",
                inline: "center"
            });

            if (!box.checked) {
                box.click();
            }

            return box.checked;
        }
    }

    return false;
    """

    end_time = time.time() + 8

    while time.time() < end_time:
        checked = driver.execute_script(script)

        if checked:
            return

        time.sleep(0.01 if not randomize_next else 0.05)

    raise RuntimeError(
        "Confirmation checkbox was found but could not be selected."
    )

def process_student(driver, student, index):
    started = time.perf_counter()

    course = student["course"]
    teacher = student["teacher"]

    try:
        driver.get(BASE_URL + "enroll")

        try:
            arrange_browser(driver, index, len(students))
        except Exception:
            pass

        select_text(driver, "//select[1]", student["year_text"])
        wait_next_delay()

        click_text(driver, "เลือก")

        fill_student_page(driver, student)

        wait_next_delay()
        click_text(driver, "ถัดไป")

        wait_next_delay()
        click_text(driver, "เลือก 1 วิชา")

        wait_next_delay()
        click_text(driver, "ถัดไป")

        if manual_select:
            update_student_status(
                index,
                student,
                "Manual select.",
                Fore.LIGHTYELLOW_EX
            )
            return index

        try:
            select_course(driver, course, teacher)
        except TimeoutException:
            # Keep the same manual fallback behavior without extra NOTICE lines.
            try:
                screen_width, screen_height = get_screen_size()
                manual_width = 1100
                manual_height = min(800, screen_height - 80)

                driver.set_window_rect(
                    x=max(0, (screen_width - manual_width) // 2),
                    y=35,
                    width=manual_width,
                    height=manual_height
                )
            except Exception:
                pass

            with CONSOLE_LOCK:
                print(
                    Fore.LIGHTCYAN_EX +
                    f"Student {index}: Select the course manually, "
                    "then press Enter..." +
                    Style.RESET_ALL,
                    flush=True,
                )

            input()

            selected = driver.execute_script(
                """
                return document.querySelectorAll(
                    'input[type="checkbox"]:checked'
                ).length > 0;
                """
            )

            if not selected:
                raise RuntimeError(
                    "No course checkbox is selected after manual selection."
                )

        select_confirmation(driver)

        elapsed = time.perf_counter() - started
        status = f"Done! Finished in {elapsed:.2f}s."
        update_student_status(
            index,
            student,
            status,
            Fore.LIGHTGREEN_EX
        )

        if confirm:
            click_text(driver, "ลงทะเบียน")
            driver.quit()

        return index

    except Exception as exc:
        elapsed = time.perf_counter() - started
        update_student_status(
            index,
            student,
            f"Failed after {elapsed:.2f}s.",
            Fore.LIGHTRED_EX
        )
        log_session_line(f"[ ERROR : Student {index} ] {exc}")
        log_session_line(traceback.format_exc())
        return index


def create_driver(index):
    options = webdriver.ChromeOptions()
    options.page_load_strategy = "eager"
    options.add_argument("--start-maximized")

    # Keep Chrome/ChromeDriver diagnostics out of the console.
    # They are not part of the NOTICE interface and should not be shown.
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    profile_dir = Path(
        tempfile.mkdtemp(prefix=f"elective_student_{index}_")
    )

    options.add_argument(f"--user-data-dir={profile_dir}")

    service = Service(log_output=subprocess.DEVNULL)
    return webdriver.Chrome(service=service, options=options)


def main():
    data = load_data()

    if data is None:
        return

    global confirm, randomize_next, manual_select, students
    global SESSION_FINAL_STATUS

    confirm = data["confirm"]
    randomize_next = data["randomize_next"]
    manual_select = data["manual_select"]
    students = data["students"]

    # Start prompt.
    answer = input(
        f"{Fore.LIGHTYELLOW_EX}"
        f"[ NOTICE : {timestamp()} ] Start? [y/n]: "
        f"{Style.RESET_ALL}"
    ).strip().lower()

    if answer != "y":
        return

    clear_console()

    # Exact start screen after confirmation.
    notice(
        f"Session: {SESSION_ID}",
        Fore.LIGHTCYAN_EX
    )
    separator()

    render_working_lines(students)

    failed = 0
    futures = []

    with ThreadPoolExecutor(max_workers=len(students)) as executor:
        for index, student in enumerate(students, start=1):
            try:
                driver = create_driver(index)

                try:
                    arrange_browser(driver, index, len(students))
                except Exception:
                    pass

                futures.append(
                    executor.submit(
                        process_student,
                        driver,
                        student,
                        index
                    )
                )

            except Exception as exc:
                failed += 1
                update_student_status(
                    index,
                    student,
                    "Failed to start.",
                    Fore.LIGHTRED_EX
                )
                log_session_line(f"[ ERROR : Student {index} ] {exc}")

        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                failed += 1
                log_session_line(f"[ ERROR : Worker ] {exc}")
                log_session_line(traceback.format_exc())

    SESSION_FINAL_STATUS = "partial_failure" if failed else "completed"


if __name__ == "__main__":
    final_status = "completed"

    try:
        init_session()

        # First screen is intentionally shown before package setup.
        bootstrap_notice(
            f"Session: {SESSION_ID}",
            ANSI_CYAN
        )
        bootstrap_separator()

        install_packages()

        from colorama import Fore as ColoramaFore, Style as ColoramaStyle, init as colorama_init
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait, Select
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException

        colorama_init(autoreset=True)
        Fore = ColoramaFore
        Style = ColoramaStyle

        main()

    except KeyboardInterrupt:
        final_status = "stopped_by_user"
        log_session_line("[ ERROR ] Stopped by user.")

    except Exception as exc:
        final_status = "fatal_error"

        try:
            error(f"Fatal error: {exc}")
            log_session_line("[ ERROR TRACEBACK ]")
            log_session_line(traceback.format_exc())
        except Exception:
            print(f"[ ERROR ] Fatal error: {exc}")

    finally:
        try:
            if final_status == "completed":
                final_status = SESSION_FINAL_STATUS

            finish_session(final_status)
        except Exception as exc:
            print(f"[ ERROR ] Could not save session: {exc}")

        # Keep the window open without adding another NOTICE line.
        try:
            input()
        except EOFError:
            time.sleep(1)
