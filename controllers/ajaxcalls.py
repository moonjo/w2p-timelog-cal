from xutils import *
import os
import re
from datetime import datetime, date, timedelta, time
from gluon.contrib import simplejson

EVENT_COLOUR = '#ee01fd'

def getTaskCards():
    """Return tasks
    """
    sid = int(request.vars.suserid)
    suser = sg.find_one('HumanUser',
                        [['id', 'is', sid]],
                        fields=['login', 'name']
                        )
    if not suser:
        return ''
    
    task_status_filter = []
    task_check_days = 2
    userconfig = db(db.auth_user.username==suser['login']).select(db.auth_user.ALL).first()
    if userconfig:
        if userconfig.task_status:
            task_status_filter = [x.strip() for x in userconfig.task_status.split(',') if x is not ' ']
            user_task_status = task_status_filter
        try:
            if userconfig.task_check_days:
                task_check_days = int(userconfig.task_check_days)
        except:
            pass
    
    task_projects = set()
    task_status = set()
    task_lis = []
    user_tasks = userTasks(suser, task_status_filter)
    for user_task in user_tasks:
        # get task project
        if user_task['project']:
            #task_projects[user_task['project']['id']] = user_task['project']['name']
            task_projects.add(user_task['project']['name'])
        
        # get task status
        if user_task['sg_status_list']:
            task_status.add(user_task['sg_status_list'])
        
        task_lis.append(taskCard(user_task, status_task=session.status_task))
    
    task_cards = ''.join([t.xml() for t in task_lis])
    
    # select
    topts = []
    for task in user_tasks:
        task_description = task['sg_description'] or '-'
        label = '[{0}] {1} / {2}'.format(task['project']['name'], task['entity']['name'], task_description)
        topts.append(OPTION(label,
                           **{'_value': task['id'],
                              '_data-projectid': task['project']['id'],
                              }
                           ))
    task_select = SELECT(*topts, _id='task-select', _class='form-control input-sm').xml()
    
    # project dropdown
    popts = [OPTION('All Project',_value='').xml()] + [OPTION(p).xml() for p in sorted(task_projects)]
    popts = ''.join(popts)
    
    # status dropdown
    sopts = [OPTION('All Status',_value='').xml()] + [OPTION(p).xml() for p in sorted(task_status)]
    sopts = ''.join(sopts)
    
    return simplejson.dumps({'cards': task_cards,
                             'tasks': task_select,
                             'projs': popts,
                             'status': sopts,
                             })

def projinfo(code=None, name=None):
    if session.all_projects:
        for p in session.all_projects:
            if code and p['code'] == code:
                return p
            elif name and p['name'] == name:
                return p
    return None

def getUserTimelogs():
    # {'start': '2015-06-28', 'end': '2015-08-09', 'shotgunid': '371', '_': '1438122316646'}
    
    shotgunid = int(request.vars.shotgunid)
    start = request.vars.start
    end = request.vars.end
    
    timelogs = getTimelogs(shotgunid, start, end)
    
    # get task ids
    task_ids = set()
    new_task_ids = set()
    for t in timelogs:
        if t['entity']:
            """
            # check if this task is in user_tasks
            if session.tasks.has_key(t['entity']['id']):
                task_ids.add(t['entity']['id'])
            else:
                new_task_ids.add(t['entity']['id'])
            """
            new_task_ids.add(t['entity']['id'])
            
    tasklist = getTasks(list(new_task_ids))
    tasks = {}
    for t in tasklist:
        tasks[t['id']] = t
    
    result = []
    """
    result.append({'id': 75744,
                   'title': 'Break',
                   'description': 'break',
                   'start': '12:00',
                   'end': '13:00',
                   'duration': '60',
                   'className': 'mrx',
                   'backgroundColor': 'brown',
                   'textColor': 'whitesmoke',
                   'allDay': False,
                   'dow': [1,2,3,4,5],
                   })
    """
    for timelog in timelogs:
        title = 'unlinked'
        proj_code = 'unknown'
        proj_ent = None
        allday = False
        
        if timelog['entity']:
            taskid = timelog['entity']['id']
            #task = session.tasks.get(taskid, tasks.get(taskid))
            task = tasks.get(taskid)
            
            if task:
                if task['entity']:
                    title = task['entity']['name']
                else:
                    title = task['content']
                    
                if re.search('vacation', title, re.I):
                    allday = True
                    
                if task['project']:
                    proj_code = re.sub('\s', '_', task['project']['name'])
                    proj_ent = projinfo(name=task['project']['name'])
                    title = '[{0}] {1}'.format(task['project']['name'], title)
        
        if proj_ent:
            projectid = proj_ent['id']
            projectname = proj_ent['name']
        else:
            projectid = 80
            projectname = 'Mr. X'
            
        bgcolour = EVENT_COLOUR
        colour = '#fff'
        if taskid == BREAK_TASK['id']:
            bgcolour = 'brown'
        elif proj_ent:
            bgcolour = rgb_to_hex(proj_ent['color'].split(','))
            if 3 > contrast_ratio(colour, bgcolour):
                colour = '#333'
                
        desc = task['sg_description']
        duration = timelog['duration'] # in minutes
        
        log_date = datetime.strptime(timelog['date'], '%Y-%m-%d')
        
        if timelog['sg_start_time_2']:
            start = timelog['sg_start_time_2']
            if not hasattr(start, 'isoformat'):
                start = datetime.strptime(start, '%Y-%m-%dT%H:%M:%S')
        else:
            start = datetime.combine(log_date, time(9, 30))
        
        # Hack to fix incorrect start time date
        if log_date.day != start.day:
            start = datetime.combine(log_date, start.time())
        
        if timelog['sg_end_time']:
            zend = timelog['sg_end_time']
            if not hasattr(zend, 'isoformat'):
                zend = datetime.strptime(zend, '%Y-%m-%dT%H:%M:%S')
                
        # hack fix for zero times
        zero_time = '00:00:00-04:00';
        if start.isoformat().endswith(zero_time) and zend.isoformat().endswith(zero_time):
            start += timedelta(hours=9, minutes=30)
            
        # calculate end time from duration and sg_start_time
        end = start + timedelta(minutes=duration)
        
        start_str = start.isoformat()
        end_str = end.isoformat()
        
        evt = {'id': timelog['id'],
               'title': title,
               'description': desc,
               'taskid': taskid,
               'projectid': projectid,
               'project': projectname,
               'start': start_str,
               'end': end_str,
               'duration': duration,
               'className': proj_code,
               'backgroundColor': bgcolour,
               'textColor': colour,
               'allDay': allday,
               }
        result.append(evt)
        
    return simplejson.dumps(result)

