import os

class Config(object):
	SECRET_KEY = os.environ.get('SECRET_KEY') or 'howAboutThat,Thi$I$ARandomStringNotTheTranscriptionOfA1stYearCSStudentTryingToExitVim!'
