import sys
import pickle
from time import sleep
from threading import Timer
from signal import signal, SIGINT
from datetime import timedelta

from rich.console import Console
from rich.table import Table

from indexer import initSession


def findLevel(course, searchId):
    if "subLevels" not in course or not course["subLevels"]:
        if "classroomList" in course:
            for classRoom in course["classroomList"]:
                if classRoom["classroomID"] == searchId:
                    return classRoom

    else:
        for sublevel in course["subLevels"]:
            classRoom = findLevel(sublevel, searchId)
            if classRoom:
                return classRoom
    return False


def getInterestingClassrooms(course, classrooms):
    interestingClasses = []
    for cr in classrooms:
        if (
            cr["classroomType"] != "Assessment"
            and cr["progress"] != 100
            and cr["durationHHMMTT"] != "00:00:00"
        ):
            classDetails = findLevel(course, cr["classroomID"])

            currentWatchTime = list(map(int, cr["timeTakenHHMMTT"].split(":")))
            finalWatchTime = list(map(int, cr["durationHHMMTT"].split(":")))

            currentWatchTimedelta = timedelta(
                minutes=currentWatchTime[1], seconds=currentWatchTime[2]
            )
            finalWatchTimedelta = timedelta(minutes=finalWatchTime[1], seconds=finalWatchTime[2])

            watchTimeLeft = finalWatchTimedelta - currentWatchTimedelta

            if classDetails and watchTimeLeft > timedelta():
                interestingClasses.append((cr, classDetails, watchTimeLeft))
    return interestingClasses


timers = []


def handleCtrlC(sig, frame):
    print("SIGINT received. Saving time..")
    for timer, timerArgs in timers:
        timer.cancel()
        func, args, kwargs = timerArgs[1:]
        print(func(*args, **kwargs).json())

    sys.exit()


def main():
    session = initSession()

    console = Console()

    index = pickle.load(open("index.pkl", "rb"))

    for i, course in enumerate(index["studentCourseList"]):
        console.print(f"[green]{i + 1}.[/green] {course['courseCode']} {course['courseName']}")

    course = index["studentCourseList"][int(input("Enter your choice: ")) - 1]

    progress = session.post(
        "/getCourseProgressReport",
        params={
            "userID": index["userID"],
            "courseLanguageID": course["clid"],
            "batchID": course["batchID"],
            "cloud": "false",
        },
    ).json()

    # Print the course details in a nice table
    table = Table(show_header=True, header_style="bold bright_blue")
    table.add_column("No.")
    table.add_column("Classroom ID")
    table.add_column("Name")
    table.add_column("Progress")
    table.add_column("Time taken")
    for i, classroom in enumerate(progress["courseProgress"]):
        table.add_row(
            str(i + 1),
            classroom["classroomID"],
            classroom["classroomName"],
            str(classroom["progress"]),
            f"{classroom['timeTakenHHMMTT']}[grey50]/{classroom['durationHHMMTT']}[/grey50]",
            style="grey50"
            if classroom["classroomType"] == "Assessment"
            else "chartreuse3"
            if classroom["progress"] == 100
            else "deep_pink3"
            if classroom["progress"] == 0
            else None,
        )
    console.print(table)

    fix = input(f"[1-{len(progress['courseProgress'])}] What would you like to watch? ")

    if not fix:
        classes = getInterestingClassrooms(course, progress["courseProgress"][::-1])[:3]
    else:
        chosenClasses = [
            progress["courseProgress"][int(classIndex) - 1] for classIndex in fix.split()
        ]
        classes = getInterestingClassrooms(course, chosenClasses)

    global timers
    for classroom, classDetails, watchTimeLeft in classes:
        reqJson = {
            "description": "Started",
            "type": "resource",
            "id": classroom["classroomID"],
            "clid": course["clid"],
            "batchID": course["batchID"],
            "userType": "student",
            "relatedTo": "null",
            "levelID": classDetails["levelID"],
            "batchCourseID": course["batchCourseID"],
        }

        lessonReq = session.post(
            "/learning_manager/track",
            json=reqJson,
        ).json()

        print(classroom["classroomID"], lessonReq)
        reqJson["description"] = "Stopped"
        reqJson["relatedTo"] = lessonReq["trackingID"]

        timerArgs = (
            watchTimeLeft.total_seconds(),
            session.post,
            ["/learning_manager/track"],
            {"json": reqJson},
        )
        timer = Timer(*timerArgs)
        timer.start()
        timers.append((timer, timerArgs))

    signal(SIGINT, handleCtrlC)

    waitTime = int(max([w[2].total_seconds() for w in classes]))
    while waitTime:
        mins, secs = divmod(waitTime, 60)
        print(f"Time left: {mins:02d}:{secs:02d}", end="\r")
        sleep(1)
        waitTime -= 1


if __name__ == "__main__":
    main()