from webdriver_manager.utils import ChromeType

# Your user id
userId = "longGibberishHere"

# Base domain
baseDomain = "https://domain.com"

# What browser to use while retrieving cookies
# ChromeType.GOOGLE = Google Chrome
# ChromeType.CHROMIUM = Chromium
# ChromeType.MSEDGE = Microsoft Edge
chrome_type = ChromeType.GOOGLE

# For savepdf.py

# Base directory
# For Windows, this may need to be something like:
# baseDir = r"C:\Users\radiantly\Documents\AmpleStuff"
baseDir = "/mnt/gdrive10"

# The directory in which pdfs for each subject is to be stored
# Each key should be in the format "Course code": "Directory name"
directoryMap = {
    "19CCE201": "MIT",
    "19CCE202": "DSA",
    "19CCE204": "Signal",
    "19MAT205": "Math",
    "CIR_SSK211": "CIR",
}
