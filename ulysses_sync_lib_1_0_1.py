# python3.3
# ulysses_sync_lib_1_0_1.py

# 2014-05-06, 16:40
# GNU (cl) 2014 @RoyRogers56
# Free to use and improve. Not for sale.
# Python Library to be imported and work with "ulysses2md_export_sync_1_0_0.py"

from xml.dom import minidom
import datetime
# import time
import xml.etree.ElementTree as ET
from os import walk
import os
import re
import uuid
import subprocess
import plistlib

use_critic_markup = True  # Change to switch between Critic Markup or HTML markup on export.
                           # Sync / import will accept either, independently of this switch.
if use_critic_markup:
    cmt_start = "{>>"
    cmt_end = "<<}"
    del_start = "{--"
    del_end = "--}"
    mark_start = "{++"
    mark_end = "++}"
else:
    # HTML markup:
    cmt_start = "<!--"
    cmt_end = "-->"
    del_start = "<!--Delete:"
    del_end = "-->"
    mark_start = "<span class='mark'>"
    mark_end = "</span>"

# Unicode manual line-break used by Ulysses:
LINE_BREAK = u"\u2028"


def debug(line_num, msg, output=True, stop=True):
    if not output:
        return

    prefix = "*** Debug at line: " + str(line_num) + ": "
    try:
        print(prefix + msg)
    except:
        print(prefix + str(msg.encode("utf-8"))[2:-1].replace("\\n", "\n"))
    if stop:
        quit()


def notify(message):
    title = "Ulysses Markdown Export Sync"

    try:
        # Uses "terminal-notifier", download at:
        # https://github.com/downloads/alloy/terminal-notifier/terminal-notifier_1.4.2.zip
        # Only works with OS X 10.8+
        subprocess.call(['/Applications/terminal-notifier.app/Contents/MacOS/terminal-notifier',
                         '-message', message, "-title", title])
    except:
        print('* "terminal-notifier.app" is missing!')

        try:
            # Uses "growlnotify", download at:
            # http://growl.cachefly.net/GrowlNotify-2.1.zip
            # Depends on Growl 2
            subprocess.call(['/usr/local/bin/growlnotify', title,
                             '-m', message])
        except:
            print('* "growlnotify" is missing!')

    print("* Message:", str(message.encode("utf-8")))
    return


def read_file(file_name):
    f = open(file_name, "r", encoding='utf-8')
    file_content = f.read()
    f.close()
    return file_content


def write_file(filename, file_content):
    f = open(filename, "w", encoding='utf-8')
    f.write(file_content)
    f.close()


def set_file_date(filename, ts):
    #ts = datetime.datetime.totimestamp(date_time)
    ts_fl = float(ts)
    ts_int = int(ts_fl)
    os.utime(filename, (-1, ts_int))
    return ts_int


def write_file_modified(filename, file_content, modified):
    write_file(filename, file_content)
    ts_int = set_file_date(filename, modified)
    return ts_int


def get_file_date(filename):
    try:
        t = os.path.getmtime(filename)
        return t
    except:
        return 0
    #return datetime.datetime.fromtimestamp(t)


def clean_file_title(title, ul_file, add_uuid):
    # Clean MD titel to make safe cross-platform filenames:
    title = re.sub(r"[/\\—|.&<>:]", r"-", title)
    title = re.sub(r"[\*]", r"_", title)

    # Strip all special chars:
    # title = re.sub(r"[^_0-9a-zA-Z \-]", r"", title)  # ASCII Only
    title = re.sub(r"[#?*^,;!$+=%§'\[\]\{\}\"\t\n\r\f\v“”‘’´`¨]", r"", title)
    title = title.strip()
    # debug(126, title, "Test title" in title)
    if title == "":
        title = "Untitled"
    if ul_file != "" and add_uuid:
        ul_file = ul_file[:-8]
        # print (ul_file)
        # quit()
        return title[:64] + " - " + ul_file
    else:
        return title[:64]


def list_all_files(path, out_path, path_count, add_ul_uuid, tree_depth=0):

    file_list = ""

    file_count = 1
    sub_path_count = 1

    info_ulgroup = path + "Info.ulgroup"

    xml_plist = ET.parse(info_ulgroup)

    group_title = xml_plist.findall(".//dict/string")
    if group_title and tree_depth > 0:
        # print("---", group_title[0].text)
        sub_out_path = group_title[0].text

        out_path += str(path_count).zfill(2) + " - "\
            + clean_file_title(sub_out_path, "", add_ul_uuid) + "/"
        path_count += 1

    nodelist = xml_plist.findall(".//dict/array//string")
    for item in nodelist:
        sub_path = item.text
        # Sheets:
        if sub_path.endswith(".ulysses"):
            file_name = path + sub_path + "/" + "Content.xml"
            modified = get_file_date(file_name)

            try:
                xml_doc = ET.parse(file_name)
            except:
                print("*** File Missing or Corrupt XML:", file_name)
                continue

            p = xml_doc.find(".//p")
            if p is not None:
                title = ET.tostring(p, "unicode", "text")
            else:
                title = "Untitled"

            title = clean_file_title(title, sub_path, add_ul_uuid)

            if re.match(r"Log - 20\d\d-[0-1]\d-[0-3]\d [0-2]\d-[0-5]\d-[0-5]\d", title):
                # debug(175, title)
                pass
            else:
                title = str(file_count).zfill(2) + " - " + title

            file_count += 1

            file_list += path + sub_path + "\t" + str(modified) + "\t"\
                + out_path + "\t" + title + "\n"
            path_count = 1
    for item in nodelist:
        sub_path = item.text
        # Groups:
        if sub_path.endswith("-ulgroup"):
            fl, pc = list_all_files(path + sub_path + "/", out_path, sub_path_count,
                                    add_ul_uuid, tree_depth + 1)
            file_list += fl
            sub_path_count += pc
            path_count += 1

    path_count = 1
    return (file_list, path_count)
