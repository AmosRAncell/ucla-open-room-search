from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, TimeField, SubmitField
from wtforms.validators import DataRequired

class RoomSearchForm(FlaskForm):
	term = SelectField('Term:',choices=['Fall','Winter','Spring'],validators=[DataRequired()])
	year = IntegerField('Year:',validators=[DataRequired()])
	dayOfWeek = SelectField('Day of Week:',choices=['Monday','Tuesday','Wednesday','Thursday','Friday'],validators=[DataRequired()])
	time = TimeField('Time:',validators=[DataRequired()])
	submit = SubmitField('Search')
