
from south.db import db
from django.db import models
from channelguide.user_profile.models import *

class Migration:

    no_dry_run = True

    def forwards(self, orm):
        "Write your forwards migration here"

        for user_profile in orm.UserProfile.objects.all():
            if user_profile.user_id == 'miroguide':
                continue # skip the miroguide user, it's added by a fixture
            if orm['auth.user'].objects.filter(username=user_profile.user_id[:30]).count():
                continue
            print 'user', user_profile.user_id
            user = orm['auth.user'](username=user_profile.user_id[:30])
            user.email = (user_profile.email or '')[:30]
            user.first_name = (user_profile.fname or '')[:30]
            user.last_name = (user_profile.lname or '')[:30]
            user.password = '!'
            user.is_active = user_profile.approved
            user.is_superuser = (user_profile.role == 'A')
            user.save()
    
    def backwards(self, orm):
        "Write your backwards migration here"
    
    
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
            'state': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'status_emails': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'to_field': "'username'", 'unique': 'True', 'db_column': "'username'"}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 10, 16, 51, 37, 925318)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 10, 16, 51, 37, 925188)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'labels.tag': {
            'Meta': {'db_table': "'cg_tag'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
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
        'channels.channel': {
            'Meta': {'db_table': "'cg_channel'"},
            'adult': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'approved_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'archived': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['labels.Category']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'featured_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'featured_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'featured_set'", 'null': 'True', 'to': "orm['auth.User']"}),
            'feed_etag': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'feed_modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'geoip': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '100'}),
            'hi_def': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['labels.Language']", 'db_column': "'primary_language_id'"}),
            'last_moderated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'last_moderated_set'", 'null': 'True', 'to': "orm['auth.User']"}),
            'license': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'moderator_shared_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'moderator_shared_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'moderator_shared_set'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'publisher': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['labels.Tag']"}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'waiting_for_reply_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'was_featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'website_url': ('django.db.models.fields.URLField', [], {'max_length': '255'})
        },
        'labels.category': {
            'Meta': {'db_table': "'cg_category'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'on_frontpage': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        }
    }
    
    complete_apps = ['user_profile']
