# python3.3
# ulysses2md_export_sync_1_0_1.py

# 2014-05-06, 16:40
# GNU (cl) 2014 @RoyRogers56
# Only tested with python 3.3 on OS X 10.9
# Free to use and improve. Not for sale.

# This Python script exports and syncs all Ulysses III Sheets to MultiMarkdown files.
# - Files names with sequence number Title and UUIDs,
# - in a numbered folder structure, corresponding to your Ulysses groups.
# - Marked-files are made on top and bottom levels (for Marked 2.x)
# - Any changed files are synced back and converted to Ulysses XML-files
# - Attachmets are exported for reference, but left untouched on file update in Ulysses
# - Should be roundtrip safe. Files are synced based on .ulysses' UUID

# - Specific Markdown XL tags are converted either to Critic Markup;
#   or HTML comment-tags (<!--...-->) and span-tags.

# - Also generates complete joined/merged markdown-files for each top level group.

# **Process order:**
# 1) Checks if files in export folders have been modified, since last export/sync.
#    Then syncs and converts these, back to corresponding sheets in Ulysses library.
#    Attachments in Ulysses sheets, will be left untouched.

# 2) New MD files, or sync-conflicts will be added as new sheets in Ulysses Inboxes.
#    Markdown/ CriticMarkup is converted back to Ulysses Markdown XL-syntax and XML-format.

# 3) Exports all sheets to temp folder, and then uses "rsync" to
#    copy only files changed since last sync, to export folders.
#    "rsync" also deletes md-files whose sheets have been deleted in Ulysses since last sync.
#    If they have been changed in export folder, they will appear as new sheets in inbox.

# 4) Any files deleted in export folders, will reappear at next sync.
#    No files will be deleted in Ulysses libraries! "Ulysses is the boss"

# 5) All media files are copied to export folder on corresponding level.
#    In addition also copied to a top_level media folder for each top-level group,
#    so top_level Marked-file can access media.
#    (Marked does not otherwise link media for md-files in sub folders)

# 6) Syncing should work even if sheets or md-files have been reorganized since last sync.
#    Syncing of changed back to Ulysses is based on matching sheet and md-files with same UUID

# 7) Ulysses III v1.2 need to be restarted to see **changes** in synced files.
#    (For some reason not neccessary in v1.1.2)
#    New files and sync conflicts will appear in Inboxes, without need for restart.
#    (Also no need to restart if only export.)

# **Disclaimer:**
# This is a working prototype.
# Please use on your own risk, or rather fix and improve!

# Uses "terminal-notifier" or "growlnotify" (If not installed, prints to console instead)
# Get the free "terminal-notifier" at:
#    https://github.com/downloads/alloy/terminal-notifier/terminal-notifier_1.4.2.zip
# Get "growlnotify" at:
#    http://growl.cachefly.net/GrowlNotify-2.1.zip (relies on Growl v.2.1)

import shutil
import os
import subprocess
import datetime
import re
import ulysses_sync_lib_1_0_1 as Ulib  # Main library for syncing, xml2md- and md2xml-conversions.

make_marked_files = True  # If True: Make Marked-files on top and bottom group level.
add_ul_uuid_to_export_filenames = True  # Have to be True to sync changes back to same Sheet

# Users home folder:
HOME = os.getenv("HOME", "") + "/"

# Full rsync backup of Ulysses library (except Daedalus Touch):
# (Max two backups kept for each day: AM and PM)
# (Use Hazel or similar apps, for cleanup of old backups)
backup_path = HOME + "Ulysses Backup/"
# Backup is run before each sync.

# Here, all Ulysses sheets are exported as Markdown files,
# in a folder structure same as original Ulysses groups:
sync_path_mac = HOME + "Dropbox/Notebooks/My Writings/Ulysses Mac Export/"
sync_path_icloud = HOME + "Dropbox/Notebooks/My Writings/Ulysses iCloud Export/"
# sync_path_demo = HOME + "Ulysses Demo Export/"

# Here, all sheets under each top level group, are joined as single Markdown files:
md_joined_path = HOME + "Ulysses MMD Joined_temp/"
# Note "md_joined_path" is a "temporary" folder, and md-files here will be deleted
# and regenerated each time this script is run.
# So, if you edit any of these files, please save them in a diferent folder!


def copy_media(from_path, media_path, to_root):
    # Copy media-files:
    if not os.path.exists(media_path):
        os.makedirs(media_path)
    for media_file in os.listdir(from_path):
        shutil.copy2(from_path + "/" + media_file, media_path)

    if "/_Inbox/" in media_path:
        # Inbox has ony one level:
        return

    # Also Copy all media-files to common folder,
    # to get Marked to link media when using toplevel .marked-file.
    media_top_path = media_path.replace(to_root, "")
    media_top_path = to_root + media_top_path.split("/")[0] + "/Media"
    if not os.path.exists(media_top_path):
        os.makedirs(media_top_path)
    for media_file in os.listdir(from_path):
        shutil.copy2(from_path + "/" + media_file, media_top_path)


