import sqlite3

# ----- User Input -----
YEAR = 2022
QUARTER = 'Fall'
DAYOFWEEK = 'Thursday'

STARTTIME = '3:30 PM'
# ----------------------

conn = sqlite3.connect('./../data/courseInfoData_fall21-fall22.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def parseTimeStr(timeStr):
	num,off = timeStr.split(' ')
	hours,mins = map(int,num.split(':'))
	return (hours%12) + (mins/60) + (0 if off == 'AM' else 12)

queryStr = '''
WITH nextCourses AS (
	SELECT
		*,
		startTime - :STARTTIME AS 'hoursTillNextClass',
		ROW_NUMBER() OVER (
			PARTITION BY building,room
			ORDER BY startTime DESC
		) AS "rowNumber"
	FROM
		courses
	WHERE
		term = :QUARTER AND
		year = :YEAR AND
		dayOfWeek = :DAYOFWEEK AND
		startTime > :STARTTIME
)
SELECT
	*
FROM
	nextCourses
WHERE
	rowNumber = 1
ORDER BY
	hoursTillNextClass DESC,
	building ASC,
	room ASC
'''
res = cur.execute(queryStr,{
	'STARTTIME':parseTimeStr(STARTTIME),
	'QUARTER':QUARTER,
	'YEAR':YEAR,
	'DAYOFWEEK':DAYOFWEEK
})
res = [*res]

if len(res) == 0:
	print('Sorry, no classrooms available for rest of day')

for i,row in enumerate(res):
	print(dict(row))
	if i == 9: break

conn.close()
