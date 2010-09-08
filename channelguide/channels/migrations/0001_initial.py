
from south.db import db
from django.db import models
from channelguide.channels.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'AddedChannel'
        db.create_table('cg_channel_added', (
            ('timestamp', orm['channels.AddedChannel:timestamp']),
            ('channel', orm['channels.AddedChannel:channel']),
            ('user', orm['channels.AddedChannel:user']),
        ))
        db.send_create_signal('channels', ['AddedChannel'])
        
        # Adding model 'LastApproved'
        db.create_table('cg_channel_last_approved', (
            ('timestamp', orm['channels.LastApproved:timestamp']),
        ))
        db.send_create_signal('channels', ['LastApproved'])
        
        # Adding model 'Item'
        db.create_table('cg_channel_item', (
            ('guid', orm['channels.Item:guid']),
            ('description', orm['channels.Item:description']),
            ('url', orm['channels.Item:url']),
            ('thumbnail_extension', orm['channels.Item:thumbnail_extension']),
            ('thumbnail_url', orm['channels.Item:thumbnail_url']),
            ('mime_type', orm['channels.Item:mime_type']),
            ('date', orm['channels.Item:date']),
            ('size', orm['channels.Item:size']),
            ('id', orm['channels.Item:id']),
            ('channel', orm['channels.Item:channel']),
            ('name', orm['channels.Item:name']),
        ))
        db.send_create_signal('channels', ['Item'])
        
        # Adding model 'Channel'
        db.create_table('cg_channel', (
            ('featured_by', orm['channels.Channel:featured_by']),
            ('last_moderated_by', orm['channels.Channel:last_moderated_by']),
            ('moderator_shared_by', orm['channels.Channel:moderator_shared_by']),
            ('creation_time', orm['channels.Channel:creation_time']),
            ('modified', orm['channels.Channel:modified']),
            ('featured', orm['channels.Channel:featured']),
            ('postal_code', orm['channels.Channel:postal_code']),
            ('owner', orm['channels.Channel:owner']),
            ('waiting_for_reply_date', orm['channels.Channel:waiting_for_reply_date']),
            ('id', orm['channels.Channel:id']),
            ('license', orm['channels.Channel:license']),
            ('archived', orm['channels.Channel:archived']),
            ('hi_def', orm['channels.Channel:hi_def']),
            ('state', orm['channels.Channel:state']),
            ('website_url', orm['channels.Channel:website_url']),
            ('description', orm['channels.Channel:description']),
            ('featured_at', orm['channels.Channel:featured_at']),
            ('moderator_shared_at', orm['channels.Channel:moderator_shared_at']),
            ('adult', orm['channels.Channel:adult']),
            ('feed_modified', orm['channels.Channel:feed_modified']),
            ('was_featured', orm['channels.Channel:was_featured']),
            ('publisher', orm['channels.Channel:publisher']),
            ('name', orm['channels.Channel:name']),
            ('language', orm['channels.Channel:language']),
            ('url', orm['channels.Channel:url']),
            ('geoip', orm['channels.Channel:geoip']),
            ('feed_etag', orm['channels.Channel:feed_etag']),
            ('thumbnail_extension', orm['channels.Channel:thumbnail_extension']),
            ('approved_at', orm['channels.Channel:approved_at']),
        ))
        db.send_create_signal('channels', ['Channel'])
        
        # Adding ManyToManyField 'Channel.categories'
        db.create_table('cg_category_map', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('channel', models.ForeignKey(orm.Channel, null=False)),
            ('category', models.ForeignKey(orm['labels.Category'], null=False))
        ))
        
        # Creating unique_together for [channel, user] on AddedChannel.
        db.create_unique('cg_channel_added', ['channel_id', 'user_id'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'AddedChannel'
        db.delete_table('cg_channel_added')
        
        # Deleting model 'LastApproved'
        db.delete_table('cg_channel_last_approved')
        
        # Deleting model 'Item'
        db.delete_table('cg_channel_item')
        
        # Deleting model 'Channel'
        db.delete_table('cg_channel')
        
        # Dropping ManyToManyField 'Channel.categories'
        db.delete_table('cg_category_map')
        
        # Deleting unique_together for [channel, user] on AddedChannel.
        db.delete_unique('cg_channel_added', ['channel_id', 'user_id'])
        
    
    
    models = {
        'labels.language': {
            'Meta': {'db_table': "'cg_channel_language'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 16, 3, 13, 807825)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2009, 7, 22, 16, 3, 13, 807695)'}),
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
        'channels.item': {
            'Meta': {'db_table': "'cg_channel_item'"},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'items'", 'to': "orm['channels.Channel']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'guid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'size': ('django.db.models.fields.IntegerField', [], {}),
            'thumbnail_extension': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '8', 'null': 'True'}),
            'thumbnail_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '255'})
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
        },
        'channels.addedchannel': {
            'Meta': {'unique_together': "[('channel', 'user')]", 'db_table': "'cg_channel_added'"},
            'channel': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'added_channels'", 'to': "orm['channels.Channel']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'added_channels'", 'to': "orm['auth.User']"})
        },
        'channels.lastapproved': {
            'Meta': {'db_table': "'cg_channel_last_approved'"},
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'primary_key': 'True'})
        }
    }
    
    complete_apps = ['channels']
