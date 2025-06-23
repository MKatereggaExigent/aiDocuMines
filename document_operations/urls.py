from django.urls import path
from .views import (
    FolderDetailView, FileDetailView,
    RenameFileView, RenameFolderView,
    TrashFilesView, MoveFilesView,
    DeleteFileView, DeleteFolderView,
    DuplicateFileView, CopyFileView,
    ZipFilesView, ProtectFileView,
    RestoreFileView, RestoreFolderView,
    ListFileVersionsView, RestoreFileVersionView,
    ShareFileView, UnshareFileView, SharedFilesView,
    FilePreviewView, FileAuditLogView,
    PublicSharedFileView, FolderListView,
    FolderCreateView, TrashSingleFileView, FolderListCreateView
)

urlpatterns = [
    # 📁 FOLDER OPERATIONS
    # path("folders/", FolderListView.as_view(), name="folder_list"),
    # path("folders/", FolderCreateView.as_view(), name="create-folder"),
    path("folders/", FolderListCreateView.as_view(), name="folder_list_create"),
    path("files/<int:pk>/trash/", TrashSingleFileView.as_view(), name="trash-file"),
    path("folders/<uuid:pk>/", FolderDetailView.as_view(), name="folder_detail"),
    path("folders/<uuid:pk>/rename/", RenameFolderView.as_view(), name="folder_rename"),
    path("folders/<uuid:pk>/delete/", DeleteFolderView.as_view(), name="folder_delete"),
    path("folders/<uuid:pk>/restore/", RestoreFolderView.as_view(), name="folder_restore"),

    # 📄 FILE OPERATIONS
    path("files/<int:pk>/", FileDetailView.as_view(), name="file_detail"),
    path("files/<int:pk>/rename/", RenameFileView.as_view(), name="file_rename"),
    path("files/<int:pk>/delete/", DeleteFileView.as_view(), name="file_delete"),
    path("files/<int:pk>/duplicate/", DuplicateFileView.as_view(), name="file_duplicate"),
    path("files/<int:pk>/copy/", CopyFileView.as_view(), name="file_copy"),
    path("files/<int:pk>/protect/", ProtectFileView.as_view(), name="file_protect"),
    path("files/<int:pk>/restore/", RestoreFileView.as_view(), name="file_restore"),

    # 🗂️ BULK & UTILITIES
    path("files/trash/", TrashFilesView.as_view(), name="file_bulk_trash"),
    path("files/move/", MoveFilesView.as_view(), name="file_bulk_move"),
    path("files/zip/", ZipFilesView.as_view(), name="file_zip"),

    # 📜 FILE VERSIONING
    path("files/<int:pk>/versions/", ListFileVersionsView.as_view(), name="file_versions_list"),
    path("files/<int:pk>/versions/<int:version_number>/restore/", RestoreFileVersionView.as_view(), name="file_version_restore"),

    # 🔗 FILE SHARING
    path("files/<int:pk>/share/", ShareFileView.as_view(), name="file_share"),
    path("files/<int:pk>/unshare/", UnshareFileView.as_view(), name="file_unshare"),
    path("files/shared/", SharedFilesView.as_view(), name="file_shared_with_me"),

    # 👁️ FILE PREVIEW
    path("files/<int:pk>/preview/", FilePreviewView.as_view(), name="file_preview"),

    # 🕵️‍♂️ FILE ACTIVITY LOGS
    path("files/<int:pk>/audit/", FileAuditLogView.as_view(), name="file_audit_log"),

    # 🌐 PUBLIC ACCESS (if enabled)
    path("public/share/<uuid:share_token>/", PublicSharedFileView.as_view(), name="public_file_access"),
]

