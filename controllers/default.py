import sys
import re
import calendar
from datetime import datetime, date, timedelta
from collections import defaultdict
import csv
import logging
import logging.config
from gluon.contrib import simplejson

from xutils import *

logging.config.fileConfig('logging.conf')
logger = logging.getLogger("web2py.app.%s" %request.application)

__version__ = "0.8"

if request.application.endswith('_dev'):
    LOGIN_EMAIL = "admin@mail.com"
else:
    LOGIN_EMAIL = "auth"
session.login_email = LOGIN_EMAIL

mail = auth.settings.mailer
mail.settings.server = 'mail.com'
mail.settings.sender = 'sysadmin@mail.com'
mail.settings.login = 'admin:pass'

# shotgun
sys.path.append('/X/tools/pythonlib')
from shotgun_api3 import Shotgun
sg_server = "https://shotgun.mock.com/"
sg_script_name = "timelogscript"
sg_script_key = "Hh32hrdhf9813eklf9H3h"
sg = Shotgun(sg_server, sg_script_name, sg_script_key)

"""
NO DYNAMIC GLOBALS
"""

TODAY = date.today()

#@cache(request.env.path_info, time_expire=300, cache_model=cache.ram)
@auth.requires_login()
@auth.requires(auth.has_membership('admin') or auth.has_membership('hr') or auth.has_membership('tester'))
def index():
    """Main view
    """
    current_username = auth.user.username
    suser = sg.find_one('HumanUser',
                        [['login', 'is', current_username]],
                        fields=['email', 'login', 'name', 'department', 'sg_status_list', 'sg_freelancer']
                        )
    if not suser:
        # Shotgun account not setup, force logout
        auth.messages.logged_out = "Shotgun account is not setup."
        auth.logout()
    
    shotgun_id = suser['id']
    
    # query Shotgun
    initStatus()
    
    # get user tasks
    task_status_filter = []
    task_check_days = 2
    
    userconfig = db(db.auth_user.username==suser['login']).select(db.auth_user.ALL).first()
    
    #print 'XCAL', userconfig
    """
    if userconfig:
        if userconfig.task_status:
            task_status_filter = [x.strip() for x in userconfig.task_status.split(',') if x is not ' ']
            user_task_status = task_status_filter
            
        try:
            if userconfig.task_check_days:
                task_check_days = int(userconfig.task_check_days)
        except:
            pass
    """
    
    #user_tasks = userTasks(suser, task_status_filter)
    user_tasks = []
    
    task_lis = []
    for user_task in user_tasks:
        tc = taskCard(user_task, status_task=session.status_task)
        task_lis.append(tc)
    
    task_cards = UL(_id='task-list', _class='', *task_lis)
    
    # DEBUG
    #shotgun_id = 391 #kyles
    tcreate_form = bubbleDialog(user_tasks, 'create')
    tedit_form = bubbleDialog(user_tasks, 'edit')
    
    # user dropdown
    opt_users = set()
    tmp_users = set()
    
    for u in get_active_employees():
        if not u['name'].startswith('#') and not re.match('^\d', u['name']):
            name = '{0} {1}'.format(auth.user.first_name, auth.user.last_name)
            if name != u['name']:
                opt_users.add((u['name'], u['id']))
    
    user_opts = [OPTION(x[0], _value=x[1]) for x in sorted(opt_users)]
    user_opts.insert(0, OPTION('Impersonate ...', _value=''))
    
    impersonate_select = SELECT(user_opts,
                                _id='impersonate',
                                _class='form-control input-sm',
                                )
    
    holidays = dict(can={}, us={})
    csvs = ['stat_holidays_can.csv', 'stat_holidays_us.csv']
    for c in csvs:
        f = os.path.join(request.folder, 'static', c)
        data = csv.reader(file(f))
        headers = data.next() # ['year', "New Year's Day", 'Family Day', ]
        headers.pop(0)
        co = os.path.splitext(c)[0].split('_')[-1]
        for row in data:
            year = row.pop(0)
            holidays[co][year] = zip(row, headers)
            
    if not session.all_projects:
        session.all_projects = sg.find('Project',
                                       [['name', 'not_contains','DO NOT USE']],
                                       fields=['name','code','color'],
                                       order=[{'field_name':'name', 'direction':'asc'}]
                                       )
        
    isadmin = auth.has_membership("admin") or auth.has_membership("supe") or auth.has_membership("hr") or auth.has_membership("pm")
    
    return dict(isadmin=isadmin,
                shotgunid=shotgun_id,
                today_date=TODAY.strftime("%B %d, %Y").upper(),
                tasklist=task_cards,
                bubblecreate=tcreate_form,
                bubbleedit=tedit_form,
                impselect=impersonate_select,
                holidays=simplejson.dumps(holidays),
                )

