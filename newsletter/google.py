from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from apiclient.errors import HttpError
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from newsletter.models import Subscription, Newsletter
import json
import re
import random


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/groupssettings-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/admin.directory.group.member'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Groups Settings API Python Quickstart'



def remove(email,group,service=None):
    if not service:
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('admin', 'directory_v1', http=http)
    
    
    print(group)
    try:
        
        results=service.members().delete(groupKey=group,memberKey=email).execute()
        print('REMOVED: {0}'.format(results))
    except HttpError as err:
        
        print('ERROR REMOVE: {0}'.format(err._get_reason()))
        print('ERROR REMOVE: {0}'.format(email))
        
    
def list(group,service=None):
    if not service:
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('admin', 'directory_v1', http=http)
    
    
    current=service.members().list(groupKey=group).execute()
    next=current.get("nextPageToken",False)
    current=current.get("members",[])
    members=[item['email'] for item in current]
    
    while next:
        try:
            
            current=service.members().list(groupKey=group,pageToken=next).execute()
            next=current.get("nextPageToken",'')
            current=current.get("members",[])
            members=members+[item['email'] for item in current]
            
        except HttpError as err:
            print('ERROR REMOVE: {0}'.format(err._get_reason()))
            pass
    
    return members
        
def add(record,group,service=None):
    
    if not service:
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('admin', 'directory_v1', http=http)
    body={ # JSON template for Member resource in Directory API.
        "status": "ACTIVE", # Status of member (Immutable)
        "kind": "admin#directory#member", # Kind of resource this is.
        
        "role": "MEMBER", # Role of member
        "type":"EXTERNAL",
        "email": record.get_email(), # Email of member (Read-only)
        }
    print(group)
    try:
        results=service.members().insert(groupKey=group,body=body).execute()
        print('ADDED: {0}'.format(results))
    except HttpError as err:
        
        
        print('ERROR ADD: {0}'.format(err._get_reason()))
        print('ERROR ADD: {0}'.format(record.get_email()))
       
def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'groupssettings-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        
        print('Storing credentials to ' + credential_path)
    return credentials

def purge_from_file(file):
    """Shows basic usage of the Google Admin-SDK Groups Settings API.

    Creates a Google Admin-SDK Groups Settings API service object and outputs a
    group's settings identified by the group's email address.
    """
    
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('admin', 'directory_v1', http=http)
    f=open(file)
    for email in f:
        email=email.strip().rstrip(',')
        remove(email,"_newsletter@africaglobalfunds.com",service=service)
        remove(email,"_promo@africaglobalfunds.com",service=service)
        try:
            user = User.objects.get(email__iexact=email)
            try:
                s=Subscription.objects.filter(user=user)
                for s in s:
                    print("Deletin Subscription")
                    s.delete()
            except ObjectDoesNotExist:
                pass
            print("Deletin User")
            user.delete()
        except ObjectDoesNotExist:
            s=Subscription.objects.filter(email_field__iexact=email)
            for s in s:
                print("Deletin Subscription")
                s.delete()
        
def sync(group,title):
    """Shows basic usage of the Google Admin-SDK Groups Settings API.

    Creates a Google Admin-SDK Groups Settings API service object and outputs a
    group's settings identified by the group's email address.
    """
    
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('admin', 'directory_v1', http=http)
    
    nl=list(group,service=service)
    for email in nl:
        try:
            user = User.objects.get(email__iexact=email)
            try:
                s=Subscription.objects.filter(newsletter__title=title,user=user)
                if not s:
                    remove(email,group,service=service)
                    
            except ObjectDoesNotExist:
                pass
            
        except ObjectDoesNotExist:
            
            s=Subscription.objects.filter(newsletter__title=title,email_field__iexact=email)
            if not s:
                remove(email,group,service=service)
                
def sync_up(group,title):
    """Shows basic usage of the Google Admin-SDK Groups Settings API.

    Creates a Google Admin-SDK Groups Settings API service object and outputs a
    group's settings identified by the group's email address.
    """
    
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('admin', 'directory_v1', http=http)
    
    s=Subscription.objects.filter(newsletter__title=title)
    #l=list(group,service=service)
    for person in s:
        if not re.match(r"[^@]+@[^@]+\.[^@]+",person.get_email()):
            
            print("REMOVED SUBSCRIPTION {0}".format(person.get_email()))
            person.delete()
            continue
        add(person,group,service)
            
def remove_dupes(title):
    s_u=Subscription.objects.filter(newsletter__title=title,email_field=None)
    s_n_u=Subscription.objects.filter(newsletter__title=title,user=None)
    
    for item in s_u:
        for s in s_n_u:
            if s.email_field.lower()==item.user.email.lower():
                print("REMOVING {0}".format(s.email_field))
                s.delete()
    for item in s_n_u:
        for s in s_n_u:
            if (s.email_field.lower()==item.get_email().lower()) and (s.id != item.id):
                print("REMOVING SNU {0}".format(s.email_field))
                s.delete()
                
def clone_local(title_from,title_to,group_to):
    _from=Subscription.objects.filter(newsletter__title=title_from)
   
    title_to=Newsletter.objects.get(title=title_to)
    
    for item in _from:
        item.newsletter=title_to
        item.pk=None
        
        
        item.save()
        
#if __name__ == '__main__':
#    main()


