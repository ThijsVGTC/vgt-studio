from django.urls import path
from . import views

urlpatterns = [
    path("", views.recording_list, name="recording_list"),
    path("bulk-update/",views.bulk_update_recordings,name="bulk_update_recordings"),
    path("bulk-video-upload/",views.bulk_video_upload,name="bulk_video_upload"),
    path("video-controle/",views.video_review,name="video_review",),
    path("video-controle/<int:signbank_id>/goedkeuren/",views.approve_new_video,name="approve_new_video",),
    path("video-controle/<int:signbank_id>/afkeuren/",views.reject_new_video,name="reject_new_video",),
    path("opname/<int:signbank_id>/",views.recording_detail,name="recording_detail"),
    path("import/", views.import_urls, name="import_urls"),
    path("import-google-sheet/", views.import_google_sheet, name="import_google_sheet"),
    path("sync-google-sheet/", views.sync_google_sheet,name="sync_google_sheet"),
    path("sync-to-google-sheet/", views.sync_to_google_sheet,name="sync_to_google_sheet"),
    path("review-status/<int:item_id>/",views.update_review_status,name="update_review_status"),
    path("opnamereeks/start/",views.start_recording_series,name="start_recording_series"),
    path("opname/<int:signbank_id>/goedkeuren/",views.approve_recording,name="approve_recording"),
    path("opname/<int:signbank_id>/overslaan-opmerking/",views.skip_recording_with_remark,name="skip_recording_with_remark",),
    path("opname/<int:signbank_id>/overslaan-video/",views.skip_recording_existing_video,name="skip_recording_existing_video",),
    path("opname/<int:signbank_id>/opmerkingen/",views.update_remarks,name="update_remarks",),
    path("opnamereeks/vorige/",views.go_to_previous_recording_item,name="previous_recording_item",),
    path("opnamereeks/voltooid/",views.recording_series_complete,name="recording_series_complete",),
    path("opnamereeks/stop/",views.stop_opnamereeks,name="stop_opnamereeks"),
]