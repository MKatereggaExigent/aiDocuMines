import os
from django.db.models import Q
from core.models import File
from document_operations.utils import get_user_accessible_file_ids
from django.contrib.auth import get_user_model


User = get_user_model()



import os
from core.models import File
from document_operations.utils import get_user_accessible_file_ids
from django.contrib.auth import get_user_model

User = get_user_model()

def get_user_file_tree(user, base_upload_dir=None):
    if not base_upload_dir:
        base_upload_dir = os.path.abspath(os.path.join("media", "uploads"))

    file_tree = []

    # 🔐 Files user can access: owned + shared
    accessible_ids = get_user_accessible_file_ids(user)
    all_files = File.objects.filter(id__in=accessible_ids)
    file_map = {os.path.normpath(os.path.abspath(f.filepath)): f.id for f in all_files}

    fallback_id_counter = {"counter": -1}

    def get_or_assign_id(filepath):
        norm_path = os.path.normpath(os.path.abspath(filepath))
        if norm_path in file_map:
            return file_map[norm_path]
        else:
            new_id = fallback_id_counter["counter"]
            fallback_id_counter["counter"] -= 1
            return new_id

    def build_tree(abs_dir, rel_path_parts):
        items = []
        try:
            entries = os.listdir(abs_dir)
        except FileNotFoundError:
            return []

        for entry in sorted(entries):
            abs_path = os.path.join(abs_dir, entry)
            rel_path = os.path.join(*rel_path_parts, entry)

            if os.path.isdir(abs_path):
                items.append({
                    "id": entry,
                    "name": entry,
                    "type": "folder",
                    "children": build_tree(abs_path, rel_path_parts + [entry])
                })
            else:
                file_id = get_or_assign_id(abs_path)
                download_url = f"/media/uploads/{rel_path}".replace("\\", "/")
                items.append({
                    "id": file_id,
                    "name": entry,
                    "type": "file",
                    "download_url": download_url,
                })

        return items

    # 1️⃣ Actual physical folder (user uploads)
    try:
        client_ids = os.listdir(base_upload_dir)
    except FileNotFoundError:
        client_ids = []

    for client_id in client_ids:
        client_dir = os.path.join(base_upload_dir, client_id)
        if not os.path.isdir(client_dir):
            continue

        #user_dir = os.path.join(client_dir, str(user.id))
        #if not os.path.isdir(user_dir):
        #    continue

        #file_tree.append({
        #    "id": client_id,
        #    "name": client_id,
        #    "type": "folder",
        #    "children": build_tree(user_dir, [client_id, str(user.id)])
        #})

        # Instead of diving into the user_id level, scan all subdirs below client_dir
        for subdir in sorted(os.listdir(client_dir)):
            project_root = os.path.join(client_dir, subdir)
            if not os.path.isdir(project_root):
                continue

            file_tree.append({
                "id": f"{client_id}/{subdir}",
                "name": subdir,
                "type": "folder",
                "children": build_tree(project_root, [client_id, subdir])
            })


    # 2️⃣ Virtual folders for shared files
    seen_virtual_paths = set()

    for file in all_files:
        abs_path = os.path.normpath(os.path.abspath(file.filepath))

        try:
            rel_path = abs_path.split("uploads" + os.sep, 1)[1]
        except IndexError:
            continue

        parts = rel_path.split(os.sep)

        if len(parts) < 3:
            continue

        # 👇 Replace original user ID (2nd part) with current user ID
        parts[1] = str(user.id)
        virtual_rel_path = os.path.join(*parts)
        norm_virtual_path = os.path.normpath(virtual_rel_path)

        if norm_virtual_path in seen_virtual_paths:
            continue
        seen_virtual_paths.add(norm_virtual_path)

        current_level = file_tree
        for i, part in enumerate(parts[:-1]):
            match = next((item for item in current_level if item["type"] == "folder" and item["name"] == part), None)
            if not match:
                new_folder = {
                    "id": f"{'/'.join(parts[:i+1])}",
                    "name": part,
                    "type": "folder",
                    "children": []
                }
                current_level.append(new_folder)
                current_level = new_folder["children"]
            else:
                current_level = match["children"]

        # ⬇️ Add the file itself
        current_level.append({
            "id": file.id,
            "name": os.path.basename(file.filepath),
            "type": "file",
            "download_url": f"/media/uploads/{'/'.join(parts)}".replace("\\", "/")
        })

    return file_tree





