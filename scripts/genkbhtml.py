# Author: Krzysztof Kowalczyk
# Dates: 2005-12-28 started
# This script reads the file given as first argument (knowledge-base.txt if
# not given) and generates a set of static html pages.

import sys, string, os, os.path, urllib, re, time, md5
import markdown2

HEADER_HTML = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
 <meta http-equiv="Content-Language" content="en-us">
 <meta name="description" content="{{title}}">
 <link rel="stylesheet" href="../css/wp-style.css" type="text/css">
 <link rel="stylesheet" href="../css/article.css" type="text/css">
 {{prettify-links}}
 <title>{{title}}</title>
</head>

<body{{prettify-onload}}>
<div id="container">

<p><a href="../index.html">home</a> &raquo; <a href="index.html">knowledge base</a> &raquo; <strong>{{title}}</strong> <font color="#aaaaaa" size="-1">({{creation-date}})</font></p>
"""

PRETTIFY_LINKS_VAR = "{{prettify-links}}"
PRETTIFY_ONLOAD_VAR = "{{prettify-onload}}"

PRETTIFY_LINKS="""<link href="../js/prettify.css" type="text/css" rel="stylesheet" />
<script type="text/javascript" src="../js/prettify.js"></script>
"""

PRETTIFY_ONLOAD=' onload="prettyPrint()"'

FOOTER_HTML = """<hr>
<center><a href=../../index.html>Krzysztof Kowalczyk</a></center>
</div>

<script type="text/javascript">
var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
</script>
<script type="text/javascript">
var pageTracker = _gat._getTracker("UA-194516-1");
pageTracker._initData();
pageTracker._trackPageview();
</script>

  </body>
