"""
AppScale AppDashboard, a Python 2.7 webapp for interacting with AppScale.
"""
import cgi
import jinja2
import logging
import os
import re
import urllib
import webapp2
import sys
from lib.app_dashboard_helper import AppDashboardHelper
from lib.app_dashboard_helper import AppHelperException

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__) + \
      os.sep + 'templates'))


class AppDashboard(webapp2.RequestHandler):
  """ Class that all pages in the Dashboard must inherit from. """

  def __init__(self, request, response):
    """ Constructor """
    self.initialize(request, response)
    # initialize helper
    self.helper = AppDashboardHelper(self.response)

  def render_template(self, template_file, values={}):
    """ Renders a template file with all variables loaded.

    Args: 
      template_file: relative path to tempate file.
      values: dict with key/value pairs used by the template file.
    Returns:
      str with the rendered template.
    """
    template = jinja_environment.get_template(template_file)
    sub_vars = {
      'logged_in' : self.helper.is_user_logged_in(),
      'user_email' : self.helper.get_user_email(),
      'is_user_cloud_admin' : self.helper.is_user_cloud_admin(),
      'i_can_upload' : self.helper.i_can_upload(),
    }
    for key in values.keys():
      sub_vars[key] = values[key]
    return template.render(sub_vars)
    
  def get_shared_navigation(self):
    """ Renders the shared navigation.

    Returns:
      A str with the navigation bar rendered.
    """
    return self.render_template(template_file = 'shared/navigation.html')

  def render_page(self, page, template_file, values = {} ):
    """ Renders a template with the main layout and nav bar. """
    self.response.headers['Content-Type'] = 'text/html'
    template = jinja_environment.get_template('layouts/main.html')
    self.response.out.write(template.render(
        page_name = page,
        page_body = self.render_template(template_file, values),
        shared_navigation = self.get_shared_navigation()
        ))
    

class IndexPage(AppDashboard):
  """ Class to handle request to the / page. """

  TEMPLATE = 'landing/index.html'

  def get(self):
    """ Handler for GET requests. """
    self.render_page(page='landing', template_file=self.TEMPLATE, values = {
      'monitoring_url' : self.helper.get_monitoring_url(),
    })


class StatusPage(AppDashboard):
  """ Class to handle request to the /status page. """

  TEMPLATE = 'status/cloud.html'

  def get(self):
    """ Handler for GET requests. """
    self.render_page(page='status', template_file=self.TEMPLATE, values = {
      'server_info' : self.helper.get_status_info(),
      'dbinfo' : self.helper.get_database_info(),
      'service_info' : self.helper.get_service_info(),
      'apps' : self.helper.get_application_info(),
      'monitoring_url' : self.helper.get_monitoring_url(),
    })


class NewUserPage(AppDashboard):
  """ Class to handle request to the /users/new and /users/create page. """

  TEMPLATE = 'users/new.html'

  def parse_new_user_post(self):
    """ Parse the input from the create user form.

    Returns:
      Three dicts, the first with the form data, and the second with True/False
      values for errors in each field, the third with specific error messages.
    """
    users = {}
    errors = {}
    error_msgs = {}
    users['email'] = cgi.escape(self.request.get('user_email'))
    if re.match('^\w[^@\s]*@[^@\s]{2,}$', users['email']):
      errors['email'] = False
    else:
      error_msgs['email'] = 'Format must be foo@boo.goo.' 
      errors['email'] = True

    users['password'] = cgi.escape(self.request.get('user_password'))
    if len(users['password']) >= 6:
      errors['password'] = False
    else:
      error_msgs['password'] = 'Password must be at least 6 characters long.'
      errors['password'] = True

    users['password_confirmation'] = cgi.escape(
      self.request.get('user_password_confirmation'))
    if users['password_confirmation'] == users['password']:
      errors['password_confirmation'] = False
    else:
      error_msgs['password_confirmation'] = 'Passwords do not match.'
      errors['password_confirmation'] = True

    return users, errors, error_msgs

  def process_new_user_post(self, users, errors):
    """ Creates new user if parse was successful.

    Args:
      users: A dict with the form data.
      errors: A dict with True/False values for errors in each of the users
              fields.
    Returns:
      True if user was create, else False.
    """
    if errors['email'] or errors['password'] or errors['password_confirmation']:
      return False
    else:
      return self.helper.create_new_user(cgi.escape(users['email']),
           cgi.escape(users['password']) )

  def post(self):
    """ Handler for POST requests. """
    users, errors, err_msgs = self.parse_new_user_post()
    try:
      if self.process_new_user_post(users, errors):
        self.redirect('/', self.response)
        return
    except Exception as e:
      sys.stderr.write("NewUserPage.POST() exception: "+str(e))
      err_msgs['email'] = str(e)
      errors['email'] = True
    
    self.render_page(page = 'users', template_file = self.TEMPLATE, values = {
        'display_error_messages': errors,
        'user' : users,
        'error_message_content' : err_msgs,
        })

  def get(self):
    """ Handler for GET requests. """
    self.render_page(page = 'users', template_file = self.TEMPLATE, values = {
      'display_error_messages' : {},
      'user' : {}
    })