'''
def get_user_file_tree(user, base_upload_dir=None):
    if not base_upload_dir:
        base_upload_dir = os.path.abspath(os.path.join("media", "uploads"))

    file_tree = []

    # 🔐 Fetch files user can access (owned + shared)
    accessible_ids = get_user_accessible_file_ids(user)
    all_files = File.objects.filter(id__in=accessible_ids)
    file_map = {os.path.normpath(os.path.abspath(f.filepath)): f.id for f in all_files}

    fallback_id_counter = {"counter": -1}

    def get_or_assign_id(filepath):
        norm_path = os.path.normpath(os.path.abspath(filepath))
        if norm_path in file_map:
            return file_map[norm_path]
        else:
            new_id = fallback_id_counter["counter"]
            fallback_id_counter["counter"] -= 1
            return new_id

    def build_tree(abs_dir, rel_path_parts):
        items = []
        try:
            entries = os.listdir(abs_dir)
        except FileNotFoundError:
            return []

        for entry in sorted(entries):
            abs_path = os.path.join(abs_dir, entry)
            rel_path = os.path.join(*rel_path_parts, entry)

            if os.path.isdir(abs_path):
                items.append({
                    "id": entry,
                    "name": entry,
                    "type": "folder",
                    "children": build_tree(abs_path, rel_path_parts + [entry])
                })
            else:
                file_id = get_or_assign_id(abs_path)
                download_url = f"/media/uploads/{rel_path}".replace("\\", "/")
                items.append({
                    "id": file_id,
                    "name": entry,
                    "type": "file",
                    "download_url": download_url,
                })

        return items

    # Scan base_upload_dir
    try:
        client_ids = os.listdir(base_upload_dir)
    except FileNotFoundError:
        client_ids = []

    for client_id in client_ids:
        client_dir = os.path.join(base_upload_dir, client_id)
        if not os.path.isdir(client_dir):
            continue

        user_dir = os.path.join(client_dir, str(user.id))
        if not os.path.isdir(user_dir):
            continue

        file_tree.append({
            "id": client_id,
            "name": client_id,
            "type": "folder",
            "children": build_tree(user_dir, [client_id, str(user.id)])
        })

    return file_tree
'''

'''
def get_user_file_tree(user_id, base_upload_dir=None, base_url=None):
    """
    Returns the full nested tree of user's uploaded files and folders,
    including download URLs and DB file IDs.
    Matches the NEW upload path structure:
      uploads/<client_id>/<user_id>/<project_id>/<service_id>/<yyyymmdd>/
    """
    if not base_upload_dir:
        base_upload_dir = os.path.abspath(os.path.join("media", "uploads"))

    file_tree = []

    # Pre-fetch all file records for this user
    all_files = File.objects.filter(user_id=user_id)
    file_map = {os.path.normpath(os.path.abspath(f.filepath)): f.id for f in all_files}

    fallback_id_counter = {"counter": -1}

    def get_or_assign_id(filepath):
        norm_path = os.path.normpath(os.path.abspath(filepath))
        if norm_path in file_map:
            return file_map[norm_path]
        else:
            new_id = fallback_id_counter["counter"]
            fallback_id_counter["counter"] -= 1
            return new_id

    def build_tree(abs_dir, rel_path_parts):
        items = []
        try:
            entries = os.listdir(abs_dir)
        except FileNotFoundError:
            return []

        for entry in sorted(entries):
            abs_path = os.path.join(abs_dir, entry)
            rel_path = os.path.join(*rel_path_parts, entry)

            if os.path.isdir(abs_path):
                items.append({
                    "id": entry,
                    "name": entry,
                    "type": "folder",
                    "children": build_tree(abs_path, rel_path_parts + [entry])
                })
            else:
                file_id = get_or_assign_id(abs_path)
                download_url = f"/media/uploads/{rel_path}".replace("\\", "/")

                items.append({
                    "id": file_id,
                    "name": entry,
                    "type": "file",
                    "download_url": download_url,
                })

        return items

    # Scan base_upload_dir
    try:
        client_ids = os.listdir(base_upload_dir)
    except FileNotFoundError:
        client_ids = []

    for client_id in client_ids:
        client_dir = os.path.join(base_upload_dir, client_id)
        if not os.path.isdir(client_dir):
            continue

        user_dir = os.path.join(client_dir, str(user_id))
        if not os.path.isdir(user_dir):
            continue

        file_tree.append({
            "id": client_id,
            "name": client_id,
            "type": "folder",
            "children": build_tree(user_dir, [client_id, str(user_id)])
        })

    return file_tree
'''


