import json # used to turn a string of a list into a list, e.g "['a','b']" --> ['a','b']
import time # used to delay requests so as to not overwhelm the server
import sqlite3

# used for scraping
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# ----- User Input -----
quartersToGet = [
	# (2021,'Fall'),
	# (2022,'Winter'),
	# (2022,'Spring'),
	(2022,'Fall'),
]

infoDB_outN = './../data/courseInfoData_fall22.db'
# ----------------------

### Start a headless (i.e no GUI) Selenium driver
op = webdriver.ChromeOptions()
op.add_argument('--headless')
driver = webdriver.Chrome(ChromeDriverManager().install(),options=op)

# Create a connection & cursor to the database and create the courses table
conn = sqlite3.connect(infoDB_outN)
cur = conn.cursor()
cur.execute("""
	CREATE TABLE IF NOT EXISTS courses(term,year,building,room,dayOfWeek,title,enrollment,startTime,endTime);
""")

### Get list of classes and their buildings/room names ###
print('Getting class and building names')
classListURL = "https://sa.ucla.edu/RO/Public/SOC/Search/ClassroomGridSearch"
driver.get(classListURL)

js = """
return document
	.querySelector('ucla-sa-soc-app')
	.shadowRoot
	.querySelector('#classroom_autocomplete')
""".strip() # the js to find the tag containing a list of the building and room names

classes = driver.execute_script(js).get_attribute('options') # options is now a string representation of the desired list
classes = json.loads(classes) # convert the string of lists into a Python list

# classes contains pairs of the form {'text': 'BOELTER  7738', 'value': 'BOELTER |  07738  '}
# we now unpack these pairs into an easier format to work with
classInfo = []
for pair in classes:
	text,value	= pair.values()
	building	= value.split('|')[0].strip()
	roomNumber	= value.split('|')[1].strip()
	if building == 'ONLINE':
		continue
	# classQueryParam is the URL parameter corresponding to the website with the class' schedule
	classQueryParam = value.replace(' ','+').replace('|','%7C')
	classInfo.append([building,roomNumber,classQueryParam])

# yield successive chunks from arr
def chunkList(arr,chunkSize):
	for i in range(0,len(arr),chunkSize):
		yield arr[i:i+chunkSize]

# NOTE: maybe better for classInfo to be a list of dicts? Or named tuples?

### Now that we have a list of classes, we scrape each of their schedules ###
daysOfWeek = ['Monday','Tuesday','Wednesday','Thursday','Friday']

# returns the 
def getRoomURL(termName,year,classQueryParam):
	baseURL = 'https://sa.ucla.edu/ro/Public/SOC/Results/ClassroomDetail'
	year = str(year) # allows year to be passed as a string or int
	termCode = termName[0].upper() # makes function case-insensitive to termName
	if termName.lower().startswith('summer sessions'):
		termCode = '1'
	elif termName.lower().startswith('summer'):
		termCode = '2'
	term = f'{year[-2:]}{termCode}'
	return f'{baseURL}?term={term}&classroom={classQueryParam}'

def parseTimeStr(timeStr):
	num,off = timeStr.split(' ')
	hours,mins = map(int,num.split(':'))
	return (hours%12) + (mins/60) + (0 if off == 'AM' else 12)

def getCourseInfo(td):
	allCourseInfo = []
	for courseDiv in td.find_elements(By.CLASS_NAME,'fc-content'):
		timeDiv = courseDiv.find_elements(By.CLASS_NAME,'fc-time')
		msg = 'no time div found'
		assert len(timeDiv) == 1,msg
		courseTime = timeDiv[0].get_attribute('data-full')
		startTime = parseTimeStr(courseTime.split(' - ')[0])
		endTime = parseTimeStr(courseTime.split(' - ')[1])
		titleDiv = courseDiv.find_elements(By.CLASS_NAME,'fc-title')
		msg = 'no title div found'
		assert len(titleDiv) == 1,msg
		info = titleDiv[0].text.split('\n')
		title = ', '.join(info[:2])
		try :
			enrollmentInfo = info[2]
		except IndexError:
			print(f'Error getting enrollment info. info = {info}, title = {title}')
			enrollmentInfo = None
		allCourseInfo.append([title,enrollmentInfo,startTime,endTime])
	return allCourseInfo