class LoginVerify(AppDashboard):
  """ Class to handle request to /users/confirm and /users/verify pages. """

  TEMPLATE = 'users/confirm.html'
  
  def post(self):
    """ Handler for POST requests. """
    if self.request.get('continue') != '' and\
       self.request.get('commit') == 'Yes':
      sys.stderr.write("\n\ncontinue URL: " + \
        self.request.get('continue').encode('ascii','ignore') + "\n\n")
      self.redirect(self.request.get('continue').encode('ascii','ignore'), 
        self.response)
    else:
      self.redirect('/', self.response)


  def get(self):
    """ Handler for GET requests. """
    continue_url = urllib.unquote(self.request.get('continue'))
    url_match = re.search('continue=(.*)$', continue_url)
    if url_match:
      continue_url = url_match.group(1)

    self.render_page(page = 'users', template_file = self.TEMPLATE, values = {
      'continue' : continue_url
    })
   


class LogoutPage(AppDashboard):
  """ Class to handle request to the /users/logout page. """

  def get(self):
    """ Handler for GET requests. """
    self.helper.logout_user()
    self.redirect('/', self.response)


class LoginPage(AppDashboard):
  """ Class to handle request to the /users/login page. """

  TEMPLATE = 'users/login.html'

  def post(self):
    """ Handler for post requests. """
    if self.helper.login_user( self.request.POST.get('user_email'),
       self.request.POST.get('user_password') ):
    
      if self.request.get('continue') != '':
        self.redirect('/users/confirm?continue=' +
          urllib.quote( str(self.request.get('continue'))
          ).encode('ascii','ignore'), self.response)
      else:
        self.redirect('/', self.response)
    else:
      self.render_page(page = 'users', template_file = self.TEMPLATE,
        values = {
          'continue' : self.request.POST.get('continue'),
          'user_email' : self.request.POST.get('user_email'),
          'flash_message': 
          "Incorrect username / password combination. Please try again."
        })

  def get(self):
    """ Handler for GET requests. """
    self.render_page(page = 'users', template_file = self.TEMPLATE, values = {
      'continue' : self.request.get('continue')
    })