</html>
"""

# directory where we'll generate the files
OUTDIR = "."

KNOWN_LANGUAGES = ["c", "c++", "cpp", "c#", "python", "java", "diff", "diffu", "html", "javascript", "makefile", "perl", "lisp", "elisp", "scheme", "sh", "sql", "tcl", "php", "batch", "xml", "lua"]

def known_lang(lang):
    return lang in KNOWN_LANGUAGES

def lang_to_prettify_lang(lang):
    #from http://google-code-prettify.googlecode.com/svn/trunk/README.html
    #"bsh", "c", "cc", "cpp", "cs", "csh", "cyc", "cv", "htm", "html",
    #"java", "js", "m", "mxml", "perl", "pl", "pm", "py", "rb", "sh",
    #"xhtml", "xml", "xsl".
    LANG_TO_PRETTIFY_LANG_MAP = { 
        "c" : "c", 
        "c++" : "cc", 
        "cpp" : "cpp", 
        "python" : "py",
        "html" : "html",
        "xml" : "xml",
        "perl" : "pl",
        "c#" : "cs",
        "javascript" : "js",
        "java" : "java"
    }
    if lang in LANG_TO_PRETTIFY_LANG_MAP:
        return "lang-%s" % LANG_TO_PRETTIFY_LANG_MAP[lang]
    return None

# convert 'content' text to html using enscript
def code_to_html(code, lang):
    lang = lang_to_prettify_lang(lang)
    if lang is not None:
        odata = '<pre class="prettyprint %s">\n%s</pre>' % (lang, encode_code(code))
    else:
        odata = '<pre class="prettyprint">\n%s</pre>' % encode_code(code)

    # Strip header and footer
#    beg = odata.find('<PRE>')
#    if beg < 0: beg = 0
#    end = odata.rfind('</PRE>')
#    if end < 0:
#        end = len(odata)
#    else:
#        end = end + 6
#    odata = odata[beg:end]
    return odata

TAGS_TXT = "Tags".lower()
TITLE_TXT = "Title".lower()
DATE_TXT = "Date".lower()

# valid attributes of a post, normalized to lower case
valid_attrs = [TITLE_TXT, DATE_TXT, TAGS_TXT]

# if article has a "hidden" tag, then we shouldn't show it. Those are like drafts
HIDDEN_TXT = "hidden".lower()

def empty_str(txt): return not len(txt.strip())

# create a sane file name out of arbitray text
def sanitize_for_filename(txt):
     # characters invalid in a filename are replaced with "-"
    to_replace = [" ", "/", "\\", "\"", "'", "(", ")"]
    for c in to_replace:
        txt = txt.replace(c, "-")
    return txt.lower()

# covert arbitrary string to a valid, sanitized url
def txt_to_url(txt):
    return urllib.quote_plus(sanitize_for_filename(txt))

def valid_attr(attr):
    return attr.lower() in valid_attrs

# article 'Date' tag must be in YYYY-MM-DD format so that they can be sorted as strings
_valid_article_date_rx = re.compile("^\d\d\d\d-\d\d-\d\d$")

def valid_article_dates(article_dates):
    if 0 == len(article_dates):
        return False
    for article_date in article_dates:
        re_match = _valid_article_date_rx.search(article_date)
        if None == re_match:
            return False
    return True

# given a string in the format of "@[\*]+$attr:[\w]*$value", return (attr, value)
def get_attr_value(str):
    assert str.startswith("@")
    (attr, value) = str.split(":", 1)
    return (attr[1:].strip(), value.strip())

def is_attr_tags(str): return str == TAGS_TXT

def txt_cookie(txt):
    txt_md5 = md5.new(txt)
    return txt_md5.hexdigest()

def markdown(txt):
    #txt = txt.decode('ascii').encode('utf-8')
    try:
        res = markdown2.markdown(txt)
    except:
        print(txt)
        raise
    #res = res.decode('utf-8').encode('iso-8859-1')
    return res

def markdown_with_code_to_html(txt):
    code_parts = {}
    while True:
        code_start = txt.find("<code", 0)
        if -1 == code_start: break
        lang_start = code_start + len("<code")
        lang_end = txt.find(">", lang_start)
        if -1 == lang_end: break
        code_end_start = txt.find("</code>", lang_end)
        if -1 == code_end_start: break
        code_end_end = code_end_start + len("</code>")
        lang = txt[lang_start:lang_end].strip()
        code = txt[lang_end+1:code_end_start].strip()
        #print("-------------\n'%s'\n--------------" % code)
        prettify_lang = None
        if lang:
            #print("lang=%s" % lang)
            prettify_lang = lang_to_prettify_lang(lang)
        if prettify_lang:
            new_code = '<pre class="prettyprint %s">\n%s</pre>' % (prettify_lang, encode_code(code))
        else:
            new_code = '<pre class="prettyprint">\n%s</pre>' % encode_code(code)
        new_code_cookie = txt_cookie(new_code)
        assert(new_code_cookie not in code_parts)
        code_parts[new_code_cookie] = new_code
        to_replace = txt[code_start:code_end_end]
        txt = txt.replace(to_replace, new_code_cookie)

    html = markdown(txt)
    has_code = False
    for (code_replacement_cookie, code_html) in code_parts.items():
        html = html.replace(code_replacement_cookie, code_html)
        has_code = True
    return (html, has_code)

class Article(object):
    def __init__(self):
        self.attrs = {}
        # we need to keep temporary date during parsing, _body_lines is a list of
        # lines of text for a currently parsed body
        self._body_lines = []
        self._body = None
        self._html = None

        # those are build during parsing from attributes of an article
        self.dates = None # list of dates, calculated for 'Date' attribute
        self.tags = [] # list of tags, calculated from 'Tags' attribute
        self.title = None # calculated from 'Title' attribute
        self.url = None # calculated from 'Title' attribute
        self.html_file_name = None # calculated from 'Title' attribute
        self.has_code = False

    def get_body(self):
        assert(self._body)
        return self._body

    def add_attr(self, attr, val):
        attr = attr.lower()
        assert(valid_attr(attr))
        assert not attr in self.attrs
        val = val.strip()
        if TAGS_TXT == attr:
            val = val.strip()
            self.tags = [t.lower().strip() for t in val.split(",")]
        elif DATE_TXT == attr:
            self.dates = val.split()
        elif TITLE_TXT == attr:
            self.title = val
            self.url = txt_to_url(self.title) + ".html"
            self.html_file_name = sanitize_for_filename(self.title) + ".html"            
        self.attrs[attr] = val
    
    def start_body(self):
        assert(not self._body_lines)
        pass

    def finish_body(self):
        assert(self._body_lines)
        self._body = "".join(self._body_lines).strip()
        (html, has_code) = markdown_with_code_to_html(self._body)
        self._html = html
        self.has_code = has_code

    def get_html(self):
        assert(self._html)
        return self._html

    def add_to_body(self,l): self._body_lines.append(l)

    def is_hidden(self): return HIDDEN_TXT in self.tags

    # for debugging, dump your state
    def dump(self):
        for (attr, val) in self.attrs.items():
            print "'%s': %s" % (attr, val)
        print "'Body': %s" % self.get_body()
        print "is_hidden: %s" % str(self.is_hidden())

    def assert_if_invalid(self):
        if None == self.dates:
            self.dump()
            assert None != self.dates

        if not valid_article_dates(self.dates):
            self.dump()
            assert valid_article_dates(self.dates)

        if not self.tags:
            self.dump()
            assert self.tags
            
        if None == self.title:
            self.dump()
            assert self.title

        if None == self.url:
            self.dump()
            assert self.url


# states for parsing state machine
ST_START, ST_PARSING_ATTRS, ST_IN_TEXT = range(3)

def process_file(file_name):
    articles = []
    state = ST_START
    cur_article = None
    was_prev_empty = True
    fo = open(file_name, "rb")

    def do_first_attribute(l, articles):
        if cur_article:
            cur_article.finish_body()
            articles.append(cur_article)
        new_cur_article = Article()
        (attr, value) = get_attr_value(l)
        new_cur_article.add_attr(attr, value);
        return new_cur_article

    for l in fo.readlines():
        #print("'%s'" % l.strip())
        is_empty = empty_str(l)
        if ST_START == state:
            # this is the initial state and lasts until finding beggining of
            # a first article (first attribute). It skips comments and empty lines
            #print " state: ST_START"
            if l.startswith("#"):
                # skip comments
                pass
            elif l.startswith("@"):
                assert None == cur_article
                cur_article = do_first_attribute(l, articles)
                state = ST_PARSING_ATTRS
            elif is_empty: # skip empty lines
                continue
            else:
                print("line: '%s'" % l.strip())
                assert False, "unexpected text"
        elif ST_PARSING_ATTRS == state:
            # parsing attributes of a given article
            #print " state: ST_PARSING_ATTRS"
            if l.startswith("@"):
                assert None != cur_article
                (attr, value) = get_attr_value(l)
                cur_article.add_attr(attr, value)
            else:
                state = ST_IN_TEXT
                cur_article.start_body()
                cur_article.add_to_body(l)
        elif ST_IN_TEXT == state:
            # parsing the text of the article in a markup language
            #print " state: ST_IN_TEXT"
            if l.startswith("@") and was_prev_empty:
                cur_article = do_first_attribute(l, articles)
                state = ST_PARSING_ATTRS
            else:
                cur_article.add_to_body(l)
        else:
            assert False
        was_prev_empty = is_empty
    fo.close()
    return articles

def write_to_file(file_name, txt):
    fo = open(file_name, "wb")
    fo.write(txt)
    fo.close()

def txt_replace_vars(txt, vars_values):
    for (var, value) in vars_values:
        txt = txt.replace(var, value)
    return txt

def today_as_yyyy_mm_dd(): return time.strftime("%Y-%m-%d", time.localtime())

def in_tag(tag, txt):return '<%s>%s</%s>' % (tag, txt, tag)

def in_link(url, title): return '<a href="%s">%s</a>' % (url, title)

def in_font_size(txt, size="-1"): 
    return '<font size="%s">%s</font>' % (size, txt)

def in_font_color(txt, color):
    return '<font color="%s">%s</font>' % (color, txt)

def in_gray(txt): return in_font_color(txt, "gray")

def encode_code(text):
    for (txt,replacement) in [("&","&amp;"), ("<","&lt;"), (">","&gt;")]:
        text = text.replace(txt, replacement)
    return text

def gen_html(articles):
    hidden_count = 0

    tag_article_map = {} # maps tags to a list of articles
    def build_tag_article_map(article):
        for tag in article.tags:
            if tag_article_map.has_key(tag):
                tag_article_map[tag].append(article)
            else:
                tag_article_map[tag] = [article]

    urls = {} # for finding titles that would end-up in duplicate urls
    all_articles_count = len(articles)
    all_articles = [article for article in articles if not article.is_hidden()]
    filtered_articles_count = len(articles)
    hidden_count = all_articles_count - filtered_articles_count
    for article in all_articles:
        article.assert_if_invalid()
        url = article.url
        # print "__%s__" % url
        if url in urls:
            assert not url in urls, "title '%s' creates a duplicate url" % article.title
        urls[url] = True

    for article in all_articles:
        build_tag_article_map(article)

    print "Finished processing"
    print "Number of articles: %d (hidden: %d)" % (len(articles), hidden_count)
    print "Number of tags: %d" % len(tag_article_map)

    links_per_page = 25

    all_articles.sort(lambda x,y: cmp(y.dates[0], x.dates[0]))
    all_articles_count = len(all_articles)
    pages_count = (all_articles_count +  links_per_page - 1) / links_per_page

    html_footer_txt = FOOTER_HTML

    def gen_tags(txt, tags, tag_to_unlink=None):
        txt = ['<div class="tags">', txt]
        for tag in tags:
            count_txt = in_gray(" (%s) " % len(tag_article_map[tag]))
            if tag == tag_to_unlink:
                txt.append(" " + tag + count_txt)
            else:
                url = txt_to_url("tag-%s" % sanitize_for_filename(tag)) + ".html"
                link_txt = in_link(url, tag) + count_txt
                txt.append(link_txt)
        txt.append("</div>")
        return string.join(txt, "\n")

    print "pages_count = %d" % pages_count
    # generate html index pages index.html for the first page and index-$n.html
    # for all subsequent pages. Those pages have all tags at the top followed
    # by a list of $linkes_per_page links to articles, sorted by date, with
    # the most recent at the top

    all_tags_sorted = tag_article_map.keys()
    all_tags_sorted.sort()

    for page_no in range(pages_count):
        title = "Index of all articles"
        creation_date = today_as_yyyy_mm_dd()
        html_header_txt = txt_replace_vars(HEADER_HTML, [["{{title}}", title], ["{{creation-date}}", creation_date], [PRETTIFY_LINKS_VAR, ""], [PRETTIFY_ONLOAD_VAR, ""]])
        html = [html_header_txt]

        tags_txt = gen_tags("Tags: ", all_tags_sorted)
        html.append(tags_txt)
    
        html.append('<div id="kb">')
        first_article_no = page_no * links_per_page + 1
        last_article_no = (page_no + 1) * links_per_page
        if last_article_no > all_articles_count:
            last_article_no = all_articles_count

        html.append("<p>Recent articles (%d - %d):</p>" % (first_article_no, last_article_no))

        html.append("<ul>")
        articles_on_page = all_articles[first_article_no-1 : last_article_no]
        for article in articles_on_page:
            date_txt = in_font_size(in_gray("(%s)" % article.dates[0]))
            link_txt = in_link(article.url, article.title)
            html.append("<li>%s %s</li>" % (link_txt, date_txt))
        html.append("</ul>")
        
        if pages_count > 1:
            html.append("<p/><center>")
            txt = "previous"
            if page_no > 0:
                page_name = "index.html"
                if page_no > 1:
                    page_name = "index-%d.html" % (page_no-1)
                txt = in_link(page_name, txt)
            html.append(txt)

            html.append(" &deg; ")

            txt = "next"
            if page_no != pages_count -1:
                txt = in_link("index-%d.html" % (page_no + 1), txt)
            html.append(txt)
            html.append("</center>")

        html.append('</div>')
        html.append(tags_txt)
        html.append("<p> </p>")
        html.append(html_footer_txt)

        html_txt = string.join(html, "\n")
        file_name = "index-%d.html" % page_no
        if 0 == page_no:
            file_name = "index.html"
        write_to_file(os.path.join(OUTDIR, file_name), html_txt)

    # for each article, generate "${url}.html" file
    for article in all_articles:
        title = article.title
        creation_date = article.dates[0]
        html_header_txt = txt_replace_vars(HEADER_HTML, [["{{title}}", title], ["{{creation-date}}", creation_date]])
        if article.has_code:
            html_header_txt = html_header_txt.replace(PRETTIFY_LINKS_VAR, PRETTIFY_LINKS)
            html_header_txt = html_header_txt.replace(PRETTIFY_ONLOAD_VAR, PRETTIFY_ONLOAD)
        else:
            html_header_txt = html_header_txt.replace(PRETTIFY_LINKS_VAR, "")
            html_header_txt = html_header_txt.replace(PRETTIFY_ONLOAD_VAR, "")
            
        html = [html_header_txt]

        tags = article.tags
        tags.sort()
        tags_txt = gen_tags("Tags: ", tags)
        html.append(tags_txt)
        html.append('<div id="kb">')

        html.append('<p><center><font size="+1"><b>%s</b></font></center></p>' % title)
        html.append(article.get_html())
        html.append('</div>')
        html.append(tags_txt)
        html.append("<p> </p>")
        html.append(html_footer_txt)
        html_txt = string.join(html, "\n")
        write_to_file(os.path.join(OUTDIR, article.html_file_name), html_txt)

    # for each tag, generate "tag-$tag.html" file
    for tag in tag_article_map.keys():
        title = "Articles tagged with <b>%s</b> tag:" % tag
        creation_date = today_as_yyyy_mm_dd()
        html_header_txt = txt_replace_vars(HEADER_HTML, [["{{title}}", title], ["{{creation-date}}", creation_date], [PRETTIFY_LINKS_VAR, ""], [PRETTIFY_ONLOAD_VAR, ""]])
        html = [html_header_txt]

        tags_txt = gen_tags("Tags: ", all_tags_sorted, tag)
        html.append(tags_txt)
        html.append('<div id="kb">')

        articles_with_tag = tag_article_map[tag]
        articles_with_tag.sort(lambda x,y: cmp(y.dates[0], x.dates[0]))

        # TODO: should probably break up into page is a number of articles is large
        # (same limit as for index page)
        html.append("<p>%s</p>" % title)
        html.append("<ul>")
        for article in articles_with_tag:
            date_txt = in_font_size(in_gray("(%s)" % article.dates[0]))
            link_txt = in_link(article.url, article.title)
            html.append("<li>%s %s</li>" % (link_txt, date_txt))
        html.append("</ul>")

        html.append('</div>')
        html.append(tags_txt)
        html.append("<p> </p>")
        html.append(html_footer_txt)
        html_txt = string.join(html, "\n")
        file_name = "tag-%s.html" % sanitize_for_filename(tag)
        write_to_file(os.path.join(OUTDIR, file_name), html_txt)

def usage_and_exit():
    print "Usage: genkbhtml.py [dir] [file-to-process]"
    sys.exit(0)

def main():
    global OUTDIR
    if len(sys.argv) != 3:
        usage_and_exit()
    OUTDIR = sys.argv[1]
    try:
        os.mkdir(OUTDIR)
    except OSError:
        # directory already exists
        pass

    file_to_process = sys.argv[2]
    articles = process_file(file_to_process)
    gen_html(articles)

if __name__ == "__main__":
    main()
