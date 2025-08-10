# file_system/utils.py
import os
from django.db.models import Q  # if you need it elsewhere
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

        # --- CHANGE (A): only traverse the current user's dir, and hide user_id in tree ---
        user_dir = os.path.join(client_dir, str(user.id))
        if not os.path.isdir(user_dir):
            continue

        # Show a client-level folder; children start at user's root
        file_tree.append({
            "id": client_id,
            "name": client_id,
            "type": "folder",
            # IMPORTANT: rel_path_parts includes user.id so download_url stays correct,
            # but user.id never appears in visible folder 'name's (coming from disk entries).
            "children": build_tree(user_dir, [client_id, str(user.id)])
        })
        # --- END CHANGE (A) ---

    # 2️⃣ Virtual folders for shared files (hide the owner user_id in display)
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


        # 🚩 Skip files you own — they're already in the physical tree!
        if str(parts[1]) == str(user.id):
            continue


        # parts = [client, owner_user_id, ..., filename]
        client = parts[0]
        filename = parts[-1]

        # --- CHANGE (B): do NOT inject any user_id in the visible tree ---
        # Display path skips parts[1] (owner_user_id)
        display_parts = [client] + parts[2:-1]
        # --- END CHANGE (B) ---

        # Dedup by display path + filename
        display_key = tuple(display_parts + [filename])
        if display_key in seen_virtual_paths:
            continue
        seen_virtual_paths.add(display_key)

        # Walk/create folders in file_tree according to display_parts
        current_level = file_tree
        for i, part in enumerate(display_parts):
            match = next((item for item in current_level
                          if item["type"] == "folder" and item["name"] == part), None)
            if not match:
                new_folder = {
                    "id": f"{'/'.join(display_parts[:i+1])}",
                    "name": part,
                    "type": "folder",
                    "children": []
                }
                current_level.append(new_folder)
                current_level = new_folder["children"]
            else:
                current_level = match["children"]

        # ⬇️ Add the file itself (download_url keeps original path incl. owner id)
        current_level.append({
            "id": file.id,
            "name": filename,
            "type": "file",
            "download_url": f"/media/uploads/{rel_path}".replace("\\", "/")
        })

    return file_tree

