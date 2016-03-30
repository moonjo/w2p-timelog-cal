# -*- coding: utf-8 -*-
from gluon.custom_import import track_changes; track_changes(True)
from MySQLdb.constants.FIELD_TYPE import VARCHAR, DATE

#########################################################################
## This scaffolding model makes your app work on Google App Engine too
## File is released under public domain and you can use without limitations
#########################################################################

## if SSL/HTTPS is properly configured and you want all HTTP requests to
## be redirected to HTTPS, uncomment the line below:
# request.requires_https()

if not request.env.web2py_runtime_gae:
    ## if NOT running on Google App Engine use SQLite or other DB
    #db = DAL('mysql://xhours@localhost/xhours')
    db = DAL('mysql://timelog.sqlite')
    #session.connect(request, response, db=db, masterapp='xhours')
else:
    ## connect to Google BigTable (optional 'google:datastore://namespace')
    db = DAL('google:datastore')
    ## store sessions and tickets there
    session.connect(request, response, db=db)
    ## or store session in Memcache, Redis, etc.
    ## from gluon.contrib.memdb import MEMDB
    ## from google.appengine.api.memcache import Client
    ## session.connect(request, response, db = MEMDB(Client()))

## by default give a view/generic.extension to all actions from localhost
## none otherwise. a pattern can be 'controller/function.extension'
response.generic_patterns = ['*'] if request.is_local else []
## (optional) optimize handling of static files
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

#########################################################################
## Here is sample code if you need for
## - email capabilities
## - authentication (registration, login, logout, ... )
## - authorization (role based authorization)
## - services (xml, csv, json, xmlrpc, jsonrpc, amf, rss)
## - old style crud actions
## (more options discussed in gluon/tools.py)
#########################################################################

from gluon.tools import Auth, Crud, Service, PluginManager, prettydate
#auth = Auth(db)
auth = Auth(db, cas_provider=URL('xcas', 'default','user',args=['cas'],scheme=True,host=True))
crud, service, plugins = Crud(db), Service(), PluginManager()

## create all tables needed by auth if not custom tables
#auth.settings.login_url = URL(a='xhours', c='default', f='user', args=['login'])

from datetime import time

auth.settings.create_user_groups = False
"""
auth.settings.extra_fields['auth_user'] = [
    Field('username', length=50, unique=True, notnull=True),
    Field('first_name', length=50, notnull=True),
    Field('last_name', length=50, notnull=True),
    Field('phone', length=25, default=''),
    Field('default_start_time', 'time', default=time(9,30)),
    Field('default_end_time', 'time', default=time(18,30)),
    Field('history', 'integer', default=1),
    Field('hired_date', 'date', notnull=True, writable=False),
    Field('tier_date', 'date', writable=False),
    Field('prev_hired_date', 'date', writable=False),
    Field('active', 'integer', default=1, writable=False),
    Field('task_status', length=128, default=''),
    Field('task_check_days', 'integer', default=2),
    Field('location', length=25, default='Toronto'),
    Field('vac_tier_start', 'integer', default=1, writable=False),
    Field('new_contract', 'integer', default=1, writable=False),
    ]
"""
auth.define_tables(username=True, signature=False, migrate=True, fake_migrate=True)

## configure email
mail = auth.settings.mailer
mail.settings.server = 'logging' or 'mail.com'
mail.settings.sender = 'systems@mail.com'
mail.settings.login = 'admin:pass'

## configure auth policy
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = False
auth.settings.reset_password_requires_verification = True

one_day = 3600 * 24
auth.settings.expiration = one_day # seconds * hours * days
auth.settings.long_expiration = one_day * 7 # seconds * hours * days
auth.settings.remember_me_form = True

## if you need to use OpenID, Facebook, MySpace, Twitter, Linkedin, etc.
## register with janrain.com, write your domain:api_key in private/janrain.key
from gluon.contrib.login_methods.rpx_account import use_janrain
use_janrain(auth, filename='private/janrain.key')

#########################################################################
## Define your tables below (or better in another model file) for example
##
## >>> db.define_table('mytable',Field('myfield','string'))
##
## Fields can be 'string','text','password','integer','double','boolean'
##       'date','time','datetime','blob','upload', 'reference TABLENAME'
## There is an implicit 'id integer autoincrement' field
## Consult manual for more options, validators, etc.
##
## More API examples for controllers:
##
## >>> db.mytable.insert(myfield='value')
## >>> rows=db(db.mytable.myfield=='value').select(db.mytable.ALL)
## >>> for row in rows: print row.id, row.myfield
#########################################################################


## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)