#end_def list_all_files(path, out_path, path_count, add_ul_uuid, tree_depth=0)


class UlyssesToMarkdown:

    def __init__(self):
        self.footnotes = ""
        self.links = ""
        self.img_links = ""
        self.img_num = 1
        self.fn_num = 1
        self.link_num = 1

    def parse_paragraph(self, document):
        md_line = ""

        for child in document.childNodes:
            #if child.nodeType == child.TEXT_NODE:
                # tag = document.tagName
            if document.tagName == "p":
                if child.nodeType == child.TEXT_NODE:
                    #print(child.data, end='')
                    md_line += child.data
            elif document.tagName == 'tag':
                if child.nodeType == child.TEXT_NODE:
                    #print(child.data)
                    md_line += re.sub(r"^[ \t]*''", r"\t", child.data)
            elif document.tagName == 'tags':
                pass
            elif document.tagName == 'escape':
                if child.nodeType == child.TEXT_NODE:
                    md_line += child.data[1:]  # Strips off the escape char: "\""
            elif document.tagName == 'element':
                kind = document.attributes["kind"].value
                startTag = ""
                if kind == "strong" or kind == "emph" or kind == "code":
                    startTag = document.attributes["startTag"].value
                    md_line += startTag
                    if child.nodeType == child.TEXT_NODE:
                        md_line += child.data
                    if child.nodeType == child.ELEMENT_NODE:
                        md_line += self.parse_paragraph(child)
                    md_line += startTag
                    continue
                elif kind == "inlineNative":
                    if child.nodeType == child.TEXT_NODE:
                        md_line += child.data
                    continue
                elif kind == "inlineComment":
                    #startTag = document.attributes["startTag"].value
                    md_line += cmt_start  # startTag
                    if child.nodeType == child.TEXT_NODE:
                        md_line += child.data
                    if child.nodeType == child.ELEMENT_NODE:
                        md_line += self.parse_paragraph(child)
                    md_line += cmt_end  # startTag
                    continue
                elif kind == "delete":
                    #startTag = document.attributes["startTag"].value
                    md_line += del_start  # startTag
                    if child.nodeType == child.TEXT_NODE:
                        md_line += child.data
                    if child.nodeType == child.ELEMENT_NODE:
                        md_line += self.parse_paragraph(child)
                    md_line += del_end  # startTag
                    continue
                elif kind == "mark":
                    #startTag = document.attributes["startTag"].value
                    md_line += mark_start  # startTag
                    if child.nodeType == child.TEXT_NODE:
                        md_line += child.data
                    if child.nodeType == child.ELEMENT_NODE:
                        md_line += self.parse_paragraph(child)
                    md_line += mark_end  # startTag
                    continue
                elif kind == "link":
                    url, title, text = "", "", ""
                    element_node = ET.fromstring(document.toxml())

                    elem = element_node.find("attribute[@identifier='URL']")
                    if elem is not None:
                        if elem.text is not None:
                            url = elem.text
                    elem = element_node.find("attribute[@identifier='title']")
                    if elem is not None:
                        if elem.text is not None:
                            title = elem.text
                    for item in element_node.itertext():
                        if item is not None:
                            text = item
                    if url == "":
                        md_line += "[" + text + "]()"
                    else:
                        md_line += "[" + text + "][" + str(self.link_num) + "]"
                        self.links += "[" + str(self.link_num) + "]:\t" + url\
                            + ' "' + title + '"\n'
                        self.link_num += 1
                    break
                elif kind == "image":
                    image, title, description, link = "", "", "", ""
                    element_node = ET.fromstring(document.toxml())

                    elem = element_node.find("attribute[@identifier='URL']")
                    if elem is not None:
                        if elem.text is not None:
                            link = elem.text.replace(" ", "%20")
                    elem = element_node.find("attribute[@identifier='image']")
                    if elem is not None:
                        if elem.text is not None:
                            if link != "":
                                image = "<!--Media:" + elem.text + "-->\n"
                            else:
                                link = "Media/" + elem.text + ".#fileref"
                    elem = element_node.find("attribute[@identifier='title']")
                    if elem is not None:
                        if elem.text is not None:
                            title = elem.text
                    elem = element_node.find("attribute[@identifier='description']")
                    if elem is not None:
                        if elem.text is not None:
                            description = elem.text

                    md_line += "![" + description + "]["+kind+"-" + str(self.img_num) + "]"

                    self.img_links += "["+kind+"-" + str(self.img_num) + "]:\t"\
                        + link + ' "' + title + '"\n' + image
                    self.img_num += 1
                    break
                elif kind == "video":
                    link, image = "", ""
                    element_node = ET.fromstring(document.toxml())
                    elem = element_node.find("attribute[@identifier='URL']")
                    if elem is not None:
                        if elem.text is not None:
                            link = elem.text.replace(" ", "%20")
                    elem = element_node.find("attribute[@identifier='video']")
                    if elem is not None:
                        if elem.text is not None:
                            if link != "":
                                image = "<!--Media:" + elem.text + "-->"
                            else:
                                link = "Media/" + elem.text + ".#fileref"
                    md_line += '<figure><video src="'+link+'">'+image+'</video></figure>'
                    break
                elif kind == "annotation":
                    anno = document.toxml().replace("\n", "")
                    annotated = re.sub(r"(<element.*?</string></attribute>)(.*?)</element>",
                                       r"\2", anno)

                    note = ""
                    for child2 in child.getElementsByTagName("p"):
                        if child2.nodeType == child2.ELEMENT_NODE:
                            note += self.parse_paragraph(child2) + "<br/>"
                    note = note[:-5]  # Strip last <br/>

                    if use_critic_markup:
                        md_line += "{==" + annotated + "==}{>>" + note + "<<}"
                    else:
                        md_line += "<span class='annotation'>" + annotated + "</span>"\
                                   "<!--" + note + "-->"
                    break
                elif kind == "footnote":
                    md_line += "[^" + str(self.fn_num) + "]"

                    note = ""
                    for child2 in child.getElementsByTagName("p"):
                        if child2.nodeType == child2.ELEMENT_NODE:
                            note += self.parse_paragraph(child2) + "  \n\t"

                    note = note[:-1]
                    # print (str(note.encode("utf-8")))
                    # quit()

                    self.footnotes += "[^" + str(self.fn_num) + "]:\t" + note + "\n"
                    self.fn_num += 1
                    break
                else:
                    if child.nodeType == child.TEXT_NODE:
                        #print("<" + kind + ">", child.data, end="")
                        md_line += "{>>Unhandled: " + kind + ": " + child.data + "<<}"
                    else:
                        md_line += child.toxml()
            else:
                #md_line += "---" + child.toxml()
                pass
            if child.nodeType == minidom.Node.ELEMENT_NODE:
                md_line += self.parse_paragraph(child)
        #endfor child in document.childNodes
        return md_line
    #end_def parse_paragraph(self, document)

    def get_attacments_as_md(self, xml_data):
        # Adding all attachmets to md-output, as commented text using MMD/ CriticMarkup:
        #xml_doc = ET.parse(ulysses_file)
        attachments = ""
        xml_doc = ET.fromstring(xml_data)

        sheet_version = xml_doc.attrib["version"]

        if sheet_version == "2":
            type_note = "note"
            type_file = "file"
            type_keywords = "keywords"
        else:
            type_note = "1"
            type_file = "2"
            type_keywords = "3"

        nodelist = xml_doc.find(".//attachment")
        if nodelist is not None:
            attachments = "<!--ul_attachments:\n### Attachments:\n"

            nodelist = xml_doc.findall("attachment[@type='" + type_note + "']/string")  # 1
            for node in nodelist:
                # Quick and dirty: just stripping of any char formatting like em and strong:
                string = str(ET.tostring(node, encoding="unicode", method="xml"))
                string = "_Note_:  " + re.sub(r"<.+?>", r"", string)
                string = string.replace("\n", "  \n")
                attachments += "\n" + string

            nodelist = xml_doc.findall("attachment[@type='"+type_file+"']")  # "2"
            for node in nodelist:
                if node.text is not None:
                    # print ("_Image_: ![Image](Media/" + node.text + ".#fileref)\n")
                    attachments += "\n_Image_: ![Image](Media/" + node.text + ".#fileref)\n"

            nodelist = xml_doc.findall("attachment[@type='"+type_keywords+"']")  # 3
            for node in nodelist:
                if node.text is not None:
                    keylist = node.text.split(",")
                    keywords = ""
                    for key in keylist:
                        keywords += "@" + key + ", "
                    # print ("_Keywords_: " + keywords + "\n")
                    attachments += "\n_Keywords_: " + keywords + "\n"

            nodelist = xml_doc.findall("attachment[@type='goal']")
            for node in nodelist:
                if node.text is not None:
                    attachments += "\n_Goal_: " + node.text + "\n"

            attachments += "-->\n"
        return attachments
    #end_def get_attacments_as_md(self, xml_data)

    def xml2markdown(self, ulysses_path):
        md_text = ""

        ulysses_file = ulysses_path + "/Content.xml"

        ul_file = open(ulysses_file, "r", encoding='utf-8')
        xml_data = ul_file.read()
        ul_file.close()

        xdoc = minidom.parseString(xml_data)

        document = xdoc.documentElement
        self.footnotes = ""
        self.links = ""
        self.img_links = ""
        document = document.childNodes[3]
        for child in document.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'p':
                    if child.childNodes:
                        # Here is where most formatting is done:
                        line = self.parse_paragraph(child)

                        # if LINE_BREAK in line:
                        # Manual line-break in MD: add two spaces at end of line:
                        line = line.replace(LINE_BREAK, "  \n")

                        # Post-processing some beginning-of-line-tags:
                        if line.startswith("%% "):
                            md_text += cmt_start + line[3:] + cmt_end
                        elif line.startswith("%%"):
                            md_text += cmt_start + line[2:] + cmt_end
                        elif line.startswith("~~ "):
                            # Native code (HTML), don't need escaping in MD
                            md_text += line[3:]
                        elif line.startswith("~~"):
                            md_text += line[2:]
                        elif line.startswith("> >"):
                            # Making multiple levels of BlockQuotes as >>>> instead of > > > >:
                            line = line.replace("> ", ">")
                            # Adding one space after sequence of >>>>:
                            line = re.sub(r"(^>+)", r"\1 ", line)
                            md_text += line
                        else:
                            md_text += line

                    # Add line feed, also for empty lines:
                    md_text += "\n"
                #endif child.tagName == 'p'
            #endif child.nodeType == child.ELEMENT_NODE:
        #endfor child in document.childNodes
        md_text = md_text[:-1]  # Strip last "\n"

        attachments = self.get_attacments_as_md(xml_data)
        tail = attachments + self.footnotes + self.links + self.img_links
        if tail != "":
            return md_text + "\n\n" + tail
        else:
            return md_text
    #end_def xml2markdown(self, ulysses_path)

