# Generated by Django 2.2.4 on 2019-10-23 10:25

import cvat.apps.engine.models
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

from cvat.apps.engine.models import DataChoice

# from cvat.apps.engine.serializers import TaskSerializer, DataSerializer

import os
import shutil

def create_data_objects(apps, schema_editor):
    def get_frame_path(frame):
        d1, d2 = str(int(frame) // 10000), str(int(frame) // 100)
        return os.path.join(d1, d2, str(frame) + '.jpg')

    def fix_path(path):
        ind = path.find('.upload')
        if ind != -1:
            path = path[ind + len('.upload'):]
        return path

    Task = apps.get_model('engine', 'Task')
    Data = apps.get_model('engine', 'Data')

    for db_task in Task.objects.prefetch_related("image_set").select_related("video").all():
        # create folders
        new_task_dir = os.path.join(settings.TASKS_ROOT, str(db_task.id))
        os.makedirs(new_task_dir)
        os.makedirs(os.path.join(new_task_dir, 'artifacts'))
        new_task_logs_dir = os.path.join(new_task_dir, 'logs')
        os.makedirs(new_task_logs_dir)

        # create Data object
        db_data = Data.objects.create(
            size=db_task.size,
            image_quality=db_task.image_quality,
            start_frame=db_task.start_frame,
            stop_frame=db_task.stop_frame,
            frame_filter=db_task.frame_filter,
            type=DataChoice.LIST,
        )
        db_data.save()

        db_task.data = db_data

        db_data_dir = os.path.join(settings.MEDIA_DATA_ROOT, str(db_data.id))
        os.makedirs(db_data_dir)
        compressed_cache_dir = os.path.join(db_data_dir, 'cache', 'compressed')
        # os.makedirs(compressed_cache_dir)
        os.makedirs(os.path.join(db_data_dir, 'cache', 'original'))

        old_db_task_dir = os.path.join(settings.DATA_ROOT, str(db_task.id))

        # move image data
        # compressed images
        old_task_data_dir = os.path.join(old_db_task_dir, 'data')
        if os.path.isdir(old_task_data_dir):
            shutil.copytree(old_task_data_dir, compressed_cache_dir, symlinks=False)

        # original images
        # ???


        # move logs
        task_log_file = os.path.join(old_db_task_dir, 'task.log')
        if os.path.isfile(task_log_file):
            shutil.move(task_log_file, new_task_logs_dir)

        client_log_file = os.path.join(old_db_task_dir, 'client.log')
        if os.path.isfile(client_log_file):
            shutil.move(client_log_file, new_task_logs_dir)

        # prepare *.list chunks
        for chunk_idx, start_frame in enumerate(range(0, db_data.size, db_data.chunk_size)):
            with open(os.path.join(compressed_cache_dir, '{}.list'.format(chunk_idx)), 'w') as chunk:
                stop_frame = min(db_data.chunk_size, db_data.size)
                for frame in range(start_frame, stop_frame):
                    image_path = os.path.join(compressed_cache_dir, get_frame_path(frame))
                    chunk.write(image_path + '\n')


        # create preview
        shutil.copyfile(os.path.join(compressed_cache_dir, get_frame_path(0)), os.path.join(db_data_dir, 'preview.jpeg'))

        if hasattr(db_task, 'video'):
            db_task.video.data = db_data
            db_task.video.path = fix_path(db_task.video.path)
            db_task.video.save()

        for db_image in db_task.image_set.all():
            db_image.data = db_data
            db_image.path = fix_path(db_image.path)
            db_image.save()

        db_task.clientfile_set.all().delete()
        db_task.serverfile_set.all().delete()
        db_task.remotefile_set.all().delete()

        db_task.save()

        shutil.rmtree(old_db_task_dir)

    # DL models migration
    DLModel = apps.get_model('auto_annotation', 'AnnotationModel')

    for db_model in DLModel.objects.all():
        old_location = os.path.join(settings.BASE_DIR, 'models', str(db_model.id))
        new_location = os.path.join(settings.BASE_DIR, 'data', 'models', str(db_model.id))

        shutil.copytree(old_location, new_location)

        db_model.model_file.name = db_model.model_file.name.replace(old_location, new_location)
        db_model.weights_file.name = db_model.weights_file.name.replace(old_location, new_location)
        db_model.labelmap_file.name = db_model.labelmap_file.name.replace(old_location, new_location)
        db_model.interpretation_file.name = db_model.interpretation_file.name.replace(old_location, new_location)

        db_model.save()

class Migration(migrations.Migration):

    dependencies = [
        ('engine', '0022_auto_20191004_0817'),
    ]

    operations = [
        migrations.CreateModel(
            name='Data',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chunk_size', models.PositiveIntegerField(default=36)),
                ('size', models.PositiveIntegerField(default=0)),
                ('image_quality', models.PositiveSmallIntegerField(default=50)),
                ('start_frame', models.PositiveIntegerField(default=0)),
                ('stop_frame', models.PositiveIntegerField(default=0)),
                ('frame_filter', models.CharField(blank=True, default='', max_length=256)),
                ('type', models.CharField(choices=[('video', 'VIDEO'), ('imageset', 'IMAGESET'), ('list', 'LIST')], default=cvat.apps.engine.models.DataChoice('imageset'), max_length=32)),
            ],
            options={
                'default_permissions': (),
            },
        ),
        migrations.AddField(
            model_name='task',
            name='data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='engine.Data'),
        ),
        migrations.AddField(
            model_name='image',
            name='data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='engine.Data'),
        ),
        migrations.AddField(
            model_name='video',
            name='data',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='video', to='engine.Data'),
        ),
        migrations.AddField(
            model_name='clientfile',
            name='data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='client_files', to='engine.Data'),
        ),
        migrations.AddField(
            model_name='remotefile',
            name='data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='remote_files', to='engine.Data'),
        ),
        migrations.AddField(
            model_name='serverfile',
            name='data',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='server_files', to='engine.Data'),
        ),
        migrations.RunPython(
            code=create_data_objects
        ),
        migrations.RemoveField(
            model_name='image',
            name='task',
        ),
        migrations.RemoveField(
            model_name='remotefile',
            name='task',
        ),
        migrations.RemoveField(
            model_name='serverfile',
            name='task',
        ),
        migrations.RemoveField(
            model_name='task',
            name='frame_filter',
        ),
        migrations.RemoveField(
            model_name='task',
            name='image_quality',
        ),
        migrations.RemoveField(
            model_name='task',
            name='size',
        ),
        migrations.RemoveField(
            model_name='task',
            name='start_frame',
        ),
        migrations.RemoveField(
            model_name='task',
            name='stop_frame',
        ),
        migrations.RemoveField(
            model_name='video',
            name='task',
        ),
        migrations.AlterField(
            model_name='image',
            name='path',
            field=models.CharField(default='', max_length=1024),
        ),
        migrations.AlterField(
            model_name='video',
            name='path',
            field=models.CharField(default='', max_length=1024),
        ),
        migrations.AlterUniqueTogether(
            name='clientfile',
            unique_together={('data', 'file')},
        ),
        migrations.RemoveField(
            model_name='clientfile',
            name='task',
        ),
    ]