def backup_ulysses(from_path, backup_path, branch):
    # date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H")  # Hourly cycle
    date_time = datetime.datetime.now().strftime("%Y-%m-%d_%p")  # Twice a day cycle (AM / PM)
    # date_time = datetime.datetime.now().strftime("%Y-%m-%d")  # Daily cycle
    # date_time = datetime.datetime.now().strftime("%Y-%m-%d")[:-1]  # 10 day cycle
    backup_path = backup_path + branch + "_Library_" + date_time + "/"

    if not os.path.exists(backup_path):
        os.makedirs(backup_path)

    print("=================================================================================")
    print("*** BACKUP TO:", backup_path)
    subprocess.call(['rsync', '-t', '-r', from_path, backup_path])
    print("*** End Backup")
    print()


def export_files(file_list, sync_temp, md_joined_path, last_synced, log, sync_path):

    marked_text_top = ""
    marked_text_bottom = ""
    marked_top_modified = 0
    marked_bottom_modified = 0

    last_group_path = ""
    last_path = ""
    md_main_text = ""
    ul2md = Ulib.UlyssesToMarkdown()

    for line in file_list.split("\n"):
        if line == "":
            continue
        columns = line.split("\t")
        from_path = columns[0]
        modified = columns[1]
        to_path = columns[2]
        to_file = columns[3]

        to_full_path = sync_temp + to_path

        if not os.path.exists(to_full_path):
            os.makedirs(to_full_path)

        md_text = ul2md.xml2markdown(from_path)

        if os.path.exists(from_path + "/Media"):
            media_path = to_full_path + "Media"
            copy_media(from_path + "/Media", media_path, sync_temp)

            for media_file in os.listdir(media_path):
                # print(from_path, media_file)
                try:
                    media_ref = media_file.split(".")[-2]
                    media_file = media_file.replace(" ", "%20")
                    # print(media_ref, media_file)
                    md_text = md_text.replace(media_ref + ".#fileref", media_file)
                except:
                    pass

        to_file_full = to_path + to_file + ".md"

        ts_modified = Ulib.write_file_modified(sync_temp + to_file_full, md_text, modified)

        # Check only to making log entries for exported files:
        if ts_modified > last_synced:
            dest_file = sync_path + to_file_full
            dest_modified = Ulib.get_file_date(dest_file)
            if ts_modified > dest_modified:
                if "_Inbox" in sync_temp:
                    file_name = "_Inbox/" + to_file
                else:
                    file_name = to_path + to_file
                modified_date = datetime.datetime.\
                    fromtimestamp(ts_modified).strftime("%Y-%m-%d %H:%M:%S")
                # file_name = re.sub(r"/\d\d - ", r"/", file_name)
                file_name = re.sub(r" - [0-9a-f]{32}$", r"", file_name)
                # Ulib.debug(190, file_name)
                log.add_line("Sheet edited at: ", modified_date, file_name, " - Exported to:")

        if ts_modified > marked_top_modified:
            marked_top_modified = ts_modified
        if ts_modified > marked_bottom_modified:
            marked_bottom_modified = ts_modified

        sub_paths = to_path.split("/")
        group_path = sub_paths[0] + "/"

        # make marked-file for top groups:
        if group_path != last_group_path and last_group_path != "":
            if make_marked_files:
                marked_file = sync_temp + last_group_path + "_" + last_group_path[5:-1] + ".marked"
                Ulib.write_file_modified(marked_file, marked_text_top, marked_top_modified)
                marked_text_top = ""
                marked_top_modified = 0

            # Complete Markdown file for top level group:
            Ulib.write_file(md_joined_path + last_group_path[:-1] + ".md", md_main_text)
            md_main_text = ""

        # make marked-file for bottom groups:
        if to_path != last_path and last_path != "":
            sub_paths = last_path.split("/")
            pos = len(sub_paths) - 2
            if make_marked_files:
                marked_file = sync_temp + last_path + "_" + sub_paths[pos][5:] + ".marked"
                Ulib.write_file_modified(marked_file, marked_text_bottom, marked_bottom_modified)
                marked_bottom_modified = 0
                marked_text_bottom = ""

        comment = ""  # "{>>@: " + to_file_full + "<<}\n"
        md_main_text += comment + md_text.rstrip() + "\n\n\n"

        to_file_first = to_file_full.replace(group_path, "")
        marked_text_top += "<<[" + to_file_first + "]\n"
        marked_text_bottom += "<<[" + to_file + ".md]\n"

        last_group_path = group_path
        last_path = to_path
    # endfor line in file_list.split("\n")

    # Write leftovers after end of for loop:
    if make_marked_files:
        if marked_text_top != "":
            marked_file = sync_temp + last_group_path + "_" + last_group_path[5:-1] + ".marked"
            Ulib.write_file_modified(marked_file, marked_text_top, marked_top_modified)

        if marked_text_bottom != "":
            sub_paths = last_path.split("/")
            pos = len(sub_paths) - 2
            marked_file = sync_temp + last_path + "_" + sub_paths[pos][5:] + ".marked"
            Ulib.write_file_modified(marked_file, marked_text_bottom, marked_bottom_modified)
    if md_main_text != "":
        Ulib.write_file(md_joined_path + last_group_path[:-1] + ".md", md_main_text)

    return
