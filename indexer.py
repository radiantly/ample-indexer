import sys
import pickle
import urllib
import requests
from time import sleep
from pathlib import Path
from requests.compat import urljoin
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from CachedSession import CachedSession

from rich.console import Console
from rich.table import Table

try:
    from CONFIG import chrome_type, user_email, user_passw

    replMode = False
except:
    from getpass import getpass

    replMode = True


baseDomain = "ude.atirma.elpma//:sptth"[::-1]
session = CachedSession(prefix_url=baseDomain)

userId = None


def retrieveUserId():
    global userId
    indexPickle = Path("index.pkl")
    if indexPickle.exists():
        try:
            userId = pickle.load(open(indexPickle, "rb"))["userID"]
            return userId
        except:
            indexPickle.unlink()


def getFreshCookies():
    """Open a browser to retrieve the required cookies for the session"""

    global userId
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")

    # To store session. But this doesn't work well.
    # chrome_options.add_argument("--user-data-dir=chrome-data")

    # Headless mode. Comment this if you're facing issues with selenium

    if replMode:
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        user_email = input("Enter your student email id: ")
        user_passw = getpass("Enter your password: ")
        browser = webdriver.Chrome(options=chrome_options)
    else:
        chrome_options.add_argument("--headless")
        browser = webdriver.Chrome(
            ChromeDriverManager(chrome_type=chrome_type).install(), options=chrome_options
        )

    browser.implicitly_wait(5)

    browser.get(urljoin(baseDomain, "/ssologin?tenant=CB"))

    print("Entering email..")
    browser.find_element_by_css_selector("[type=email]").send_keys(user_email)
    browser.find_element_by_css_selector("[type=submit]").click()
    sleep(1)

    print("Entering password..")
    browser.find_element_by_css_selector("[type=password]").send_keys(user_passw)
    browser.find_element_by_css_selector("[type=submit]").click()
    sleep(1)

    noButton = browser.find_elements_by_css_selector("[type=button]")
    if noButton:
        noButton[0].click()

    print("Waiting for redirect..")
    WebDriverWait(browser, timeout=5).until(
        lambda driver: driver.current_url.startswith(urljoin(baseDomain, "/home"))
    )

    userId = browser.find_element_by_id("userID").get_attribute("value")

    return browser.get_cookies(), userId


def testCookies(cookies):
    """Test if the cookies are still active by sending a request"""
    # The error response is invalid json, so if json conversion fails, we
    # assume that the cookies are no longer good.
    try:
        session.setCookies(cookies).post("/userHeaderData", json={"userID": userId}).json()
        return True
    except:
        return False


def initSession():
    cookiePickle = Path("cookies.pkl")
    if cookiePickle.exists():
        pickledCookies = pickle.load(open(cookiePickle, "rb"))
        if not retrieveUserId():
            cookiePickle.unlink()
            print(
                "Error. Please re-run. If you get this error multiple times, get in touch with the creator."
            )
            sys.exit(1)
        if testCookies(pickledCookies):
            return session
    freshCookies, uId = getFreshCookies()
    session.setCookies(freshCookies)
    pickle.dump(freshCookies, open(cookiePickle, "wb"))
    return session


def displayLevel(course, levelInfo, spaces=0):
    # Print level name if it exists
    if levelInfo["levelName"]:
        print(
            f"{' ' * spaces}{levelInfo['levelName']} | {levelInfo['levelType']} | {levelInfo['levelID']}"
        )

    # If it has no more subLevels, check if we need to retrieve the level information
    if not levelInfo["subLevels"]:
        if levelInfo["levelType"] in [1, 2, 3]:
            levelData = session.get(
                "/learning_manager/getLevelData",
                params={
                    "levelid": levelInfo["levelID"],
                    "level": levelInfo["levelType"],
                    "clid": course["clid"],
                    "lid": "5",  # Language ID = 5 (English)
                    "batchID": course["batchID"],
                    "userType": "student",
                },
            ).json()
            # print(levelData.text)
            levelInfo["classroomList"] = levelData["classroomList"]
            for classRoom in levelData["classroomList"]:
                if classRoom["classroomType"] != "HTML":  # Hide HTML because it fills the terminal
                    print(
                        f"{' ' * (spaces + 2)} {classRoom['classroomType']} {classRoom['fileName']} "
                    )

        # So, if files exist on the level as well as sublevels, we need to send an additional
        # request to ascertain whether sublevels exist. Atm only sending this request for
        # Units (level type = 1), but this might need to be sent for sublevels too.
        if levelInfo["levelType"] in [1]:
            levelCourseContent = session.post(
                "/learning_manager/levelWiseCourseContent",
                data={
                    "levelID": levelInfo["levelID"],
                    "clg": course["clid"],
                    "langID": "5",  # Language ID = 5 (English)
                    "batchID": course["batchID"],
                },
            ).json()
            levelInfo["subLevels"] = levelCourseContent["subLevels"]
            # print(levelInfo["subLevels"].text)
            # sys.exit()
            if not levelInfo["subLevels"]:
                return
        else:
            return
    for sublevel in levelInfo["subLevels"]:
        displayLevel(course, sublevel, spaces + 2)


def main():
    # Initiate session (set required cookies)
    initSession()

    console = Console()

    # Get course list
    dashDetails = session.post(
        "/userDashboardData", data={"userType": "Student", "userID": userId}
    ).json()
    print(f"Name: {dashDetails['userName']}")
    print(f"User Id: {dashDetails['userID']}")

    # Print the course details in a nice table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Course code")
    table.add_column("CourseID")
    table.add_column("clid")
    table.add_column("BatchID")
    for course in dashDetails["studentCourseList"]:
        table.add_row(course["courseCode"], course["courseID"], course["clid"], course["batchID"])
    console.print(table)

    # For each course
    for course in dashDetails["studentCourseList"]:
        clg = course["clid"]  # Interestingly, clid stands for "Course Language ID"
        batchId = course["batchID"]

        # Retrieve basic course structure for each course.
        # The response is a nested structure with multiple subLevels.
        courseStructure = session.post(
            "/learning_manager/myCourseContent",
            data={"userType": "student", "langID": "5", "clg": clg, "batchID": batchId},
        ).json()

        course["subLevels"] = courseStructure["subLevels"]

        # Print course code and levels
        console.print(f"{course['courseCode']} - {course['courseName']}", style="bold red")

        # Print sublevels
        displayLevel(course, courseStructure)

    print(f"Requests made: {session.request_count}")

    # Pickle the entire structure for use in other scripts
    with open("index.pkl", "wb") as indexFile:
        pickle.dump(dashDetails, indexFile)


if __name__ == "__main__":
    main()
