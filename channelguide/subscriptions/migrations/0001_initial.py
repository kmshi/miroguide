
from south.db import db
from django.db import models
from channelguide.subscriptions.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Subscription'
        db.create_table('cg_channel_subscription', (
            ('timestamp', orm['subscriptions.Subscription:timestamp']),
            ('ip_address', orm['subscriptions.Subscription:ip_address']),
            ('channel', orm['subscriptions.Subscription:channel']),
            ('ignore_for_recommendations', orm['subscriptions.Subscription:ignore_for_recommendations']),
        ))
        db.send_create_signal('subscriptions', ['Subscription'])
        
        # Adding model 'GeneratedStats'
        db.create_table('cg_channel_generated_stats', (
            ('subscription_count_today', orm['subscriptions.GeneratedStats:subscription_count_today']),
            ('subscription_count_month', orm['subscriptions.GeneratedStats:subscription_count_month']),
            ('channel', orm['subscriptions.GeneratedStats:channel']),
            ('subscription_count', orm['subscriptions.GeneratedStats:subscription_count']),
        ))
        db.send_create_signal('subscriptions', ['GeneratedStats'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'Subscription'
        db.delete_table('cg_channel_subscription')
        
        # Deleting model 'GeneratedStats'
        db.delete_table('cg_channel_generated_stats')
        
    
    
    models = {
        'labels.language': {
            'Meta': {'db_table': "'cg_channel_language'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 17, 28, 57, 419485)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 17, 28, 57, 419346)'}),
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
        'subscriptions.generatedstats': {
            'Meta': {'db_table': "'cg_channel_generated_stats'"},
            'channel': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'stats'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['channels.Channel']"}),
            'subscription_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_column': "'subscription_count_total'"}),
            'subscription_count_month': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'subscription_count_today': ('django.db.models.fields.IntegerField', [], {'default': '0'})
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
            'language': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'channels'", 'db_column': "'primary_language_id'", 'to': "orm['labels.Language']"}),
            'last_moderated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'last_moderated_set'", 'null': 'True', 'to': "orm['auth.User']"}),
            'license': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40'}),
            'moderator_shared_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'moderator_shared_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'moderator_shared_set'", 'null': 'True', 'to': "orm['auth.User']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'channels'", 'to': "orm['auth.User']"}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'publisher': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['labels.Tag']"}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '8', 'null': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'waiting_for_reply_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'was_featured': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'website_url': ('django.db.models.fields.URLField', [], {'max_length': '255'})
        },
        'subscriptions.subscription': {
            'Meta': {'db_table': "'cg_channel_subscription'"},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['channels.Channel']"}),
            'ignore_for_recommendations': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {})
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
    
    complete_apps = ['subscriptions']
