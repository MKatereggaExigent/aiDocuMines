import os
from django.db.models import Q
from core.models import File


def get_user_file_tree(user_id, base_upload_dir=None, base_url=None):
    """
    Returns the full nested tree of user's uploaded files and folders,
    including direct download URL and ID from database for each file.
    Files not in the DB are shown with a unique fallback ID but not saved.
    """
    if not base_upload_dir:
        base_upload_dir = os.path.abspath(os.path.join("media", "uploads", str(user_id)))

    if not base_url:
        base_url = f"/media/uploads/{user_id}"

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

