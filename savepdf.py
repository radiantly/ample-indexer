import re
import pickle
import requests
from pathlib import Path
from requests.compat import urljoin
from CONFIG import baseDomain, directoryMap, baseDir

basePath = Path(baseDir)


def safeFileName(filename: str):
    return re.sub(r"[*?:/\\<>{}\"]", "", filename)


def getFileList(course):
    if "subLevels" not in course or not course["subLevels"]:
        if "classroomList" in course:
            return [
                (classRoom["contentName"], classRoom["fileName"])
                for classRoom in course["classroomList"]
                if classRoom["classroomType"] == "PDF"
            ]
        return []

    files = []

    for sublevel in course["subLevels"]:
        files.extend(getFileList(sublevel))
    return files


def main():
    # Retrieve index from index.pkl
    index = pickle.load(open("index.pkl", "rb"))

    for course in index["studentCourseList"]:

        # Skip course if save directory not specified
        if course["courseCode"] not in directoryMap:
            print(f"{course['courseCode']} not found in directory map. Skipping.")
            continue

        # Check if save directory actually exists
        localCourseFolder = basePath / directoryMap[course["courseCode"]]
        if not localCourseFolder.exists():
            print(f"Cannot find {localCourseFolder.as_posix()}")
            continue

        # Save resources in an Ample folder (create if it does not exist)
        resourceSaveDir = localCourseFolder / "Ample"
        resourceSaveDir.mkdir(exist_ok=True)

        resourceUrl = urljoin(
            baseDomain, f"/resources/userspace/Courses/{course['courseID']}/ClassroomDocument/EN/"
        )

        for contentName, fileName in getFileList(course):
            diskFilePath = resourceSaveDir / f"{safeFileName(contentName)}.pdf"

            # If file already exists, skip
            if diskFilePath.exists():
                continue

            # Else download the file
            print(diskFilePath.as_posix())
            response = requests.get(urljoin(resourceUrl, fileName))
            with open(diskFilePath, "wb") as f:
                f.write(response.content)


if __name__ == "__main__":
    main()