#end_class UlyssesToMarkdown


class UlFileList:
    # preprocessing all UL files for dictionary lookup, to match files on sync import:
    # Also making plaintext filelist with filenames for export
    def __init__(self):
        self.__ul_files = {}
        self.__export_paths = {}
        self.file_list = ""

    def get_ul_files(self):
        return self.__ul_files

    def get_ul_path(self, ul_uuid):
        try:
            path = self.__ul_files[ul_uuid]
            return path
        except Exception:
            return ""

    def get_export_paths(self):
        return self.__export_paths

    def make_file_list(self, path, out_path, path_count):
        file_list = ""
        file_count = 1
        sub_path_count = 1

        info_ulgroup = path + "Info.ulgroup"

        xml_plist = ET.parse(info_ulgroup)

        group_title = xml_plist.findall(".//dict/string")
        if group_title:
            # print("---", group_title[0].text)
            sub_out_path = group_title[0].text
            out_path += str(path_count).zfill(2) + " "\
                + clean_file_title(sub_out_path, "", False) + "/"
            path_count += 1

        nodelist = xml_plist.findall(".//dict/array//string")
        for item in nodelist:
            # Do all sheets first:
            sub_path = item.text
            if sub_path.endswith(".ulysses"):
                file_name = path + sub_path + "/" + "Content.xml"
                modified = get_file_date(file_name)

                try:
                    xml_doc = ET.parse(file_name)
                except:
                    print("*** File Missing or Corrupt XML", file_name)
                    continue

                p = xml_doc.find(".//p")
                if p is not None:
                    title = ET.tostring(p, "unicode", "text")
                    # debug(554, title, "Test title" in title)
                else:
                    title = "Untitled"

                title = str(file_count).zfill(2) + " " + clean_file_title(title, "", False)

                file_count += 1
                ul_uuid = sub_path[:-8]
                self.__ul_files[ul_uuid] = path

                self.file_list += path + sub_path + "\t" + str(modified) + "\t"\
                    + out_path + "\t" + title + "\n"

        self.__export_paths[out_path] = path

        for item in nodelist:
            # Do all groups second:
            sub_path = item.text
            if sub_path.endswith("-ulgroup"):
                (fl, pc) = self.make_file_list(path + sub_path + "/", out_path, sub_path_count)
                sub_path_count += pc
                path_count += 1

        path_count = 1
        return file_list, path_count
    #end_def make_file_list(self, path, out_path, path_count)

