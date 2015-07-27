from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid import threadlocal
from pyramid_mailer import get_mailer
from pyramid_mailer.message import Message
from datetime import date
from ConfigParser import SafeConfigParser
import requests
# local modules
import auth2 as d2lauth
from forms import SelectCoursesForm, AdditionalCourseForm

# constants for calculating semester code
BASE_YEAR = 1945
FALL = '0'
SPRING = '5'
SUMMER = '8'

JAN = 1
MAY = 5
AUG = 8
DEC = 12

parser = SafeConfigParser()
parser.read('development.ini')

appContext = d2lauth.fashion_app_context(
    app_id=parser.get('app:main', 'APP_ID'),
    app_key=parser.get('app:main', 'APP_KEY'))


@view_config(route_name='logout')
def logout(request):
    '''
    Dumps session data
    '''
    request.session.invalidate()
    return HTTPFound(
        location=request.registry.settings['REDIRECT_AFTER_LOGOUT'])


@view_config(route_name='login', renderer='templates/login.jinja2')
def login(request):
    '''
    Generates login URL, post-authorization callback URL, and links it from
    login page.
    '''
    csrf_token = request.session.get_csrf_token()
    auth_callback = '{0}://{1}:{2}{3}'.format(
        request.registry.settings['SCHEME'],
        request.registry.settings['HOST'],
        request.registry.settings['PORT'],
        request.registry.settings['AUTH_ROUTE']
        )

    auth_url = appContext.create_url_for_authentication(
            host=request.registry.settings['LMS_HOST'], 
            client_app_url=auth_callback,
            encrypt_request=request.registry.settings['ENCRYPT_REQUESTS'])
    return {'auth_url': auth_url, 'csrf_token': str(csrf_token)}


@view_config(route_name='request', renderer='templates/request.jinja2')
def request_form(request):
    '''
    Creates two forms on one page, one for selecting courses to be combined
    and one for adding courses to the list of options for course combinations.
    '''
    #session = request.session
    csrf_token = request.session.get_csrf_token()

    current_session = session_exists(request)
    if not current_session:
        return HTTPFound(location=request.route_url('login'))
    else:
        uc, service_uc = current_session
    user_data = get_user_data(uc, request)
    store_user_data(request, user_data)
    semester_code = get_semester_code()
    
    if 'course_list' in request.session:
        course_list = request.session['course_list']
    else:
        request.session['course_list'] = course_list = \
            get_courses(service_uc, semester_code, request)

    form = SelectCoursesForm(request.POST, prefix="form")
    form.courseIds.choices = get_courseId_choices(course_list)

    # Flash message if no courses are found for this semester.
    if form.courseIds.choices == []:
        request.session.flash('No courses were found in D2L for this semester.\
            Please <a href="http://www.uwosh.edu/d2lfaq/d2l-login">log into \
            D2L</a> to confirm you have classes in D2L.')
        return {'form': form, 'add_form': add_form, 'csrf_token': csrf_token}
    form.baseCourse.choices = get_baseCourse_choices(course_list, request)
    add_form = AdditionalCourseForm(request.POST, prefix="add_form")
    if request.method == 'POST':
        if 'Add Class' in request.POST:
            return process_add_class(service_uc, request, form, add_form, semester_code)
        if 'Submit Request' in request.POST:
            return process_combine_request(form, add_form, course_list, request)
        else:
            return {'form': form, 'add_form': add_form, 'csrf_token': csrf_token}
    else:
        return {'form': form, 'add_form': add_form, 'csrf_token': csrf_token}


@view_config(route_name='check', renderer='templates/check.jinja2')
def check(request):
    '''
    Generates a pre-confirmation check page to present when user selects one
    course from the combine list and a different one from the base course list.
    '''
    if not logged_in(request):
        return HTTPFound(location=request.route_url('login'))
    return {'baseCourse': request.session['base_course'],
        'coursesToCombine': request.session['courses_to_combine']}


@view_config(route_name='confirmation', renderer='templates/confirmation.jinja2')
def confirmation(request):
    '''
    Generates confirmation page and confirmation emails to user and D2L site 
    admin.
    '''
    if not logged_in(request):
        return HTTPFound(location=request.route_url('login'))
    form = SelectCoursesForm()
    csrf_token = request.session.get_csrf_token()

    submitter_email = request.session['uniqueName'] + '@' + \
        request.registry.settings['EMAIL_DOMAIN']
    name = request.session['firstName'] + ' ' + request.session['lastName']
    sender = request.registry.settings['mail.username']

    '''remove for production'''
    submitter_email = 'lookerb@uwosh.edu'

    message = Message(subject="Course Combine Confirmation",
        sender=sender,
        recipients=[sender, submitter_email])
    message.body = make_msg_text(name, submitter_email, request)
    message.html = make_msg_html(name, submitter_email, request)
    mailer = get_mailer(request)
    mailer.send_immediately(message, fail_silently=False)

    return{'csrf_token': csrf_token,
        'name': name,
        'form': form, 
        'base_course': request.session['base_course'],
        'courses_to_combine': request.session['courses_to_combine']
        }