#end_def export_files


def main(ulysses_path, sync_temp, sync_path, md_joined_path):
    print()
    print("==============================================================================")
    print("Exporting files ...")
    print("From:", ulysses_path)
    print(" --> ", sync_path)
    print()
    # inbox_path = ulysses_path + "Unfiled-ulgroup/"
    ulgroup_path = ulysses_path + "Groups-ulgroup/"
    file_list = ""
    last_synced = 0

    if os.path.exists(md_joined_path):
        if md_joined_path != HOME and md_joined_path + "/" != HOME \
                and "." not in md_joined_path:
            # Make sure md_joined_path is not HOME path!!!
            # We don't want to delete all users files by mistake!!!
            shutil.rmtree(md_joined_path)
    if not os.path.exists(md_joined_path):
        os.makedirs(md_joined_path)

    sync_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # log = Ulib.LogFileSheet(inbox_path, sync_date)
    log = Ulib.LogFileSheet(ulgroup_path, sync_date)

    if os.path.exists(sync_path):
        sync_file = sync_path + ".ulysses_sync.log"
        last_synced = Ulib.get_file_date(sync_file)
        # Syncs markdown files changed since last sync,
        # back to corresponding sheets MardownXL and XML in Ulysses library:
        log.add_entry("**Markdown to Ulysses Sync:**")
        Ulib.sync_files(sync_path, ulysses_path, log)
    else:
        os.makedirs(sync_path)

    # Generate file list to be used by "export_files" below:
    (file_list, pc) = Ulib.list_all_files(ulysses_path + "Groups-ulgroup/", "", 1,
                                          add_ul_uuid_to_export_filenames)

    # Exports all files in Library ulysses_path to temp path: sync_temp
    # and also makes complete joined MD files for each Top Level Group to: md_joined_path
    # Ulysses Markdown XL is converted to MultiMarkdown with CriticsMarkup or
    # to plain Markdown combined with HTML comment-tags or span-tags. Set flag in lib-file

    log.add_entry("**Ulysses to Markdown Export:**")
    log.line_count = 0

    export_files(file_list, sync_temp, md_joined_path, last_synced, log, sync_path)

    # To include Default group (Unfiled-ulgroup or Inbox):
    (file_list, pc) = Ulib.list_all_files(ulysses_path + "Unfiled-ulgroup/", "", 1,
                                          add_ul_uuid_to_export_filenames)
    export_files(file_list, sync_temp + "_Inbox/", md_joined_path, last_synced,
                 log, sync_path + "_Inbox/")

    # Use rsync to copy files changed since last sync to export path: sync_path,
    # and deletes files if sheet have been deleted in Ulysses.
    subprocess.call(['rsync', '-t', '-r', '--delete', '--progress', sync_temp, sync_path])

    # sync_file must be written here after rsync, otherwise rsync will delete the file.
    sync_file = sync_path + ".ulysses_sync.log"
    Ulib.write_file(sync_file, file_list)

    shutil.rmtree(sync_temp)

    print()
    print("Export Done to: " + sync_path)
    log.write_log_sheet(False)

    return log.get_md_log()

#end_def main(ulysses_path, sync_path):


# Main Program:
main_log = ""

HOME = os.getenv("HOME", "") + "/"

ulysses_path_mac = HOME + "Library/Containers/com.soulmen.ulysses3/Data/"\
    + "Documents/Library/"
ulysses_path_icloud = HOME + "Library/Mobile Documents/X5AZV975AG~com~soulmen~ulysses3/"\
    + "Documents/Library/"
ulysses_path_demo = HOME + "Library/Containers/com.soulmen.ulysses3.demo/Data/"\
    + "Documents/Library/"

sync_temp = HOME + "ulysses_temp/"

# if os.path.exists(sync_temp):
#     print("*** WARNING!! This folder already exists:", sync_temp)
#     print("*** Rename, or delete manually if sure it contains only temp files! ***")
#     print("*** Then restart this script ***")
#     quit()

backup_ulysses(ulysses_path_mac, backup_path, "On My Mac")
backup_ulysses(ulysses_path_icloud, backup_path, "iCloud")

main_log += "Synced from: " + sync_path_mac + "\n"
main_log += main(ulysses_path_mac, sync_temp, sync_path_mac, md_joined_path + "On My Mac/")

main_log += "\nSynced from: " + sync_path_icloud + "\n"
main_log += main(ulysses_path_icloud, sync_temp, sync_path_icloud, md_joined_path + "iCloud/")

# main_log += "\nSynced from: " + sync_path_demo + "\n"
# main_log += main(ulysses_path_demo, sync_temp, sync_path_demo, md_joined_path + "Demo/")

# print()
print()
print("==============================================================================")
print(str(main_log.encode("utf-8")).replace("\\n", "\n")[2:-1].replace("\\xe2\\x80\\xa8", "\t"))
print("==============================================================================")
# Ulib.notify("Ulysses sync completed")
# print("==============================================================================")
