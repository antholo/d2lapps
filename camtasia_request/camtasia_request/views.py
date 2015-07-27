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
from forms import RequestForm

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

appContext = d2lauth.fashion_app_context(app_id=parser.get('app:main', 'APP_ID'),
                                         app_key=parser.get('app:main', 'APP_KEY'))


@view_config(route_name='logout')
def logout(request):
    '''
    Dumps session data
    '''
    request.session.invalidate()
    return HTTPFound(location=request.registry.settings['REDIRECT_AFTER_LOGOUT'])

#@view_config(route_name='login', renderer='templates/login.pt')
@view_config(route_name='login', renderer='templates/login.jinja2')
def login(request):
    '''
    Generates authorization and callback URLs for login page.
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
    print request.scheme # CHECKING FOR HTTPS
    return {'auth_url': auth_url, 'csrf_token': csrf_token}


#@view_config(route_name='request', renderer='templates/request.pt')
@view_config(route_name='request', renderer='templates/request.jinja2')
def request_form(request):
    '''
    Generates and processes request form.
    '''
    #session = request.session
    csrf_token = request.session.get_csrf_token()

    if 'uc' in request.session:
        uc = request.session['uc']
    else:
        try:
            request.session['uc'] = uc = appContext.create_user_context(
                result_uri=request.url, 
                host=request.registry.settings['LMS_HOST'],
                encrypt_requests=request.registry.settings['ENCRYPT_REQUESTS'])
        except KeyError:
            request.session.flash('Please login.')
            return HTTPFound(location=request.route_url('login'))

    user_data = get_user_data(uc, request)
    store_user_data(request.session, user_data)
    code = get_semester_code()

    request.session['course_list'] = get_courses(uc, code, request)
    form = RequestForm(request.POST)
    form.course.choices = get_course_choices(request.session['course_list'], request)

    if form.course.choices == []:
        request.session.flash('No courses were found in D2L for this semester. \
            Please <a href="http://www.uwosh.edu/d2lfaq/d2l-login">log into \
            D2L</a> to confirm you have classes in D2L.')

        return {'form': form, 'csrf_token': csrf_token}

    print request.scheme #CHECKING FOR HTTPS

    #if request.method == 'POST' and form.validate():
    if 'form_submit' in request.POST and form.validate():
        process_form(form, request.session)


        return HTTPFound(location=request.route_url('confirmation'))
    else:
        return {'form': form, 'csrf_token': csrf_token}


#@view_config(route_name='confirmation', renderer='templates/confirmation.pt')
@view_config(route_name='confirmation', renderer='templates/confirmation.jinja2')
def confirmation_page(request):

    form = RequestForm()
    session = request.session
    csrf_token = session.get_csrf_token()
    
    if 'uc' not in request.session:
        request.session.flash('Please login to place request')
        return HTTPFound(location=request.route_url('login'))

    submitter_email = request.session['uniqueName'] + '@' + \
        request.registry.settings['EMAIL_DOMAIN']
    name = request.session['firstName'] + ' ' + request.session['lastName']
    sender = request.registry.settings['mail.username']

    # remove for production
    submitter_email = 'lookerb@uwosh.edu'

    message = Message(subject="Relay account setup",
        sender=sender,
        recipients=[sender,submitter_email])

    message.body = make_msg_text(name,
        submitter_email,
        request.session['requestDetails'],
        form)

    message.html = make_msg_html(name,
        submitter_email,
        request.session['requestDetails'],
        form)
    
    mailer = get_mailer(request)
    mailer.send_immediately(message, fail_silently=False)
    
    print request.scheme #CHECKING FOR HTTPS
    return {
        'csrf_token': csrf_token,
        'name': name,
        'form': form,
        'requestDetails': request.session['requestDetails']
        }

###########
# helpers #
###########

def get_user_data(uc, request):
    '''
    Requests current user info from D2L via whoami route
    http://docs.valence.desire2learn.com/res/user.html#get--d2l-api-lp-%28version%29-users-whoami
    '''
    my_url = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/users/whoami'.format(request.registry.settings['VER']))
    return requests.get(my_url).json()


def store_user_data(session, userData):
    '''
    Stores user info in session.
    '''
    session['firstName'] = userData['FirstName']
    session['lastName'] = userData['LastName']
    session['userId'] = userData['Identifier']
    '''PRODUCTION: UNCOMMENT FOLLOWING LINE AND DELETE THE ONE AFTER THAT'''
    #session['uniqueName'] = userData['UniqueName']
    session['uniqueName'] = 'lookerb'


def get_semester_code():
    '''
    Computers current semester code by today's date.
    '''
    year = date.today().year - BASE_YEAR
    month = date.today().month
    if month >= 8 and month <= 12:
        semester = FALL
    elif month >= 1 and month <= 5:
        semester = SPRING
        year = year - 1
    else: # month is between
        semester = SUMMER
        year = year - 1
    code = str(year) + semester
    while len(code) < 4:
        code = '0' + code
    return code


def get_courses(uc, semester_code, request):
    '''
    Creates dictionary of lists of courses keyed by semester code and stores
    it in session for easy access post-creation.
    '''
    my_url = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/enrollments/myenrollments/'.format(request.registry.settings['VER']))
    kwargs = {'params': {}}
    kwargs['params'].update({'orgUnitTypeId': request.registry.settings['ORG_UNIT_TYPE_ID']})
    r = requests.get(my_url, **kwargs)
    course_list = []
    end = False
    while end == False:
        for course in r.json()['Items']:
            sem_code = str(course['OrgUnit']['Code'][6:10])
            if sem_code == semester_code:
                course_list.append({u'courseId': int(course['OrgUnit']['Id']),
                    u'name': course['OrgUnit']['Name'],
                    u'code': course['OrgUnit']['Code'],
                    u'parsed': parse_code(course['OrgUnit']['Code'])})
            if r.json()['PagingInfo']['HasMoreItems'] == True:
                kwargs['params']['bookmark'] = r.json()['PagingInfo']['Bookmark']
                r = requests.get(my_url, **kwargs)
            else:
                end = True
    return course_list


def get_course_choices(course_list, request):
    link_prefix = "<a target=\"_blank\" href='http://" +\
        request.registry.settings['LMS_HOST'] + \
        "/d2l/home/"
    choices = [(course['courseId'],
        course['name'] +
        ", " +
        course['parsed'] +
        link_prefix + 
        str(course['courseId']) +
        "'> D2L Page</a>") for course in course_list]
    return choices


def parse_code(code):
    '''
    Breaks up code into more readable version to present to user.
    '''
    parsed = code.split("_")
    return parsed[3] + " " + parsed[4] + " " + parsed[5]


def process_form(form, session):
    embed = 'no'
    if form.embed.data:
        embed = 'yes'
    download = 'no'
    if form.download.data:
        download = 'yes'
    share = 'no'
    if form.share.data:
        share = 'yes'
    training = 'no'
    if form.training.data:
        training = 'yes'
            
    session['requestDetails'] = {
        'courseId' : str(form.course.data),
        'embed' : embed,
        'download' : download,
        'share' : share,
        'training' : training,
        'location' : form.location.data,
        'courseName' : form.courseName.data,
        'comments' : form.comments.data,
        'expiration' : form.expiration.data
        }


def make_msg_text(name, submitter_email, requestDetails, form):
    email = 'Your E-Mail Address\n\t{0}\n'.format(submitter_email)
    name =  'Name\n\t{0}\n'.format(name)
    embed = '{0}\n\t{1}\n'.format(form.embed.label, requestDetails['embed'])
    download = '{0}\n\t{1}\n'.format(form.download.label,
        requestDetails['download'])
    share = '{0}\n\t{1}\n'.format(form.share.label, requestDetails['share'])
    ouNumber = 'OU Number\n\t{0}\n'.format(requestDetails['courseId'])
    location = '{0}\n\t{1}'.format(form.location.label,
        requestDetails['location'])
    courseName = '{0}\n\t{1}\n'.format(form.courseName.label,
        requestDetails['courseName'])
    expiration = '{0}\n\t{1}\n'.format(form.expiration.label,
        requestDetails['expiration'])
    training = '{0}\n\t{1}\n'.format(form.training.label,
        requestDetails['training'])
    comments = '{0}\n\t{1}\n'.format(form.comments.label,
        requestDetails['comments'])
    return email + name + embed + download + share + ouNumber + location + \
        courseName + expiration + training + comments


def make_msg_html(name, submitter_email, requestDetails, form):
    email = '<dl><dt>Your E-Mail Address</dt><dd><a href=3D"mailto:{0}' + \
         ' target=3D"_blank">{0}</a></dd>'.format(submitter_email)
    name = '<dt>Name</dt><dd>{0}</dd>'.format(name)
    embed = '<dt>{0}</dt><dd>{1}</dd>'.format(form.embed.label,
        requestDetails['embed'])
    download = '<dt>{0}</dt><dd>{1}</dd>'.format(form.download.label,
        requestDetails['download'])
    share = '<dt>{0}<dt><dd>{1}</dd>'.format(form.share.label,
        requestDetails['share'])
    ouNumber = '<dt>OU Number</dt><dd>{0}</dd>'.format(requestDetails['courseId'])
    location = '<dt>{0}</dt><dd>{1}</dd>'.format(form.location.label,
        requestDetails['location'])
    courseName = '<dt>{0}</dt><dd>{1}</dd>'.format(form.courseName.label,
        requestDetails['courseName'])
    expiration = '<dt>{0}</dt><dd>{1}</dd>'.format(form.expiration.label,
        requestDetails['expiration'])
    training = '<dt>{0}</dt><dd>{1}</dd>'.format(form.training.label,
        requestDetails['training'])
    comments = '<dt>{0}</dt><dd>{1}</dd></dl>'.format(form.comments.label,
        requestDetails['comments'])
    return email + name + embed + download + share + ouNumber + location + \
        courseName + expiration + training + comments