###########
# Helpers #
###########


def session_exists(request):
    if 'uc' in request.session:
        uc = request.session['uc']
        service_uc = request.session['service_uc']
        return uc, service_uc
    else:
        try:
            request.session['uc'] = uc = appContext.create_user_context(
                result_uri=request.url,
                host=request.registry.settings['LMS_HOST'],
                encrypt_requests=request.registry.settings['ENCRYPT_REQUESTS'])
            request.session['service_uc'] = service_uc = \
                appContext.create_user_context(
                result_uri=request.url,
                host=request.registry.settings['LMS_HOST'],
                encrypt_requests=request.registry.settings['ENCRYPT_REQUESTS'])
            service_uc.user_id = request.registry.settings['USER_ID']
            service_uc.user_key = request.registry.settings['USER_KEY']
            return uc, service_uc
        except KeyError:
            session.flash('Please login.')
            return False

def logged_in(request):
    if 'uc' not in request.session:
        request.session.flash('Please login to place request.')
        return False
    return True


def get_user_data(uc, request):
    '''
    Requests current user info from D2L via whoami route
    http://docs.valence.desire2learn.com/res/user.html#get--d2l-api-lp-%28version%29-users-whoami
    '''
    my_url = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/users/whoami'.format(request.registry.settings['VER']))
    return requests.get(my_url).json()


def store_user_data(request, userData):
    '''
    Stores user info in session.
    '''
    request.session['firstName'] = userData['FirstName']
    request.session['lastName'] = userData['LastName']
    request.session['userId'] = userData['Identifier']
    '''PRODUCTION: UNCOMMENT FOLLOWING LINE AND DELETE THE ONE AFTER THAT'''
    #request.session['uniqueName'] = userData['UniqueName']
    request.session['uniqueName'] = 'lookerb'


def get_semester_code():
    '''
    Computes current semester code by today's date.
    '''
    year = date.today().year - BASE_YEAR
    month = date.today().month
    if month >= 8 and month <= 12:
        semester = FALL
    elif month >= 1 and month <= 5:
        semester = SPRING
        year = year - 1
    else: # month equals/is between 6 & 7
        semester = SUMMER
        year = year - 1
    code = str(year) + semester
    while len(code) < 4:
        code = '0' + code
    # DELETE FOLLOWING LINE FOR PRODUCTION
    #code = '0685'
    return code


def get_courses(uc, semester_code, request):
    '''
    Creates list of courses with same semester code.
    '''
    myUrl = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/enrollments/users/{1}/orgUnits/'.format(
        request.registry.settings['VER'], request.session['userId']))
    kwargs = {'params': {}}
    kwargs['params'].update({'roleId':request.registry.settings['ROLE_ID']})
    kwargs['params'].update({'orgUnitTypeId': request.registry.settings['ORG_UNIT_TYPE_ID']})
    r = requests.get(myUrl, **kwargs)

    course_list = []
    end = False
    while end == False:
        for course in r.json()['Items']:
            semCode = str(course['OrgUnit']['Code'][6:10])
            if semCode == semester_code:
                course_list.append({
                    u'courseId': int(course['OrgUnit']['Id']),
                    u'name': course['OrgUnit']['Name'],
                    u'code': course['OrgUnit']['Code'],
                    u'parsed': parse_code(course['OrgUnit']['Code'])
                    })
            if r.json()['PagingInfo']['HasMoreItems'] == True:
                kwargs['params']['bookmark'] = r.json()['PagingInfo']['Bookmark']
                r = requests.get(myUrl, **kwargs)
        else:
            end = True
    return course_list


def parse_code(code):
    '''
    Breaks up code into more readable version to present to user.
    '''
    parsed = code.split("_")
    return parsed[3] + " " + parsed[4] + " " + parsed[5]


def get_courseId_choices(course_list):
    '''
    Pulls elements from course_list to use in form choices.
    '''
    return [(course['courseId'], 
        course['name'] + ", " + course['parsed']) for course in course_list]


def get_baseCourse_choices(course_list, request):
    '''
    Pulls elements from course_list to use in baseCourse choices, with markup to
    make choices linkable.
    '''
    linkPrefix = "<a target=\"_blank\" href='http://" + \
        request.registry.settings['LMS_HOST'] + \
        "/d2l/lp/manageCourses/course_offering_info_viewedit.d2l?ou="

    return [(course['courseId'],
        linkPrefix +
        str(course['courseId']) +
        "'>" +
        course['name'] +
        ", " +
        course['parsed'] +
        "</a>") for course in course_list]


def make_code(add_form, code):
    '''
    Creates course code from the elements submitted in add form.
    '''
    return '_'.join(('UWOSH',
        code,
        add_form.sessionLength.data,
        add_form.subject.data,
        add_form.catalogNumber.data,
        'SEC' + add_form.section.data,
        add_form.classNumber.data))