#end_class UlFileList


class MmdRefClass:
    # Class making dictionary lookup for all MD links, footnotes, and images.
    def __init__(self):
        self.__ref = {}
        self.md_attachments = ""

    def make_ref(self, md_text):
        # Loads all footnotes into dictionary and strips those lines
        new_md_text = ""
        key = ""
        value = ""
        entry_found = False
        in_attachments = False
        skip_blank_lines = False

        for line in md_text.split("\n"):  # [:-1]:
        # Skip all lines in exported attachments:
            if in_attachments:
                self.md_attachments += "\n" + line
                if line.strip().startswith("-->"):
                    in_attachments = False
                    skip_blank_lines = True
                continue
            if line.strip().startswith("&lt;!--ul_attachments:"):
                in_attachments = True
                # Strip last char: "\n" (extra blank line inserted by export):
                self.md_attachments = line
                continue

            match = re.match("\[(\^?.+)\]:[\t ]*(.*)", line)
            if match:
                skip_blank_lines = True
                if entry_found:
                    self.__ref[key] = value
                key = match.group(1)
                value = match.group(2)
                entry_found = True
                #self.__ref[key] = value
            elif entry_found and line.startswith("\t"):
                value += "\n" + line.strip()
            elif entry_found and "&lt;!--Media:" in line:
                media = re.sub(r"&lt;!--Media:(.+?)-->", r"\1", line)
                value += "\t" + media.strip()
            else:
                if entry_found:
                    self.__ref[key] = value
                    entry_found = False
                elif skip_blank_lines and line.strip() == "":
                    pass
                else:
                    new_md_text += line + "\n"

        if entry_found:
            self.__ref[key] = value

        if skip_blank_lines:
            return new_md_text[:-2]
        else:
            return new_md_text[:-1]
    #end_def make_ref(self, md_text)

    def get_value(self, key):
        return self.__ref[key]

    def get_attachments(self):
        return self.md_attachments

    def get_footnotes(self, line):
        match = re.findall("(\[\^\d+?\])", line)
        if match:
            for item in match:
                key = item[1:-1]
                value = self.__ref[key]
                value = value.replace("\n", "</p>\n<p>")
                footnote = '<element kind="footnote"><attribute identifier="text">'\
                    '<string xml:space="preserve">\n<p>' + value + '</p>\n'\
                    '</string></attribute></element>'
                line = line.replace(item, footnote)
        return line

    def get_links(self, line):
        #URL Links:
        match = re.findall("(\[.+?\])(\[\d+?\])", line)
        if match:
            for item in match:
                (text, key) = item
                key2 = key[1:-1]
                text2 = text[1:-1]
                value = self.__ref[key2]
                pos = value.find(" ")
                title = ""
                if pos == -1:
                    URL = value
                else:
                    URL = value[:pos]
                    title = value.rstrip()[pos+2:-1]

                link = '<element kind="link">'\
                       + '<attribute identifier="URL">' + URL + '</attribute>'\
                       + '<attribute identifier="title">' + title + '</attribute>'\
                       + text2 + '</element>'

                line = line.replace(text + key, link)

        #Photo links:
        match = re.findall("!\[(.*?)\]\[(.+?)\]", line)
        if match:
            for item in match:
                image = ""
                (text, key) = item
                value = self.get_value(key)
                if "\t" in value:
                    parts = value.split("\t")
                    value = parts[0]
                    image = parts[1]

                title = ""
                url = ""
                link = ""
                pos = value.find(" ")
                if pos == -1:
                    link = value
                else:
                    link = value[:pos]
                    title = value[pos+2:-1]

                if link.startswith("Media/"):
                    image = re.sub(r"^Media/.+?\.([0-9a-f]{32})\..+$", r"\1", link)
                else:
                    url = link

                link = '<element kind="image">'\
                       + '<attribute identifier="URL">' + url + '</attribute>'\
                       + '<attribute identifier="image">' + image + '</attribute>'\
                       + '<attribute identifier="title">' + title + '</attribute>'\
                       + '<attribute identifier="description">' + text + '</attribute>'\
                       + '</element>'
                text_key = "![" + text + "][" + key + "]"
                line = line.replace(text_key, link)

        return line
    #end_def get_links(self, line)
