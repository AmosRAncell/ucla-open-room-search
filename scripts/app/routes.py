# NOTE: the database stuff with get_db, close_connection comes from: https://flask.palletsprojects.com/en/2.2.x/patterns/sqlite3/
from flask import render_template, flash, g
from app import app
from app.forms import RoomSearchForm

import sqlite3

DATABASEPATH = '/Users/amosancell/Documents/CodingProjects/UclaClassGridSearch/sqliteVersion/data/courseInfoData_fall21-fall22.db'

def get_db():
	db = getattr(g,'_database',None)
	if db is None:
		db = sqlite3.connect(DATABASEPATH)
		db.row_factory = sqlite3.Row
		g._database = db
	return db

@app.teardown_appcontext
def close_db_connection(exception):
	db = getattr(g,'_database',None)
	if db is not None:
		db.close()

def query_db(query,args,one=False):
	cur = get_db().execute(query,args)
	res = cur.fetchall()
	cur.close()
	return (res[0] if res else None) if one else res

def findOpenRooms(term,year,dayOfWeek,startTime,**kwargs):
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
			term = :TERM AND
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
	return query_db(queryStr,{
		'STARTTIME':startTime,
		'TERM':term,
		'YEAR':year,
		'DAYOFWEEK':dayOfWeek
	},**kwargs)

@app.route('/',methods=['GET','POST'])
@app.route('/index',methods=['GET','POST'])
def index():
	form = RoomSearchForm()
	if form.validate_on_submit():
		startTime = form.time.data.hour + form.time.data.minute/60
		flash(f'Search request for: term={form.term.data}, year={form.year.data}, dayOfWeek={form.dayOfWeek.data}, time={startTime}')
		openRooms = findOpenRooms(form.term.data,form.year.data,form.dayOfWeek.data,startTime)
		return render_template('index.html', form=form, openRooms=openRooms)
	return render_template('index.html', form=form)

