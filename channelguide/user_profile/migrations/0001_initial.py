
from south.db import db
from django.db import models
from channelguide.user_profile.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'UserShownLanguages'
        db.create_table('user_shown_languages', (
            ('language', orm['user_profile.UserShownLanguages:language']),
            ('user', orm['user_profile.UserShownLanguages:user']),
        ))
        db.send_create_signal('user_profile', ['UserShownLanguages'])
        
        # Adding model 'UserProfile'
        db.create_table('user', (
            ('hashed_password', orm['user_profile.UserProfile:hashed_password']),
            ('updated_at', orm['user_profile.UserProfile:updated_at']),
            ('im_username', orm['user_profile.UserProfile:im_username']),
            ('id', orm['user_profile.UserProfile:id']),
            ('blocked', orm['user_profile.UserProfile:blocked']),
            ('city', orm['user_profile.UserProfile:city']),
            ('im_type', orm['user_profile.UserProfile:im_type']),
            ('zip', orm['user_profile.UserProfile:zip']),
            ('lname', orm['user_profile.UserProfile:lname']),
            ('age', orm['user_profile.UserProfile:age']),
            ('state', orm['user_profile.UserProfile:state']),
            ('role', orm['user_profile.UserProfile:role']),
            ('fname', orm['user_profile.UserProfile:fname']),
            ('show_explicit', orm['user_profile.UserProfile:show_explicit']),
            ('email', orm['user_profile.UserProfile:email']),
            ('channel_owner_emails', orm['user_profile.UserProfile:channel_owner_emails']),
            ('moderator_board_email', orm['user_profile.UserProfile:moderator_board_email']),
            ('user', orm['user_profile.UserProfile:user']),
            ('status_emails', orm['user_profile.UserProfile:status_emails']),
            ('approved', orm['user_profile.UserProfile:approved']),
            ('language', orm['user_profile.UserProfile:language']),
            ('country', orm['user_profile.UserProfile:country']),
            ('email_updates', orm['user_profile.UserProfile:email_updates']),
            ('gender', orm['user_profile.UserProfile:gender']),
            ('filter_languages', orm['user_profile.UserProfile:filter_languages']),
            ('created_at', orm['user_profile.UserProfile:created_at']),
        ))
        db.send_create_signal('user_profile', ['UserProfile'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'UserShownLanguages'
        db.delete_table('user_shown_languages')
        
        # Deleting model 'UserProfile'
        db.delete_table('user')
        
    
    
    models = {
        'labels.language': {
            'Meta': {'db_table': "'cg_channel_language'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'user_profile.userprofile': {
            'Meta': {'db_table': "'user'"},
            'age': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'blocked': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'channel_owner_emails': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '45'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'email_updates': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'filter_languages': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'fname': ('django.db.models.fields.CharField', [], {'max_length': '45'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'hashed_password': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'im_type': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'im_username': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'language': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '5'}),
            'lname': ('django.db.models.fields.CharField', [], {'max_length': '45'}),
            'moderator_board_email': ('django.db.models.fields.CharField', [], {'default': "'S'", 'max_length': '1'}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'U'", 'max_length': '1'}),
            'show_explicit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'shown_languages': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['labels.Language']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status_emails': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'to_field': "'username'", 'unique': 'True', 'db_column': "'username'"}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 16, 34, 12, 741061)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 16, 34, 12, 740933)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'user_profile.usershownlanguages': {
            'Meta': {'db_table': "'user_shown_languages'"},
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['labels.Language']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['user_profile.UserProfile']"})
        },
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        }
    }
    
    complete_apps = ['user_profile']
