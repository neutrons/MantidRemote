from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User

class Transaction( models.Model):
    owner = models.ForeignKey(User)
    directory = models.TextField()
    start_time = models.DateTimeField(auto_now = False, auto_now_add = True)
    # Note: we're also relying on the automatically generated id field

class Job( models.Model):
    # Choices for the last_status field
    # These are part of the API and changing them requires rev'ing the API version
#    QUEUED='queued'
#    RUNNING='running'
#    COMPLETE='cmplt'
#    ABORTED='aborted'
#    UNKNOWN='unknown'
#    STATUS_CHOICES = (
#          (QUEUED, "Queued"),
#          (RUNNING, 'Running'),
#          (COMPLETE, 'Complete'),
#          (ABORTED, 'Aborted'),
#          (UNKNOWN, 'Unknown'),)
                      
    transaction = models.ForeignKey( 'Transaction')
#    last_status = models.CharField( max_length = 7,
#                                    choices = STATUS_CHOICES,
#                                    default = UNKNOWN)
    # The ID string returned from MoabWebServices when we submit a new job. Can't use
    # Django's built-in id field because MWS ID's aren't limited to integers.
    # 30 is just a guess for the max length, but should be sufficient
    mws_job_id = models.CharField( max_length = 30) 
    
    # The actual python script that was executed.
    script_name = models.CharField( max_length = 125)
    
class File( models.Model):
    transaction = models.ForeignKey( 'Transaction')
    name = models.CharField( max_length = 256)
    # For now, this is a char field.  In the future, we might want to use
    # Django's FileField or FilePathField 

admin.site.register(Transaction)    
admin.site.register(Job)
admin.site.register(File)
