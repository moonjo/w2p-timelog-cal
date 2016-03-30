import sys
import os
import re
import MySQLdb
from globals import current
from datetime import datetime, date
from gluon.contrib import simplejson
from gluon.html import *

sys.path.append('/X/tools/pythonlib')
from shotgun_api3 import Shotgun
sg_server = "https://shotgun.mock.com/"
sg_script_name = "timelogscript"
sg_script_key = "1HKfjhhfER842t2jfldksfhaf"
sg = Shotgun(sg_server, sg_script_name, sg_script_key)

DEPT_STATUS = {}
DEPT_STATUS_HIDE = {}
TASK_GHOST = []
BANNED_TASK = ['apr', 'cmpt', 'fin', 'na', 'omt', 'wtg', 'hld', 'pin']
TASK_STATUS = ['act', 'cbb', 'ip', 'rdy', 'rev', 'monoap', 'rend']
TASK_DEF = dict(act='Active',
                apr='Approved',
                cbb='Could Be Better',
                cmpt='Completed',
                fin='Finaled',
                hld='Hold',
                ip='In Progress',
                omt='Omit',
                pin='Pinned',
                rdy='Ready',
                rev='Pending Review',
                wtg='Waiting',
                monoap='Mono Approved',
                na='N/A',
                )
BREAK_TASK = {'type': 'Task', 'id': 75744, 'sg_description': 'break',
              'step.Step.code': 'Project Management',
              'time_logs_sum': 0, 'content': 'Break',
              'due_date': None, 'time_percent_of_est': None,
              'entity': {'type': 'Asset', 'id': 1983, 'name': 'BREAK'},
              'project': {'type': 'Project', 'id': 80, 'name': 'Mr. X'},
              'sg_status_list': 'wtg', 'est_in_mins': None,
              'sg_artist_bid_est':0, 'sg_artist_bid_est_percent':0,
              'image': 'break.jpg',
              }

TASK_BID = 'sg_artist_bid_est'
TASK_BID_ALT = 'est_in_mins'


app_folder = os.path.dirname(os.path.realpath(__file__))
MRX_EMPLOYEE_LIST = os.path.join(app_folder, 'static', 'mrxemployees.csv')

def getProject(project_id=None, project_code=None):
    if project_id:
        return sg.find_one('Project',[['id','is',int(project_id)]], ['code','color','name'])
    elif project_code:
        return sg.find_one('Project',[['code','is',int(project_code)]], ['code','color','name'])
    return None

def userTasks(human_user, status_filter=[], project_id=None):
    """ Return tasks of the user
    We are getting all tasks (even the ones with ghost status) because we can't 
    set updated date condition for shotgun task find query
    """
    g = set(status_filter)
    
    # add user's department statuses
    if human_user.has_key('department'):
        dstats = DEPT_STATUS.get(human_user['department']['name'], [])
        if dstats:
            g |= set(dstats)
    
    # remove Banned Task Status
    g |= set(BANNED_TASK)
    
    status_filter = {'path':'sg_status_list','relation':'in','values':list(g)}
    
    assignees_filter = {'path':'task_assignees', 'relation':'is', 'values':[human_user]}
    
    assigneegroup_filter = {'path':'task_assignees.Group.users',
                            'relation':'in',
                            'values':[human_user]
                            }
    
    asscond = {'logical_operator':'or', 'conditions':[assignees_filter, assigneegroup_filter]}
    
    # skip Milestone step
    milestone_filter = {'path':'step.Step.code','relation':'is_not','values':['Milestone']}
    
    c = [status_filter, asscond, milestone_filter]
    
    if project_id:
        p = {'type':'Project', 'id':project_id}
        proj_filter = {'path':'project', 'relation':'is', 'values':[p]}
    else:
        projs = sg.find('Project', [['sg_status', 'in', ['Active','Bidding','Hold','Demo/Test']]])
        proj_filter = {'path':'project', 'relation':'in', 'values':projs}
    c.append(proj_filter)
    
    filters = {'logical_operator':'and', 'conditions':c}
    # get tasks
    tasks = sg.find('Task', filters,
                    fields=['id','content','project','entity','sg_description', 
                            'sg_status_list', 'due_date', 'step.Step.code',
                            'time_percent_of_est', 'time_logs_sum', 'est_in_mins',
                            'sg_artist_bid_est', 'sg_artist_bid_est_percent',
                            'image',
                            ],
                    order=[{'field_name':'project', 'direction':'asc'},
                           {'field_name':'due_date', 'direction':'asc'}]
                    )
    tasks.append(BREAK_TASK)
    return tasks

