# Ulysses III / MMD Python Sync


**Python 3.3 script backups, exports, converts, and syncs Ulysses3 XML library files,  
to and from Markdown with Critic Markup. Roundtrip safe.**

> (MIT) (c) 2014 RoyRogers56, 2014-05-07    
**Only tested with python 3.3 on OS X 10.9**  
Free to use and improve. Not for sale.  

## Features:
- Files names with sequence number Title and UUIDs,
- Numbered folder structure, corresponding to your Ulysses groups.
- Marked-files are made on top and bottom levels (Marked 2.x)
- Any changed files are synced back and converted to Ulysses XML-files
- Attachmets are exported for reference, but left untouched on sync.
- Should be roundtrip safe. Files are synced based on .ulysses' UUID
- Specific Markdown XL tags are converted to Critic Markup (default);  
	or optionally to HTML comment-tags (<!--...-->) and span-tags.
- Sync import converts either back to Markdown XL.
- Script also generates complete, joined/merged Markdown-files for each top level group.
- Logs as sheets in Ulysses Groups: "Sync Logs" (Gear Icon)
- Makes full _**rsync**_ backup of complete Ulysses Library, before each sync. Keeps max. two a day.  
Use Hazel of similar, to cleanup old backup libraries

## Process order:
1. Checks if files in export folders have been modified, since last export/sync.  
	Then syncs and converts these, back to corresponding sheets in Ulysses library.  
	Attachments in Ulysses sheets, will be left untouched.
2. New MD files, or sync-conflicts will be added as new sheets in Ulysses Inboxes.  
	Markdown/ CriticMarkup is converted back to Ulysses Markdown XL-syntax and XML-format.
3. Exports all sheets to temp folder. Then uses "rsync" to copy changes since last sync.  
"rsync" also deletes md-files whose sheets have been deleted in Ulysses since last sync.  
If md-files of deleted sheets have been edited, they will appear as new sheets in inbox.  
4. Any md-files deleted in export folders, will reappear at next sync.   
No files will be deleted in Ulysses libraries! "Ulysses is the boss"
5. All media files are copied to export folder on corresponding level.  
In addition also copied to a top-level media folder for each top-level group,  
so top-level Marked-file can access media.  
(Marked does not otherwise link media for md-files in sub folders)
6. Syncing should work even if sheets or md-files have been reorganized since last sync.  
Sync matching is based on UUID

## Limitations (by design)
1. Attachments are only exported for reference (in HTML comment block), but are kept untouched on sync/import
2. Does not support changes to, or additional media files on sync-import
3. New links to external media-files will be imported on sync though.
3. On sync-conflicts new sheets will appear in Inbox (attachments only as plain text).  
The original sheets are left untouched.
4. No automatic snapshots of sheets before sync-import, but versions by manual saves (cmd+S), are kept intact.

**Disclaimer:**  
This is a working prototype.  
Please use on your own risk.   
Please fix and improve!

Uses "terminal-notifier" or "growlnotify"   
(If not installed, prints to console instead)  

> Get the free "terminal-notifier" at:  
https://github.com/downloads/alloy/terminal-notifier/terminal-notifier_1.4.2.zip  

> Get "growlnotify" at:  
http://growl.cachefly.net/GrowlNotify-2.1.zip (relies on Growl v.2.1)