def bubbleDialog(tasks, mode='create'):
    
    if mode == 'create':
        prefix = 'cb'
        hint = 'Please select a task'
    else:
        prefix = 'eb'
        hint = 'Edit timelog'
    
    opts = []
    for task in tasks:
        task_description = task['sg_description'] or '-'
        label = '[{0}] {1} / {2}'.format(task['project']['name'], task['entity']['name'], task_description)
        opts.append(OPTION(label,
                           **{'_value': task['id'],
                              '_data-projectid': task['project']['id'],
                              }
                           ))
    task_select = SELECT(*opts, _id='task-select', _class='form-control input-sm')
    
    content = DIV(
                DIV(
                    DIV(
                        FORM(
                             INPUT(_id='{0}-starttime'.format(prefix), _class='hidden', _type='text'),
                             INPUT(_id='{0}-endtime'.format(prefix), _class='hidden', _type='text'),
                             TABLE(
                                   TBODY(
                                         TR(
                                            TH('When:', _class='{0}-key'.format(prefix)),
                                            TD('', _id='{0}-when'.format(prefix), _class='{0}-value'.format(prefix)),
                                            ),
                                         TR(
                                            TH('Task:', _class='{0}-key'.format(prefix)),
                                            TD(
                                               DIV(
                                                   task_select,
                                                   _class='select-wrapper'
                                                   ),
                                               _id='{0}-when'.format(prefix),
                                               _class='{0}-value'.format(prefix)
                                               ),
                                            ),
                                         TR(
                                            TH('Note:', _class='{0}-key'.format(prefix)),
                                            TD(
                                               INPUT(_id='{0}-comment'.format(prefix),
                                                     _class='form-control input-sm',
                                                     _placeholder='comments',
                                                     _type='text',
                                                     ),
                                               DIV('',
                                                   _class='cb-hint'
                                                   ),
                                               _class='{0}-value'.format(prefix)
                                               ),
                                            ),
                                         TR(
                                            TD(
                                               BUTTON('{0} timelog'.format(mode.capitalize()),
                                                      _id='{0}-button'.format(mode),
                                                      _class='bubble-button btn btn-default btn-sm'
                                                      ),
                                               A('Edit Log >>', _href='#', _class='edit-link pull-right'),
                                               _class='cb-actions',
                                               _colspan=2
                                               )
                                            ),
                                         ),
                                   _class='{0}-table'.format(mode),
                                   _cellpadding=0,
                                   _cellspacing=0,
                                   ),
                             autocomplete=False
                             ),
                        _class='{0}-root'.format(prefix)
                        ),
                    ),
                _id='bubbleContent',
                _class='bubblecontent'
                )
    return content

def initStatus():
    """Save Shotgun status in session
    """
    valid_task = sg.schema_field_read('Task', 'sg_status_list')['sg_status_list']['properties']['valid_values']['value']
    session.status_task = dict((s['code'],s['name']) for s in sg.find('Status', [['code', 'in', valid_task]], fields=['code','name']))
    """
    session.status_shot = {}
    session.status_asset = {}
    session.status_task = {}
    
    status_valid_shot = sg.schema_field_read('Shot', 'sg_status_list')['sg_status_list']['properties']['valid_values']['value']
    status_valid_asset = sg.schema_field_read('Asset', 'sg_status_list')['sg_status_list']['properties']['valid_values']['value']
    status_valid_task = sg.schema_field_read('Task', 'sg_status_list')['sg_status_list']['properties']['valid_values']['value']
    
    for status in sg.find('Status', [['code', 'is_not', '']], fields=['code','name']):
        code = status['code']
        if code in status_valid_shot:
            session.status_shot[code] = status['name']
        if code in status_valid_asset:
            session.status_asset[code] = status['name']
        if code in status_valid_task:
            session.status_task[code] = status['name']
    """
    
def user():
    return dict(form=auth())


# TEST