def getTasks(taskids):
    """ Return tasks
    """
    if not taskids:
        return []
    
    tasks = sg.find('Task', [['id', 'in', taskids]],
                    fields=['id','content','project','entity','sg_description', 
                            'sg_status_list', 'due_date', 'step.Step.code',
                            'time_percent_of_est', 'time_logs_sum', 'est_in_mins',
                            'sg_artist_bid_est', 'sg_artist_bid_est_percent',
                            'image',
                            ],
                    order=[{'field_name':'project', 'direction':'asc'},
                            {'field_name':'due_date', 'direction':'asc'},
                            ])
    return tasks

def taskCard(task, project_name='None', idx=0, status_task={}):
    """Build task content - div.group
    
    :param task: Task entity (shotgun)
    :param project_name: Project name
    :param idx: Task order index
    :returns: LI object (Task entity)
    
    >>> t = {'id':1,'code':'Blah','entity':None,'content':'lskdfj','sg_status_list':'ip','sg_description':'asdf','project':{'id':0,'name':'Proj','code':'proj'},'sg_artist_bid_est':80,'sg_artist_bid_est_percent':25,'step.Step.code':'step','image':None,'due_date':'2014-03-05','time_logs_sum':60}
    >>> isinstance(taskContent(t, 'Test project'), gluon.html.DIV)
    True
    """
    entity_name = 'None'
    entity_type = 'None'
    entity_id = ''
    
    project_id = 0
    project_code = 'None'
    project_colour = '#ee01fd'
    font_colour = '#fff'
    
    if task['project']:
        project_id = task['project']['id']
        project_name = task['project']['name']
        project_ent = getProject(project_id=project_id)
        if project_ent:
            project_code = project_ent['code']
            project_colour = rgb_to_hex(tuple(project_ent.get('color', '0,0,0').split(',')))
        
    if task['entity']:
        entity_name = task['entity']['name']
        entity_type = task['entity']['type'].lower()
        if entity_type == 'shot' or entity_type == 'asset':
            entity_id = task['entity']['id']
    elif task['content']:
        entity_name = task['content']
        
    if task['sg_description']:
        desc = task['sg_description']
    else:
        desc = 'no description'
        
    if task['step.Step.code']:
        if re.match("[Pp]roject\s?[Mm]anagement", task['step.Step.code']):
            pipeline = 'PM'
        else:
            pipeline = task['step.Step.code'].replace(' ', '_')
    else:
        pipeline = 'None'
        
    if task.get('due_date'):
        due_date = task.get('due_date')
        due_date_str = rformat(task.get('due_date'), False)
    else:
        due_date = '8027-01-01'
        due_date_str = '-'
        
    bid_mins = 0
    if task[TASK_BID]:
        bid_mins = task[TASK_BID]
        
    if bid_mins == 0:
        bid_hrs = 0
        artist_logged_mins = 0
        if task.has_key('time_logs_sum'):
            artist_logged_mins = task['time_logs_sum']
            
        if artist_logged_mins > 0:
            progress_pct = 100
            progress_cls = 'danger'
        else:
            progress_pct = 0
            progress_cls = 'success'
            
    else:
        bid_hrs = roundPartial(bid_mins / 60.0)
        artist_logged_mins = int(bid_mins * (task['sg_artist_bid_est_percent'] / 100.0))
        progress_pct = roundPartial(artist_logged_mins / float(bid_mins)) * 100
        # success=green, warning=orange, danger=red
        if progress_pct > 85:
            progress_cls = 'danger'
        elif progress_pct > 70:
            progress_cls = 'warning'
        else:
            progress_cls = 'success'
            
    tlid = "timelog_%d" %task['id']
    tentity = simplejson.dumps({'type':'Task','name':task['content'],'id':task['id']}).replace('"', '&quot;')
    
    detail_header = DIV(STRONG(entity_name))
    entity_name_link = STRONG(entity_name) # task sorting display
    
    labelcls = ''
    if (not project_name.lower() in ["none", "mr. x", "tools"]) and (not entity_name.lower().startswith('admin')):
        cr = contrast_ratio("#fff", project_colour)
        if cr < 3:
            labelcls += ' label-dark-text'
            font_colour = '#333'
        
        detail_header = DIV(
                            STRONG(entity_name,
                                   _class='label{0}'.format(labelcls),
                                   _style='background-color:{0};color:{1};'.format(project_colour, font_colour),
                                   ),
                            **{'_class':'btn-view-detail detail-header pointer',
                               '_data-entity_id':entity_id,
                               '_data-entity':'&{0}={1}'.format(entity_type, entity_name),
                               '_data-project':project_name,
                               '_data-projectcode':project_code,
                               }
                            )
        
        entity_name_link = SPAN(
                                STRONG(entity_name,
                                       _class='label{0}'.format(labelcls),
                                       _style='background-color:{0};color:{1};'.format(project_colour, font_colour),
                                       ),
                                **{'_class':'bold task-entity-detail pointer',
                                   '_data-entity_id':entity_id,
                                   '_data-entity':'&{0}={1}'.format(entity_type, entity_name),
                                   '_data-project':project_name,
                                   '_data-projectcode':project_code,
                                   '_style':'color:{0};'.format(project_colour),
                                   }
                                )
    
    task_type = ''
    licls = 'task-card'
    task_status = task['sg_status_list']
    if task_status in ['hld', 'pin']:
        task_type = status_task.get(task_status, '!!!').upper()
        licls += ' pinhold'
        
    elif task_status == 'rev':
        task_type = status_task.get(task_status, '!!!').upper()
        licls += ' review'
        
    if task['image']:
        if task['id'] == BREAK_TASK['id']:
            image = URL('static', 'images/{0}'.format(task['image']))
        else:
            image = task['image']
    else:
        image = URL('static', 'images/default_task_thumb.png')
        
    task_thumb = IMG(_src=image, _class='task-thumb')
    
    edata = {'title':entity_name,
             'taskid':task['id'],
             'duration':'01:00',
             'projectid':project_id,
             'project':project_name,
             'description':desc,
             'backgroundColor': project_colour,
             'textColor': font_colour,
             }
    event_data = simplejson.dumps(edata)
    
    content = LI(
                 DIV(
                     DIV(IMG(_src=image), _class='task-card-thumb'),
                     DIV(
                         SPAN(_class='task-icon icon_status_{0}'.format(task_status),
                              _title=status_task.get(task_status, 'unknown')
                              ),
                         entity_name_link,
                         SPAN(project_name.upper(), _class='branded-header pull-right'),
                         _class='task-card-title'
                         ),
                     DIV(desc, _class='task-desc'),
                     DIV(
                         SPAN("Logged:", _class='task-label text-muted'),
                         SPAN('%.2f hrs' %roundPartial(artist_logged_mins / 60.0),
                              _id='artist-logged-{0}'.format(task['id'])
                              ),
                         _class='task-card-label'
                         ),
                     DIV(
                         SPAN("Bid:", _class='task-label text-muted'),
                         SPAN('%.2f hrs' %bid_hrs, _class='task_bid'),
                         _class='task-card-label'
                         ),
                     DIV(
                         INPUT(_class='task-duration', _value='01:00'),
                         _class='task-card-duration'
                         ),
                    _class='task-content'
                    ),
                 **{'_class':licls,
                    '_data-colour':project_colour,
                    '_data-duedate':due_date,
                    '_data-entity':entity_name,
                    '_data-event':event_data,
                    '_data-fontcolour':font_colour,
                    '_data-order':idx,
                    '_data-pipeline':pipeline,
                    '_data-project':project_name,
                    '_data-status':task_status,
                    '_data-task':task['id'],
                    '_data-type':task_type,
                    }
                 )
    return content

