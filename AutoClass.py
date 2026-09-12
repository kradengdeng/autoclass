import sys
import subprocess
import time
import random
import json
import traceback
import tempfile
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


def install_packages():
    packages = {
        "selenium": "selenium",
        "colorama": "colorama",
    }

    for module, package in packages.items():
        try:
            __import__(module)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package]
            )


install_packages()

from colorama import Fore, Style, init

init(autoreset=True)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


BASE_URL = "https://ssp-elective-course.web.app/"
DATA_FILE = Path(__file__).resolve().parent / "data.json"

SESSION_STARTED = datetime.now()
SESSION_ID = SESSION_STARTED.strftime("session_%m%d%Y_%H%M")
SESSION_DIR = Path(__file__).resolve().parent / "session"
SESSION_LOG_FILE = SESSION_DIR / f"{SESSION_ID}.txt"
SESSION_FINAL_STATUS = "completed"
manual_select = False


def init_session():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    SESSION_LOG_FILE.write_text(
        f"Session: {SESSION_ID}\n"
        f"Started: {SESSION_STARTED.isoformat(timespec='seconds')}\n"
        + "-" * 60
        + "\n",
        encoding="utf-8"
    )


def log_session_line(line):
    try:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)

        with SESSION_LOG_FILE.open(
            "a",
            encoding="utf-8"
        ) as log:
            log.write(line + "\n")
    except Exception:
        pass


def finish_session(status):
    ended = datetime.now()

    log_session_line(
        "-" * 60
    )
    log_session_line(
        f"[ SESSION ] Status: {status}"
    )
    log_session_line(
        f"[ SESSION ] Ended: {ended.isoformat(timespec='seconds')}"
    )