# temp
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
    duration_filter = {'path':'duration', 'relation':'is_not', 'values':[0]}
    cond = {'logical_operator':'and', 'conditions':[user_filter, date_filter, duration_filter]}
    result = sg.find('TimeLog',
                     cond,
                     fields=['id', 'duration', 'project', 'entity', 'date',
                             'description', 'sg_start_time_2', 'sg_end_time']
                     )
    return result

def createTimelogs(datalist):
    """Create Shotgun timelogs
    """
    batch_requests = []
    for data in datalist:
        taskid = int(data['taskid'])
        projectid = int(data['projectid'])
        suserid = int(data['suserid'])
        
        batch_requests.append({'request_type':'create',
                               'entity_type':'TimeLog',
                               'data': {'user': {'type':'HumanUser', 'id':suserid},
                                        'project': {'type':'Project', 'id':projectid},
                                        'entity': {'type':'Task', 'id':taskid},
                                        'date': data['date'],
                                        'duration': data['duration'],
                                        'description': data['comment'],
                                        'sg_start_time_2': data['start'],
                                        'sg_end_time': data['end'],
                                        }
                               })
    if batch_requests:
        ret = sg.batch(batch_requests)

def updateTimelog(timelogid, data):
    """Update Shotgun timelogs
    """
    ret = sg.update('TimeLog', timelogid, data)

def logTime():
    """Wrapper - submit a Shotgun timelog
    """
    suser_id = int(request.vars.suserid)
    task_id = int(request.vars.taskid)
    project_id = int(request.vars.projectid)
    duration = int(request.vars.duration)
    log_date = request.vars.date
    start = request.vars.start # iso format
    end = request.vars.end # iso format
    comment = request.vars.comment
    
    ret = sg.create('TimeLog',
                    {'user': {'type':'HumanUser', 'id':suser_id},
                     'project': {'type':'Project', 'id':project_id},
                     'entity': {'type':'Task', 'id':task_id},
                     'date': log_date,
                     'duration': duration,
                     'description': comment,
                     'sg_start_time_2': start,
                     'sg_end_time': end,
                     })
    if ret:
        return ret['id']
    return ''
    
def logTimes():
    """Wrapper - submit multiple Shotgun timelogs
    """
    
    return ''

def editTime():
    """Wrapper - update existing timelog
    """
    data = {}
    timelog_id = int(request.vars.timelogid)
    if request.vars.has_key('date'):
        data['date'] = request.vars.date
    if request.vars.has_key('duration'):
        data['duration'] = int(request.vars.duration)
    if request.vars.has_key('start'):
        data['sg_start_time_2'] = request.vars.start
    if request.vars.has_key('end'):
        data['sg_end_time'] = request.vars.end
    if request.vars.has_key('desc'):
        data['desc'] = request.vars.desc
    
    if data:
        updateTimelog(timelog_id, data)
        return ''
    return 'fail'