def searchEventlogs(task_ids=[], proj=None):
    """ Return tasks ids with event logs created in the last 5 days that are
    task status change to cmpt
    """
    if len(task_ids) == 0:
        return []
        
    taskchange_filter = {'path':'event_type', 'relation':'is', 'values':['Shotgun_Task_Change']}
    status_filter = {'path':'attribute_name', 'relation':'is', 'values':['sg_status_list']}
    end_date = {'path':'created_at', 'relation':'in_last', 'values':[LOOK_BACK, 'DAY']}
    task_filter = {'path':'entity.Task.id', 'relation':'in', 'values':task_ids}
    
    allc = [taskchange_filter, status_filter, end_date, task_filter]
    
    if proj:
        allc.append({'path':'project.Project.code', 'relation':'is', 'values':[proj]})
    
    all_conds = {'logical_operator':'and', 'conditions':allc}
    
    eventlogs = sg.find("EventLogEntry",
                        filters=all_conds,
                        fields=['created_at', 'description', 'entity', 'meta',
                                'project', 'user', 'event_type', 'attribute_name'],
                        order=[{'column':'created_at','direction':'desc'}])
    
    def valid_change(old_val, new_val):
        #if old_val in TASK_STATUS and new_val in TASK_GHOST:
        if old_val in TASK_STATUS and new_val in BANNED_TASK:
            return True
    # filter out valid status changes
    valids = set()
    for evlog in eventlogs:
        if valid_change(evlog['meta']['old_value'], evlog['meta']['new_value']):
            valids.add(evlog['entity']['id'])
    return list(valids)