# returns info for all courses in a week for a specific room
# driver is a selenium webdriver with the room's schedule page already loaded
# e.g driver.get(roomURL) has already been run
#     where roomURL is something like "https://sa.ucla.edu/ro/Public/SOC/Results/ClassroomDetail?term=222&classroom=BUNCHE++%7C++03178++"
def getRoomCourseInfo(driver):
	pathToClassScheduleData = "div#calendar div.fc-content-skeleton table tbody tr"
	js = """
		return document
			.querySelector('ucla-sa-soc-app').shadowRoot
			.querySelector('{}')
	""".format(pathToClassScheduleData).strip()
	tr = driver.execute_script(js)
	if tr is None:
		return None
	info = {}
	for i,td in enumerate(tr.find_elements(By.TAG_NAME,'td')[1:]):
		courseInfo = getCourseInfo(td)
		if len(courseInfo) == 0: continue
		info[daysOfWeek[i]] = courseInfo
	return info

# returns the info for all courses in classInfoDf in a given term (e.g Spring or Fall) and year (e.g 2022)
def getAllCourseInfo(termName,year,classInfo,driver):
	info = {}
	getTimes = []
	for i,(building,roomName,classQueryParam) in enumerate(classInfo):
		if i % 50 == 0: print(f'{i}/{len(classInfo)} pages scraped')
		roomURL = getRoomURL(termName,year,classQueryParam)
		start = time.time()
		driver.get(roomURL)
		getTime = time.time() - start
		getTimes.append(getTime)
		roomCourse = getRoomCourseInfo(driver)
		if roomCourse is None: continue
		info[(termName,year,building,roomName)] = roomCourse
		time.sleep(2*getTime) # to not overwhelm the website
	print(f'Mean get time: {sum(getTimes)/len(getTimes)}')
	return info

# info should be the output of getAllCourseInfo
# returns info unpacked to a list
def unpackCourseInfo(info):
	infoAsList = []
	for (termName,year,building,roomName),coursesInRoom in info.items():
		if coursesInRoom is None: continue
		for dayOfWeek,courseInfo in coursesInRoom.items():
			for title,enrollment,startTime,endTime in courseInfo:
				infoAsList.append([termName,year,building,roomName,dayOfWeek,title,enrollment,startTime,endTime])
	return infoAsList

insertStr = "INSERT INTO courses VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"

start = time.time()
allInfo = []
for yr,quarter in quartersToGet:
	print(f'Getting info for courses in {quarter} {yr}')
	for i,chunk in enumerate(chunkList(classInfo,100)):
		print(f'chunk {i} of {len(classInfo)//100+1}')
		chunkStart = time.time()
		info = getAllCourseInfo(quarter,yr,chunk,driver)
		print(f'{(time.time() - chunkStart)/60:.2f} minutes taken')
		cur.executemany(insertStr,unpackCourseInfo(info))
		conn.commit()

conn.close()
driver.close()

print(f'In total, {(time.time() - start)/60:.2f} minutes taken')

# TODO:
#	* add error catching for getAllCourseInfo to close driver if an error
#	* have the SQL look to see if the database is already created, in which case it should update new rows
#	* insert the values every yr-quarter so if there is a crash, some data might be saved?
#	* change to CREATE TABLE __ IF NOT EXISTS ___
#	* add messages and error catching to the assert statements
#	* the issue is with classInfo[733]: 'ONLINE', '00000RE', 'ONLINE++%7C++00000RE'
#		* so the easy thing is to exclude these 'ONLINE' rooms as they obv aren't physical rooms and hence aren't relevant to this project
#		* but it also raises the issue that calling .text isn't getting the correct thing. using titleDiv[0].get_attribute('innerHTML') gets the full text. Maybe this is what I should be parsing