def update_base_course(baseCourse, baseCourseData, course_list):
    '''
    Populates baseCourse dictionary with user-selected baseCourse data.
    '''
    baseCourseId = int(baseCourseData)
    for course in course_list:
        if course['courseId'] == baseCourseId:
            baseCourse.update(course)


def get_course(uc, code, request):
    '''
    Gets course information for supplied code from D2L.
    '''
    myUrl = uc.create_authenticated_url('/d2l/api/lp/{0}/orgstructure/'.format(request.registry.settings['VER']))
    kwargs = {'params': {}}
    kwargs['params'].update({'orgUnitCode': code})
    kwargs['params'].update({'orgUnitType': request.registry.settings['ORG_UNIT_TYPE_ID']})
    r = requests.get(myUrl, **kwargs)
    try:
        return r.json()['Items'][0]
    except IndexError:
        return False


def process_add_class(uc, request, form, add_form, semester_code):
    '''
    Processes add_form, the form that allows for manual addition of a course
    to the list of those available to be combined.
    '''
    session = request.session
    csrf_token = request.session.get_csrf_token()
    course_code = make_code(add_form, semester_code)
    course_to_add = get_course(uc, course_code, request)
    if course_to_add == False:
        session.flash("Error adding course to list. \
            Please check course details and try again.")
        return {'form': form, 'add_form': add_form, 'csrf_token': csrf_token}
    if add_form.validate():
        session['course_list'].append({
            u'courseId': int(course_to_add['Identifier']),
            u'name': course_to_add['Name'],
            u'code': course_code,
            u'parsed': parse_code(course_code)
            })
        return HTTPFound(location=request.route_url('request'))
    else:
        session.flash("Error adding course to list. Please check course details and try again.")
        return {'form': form, 'add_form': add_form, 'csrf_token': csrf_token}    


def process_combine_request(form, add_form, course_list, request):
    '''
    Processes form, the form for submitting the actual course combine request.
    '''
    session = request.session
    csrf_token = request.session.get_csrf_token()
    course_ids = form.courseIds.data
    courses_to_combine = [course for course in course_list if course['courseId'] in course_ids]
    base_course = {}
    if form.baseCourse.data != 'None':
        update_base_course(base_course, form.baseCourse.data, course_list)
    else:
        session.flash("You must select a base course into which to combine the courses.")
        return {'form': form, 'add_form':add_form, 'csrf_token': csrf_token}
    if len(courses_to_combine) == 0 or (len(courses_to_combine) == 1 and base_course in courses_to_combine):
        session.flash("You must select at least two courses to combine.")
        return {'form': form, 'add_form':add_form, 'csrf_token': csrf_token}
    session['base_course'], session['courses_to_combine'] = base_course, courses_to_combine
    if base_course not in courses_to_combine:
        courses_to_combine.append(base_course)
        return HTTPFound(location=request.route_url('check'))
    else:
        return HTTPFound(location=request.route_url('confirmation'))


def make_msg_text(name, submitter_email, request):
    '''
    Generates confirmation email message text.
    '''
    coursesToCombine = request.session['courses_to_combine']
    baseCourse = request.session['base_course']
    greeting = "Hello {0},\n".format(name)
    opening = "You have asked to have the following courses combined into " + \
        "{0}, {1} (OU {2}):\n\nCourse Name\t(Course Id)\tD2L OU Number\n".format(baseCourse['parsed'],
        baseCourse['name'], baseCourse['courseId'])
    courseTable = "\n".join("{0},\t{1}\t(OU {1})".format(course['name'],
        course['code'], course['courseId']) for course in coursesToCombine)
    closing = "\nYour contact information: {0}".format(submitter_email) +\
        "\nIf this is incorrect, please contact our D2L site administrator" +\
        " at {0}.".format(request.registry.settings['EMAIL_SITE_ADMIN'])
    msg_body = greeting + opening + courseTable + closing
    return msg_body


def make_msg_html(name, submitter_email, request):
    '''
    Generates confirmation email message in HTML.
    '''
    coursesToCombine = request.session['courses_to_combine']
    baseCourse = request.session['base_course']
    greeting = "<p>Hello {0},</p><p>".format(name)
    opening = "You have asked to have the following courses combined into " +\
        " {0}, {1} (OU {2}):</p>".format(baseCourse['parsed'], baseCourse['name'], baseCourse['courseId'])
    tableHead = "<table><thead><tr><th>Course Name</th><th>Course Id</th><th>(D2L OU Number)</th></thead>"
    courseTable = "".join("<tr><td>{0}</td><td>{1}</td><td>({2})</td></tr>".format(
        course['name'], course['code'], course['courseId']) for course in coursesToCombine)
    tableClose = "</table>"
    closing = "<p>Your contact information: {0}</p>".format(submitter_email) +\
        "<p>If this is incorrect, please contact our D2L site administrator" +\
        " at {0}.</p>".format(request.registry.settings['EMAIL_SITE_ADMIN'])
    msg_html = greeting + opening + tableHead + courseTable + tableClose + closing
    return msg_html