def getTimelogs(shotgunid, start, end):
    """Return a list of TimeLogs of given user (shotgunid) between start and end date
    """
    if hasattr(start, 'isoformat'):
        start = start.strftime('%Y-%m-%d')
    if hasattr(end, 'isoformat'):
        end = end.strftime('%Y-%m-%d')
    
    humanuser = {'type':'HumanUser', 'id':int(shotgunid)}
    user_filter = {'path':'user', 'relation':'is', 'values':[humanuser]}
    date_filter = {'path':'date', 'relation':'between', 'values':[start, end]}
    cond = {'logical_operator':'and', 'conditions':[user_filter, date_filter]}
    result = sg.find('TimeLog',
                     cond,
                     fields=['id', 'duration', 'project', 'entity', 'description', 'sg_start_time_2', 'sg_end_time']
                     )
    return result

def rformat(isodate, year=True):
    today = datetime.today()
    
    if not re.match('\d{4}-\d{2}-\d{2}', isodate):
        return isodate
    tmp = map(int, isodate.split('-'))
    d = date(tmp[0], tmp[1], tmp[2])
    
    if year or d.year != today.year:
        r = d.strftime('%b %d %Y')
    else:
        r = d.strftime('%b %d')
    return r

def roundPartial(value, precision=0.01):
    """Round to given precision. Default to one thousandth
    """
    return round(value / precision) * precision

# Contrast ratio functions
def hex_to_rgb(val):
    """Converts hex value to rgb value
    
    :param val: hex value
    :returns: rgb value
    """
    val = val.lstrip('#')
    lv = len(val)
    if lv == 3 and val[0]*lv == val:
        val = val * 2
        lv = len(val)
    return tuple(int(val[i:i+lv/3], 16) for i in range(0, lv, lv/3))

