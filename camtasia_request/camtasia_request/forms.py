# camtasia_request/forms.py

#from pyramid_wtforms import Form
from wtforms import Form, TextField, TextAreaField, SelectField, RadioField, BooleanField, validators
#from wtforms.csrf.session import SessionCSRF
from datetime import date, timedelta
from os import urandom

# month constants for expiration choices function
JAN = 1
SEP = 9
DEC = 12
FEB = 2
JUN = 6


#class RequestForm(BaseForm):
class RequestForm(Form):
    def get_expiration_choices():
        year = date.today().year
        month = date.today().month
        if month == JAN or (month >= SEP and month <= DEC):
            semester = 'Fall'
        elif month >= FEB and month <= JUN:
            semester = 'Spring'
        else: # month is between
            semester = 'Summer'
        choices = ['Do Not Delete', semester + " " + str(year)]
        while len(choices) < 10:
            if semester == 'Fall':
                year += 1
                semester = 'Spring'
            elif semester == 'Spring':
                semester = 'Summer'
            else: # semester == Summer
                semester = 'Fall'
            choices.append(semester + " " + str(year))
        return zip(choices, choices)

    # get OU and Course names from views
    # gets list of courses for selection
    
    course = RadioField('Select course',
        description="Which course do you want a profile for on the Camtasia Relay server?",
        validators=[validators.InputRequired(message="You must select a course")],
        coerce=int
        )
    
    # checkboxes for options
    embed = BooleanField("Would you like us to embed your videos on your course D2L homepage?",
        description="We have the option of embedding your recordings directly on the homepage of your course. This will allow new recordings to be available for students in a central location as soon as they have been created. Alternatively, you can manually add the content to D2L within your course modules.")
    download = BooleanField(" Would you like to allow your students to be able to download your recordings?",
        description="Checking this will allow students to download a copy of the file for personal use when they are offline.")
    share = BooleanField(" Would you like to allow your students to share your recordings?",
        description="Checking this will allow students to get an embed code so they may include the recording in a portfolio. It will also provide tools for students to share the recording via Facebook, Twitter, LinkedIn and other social media outlets.")
    training = BooleanField("Training?",
        description="Would you like some training? One on One and group training is available for Relay and MediaSpace.")

    # text field for recording location
    location = TextAreaField("Recording Location",
        description="The room number of the classroom you'll be teaching from. We ask so we can check to ensure the software and a working mic is installed. If you are planning on recording from your office or home let us know that here as well.",
        validators=[validators.InputRequired(message="You must enter a location--classroom, office, or home.")])

    # text field for course name - in case D2L provided coursename is unsatisfactory
    courseName = TextAreaField("Course Name",
        description="Course Name as you would like it to appear. (ie Virology, Intro to Early Civ, Pathophysiology II)",
        validators=[validators.InputRequired(message="You must enter a course name")]
        )

    # text box for additional comments
    comments = TextAreaField("Any additional information you want to give us?")

    # select field for date after which files will not be needed on the server
    expiration = SelectField("Expiration Date",
        description="We'd like to know how long you want the files to stay on the server. We won't make a habit of deleting them, but this will make it easier when we have to. Deletion will occur no earlier than the term specified.",
        default="Do Not Delete",
        choices=get_expiration_choices())

    