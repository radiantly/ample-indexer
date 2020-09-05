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
from CONFIG import userId, baseDomain, chrome_type
from CachedSession import CachedSession

from rich.console import Console
from rich.table import Table

console = Console()

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--ignore-ssl-errors")
# chrome_options.add_argument("--headless")

session = CachedSession(prefix_url=baseDomain)


def getFreshCookies():
    """Open a browser to retrieve the required cookies for the session"""

    browser = webdriver.Chrome(
        ChromeDriverManager(chrome_type=chrome_type).install(), options=chrome_options
    )

    browser.implicitly_wait(5)

    browser.get(urljoin(baseDomain, "/ssologin?tenant=CB"))

    # Wait for the user to enter their credentials and finally reach the dashboard
    WebDriverWait(browser, timeout=120).until(
        lambda driver: driver.current_url.startswith(urljoin(baseDomain, "/home"))
    )

    return browser.get_cookies()


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
        if testCookies(pickledCookies):
            return pickledCookies
    freshCookies = getFreshCookies()
    session.setCookies(freshCookies)
    pickle.dump(freshCookies, open(cookiePickle, "wb"))
    return freshCookies


def displayLevel(course, levelInfo, spaces=0):
    # Print level name if it exists
    if levelInfo["levelName"]:
        print(
            f"{' ' * spaces}{levelInfo['levelName']} | {levelInfo['levelType']} | {levelInfo['levelID']}"
        )

    # If it has no more subLevels, check if we need to retrieve the level information
    if not levelInfo["subLevels"]:
        if levelInfo["levelType"] in [2, 3]:
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
                print(f"{' ' * (spaces + 2)} {classRoom['classroomType']} {classRoom['fileName']} ")
        return
    for sublevel in levelInfo["subLevels"]:
        displayLevel(course, sublevel, spaces + 2)


def main():
    # Initiate session (set required cookies)
    initSession()

    # Get course list
    dashDetails = session.post(
        "/userDashboardData", data={"userType": "Student", "userID": userId}
    ).json()
    print(f"Name: {dashDetails['userName']}")
    print(f"User Id: {dashDetails['userID']}")

    # Print the course details in a nice table
    table = Table(show_header=True)
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

        displayLevel(course, courseStructure)

    print(f"Requests made: {session.request_count}")

    # Pickle the entire structure for use in other scripts
    with open("index.pkl", "wb") as indexFile:
        pickle.dump(dashDetails, indexFile)


if __name__ == "__main__":
    main()