def rgb_to_hex(val):
    """Converts rgb value to hex value
    
    :param val: rgb value
    :returns: hex value
    """
    # val = 3-int-tuple
    v = tuple(map(lambda x: int(x), list(val)))
    return '#%02x%02x%02x' %v

def norm(val):
    """Normalize
    
    :param val: rgb
    :returns: normalized value
    """
    v = val / 255.0
    if v < 0.03928:
        return v / 12.92
    else:
        return ((v + 0.055) / 1.055) ** 2.4

def luminance(rgb):
    """Calculates luminance of rgb
    
    :param rgb: rgb value
    :returns: luminance
    """
    r, g, b = map(norm, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(fg, bg, mode='hex'):
    """Calculate contrast between 2 colour values
    
    :param fg: foreground colour
    :param bg: background colour
    :param mode: hex or rgb
    :returns: contrast ratio
    """
    if mode == 'hex':
        # convert hex to rgb
        c1 = hex_to_rgb(fg)
        c2 = hex_to_rgb(bg)
    else:
        c1 = fg
        c2 = bg
    l1 = luminance(c1)
    l2 = luminance(c2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    cratio = roundPartial((lighter + 0.05) / (darker + 0.05))
    return cratio




def get_active_employees():
    """ Sync Shotgun users with Studio users (due to active status being used differently)
    """
    
    exceptions = ['tracey', 'alan', 'robin', 'patrick', 'matb', 'jamesb',
                  'robertod', 'tommaso', 'vaughan', 'miles',
                  ]
    # get users from mrx-net2 then cross ref with sg users
    shotgun_users = sg.find('HumanUser', [['login', 'not_in', exceptions]],
                            fields=['login', 'email', 'name', 'department', 'sg_status_list', 'sg_studio'],
                            order=[{'field_name':'name', 'direction':'asc'}]
                            )
    
    rows = []
    db_connection_error = False
    
    q = "SELECT firstName, lastName, uniqName, email, nyc FROM employees WHERE active=1 ORDER BY firstName"
    try:
        conn = MySQLdb.connect(host="mrx-net2", user="seank", passwd="", db="mrx", cursorclass=MySQLdb.cursors.DictCursor, connect_timeout=2)
        cursor = conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        tor_studio = []
        ny_studio = []
        for row in rows:
            if row['nyc']:
                ny_studio.append(row['uniqName'])
            else:
                tor_studio.append(row['uniqName'])
        
    except MySQLdb.Error, e:
        #logger.error("Error %d: %s" %(e.args[0], e.args[1]))
        db_connection_error = True
        
    if db_connection_error:
        #logger.warning("Cannot connect to mrx-net2 database. Listing all Shotgun users.")
        # fall back to exported username list
        tor_studio = []
        ny_studio = []
        for line in open(MRX_EMPLOYEE_LIST, 'r').readlines():
            username, nyc = line.split(',')
            if nyc == '1':
                ny_studio.append(username)
            else:
                tor_studio.append(username)
    
    studios = tor_studio + ny_studio
    
    mrx_users = []
    expired = []
    # rows ('Aaron', 'Weintraub', 'aaron@mrxfx.com')
    addons = ['johnnyArtist', 'traceym', 'andrewb', 'mikep', 'jamesb', 'mollyt',
              'alek', 'rowan', 'sarahb', 'zac', 'robinb', 'leslie', 'jessie',
              'anthonys', 'jpodwil', 'sarahn', 'noelc', 'matt','valentine', 'cezar',
              'mathew', 'roberto', 'ruben', 'eduardo','alexm','mile','lily','philipa',
              'tristan','davids','dmitriy','ericr',
              ]
    
    studios.extend(addons)
    
    for sguser in shotgun_users:
        if sguser['login'] in studios:
            mrx_users.append(sguser)
        else:
            expired.append(sguser)
            
    return mrx_users

