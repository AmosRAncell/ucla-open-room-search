# This is useful if ran the scraper for different terms
# takes multiple databases (output from the scraper) and combines them

import sqlite3

# ----- User Input -----
concatDB = './../data/courseInfoData_fall21-fall22.db'

dbPaths = [
	'./../data/courseInfoData_fall21.db',
	'./../data/courseInfoData_winter22.db',
	'./../data/courseInfoData_spring22.db',
	'./../data/courseInfoData_fall22.db'
]
# ----------------------

concatConn = sqlite3.connect(concatDB)
concatCur = concatConn.cursor()

conns = [sqlite3.connect(dbPath) for dbPath in dbPaths]
curs  = [conn.cursor() for conn in conns]

cols = """
	term,
	year,
	building,
	room,
	dayOfWeek,
	title,
	enrollment,
	startTime,
	endTime
"""
colsPlaceholder = ', '.join(['?']*len(cols.strip().split('\n')))


concatCur.execute(f"""
CREATE TABLE courses(
	{cols}
)
""")

for cur in curs:
	res = cur.execute(f"""
		SELECT
			{cols}
		FROM
			courses
	""")
	concatCur.executemany(f"""
		INSERT INTO
			courses({cols})
		VALUES({colsPlaceholder})
	""",res)

concatConn.commit()

for conn in conns + [concatConn]:
	conn.close()