#end_class MmdRefClass


def get_ul_xml_attachments(xml_file):
    xml_doc = ET.parse(xml_file)

    try:
        sheet_version = xml_doc.find(".").attrib["version"]
    except:
        sheet_version = "2"

    attach_nodes = xml_doc.findall("attachment")
    xml_text = ""
    for node in attach_nodes:
        xml_text += ET.tostring(node, "unicode", method='xml')
        #print(ET.tostring(node, "unicode", method='xml'))

    return (xml_text, sheet_version)


def make_xml_comment(comment_txt):
    comment_xml = ""
    lines = comment_txt.split("\n")
    for line in lines:
        comment_xml += '<p><tags><tag kind="comment">%% </tag></tags>'\
                       + line + "</p>\n"
    return comment_xml


def markdown_to_ulysses_xml(md_text, ul_path, comment_txt, keep_attachments):
    # Main function for converting MultiMarkdown exported from Ulysses,
    # back to Ulysses XML format, on sync/import.
    xml_body = ""
    line_num = 1
    xml_head = """
<markup version="1" identifier="markdownxl" displayName="Markdown XL">
\t<tag definition="heading1" pattern="#"/>
\t<tag definition="heading2" pattern="##"/>
\t<tag definition="heading3" pattern="###"/>
\t<tag definition="heading4" pattern="####"/>
\t<tag definition="heading5" pattern="#####"/>
\t<tag definition="heading6" pattern="######"/>
\t<tag definition="codeblock" pattern="''"/>
\t<tag definition="comment" pattern="%%"/>
\t<tag definition="divider" pattern="----"/>
\t<tag definition="nativeblock" pattern="~~"/>
\t<tag definition="blockquote" pattern=">"/>
\t<tag definition="orderedList" pattern="\d."/>
\t<tag definition="unorderedList" pattern="*"/>
\t<tag definition="unorderedList" pattern="+"/>
\t<tag definition="unorderedList" pattern="-"/>
\t<tag definition="code" startPattern="`" endPattern="`"/>
\t<tag definition="delete" startPattern="||" endPattern="||"/>
\t<tag definition="emph" startPattern="*" endPattern="*"/>
\t<tag definition="emph" startPattern="_" endPattern="_"/>
\t<tag definition="inlineComment" startPattern="++" endPattern="++"/>
\t<tag definition="inlineNative" startPattern="~" endPattern="~"/>
\t<tag definition="mark" startPattern="::" endPattern="::"/>
\t<tag definition="strong" startPattern="__" endPattern="__"/>
\t<tag definition="strong" startPattern="**" endPattern="**"/>
\t<tag definition="annotation" startPattern="{" endPattern="}"/>
\t<tag definition="link" startPattern="[" endPattern="]"/>
\t<tag definition="footnote" pattern="(fn)"/>
\t<tag definition="image" pattern="(img)"/>
\t<tag definition="video" pattern="(vid)"/>
</markup>
<string xml:space="preserve">"""

    md_text = md_text.replace("&", "&amp;")
    md_text = md_text.replace("<", "&lt;")

    ref = MmdRefClass()
    md_text = ref.make_ref(md_text)

    # Done after ref.make_ref since multiline footnotes uses "  \n" for paragraph break
    md_text = md_text.replace("  \n", LINE_BREAK)

    if keep_attachments:
        (xml_attachments, sheet_version) = get_ul_xml_attachments(ul_path + "Content.xml")
        xml_sheet = '<sheet version="'+sheet_version+'">'
    else:
        xml_attachments = ""
        xml_sheet = '<sheet version="2">'
        md_text += "\n" + ref.get_attachments()

        # debug(839, md_text)

    md_lines = md_text.split("\n")  # [:-1]
    for line in md_lines:

        tag_done = False

        # StartOfLine tags:
        # All Headings:
        if line.startswith("#"):
            match = re.search(r"(#+) *(.*)", line)
            if match:
                tag = match.group(1)
                level = len(tag)
                text = match.group(2)
                if level > 6:
                    level = 6
                    tag = "######"
                line = '<tags><tag kind="heading' + str(level) + '">'\
                    + tag + ' </tag></tags>' + text
                tag_done = True

        # Codeblock, Should be first, to avoid further processing:
        # if re.match(r"^\t(?![\t ]*(\* |\d+\. ))", line):  # Neg. lookahed assertion not working??
        # So workaround here:
        if re.match(r"(^\t|^    )", line) and not re.match(r"(^[\t ]+(\* |\d+\. ))", line):
            line = re.sub(r"(^\t|^    )(.*)",
                          r'<tags><tag kind="codeblock">\'\' </tag></tags>\2', line)
            # Continnue to next line, no inline processing of codeblocks:
            xml_body += "<p>" + line + "</p>\n"
            # Skip to next line, no further processing of code blocks:
            continue

        if not tag_done:
            line = re.sub(r"^ *- ?- ?(- ?)+[ \t]*|^ *_ ?_ ?(_ ?)+[ \t]*|^ *\* ?\* ?(\* ?)+[ \t]*",
                          r'<tags><tag kind="divider">---- </tag></tags>', line)

        # Footnotes:
        line = ref.get_footnotes(line)

        # Strong and emph:
        line = re.sub(r"\*\*(.+?)\*\*", r'<element kind="strong" startTag="2ast">\1</element>',
                      line)
        line = re.sub(r"__(.+?)__", r'<element kind="strong" startTag="2und">\1</element>', line)
        line = re.sub(r"\*(.+?)\*", r'<element kind="emph" startTag="ast">\1</element>', line)
        line = re.sub(r"_(.+?)_", r'<element kind="emph" startTag="und">\1</element>', line)

        # Unordered List:
        if not tag_done:
            # tabs, spaces, mix or none for indented sublevels.
            match = re.search(r"^([ \t]*)([\*-+])[ \t]+(.*)", line)
            if match:
                indent = match.group(1).replace("\t", " " * 4)
                tabs = "<tag>\t</tag>" * int(len(indent) / 4)  # 4 space = 1 tab
                line = re.sub(r"^[ \t]*([\*-+])[ \t]+(.*)",
                              r'<tags>' + tabs +
                              r'<tag kind="unorderedList">\1 </tag></tags>\2', line)
                tag_done = True

        # Ordered List:
        if not tag_done:
            # tabs, spaces, mix or none for indented sublevels.
            match = re.search(r"^([ \t]*)(\d+\.)[ \t]+(.*)", line)
            if match:
                indent = match.group(1).replace("\t", " " * 4)
                tabs = "<tag>\t</tag>" * int(len(indent) / 4)  # 4 space = 1 tab
                line = re.sub(r"^[ \t]*(\d+\.)[ \t]+(.*)", r'<tags>' + tabs +
                              r'<tag kind="orderedList">\1 </tag></tags>\2', line)
                tag_done = True

        # BlockQuote:
        if not tag_done:
            match = re.search(r"^(>+) ?(.*)", line)
            if match:
                line = line.replace("> ", ">")
                match = re.search(r"^(>+) ?(.*)", line)
                tags = '<tag kind="blockquote">&gt; </tag>' * len(match.group(1))
                line = re.sub(r"^(>)+ ?(.*)", r'<tags>' + tags + r'</tags>\2', line)
                tag_done = True

        # Html and CriticsMarkup comment "block", line by line only
        if not tag_done:
            line = re.sub(r"^&lt;!--(.+)-->$", r'<tags><tag kind="comment">%% </tag></tags>\1',
                          line)
            line = re.sub(r"^{>>(.*)&lt;&lt;}$", r'<tags><tag kind="comment">%% </tag></tags>\1',
                          line)

        # **Inline Elements:**
        # inline code:
        line = re.sub(r"`(.+?)`", r'<element kind="code" startTag="`">\1</element>', line)

        # Postprocessing strong and emph:
        line = line.replace('startTag="2ast">', 'startTag="**">')
        line = line.replace('startTag="2und">', 'startTag="__">')
        line = line.replace('startTag="ast">', 'startTag="*">')
        line = line.replace('startTag="und">', 'startTag="_">')

        # Inline html video:
        if "&lt;video src=" in line:
            if "&lt;!--Media:" in line:
                line = re.sub(r'&lt;figure>&lt;video src="(.+?)">&lt;!--Media:(.+?)-->&lt;/video>&lt;/figure>',
                              r'<element kind="video"><attribute identifier="URL">\1</attribute>'
                              + r'<attribute identifier="video">\2</attribute></element>',
                              line)
            elif "Media/" in line:
                line = re.sub(r'&lt;figure>&lt;video src="Media/.+?\.([0-9a-f]{32})\..+?">&lt;/video>&lt;/figure>',
                              r'<element kind="video"><attribute identifier="video">\1</attribute></element>',
                              line)
            else:
                line = re.sub(r'&lt;figure>&lt;video src="(.+?)">&lt;/video>&lt;/figure>',
                              r'<element kind="video"><attribute identifier="URL">\1</attribute></element>',
                              line)

        # inline delete:
        re_repl = r'<element kind="delete" startTag="||">\1</element>'
        line = re.sub(r"&lt;!--Delete:(.+?)-->", re_repl, line)
        line = re.sub(r"{--(.+?)--}", re_repl, line)

        # inline mark:
        re_repl = r'<element kind="mark" startTag="::">\1</element>'
        line = re.sub(r"&lt;span class='mark'>(.+?)&lt;/span>", re_repl, line)
        line = re.sub(r"{\+\+(.+?)\+\+}", re_repl, line)

        # Annotations:
        re_repl = r'<element kind="annotation"><attribute identifier="text">'\
                  + r'<string xml:space="preserve"><p>\2</p>'\
                  + r'</string></attribute>\1</element>'
        line = re.sub(r"&lt;span class='annotation'>(.*?)&lt;/span>&lt;!--(.*?)-->", re_repl, line)
        line = re.sub(r"{==(.*?)==}{>>(.*?)&lt;&lt;}", re_repl, line)
        if '<element kind="annotation">' in line:
            line = line.replace("&lt;br/>", "</p><p>")
            # Note "reverse order" of p-tags when replacing </br>!
            # This is also ok even if </br> should appear somewhere else in line,
            # since line is wrapped by p-tags in calling function: '<p>'+line+'</p>'

        # debug(935, line, 'kind="annotation"' in line)

        # Inline comments:
        re_repl = r'<element kind="inlineComment" startTag="++">\1</element>'
        line = re.sub(r"&lt;!--(.*?)-->", re_repl, line)
        line = re.sub(r"{>>(.*?)&lt;&lt;}", re_repl, line)

        # Inline Native:
        re_repl = r'<element kind="inlineNative" startTag="~">\1</element>'

        # HTML paired outer tags, or single tags, make sequence inlineNative:
        line = re.sub(r"(&lt;(?P<tag>(.+?))[> ].*?&lt;/(?P=tag)>|&lt;.+?>)", re_repl, line)
        # debug(968, line, "&lt;!--" in line, False)

        # Unpaired HTML- or Critic Markup- comment tags,
        # and make them inlineNative Roundtrip safe:
        line = re.sub(r"(&lt;!--|-->|{>>|&lt;&lt;})", re_repl, line)
        # debug(972, line, "&lt;!--" in line)

        #Get any fn, img, or links:
        line = ref.get_links(line)

        #Escaping remaining start tags:
        line = line.replace("\\", "<escape>\\\\</escape>")
        line = line.replace("{", "<escape>\{</escape>")
        line = line.replace("[", "<escape>\[</escape>")

        #Just in case someone have entered these in markdown file :)
        line = line.replace("(fn)", "<escape>\(</escape>fn)")
        line = line.replace("(img)", "<escape>\(</escape>img)")
        line = line.replace("(vid)", "<escape>\(</escape>vid)")

        xml_body += "<p>" + line + "</p>\n"
        if line_num == 1 and comment_txt != "":
            #  Add comment below title/ first line:
            xml_body += make_xml_comment(comment_txt)
        line_num += 1

    #endfor line in md_text.split("\n")
    xml_body += "</string>\n"
    ul_xml_text = xml_sheet + xml_head + xml_body + xml_attachments + "</sheet>"
    #*** Maybe move file handling from "sync_files" and "LogFileSheet.write_log_sheet" to here
    return ul_xml_text
