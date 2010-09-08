
from south.db import db
from django.db import models
from channelguide.user_profile.models import *

class Migration:
    
    def forwards(self, orm):

        db.execute('ALTER TABLE %(table)s DROP FOREIGN KEY %(constraint)s' % {
                'table': 'user_shown_languages',
                'constraint': 'fk_user_shown_languages_user'})
        db.rename_column('user_shown_languages', 'user_id', 'userprofile_id')
        db.execute('ALTER TABLE %(table)s ADD CONSTRAINT %(constraint)s '
                   'FOREIGN KEY (%(column)s) REFERENCES '
                   '%(other_table)s (%(other_column)s) '
                   'ON DELETE CASCADE' % {
                'table': 'user_shown_languages',
                'constraint': 'fk_user_shown_languages_userprofile',
                'column': 'userprofile_id',
                'other_table': 'user',
                'other_column': 'id'})

    def backwards(self, orm):
        db.execute('ALTER TABLE %(table)s DROP FOREIGN KEY %(constraint)s' % {
                'table': 'user_shown_languages',
                'constraint': 'fk_user_shown_languages_userprofile'})
        db.rename_column('user_shown_languages', 'userprofile_id', 'user_id')
        db.execute('ALTER TABLE %(table)s ADD CONSTRAINT %(constraint)s '
                   'FOREIGN KEY (%(column)s) REFERENCES '
                   '%(other_table)s (%(other_column)s) '
                   'ON DELETE CASCADE' % {
                'table': 'user_shown_languages',
                'constraint': 'fk_user_shown_languages_user',
                'column': 'user_id',
                'other_table': 'user',
                'other_column': 'id'})

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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 16, 35, 42, 770601)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 16, 35, 42, 770477)'}),
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
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        }
    }
    
    complete_apps = ['user_profile']