def load_data():
    notice("Checking data from data.json", Fore.LIGHTMAGENTA_EX)

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
                    "teacher": "นายทิวัตถ์ กัลยาประสิทธิ์"
                }
            ],
            "year_text": "ปีการศึกษา 2569 M.3 วันพุธ"
        }

        DATA_FILE.write_text(
            json.dumps(
                sample,
                ensure_ascii=False,
                indent=4
            ),
            encoding="utf-8"
        )

        error("Not found! Please fill data in data.json", Fore.LIGHTRED_EX)
        notice(
            "Created data.json in this folder.",
            Fore.LIGHTYELLOW_EX
        )
        return None

    try:
        data = json.loads(
            DATA_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        error(f"Invalid JSON in data.json: {exc}")
        return None
    except OSError as exc:
        error(f"Could not read data.json: {exc}")
        return None

    if not isinstance(data, dict):
        error("Invalid data.json: root must be an object.")
        return None

    required_keys = {
        "confirm",
        "randomize_next",
        "manual_select",
        "students",
        "year_text"
    }

    missing = required_keys - set(data.keys())

    if missing:
        error(
            "Invalid data.json: missing "
            + ", ".join(sorted(missing))
        )
        return None

    if not isinstance(data["confirm"], bool):
        error("Invalid data.json: confirm must be true or false.")
        return None

    if not isinstance(data["randomize_next"], bool):
        error(
            "Invalid data.json: randomize_next "
            "must be true or false."
        )
        return None

    if not isinstance(data["manual_select"], bool):
        error(
            "Invalid data.json: manual_select "
            "must be true or false."
        )
        return None

    if not isinstance(data["year_text"], str) or not data["year_text"].strip():
        error("Invalid data.json: year_text must be a non-empty string.")
        return None

    if not isinstance(data["students"], list) or not data["students"]:
        error(
            "Invalid data.json: students must be a non-empty list."
        )
        return None

    student_keys = {
        "student_id",
        "title",
        "name",
        "surname",
        "room",
        "number",
        "course",
        "teacher"
    }

    for index, student in enumerate(data["students"], start=1):
        if not isinstance(student, dict):
            error(f"Invalid data.json: student {index} must be an object.")
            return None

        missing_student = student_keys - set(student.keys())

        if missing_student:
            error(
                f"Invalid data.json: student {index} missing "
                + ", ".join(sorted(missing_student))
            )
            return None

        for key in student_keys:
            if not isinstance(student[key], str):
                error(
                    f"Invalid data.json: student {index} "
                    f"'{key}' must be a string."
                )
                return None

        if not student["course"].strip():
            error(
                f"Invalid data.json: student {index} "
                "course cannot be empty."
            )
            return None

        if not student["teacher"].strip():
            error(
                f"Invalid data.json: student {index} "
                "teacher cannot be empty."
            )
            return None

    notice("data.json is valid.", Fore.LIGHTGREEN_EX)
    return data



def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def notice(message, color=Fore.LIGHTMAGENTA_EX):
    line = f"[ NOTICE : {timestamp()} ] {message}"

    print(
        f"{color}{line}{Style.RESET_ALL}"
    )

    log_session_line(line)



def step(message):
    notice(message, Fore.LIGHTYELLOW_EX)


def success(message):
    notice(message, Fore.LIGHTGREEN_EX)


def error(message, color=Fore.LIGHTRED_EX):
    notice(message, color)


def separator():
    print(Fore.LIGHTBLACK_EX + "-" * 56)



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
            success(
                f"Course/teacher matched exactly: "
                f"{course_name} / {teacher_name}"
            )
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
            success("Confirmation checkbox selected.")
            return

        time.sleep(0.01 if not randomize_next else 0.05)

    raise RuntimeError(
        "Confirmation checkbox was found but could not be selected."
    )

def process_student(driver, student, index):
    started = time.perf_counter()

    full_name = (
        f"{student.get('title', '')}"
        f"{student.get('name', '')} "
        f"{student.get('surname', '')}"
    ).strip()

    course = student["course"]
    teacher = student["teacher"]

    try:
        step(f"Student {index}: Opening enrollment page")
        driver.get(BASE_URL + "enroll")

        try:
            total_students = len(students)
            arrange_browser(
                driver,
                index,
                total_students
            )
        except Exception:
            pass

        step(f"Student {index}: Selecting academic year")
        select_text(driver, "//select[1]", year_text)
        wait_next_delay()

        step(f"Student {index}: Continuing")
        click_text(driver, "เลือก")

        step(f"Student {index}: Filling student information")
        fill_student_page(driver, student)

        wait_next_delay()
        step(f"Student {index}: Opening course selection")
        click_text(driver, "ถัดไป")

        wait_next_delay()
        step(f"Student {index}: Selecting one course")
        click_text(driver, "เลือก 1 วิชา")

        wait_next_delay()
        step(f"Student {index}: Opening course list")
        click_text(driver, "ถัดไป")

        if manual_select:
            notice(
                f"Student {index}: Manual select is ON. "
                "Stopping at course selection page.",
                Fore.LIGHTYELLOW_EX
            )
            notice(
                f"Student {index}: Select the course manually. "
                "The browser will remain open.",
                Fore.LIGHTCYAN_EX
            )
            return index

        step(
            f"Student {index}: Searching course "
            f'"{course}" + "{teacher}"'
        )

        try:
            select_course(driver, course, teacher)
            success(f"Student {index}: Course found automatically")
        except TimeoutException:
            error(
                f"Student {index}: Course not found automatically"
            )
            print(
                Fore.LIGHTCYAN_EX +
                "Restore the browser, select the course manually, "
                "then press Enter here."
            )

            try:
                screen_width, screen_height = get_screen_size()

                manual_width = 1100
                manual_height = min(
                    800,
                    screen_height - 80
                )

                driver.set_window_rect(
                    x=max(
                        0,
                        (screen_width - manual_width) // 2
                    ),
                    y=35,
                    width=manual_width,
                    height=manual_height
                )
            except Exception:
                pass

            input(
                Fore.LIGHTCYAN_EX +
                f"[ Student {index} ] Press Enter after manual selection... "
            )

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

            success(f"Student {index}: Manual course selection detected")

        step(f"Student {index}: Selecting confirmation checkbox")
        select_confirmation(driver)

        elapsed = time.perf_counter() - started
        status = "Confirmed" if confirm else "Not confirm"

        success(
            f"Student {index} ({full_name}): "
            f"Completed in {elapsed:.2f}s"
        )
        notice(
            f"Class: {course} {teacher} -- {status}",
            Fore.LIGHTCYAN_EX
        )
        separator()

        if confirm:
            click_text(driver, "ลงทะเบียน")
            success(f"Student {index}: Registration submitted")
            driver.quit()
        else:
            notice(
                f"Student {index}: Final ลงทะเบียน was NOT clicked",
                Fore.LIGHTYELLOW_EX
            )
            notice(
                f"Student {index}: Browser remains open",
                Fore.LIGHTYELLOW_EX
            )

    except Exception as exc:
        elapsed = time.perf_counter() - started
        error(
            f"Student {index} ({full_name}): Failed after "
            f"{elapsed:.2f}s"
        )
        error(str(exc))
        notice(
            f"Class: {course} {teacher} -- Not completed",
            Fore.LIGHTRED_EX
        )
        separator()

        if driver is not None:
            print(
                Fore.LIGHTYELLOW_EX +
                f"Student {index}: Browser remains open for inspection."
            )
        else:
            print(
                Fore.LIGHTYELLOW_EX +
                f"Student {index}: Browser was not created."
            )

    return index

def create_driver(index):
    options = webdriver.ChromeOptions()
    options.page_load_strategy = "eager"
    options.add_argument("--start-maximized")

    profile_dir = Path(
        tempfile.mkdtemp(
            prefix=f"elective_student_{index}_"
        )
    )

    options.add_argument(
        f"--user-data-dir={profile_dir}"
    )

    return webdriver.Chrome(options=options)


def main():
    data = load_data()

    if data is None:
        return

    global confirm, randomize_next, manual_select, students, year_text
    global SESSION_FINAL_STATUS

    confirm = data["confirm"]
    randomize_next = data["randomize_next"]
    manual_select = data["manual_select"]
    students = data["students"]
    year_text = data["year_text"]

    notice("Running task...", Fore.LIGHTMAGENTA_EX)
    notice(
        f"Students: {len(students)} | "
        f"Parallel: ON | "
        f"Random delay: {'ON' if randomize_next else 'OFF'} | "
        f"Fast mode: {'OFF' if randomize_next else 'ON'} | "
        f"Manual select: {'ON' if manual_select else 'OFF'}",
        Fore.LIGHTYELLOW_EX
    )

    failed = 0
    futures = []

    # Pipeline:
    # 1. Start Student 1 Chrome.
    # 2. Immediately start Student 1's task.
    # 3. While Student 1 is working, start Student 2 Chrome.
    # 4. Repeat for the remaining students.
    with ThreadPoolExecutor(max_workers=len(students)) as executor:
        for index, student in enumerate(students, start=1):
            try:
                step(f"Student {index}: Starting Chrome")

                driver = create_driver(index)

                try:
                    arrange_browser(
                        driver,
                        index,
                        len(students)
                    )
                except Exception:
                    pass

                step(
                    f"Student {index}: Chrome ready, "
                    "starting task"
                )

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

                error(
                    f"Student {index}: Chrome could not start: {exc}"
                )

                notice(
                    f"Student {index}: No browser window was created.",
                    Fore.LIGHTYELLOW_EX
                )

    for future in as_completed(futures):
        try:
            future.result()
        except Exception as exc:
            failed += 1
            error(f"Worker error: {exc}")

    if failed:
        SESSION_FINAL_STATUS = "partial_failure"
        notice(
            f"All tasks finished with {failed} error(s).",
            Fore.LIGHTYELLOW_EX
        )
    else:
        SESSION_FINAL_STATUS = "completed"
        success("All tasks completed.")


if __name__ == "__main__":
    final_status = "completed"

    try:
        init_session()

        notice(
            f"Session: {SESSION_ID}",
            Fore.LIGHTCYAN_EX
        )

        main()

    except KeyboardInterrupt:
        final_status = "stopped_by_user"

        try:
            notice(
                "Stopped by user.",
                Fore.LIGHTYELLOW_EX
            )
        except Exception:
            print("[ NOTICE ] Stopped by user.")

    except Exception as exc:
        final_status = "fatal_error"

        try:
            error(
                f"Fatal error: {exc}"
            )

            log_session_line(
                "[ ERROR TRACEBACK ]"
            )
            log_session_line(
                traceback.format_exc()
            )

        except Exception:
            print(f"[ ERROR ] Fatal error: {exc}")

    finally:
        try:
            if final_status == "completed":
                final_status = SESSION_FINAL_STATUS

            finish_session(final_status)

            notice(
                f"Session saved: {SESSION_DIR.name}\\"
                f"{SESSION_ID}.txt",
                Fore.LIGHTGREEN_EX
            )

            notice(
                "Program finished. The window will stay open.",
                Fore.LIGHTYELLOW_EX
            )

        except Exception as exc:
            print(f"[ ERROR ] Could not save session: {exc}")

        try:
            input("Press Enter to close...")
        except EOFError:
            time.sleep(60)