#end_def markdown_to_ulysses_xml(md_text, ul_path, comment_txt, keep_attachments)


def check_files(sync_file, from_file, to_file):
    synced_ts = get_file_date(sync_file)
    #from_ts = get_file_date(from_file)
    to_ts = 0
    if os.path.exists(to_file):
        to_ts = get_file_date(to_file)
    else:
        #print("Target file don't exists: ")
        return False

    if to_ts > synced_ts:
        print("Target file changed:", datetime.datetime.fromtimestamp(to_ts), to_file)
        return False
    else:
        return True


def update_info_plist(ul_path, append_sheet=True):
    pos = ul_path.rfind("/", 0, -2)
    path = ul_path[:pos+1]
    new_ul_filename = ul_path[pos+1: -1]
    info_file = path + "Info.ulgroup"

    pl = plistlib.readPlist(info_file)

    try:
        if append_sheet:
            pl["sheetClusters"].append([new_ul_filename])
        else:
            pl["sheetClusters"].insert(0, [new_ul_filename])
    except:
        pl["sheetClusters"] = []
        pl["sheetClusters"].append([new_ul_filename])

    plistlib.writePlist(pl, info_file)


def add_group_plist(ul_path):
    pos = ul_path.rfind("/", 0, -2)
    path = ul_path[:pos+1]
    new_ul_filename = ul_path[pos+1: -1]
    info_file = path + "Info.ulgroup"
    # debug(1024, info_file, new_ul_filename)
    pl = plistlib.readPlist(info_file)

    try:
        # pl["sheetClusters"].insert(0, [new_ul_filename])
        pl["childOrder"].append(new_ul_filename)
    except:
        pl["childOrder"] = []
        pl["childOrder"].append(new_ul_filename)

    plistlib.writePlist(pl, info_file)