class AuthorizePage(AppDashboard):
  """ Class to handle request to the /authorize page. """

  TEMPLATE = 'authorize/cloud.html'

  def parse_update_user_permissions(self):
    """ Update authorization matrix from form submission.
    Returns: str with message to be displayed to the user.
    """
    perms = self.helper.get_all_permission_items()
    req_keys = self.request.POST.keys()
    sys.stderr.write("req_keys: "+str(req_keys))
    response = ''
    for fldname, email in self.request.POST.iteritems():
      if re.match('^user_permission_', fldname):
        for perm in perms:
          if email+'-'+perm in req_keys and\
            self.request.get('CURRENT-'+email+'-'+perm) == 'False':
            if self.helper.add_user_permissions(email, perm):
              response += 'Enabling '+perm+' for '+email+'. '
            else:
              response += 'Error enabling '+perm+' for '+email+'. '
          elif email+'-'+perm not in req_keys and\
            self.request.get('CURRENT-'+email+'-'+perm) == 'True':
            if self.helper.remove_user_permissions(email, perm):
              response += 'Disabling '+perm+' for '+email+'. '
            else:
              response += 'Error disabling '+perm+' for '+email+'. '
    return response

  def post(self):
    """ Handler for POST requests. """
    if self.helper.is_user_cloud_admin():
      self.render_page(page='authorize', template_file=self.TEMPLATE,
        values = {
        'flash_message' : self.parse_update_user_permissions(),
        'user_perm_list' : self.helper.list_all_users_permisions(),
        })
    else:
      self.render_page(page='authorize', template_file=self.TEMPLATE,
        values = {
        'flash_message':"Only the cloud administrator can change permissions.",
        'user_perm_list':{},
        })

  def get(self):
    """ Handler for GET requests. """
    if self.helper.is_user_cloud_admin():
      self.render_page(page='authorize', template_file=self.TEMPLATE, values = {
        'user_perm_list' : self.helper.list_all_users_permisions(),
      })
    else:
      self.render_page(page='authorize', template_file=self.TEMPLATE,
        values = {
        'flash_message':"Only the cloud administrator can change permissions.",
        'user_perm_list':{},
        })


class AppUploadPage(AppDashboard):
  """ Class to handle request to the /apps/new page. """

  TEMPLATE = 'apps/new.html'

  def post(self):
    """ Handler for POST requests. """
    success_msg = ''
    err_msg = ''
    if self.helper.i_can_upload():
      try: 
        success_msg = self.helper.upload_app(
          self.request.POST.multi['app_file_data'].file
          )
      except AppHelperException as e:
        err_msg = str(e)
    else:
      err_msg = "You are not authorized to upload apps."
    self.render_page(page='apps', template_file=self.TEMPLATE,
      values = {'error_message' : err_msg,
        'success_message' : success_msg
      })

  def get(self):
    """ Handler for GET requests. """
    self.render_page(page='apps', template_file=self.TEMPLATE)

class AppDeletePage(AppDashboard):
  """ Class to handle request to the /apps/delete page. """

  TEMPLATE = 'apps/delete.html'

  def post(self):
    """ Handler for POST requests. """
    appname = self.request.POST.get('appname')
    if self.helper.is_user_cloud_admin() or\
       appname in self.helper.get_user_app_list():
      message = self.helper.delete_app(appname)
    else:
      message = "You do not have permission to delete the application: "+appname
    self.render_page(page='apps', template_file=self.TEMPLATE,
      values = {'flash_message' : message,
      'apps' : self.helper.get_application_info(),
      'app_admin_list' : self.helper.get_user_app_list()
      })

  def get(self):
    """ Handler for GET requests. """
    self.render_page(page='apps', template_file=self.TEMPLATE, values = {
      'apps' : self.helper.get_application_info(),
      'app_admin_list' : self.helper.get_user_app_list()
    })


# Main Dispatcher
app = webapp2.WSGIApplication([ ('/', IndexPage),
                                ('/status', StatusPage),
                                ('/users/new', NewUserPage),
                                ('/users/create', NewUserPage),
                                ('/logout', LogoutPage),
                                ('/users/logout', LogoutPage),
                                ('/users/login', LoginPage),
                                ('/users/authenticate', LoginPage),
                                ('/login', LoginPage),
                                ('/users/verify',LoginVerify),
                                ('/users/confirm',LoginVerify),
                                ('/authorize', AuthorizePage),
                                ('/apps/new', AppUploadPage),
                                ('/apps/upload', AppUploadPage),
                                ('/apps/delete', AppDeletePage),
                              ], debug=True)
# Handle errors
def handle_404(request, response, exception):
  """ Handles 404, page not found exceptions. """
  logging.exception(exception)
  response.set_status(404)
  response.write(jinja_environment.get_template('404.html').render())

def handle_500(request, response, exception):
  """ Handles 500, error processing page exceptions. """
  logging.exception(exception)
  response.set_status(500)
  response.write(jinja_environment.get_template('500.html').render())

app.error_handlers[404] = handle_404
app.error_handlers[500] = handle_500