'''
def get_user_file_tree(user_id, base_upload_dir=None, base_url=None):
    """
    Returns the full nested tree of user's uploaded files and folders,
    including direct download URL and ID from database for each file.
    Files not in the DB are shown with a unique fallback ID but not saved.
    """
    if not base_upload_dir:
        # base_upload_dir = os.path.abspath(os.path.join("media", "uploads", str(user_id)))
        base_upload_dir = os.path.abspath(os.path.join("media", "uploads"))

    if not base_url:
        # base_url = f"/media/uploads/{user_id}"
        base_url = f"/media/uploads"

    file_tree = []

    # Pre-fetch all file records for this user
    all_files = File.objects.filter(user_id=user_id)
    file_map = {os.path.normpath(os.path.abspath(f.filepath)): f.id for f in all_files}

    # Start fallback counter one above max existing file ID
    # fallback_id_counter = {"counter": max(file_map.values(), default=0) + 1}

    fallback_id_counter = {"counter": -1}


    def get_or_assign_id(filepath):
        norm_path = os.path.normpath(os.path.abspath(filepath))
        if norm_path in file_map:
            return file_map[norm_path]
        else:
            new_id = fallback_id_counter["counter"]
            fallback_id_counter["counter"] -= 1  # Decrement for next
            return new_id


    #def get_or_assign_id(filepath):
    #    norm_path = os.path.normpath(os.path.abspath(filepath))
    #    if norm_path in file_map:
    #        return file_map[norm_path]
    #    else:
    #        new_id = fallback_id_counter["counter"]
    #        fallback_id_counter["counter"] += 1
    #        return new_id

    def build_tree(current_dir, rel_path_parts):
        items = []
        abs_dir = os.path.join(base_upload_dir, *rel_path_parts)

        try:
            entries = os.listdir(abs_dir)
        except FileNotFoundError:
            return []

        for entry in sorted(entries):
            abs_path = os.path.join(abs_dir, entry)
            rel_path = os.path.join(*rel_path_parts, entry)

            if os.path.isdir(abs_path):
                depth = len(rel_path_parts)
                if depth == 0:
                    folder_id, folder_name = entry, "datetime"
                elif depth == 1:
                    folder_id, folder_name = entry, "run"
                elif depth == 2:
                    folder_id, folder_name = "project", entry
                elif depth == 3:
                    folder_id, folder_name = "service", entry
                elif depth == 4:
                    folder_id, folder_name = entry, "files"
                else:
                    folder_id, folder_name = entry, entry

                items.append({
                    "id": folder_id,
                    "name": folder_name,
                    "type": "folder",
                    "children": build_tree(abs_path, rel_path_parts + [entry])
                })
            else:
                file_id = get_or_assign_id(abs_path)
                items.append({
                    "id": file_id,
                    "name": entry,
                    "type": "file",
                    "download_url": f"{base_url}/{rel_path}".replace("\\", "/")
                })

        return items

    # Root folders (datetime level)
    for root_entry in sorted(os.listdir(base_upload_dir)):
        root_path = os.path.join(base_upload_dir, root_entry)
        if os.path.isdir(root_path):
            file_tree.append({
                "id": root_entry,
                "name": "datetime",
                "type": "folder",
                "children": build_tree(root_path, [root_entry])
            })

    #return {
    #    "user_id": user_id,
    #    "structure": file_tree
    #}
    return file_tree

'''