class LogFileSheet:
    def __init__(self, ulgroup_path, synced_date):
        self.log_sheet_md = "# Log - " + synced_date + "\n"
        self.synclog_path = self.check_group_plist(ulgroup_path)
        self.line_count = 0
        self.synced_date = synced_date
        self.log_sheet_updates = ""
        self.is_dirty = False

    def check_group_plist(self, ulgroup_path):
        self.empty_group_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>displayName</key>
    <string>Sync Logs</string>
    <key>sheetClusters</key>
    <array/>
    <key>userIconName</key>
    <string>Gear</string>
</dict>
</plist>
"""
        group_id = str(len(ulgroup_path)).zfill(4)
        ul_uuid = "670f113670f113670f113670f113" + group_id + "-ulgroup/"
        synclog_path = ulgroup_path + ul_uuid
        if not os.path.exists(synclog_path):
            os.makedirs(synclog_path)
            info_file = synclog_path + "Info.ulgroup"
            write_file(info_file, self.empty_group_plist)
            # debug(1069, synclog_path)
            add_group_plist(synclog_path)
        return synclog_path

    def add_entry(self, text):
        self.log_sheet_md += text + "\n"
        # self.is_dirty = True

    def add_line(self, msg, date_time, file_title, msg2=""):
        self.line_count += 1
        self.log_sheet_md += str(self.line_count) + ". " + msg + date_time + msg2 \
            + LINE_BREAK + file_title + "\n"
        self.is_dirty = True

    def get_md_log(self):
        pos = self.log_sheet_md.find("\n")
        if pos > -1:
            return str(self.log_sheet_md[pos:])
        else:
            return str(self.log_sheet_md)

    def write_log_sheet(self, fixed_sheet=True):
        # #ul_path = self.inbox_path + uuid.uuid4().hex + ".ulysses/"
        # Fixed UUID-name for log sheet:

        if fixed_sheet:
            group_id = str(len(self.synclog_path)).zfill(4)
            ul_uuid = "106f113106f113106f113106f113" + group_id + ".ulysses"
            # Fixed sheets can be written even if no fileupdates
            # Just to show header with last sync run date
        elif self.is_dirty:
            ul_uuid = uuid.uuid4().hex + ".ulysses"
        else:
            # Don't write logsheets when no file updates
            return

        ul_path = self.synclog_path + ul_uuid + "/"
        # log_sheet_xml = self.log_sheet_md
        log_sheet_xml = markdown_to_ulysses_xml(self.log_sheet_md, ul_path, "", False)

        xml_file = ul_path + "Content.xml"
        txt_file = ul_path + "Text.txt"

        # Make a new sheet if not exists:
        if not os.path.exists(ul_path):
            update_info_plist(ul_path, False)
            os.makedirs(ul_path)

        write_file(xml_file, log_sheet_xml)
        write_file(txt_file, self.log_sheet_md)
        ts = get_file_date(xml_file)
        set_file_date(ul_path, ts)
        #set_file_date(self.inbox_path + "Info.ulgroup", ts)

#end_class LogFileSheet


def sync_files(sync_path, ulysses_path, log):
    # if not os.path.exists(changed_files_path):
    #     os.makedirs(changed_files_path)
    sync_file = sync_path + ".ulysses_sync.log"
    inbox_path = ulysses_path + "Unfiled-ulgroup/"

    synced_date = ""

    if os.path.exists(sync_file):
        last_synced = get_file_date(sync_file)
        synced_date = str(datetime.datetime.fromtimestamp(last_synced))
        print("Last synced:", synced_date)
    else:
        notify("* SYNC FILE MISSING: " + sync_file)
        return

    ul_list = UlFileList()
    ul_list.make_file_list(ulysses_path, sync_path, 1)

    for (dirpath, dirnames, filenames) in walk(sync_path):
        if filenames:
            for fname in filenames:
                if fname.endswith(".md"):
                    full_name = dirpath + "/" + fname

                    # Check if exported file has changed since last export/sync
                    ts = get_file_date(full_name)
                    if ts > last_synced:
                        # print("Sync import: " + str(full_name.encode("utf-8")))
                        md_text = read_file(full_name)
                        modified = get_file_date(full_name)
                        path = os.path.dirname(full_name)
                        keep_attachments = False

                        file_date_time_0 = str(datetime.datetime.fromtimestamp(modified))
                        file_date_time = file_date_time_0
                        file_date_time = file_date_time.replace(":", "-")
                        file_date_time = file_date_time.replace(" ", "<escape>\_</escape>")

                        source_group = path.replace(sync_path, "") + "/"
                        # source_group = re.sub(r"/\d+ - ", r"/", source_group)

                        # file_title = re.sub(r"^(\d+ - )?(.+) - [0-9a-f]{32}\.md$", r"\2", fname)
                        file_title = re.sub(r" - [0-9a-f]{32}\.md$", r"", fname)
                        file_title = source_group + file_title

                        msg = ""
                        comment = ""

                        match = re.search(r"^(.+? - )?([0-9a-f]{32})\.md$", fname)
                        if match:
                            ul_uuid = match.group(2)
                            ul_match = ul_list.get_ul_path(ul_uuid)
                            #print(ul_match)
                            if ul_match == "":
                            # Sheet deleted in Ulysses, make new sheet in inbox
                                msg = "Sheet deleted in Ulysses? In group: " + source_group

                                comment = msg + "\nExternal edit at: " + file_date_time
                                ul_path = inbox_path + uuid.uuid4().hex + ".ulysses/"
                                notify("New sheet in inbox, " + msg + " " + file_title)
                                log.add_line("New sheet from: ", file_date_time_0, file_title)

                            else:
                                ul_path = ul_match + ul_uuid + ".ulysses/"

                                if check_files(sync_file, full_name, ul_path + "Content.xml"):
                                # Updating existing sheet:
                                    msg = "External edit: "
                                    keep_attachments = True
                                    # comment = msg + file_date_time
                                    log.add_line("Sheet updated from: ", file_date_time_0, file_title)

                                else:
                                # Sync conflict!
                                    # Both Sheet and exported file updated since last sync,
                                    # make new sheet in inbox:
                                    msg = "Sync conflict with sheet in group: " + source_group
                                    comment = msg + "\nExternal edit at: " + file_date_time\
                                        + "\nNOTE! Attachments only as plaintext, at end of sheet"
                                    ul_path = inbox_path + uuid.uuid4().hex + ".ulysses/"
                                    notify("SYNC CONFLICT! See Inbox: " + file_title)
                                    log.add_line("SYNC CONFLICT! with: ", file_date_time_0,
                                                 file_title)

                        else:
                            # New files without Ulysses uuid, make new sheet in inbox:
                            msg = 'New sheet from export folder: ' + source_group
                            comment = msg + "\nExternal edit at: " + file_date_time

                            ul_path = inbox_path + uuid.uuid4().hex + ".ulysses/"
                            notify("New sheet in inbox: " + file_title)
                            log.add_line("New sheet from: ", file_date_time_0, file_title)

                        # Markdown to Ulysses Xml converions is done here:
                        xml_text = markdown_to_ulysses_xml(md_text, ul_path, comment,
                                                           keep_attachments)

                        # Test XML, and write Ulysses package with XML + text files
                        try:
                            validate = ET.fromstring(xml_text)
                        except Exception as inst:
                            print(inst.args)
                            debug(1199, xml_text, True, False)
                            debug(1200, ul_path, full_name)
                            # print("*** Line 1206: File did not vaidate as XML, ", full_name)
                            # *** Add some error handling and messaging here!
                            pass

                        xml_file = ul_path + "Content.xml"
                        txt_file = ul_path + "Text.txt"

                        if not os.path.exists(ul_path):
                            update_info_plist(ul_path)
                            os.makedirs(ul_path)
                        else:
                            set_file_date(ul_path, modified)

                        # In UL v1.1.2, set_file_date trigered refresh editor and sheet-list panes
                        # Not working after UL 1.2 update, need to restart UL to see changes :(
                            # # Touch UlGroup
                            # pos = ul_path.rfind("/", 0, -2)
                            # ul_group = ul_path[:pos]
                            # set_file_date(ul_group, time.time())
                            # # print(pos, ul_group)
                            # # quit()

                        # Testing for UL v1.2 to refresh "hot-swap", but not working after update:
                            #ul_info = ul_match + "Info.ulgroup"
                            #set_file_date(ul_info, modified)

                        write_file_modified(xml_file, xml_text, modified)
                        write_file_modified(txt_file, md_text, modified)

                    #endif ts > last_synced
                #endif fname.endswith(".md")
            #endfor fname in filenames
        #endif filenames
    return
#enddef sync_files(sync_path, ulysses_path, log)
