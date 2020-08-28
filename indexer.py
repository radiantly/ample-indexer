import sys
import pickle
import urllib
import requests
from time import sleep
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.utils import ChromeType
from CONFIG import userId, baseDomain

from rich.console import Console
from rich.table import Table

console = Console()

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--ignore-ssl-errors")
# chrome_options.add_argument("--headless")


def getFreshCookies():
    browser = webdriver.Chrome(
        ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(), options=chrome_options
    )

    browser.implicitly_wait(5)

    browser.get(f"{baseDomain}/ssologin?tenant=CB")

    WebDriverWait(browser, timeout=120).until(
        lambda driver: driver.current_url.startswith(f"{baseDomain}/home")
    )

    return browser.get_cookies()


def initSession(cookies):
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie["name"], cookie["value"])
    return session


def testCookies(cookies):
    try:
        initSession(cookies).post(f"{baseDomain}/userHeaderData", json={"userID": userId},).json()
        return True
    except:
        return False


def getCookies():
    cookiePickle = Path("cookies.pkl")
    if cookiePickle.exists():
        pickledCookies = pickle.load(open(cookiePickle, "rb"))
        if testCookies(pickledCookies):
            return pickledCookies
    freshCookies = getFreshCookies()
    pickle.dump(freshCookies, open(cookiePickle, "wb"))
    return freshCookies


# def displayClassRoom():


def displayLevel(course, levelInfo, req, spaces=0):
    if not levelInfo:
        levelInfo = course

    if levelInfo["levelName"]:
        print(
            f"{' ' * spaces}{levelInfo['levelName']} | {levelInfo['levelType']} | {levelInfo['levelID']}"
        )
    if not levelInfo["subLevels"]:
        if levelInfo["levelType"] in [2, 3]:
            levelData = req.get(
                f"{baseDomain}/learning_manager/getLevelData",
                params={
                    "levelid": levelInfo["levelID"],
                    "level": "3",
                    "clid": course["clid"],
                    "lid": "5",
                    "batchID": course["batchID"],
                    "userType": "student",
                },
            ).json()
            # print(levelData.text)
            # sys.exit()
            for classRoom in levelData["classroomList"]:
                print(f"{' ' * (spaces + 2)} {classRoom['classroomType']} {classRoom['fileName']} ")
        return
    for sublevel in levelInfo["subLevels"]:
        displayLevel(course, sublevel, req, spaces + 2)


def main():
    req = initSession(getCookies())

    dashDetails = req.post(
        f"{baseDomain}/userDashboardData", data={"userType": "Student", "userID": userId}
    ).json()
    print(f"Name: {dashDetails['userName']}")
    print(f"User Id: {dashDetails['userID']}")
    # print(f"Batch Id:{dashDetails['centreBatchData']['batchID']}")

    table = Table(show_header=True)
    table.add_column("Course code")
    table.add_column("CourseID")
    table.add_column("clid")
    table.add_column("BatchID")
    for course in dashDetails["studentCourseList"]:
        table.add_row(course["courseCode"], course["courseID"], course["clid"], course["batchID"])
    console.print(table)

    for course in dashDetails["studentCourseList"]:
        clg = course["clid"]
        batchId = course["batchID"]

        courseStructure = req.post(
            f"{baseDomain}/learning_manager/myCourseContent",
            data={"userType": "student", "langID": "5", "clg": clg, "batchID": batchId},
        ).json()
        print(course["courseName"])
        displayLevel(course, courseStructure, req)


if __name__ == "__main__":
    main()
