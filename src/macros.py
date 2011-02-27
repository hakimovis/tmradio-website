# vim: set tw=0 fileencoding=utf-8:

from xml.sax.saxutils import escape
import clevercss
import datetime
import email.utils
import glob
import json
import mimetypes
import os.path
import time
import urllib
import urlparse

BASE_URL = 'http://www.tmradio.net'
DISQUS_ID = 'tmradio'


def get_post_labels(post):
    if not post.has_key('labels'):
        labels = []
    else:
        labels = [l.strip() for l in post['labels'].split(',')]
    if post.has_key('file') and 'podcast' not in labels:
        labels.append('podcast')
    if post.url.startswith('blog.') and post.url != 'blog.html' and 'blog' not in labels:
        labels.append('blog')
    return sorted(labels)


def get_label_url(label):
    return '/' + label.strip().replace(' ', '_') + '.html'


def get_label_stats(posts):
    labels = {}
    for post in posts:
        for label in get_post_labels(post):
            if not labels.has_key(label):
                labels[label] = 1
            else:
                labels[label] += 1
    # Удаляем метки, для которых нет страниц.
    for label in labels.keys():
        fn = './input' + os.path.splitext(get_label_url(label))[0] + '.md'
        if not os.path.exists(fn):
            del labels[label]
    return labels


def init_comments(page):
    if DISQUS_ID is not None:
        return u'<script type="text/javascript">var disqus_url = "'+ BASE_URL + '/' + page.get('url') +'";</script>'

def parse_date_time(text):
    """Преобразует дату-время из текста в структуру.

    Поддерживаемый формат: ГГГГ-ММ-ДД ЧЧ:ММ:СС, недостающие сегменты с конца
    заполняюся нулями.
    """
    default = '0000-01-01 00:00:00'
    text = text + default[len(text):]
    return time.mktime(time.strptime(text, '%Y-%m-%d %H:%M:%S'))


def print_menu(pages, page):
    pages = [p for p in pages if p.get('mpos')]

    output = u'<ul id="nav">'
    for p in sorted(pages, key=lambda a: int(a.mpos)):
        cls = p.get('mclass', '')
        if p.url == page.url:
            cls += u' active'
        output += u'<li class="%(class)s"><a href="%(link)s">%(title)s</a></li>' % {
            'link': p.url,
            'title': p.get('mtitle', p.get('title', 'wtf :(')),
            'class': cls,
        }
    output += u'</ul>'
    return output


def pagelist(pages, limit=5, label=None, show_dates=True):
    output = u''
    pages = [page for page in pages if 'date' in page]
    if label is not None:
        pages = [page for page in pages if page.has_key('labels') and label in get_post_labels(page)]
    else:
        pages = [page for page in pages if page.url.startswith('blog.')]
    pages.sort(key=lambda p: p.get('date'), reverse=True)
    if limit is not None:
        pages = pages[:limit]

    authors = list(set([p.get('author') for p in pages if p.get('author')]))
    show_author = len(authors) > 2

    for page in pages:
        output += u'<li><a href="%s">%s</a>' % (page.get('url'), page.get('title'))
        if show_author and page.has_key('author'):
            output += u' (%s)' % page.get('author')
        if limit is None and show_dates:
            date = page.date + ' 00:00'
            date = datetime.datetime.strptime(date[:16], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y')
            output += u' <span class="date">%s</span>' % date
        if DISQUS_ID is not None:
            output += u' <a class="dcc" href="%s#disqus_thread">комментировать</a>' % (page.get('url'))
        output += u'</li>'

    if output:
        output = u'<ul class="pagelist">' + output + u'</ul>\n'
        if DISQUS_ID is not None:
            output += u'<script type="text/javascript">var disqus_shortname = "'+ DISQUS_ID +'"; (function () { var s = document.createElement("script"); s.async = true; s.type = "text/javascript"; s.src = "http://" + disqus_shortname + ".disqus.com/count.js"; (document.getElementsByTagName("HEAD")[0] || document.getElementsByTagName("BODY")[0]).appendChild(s); }());</script>'
        return output

    return u'Ничего нет.'


def add_comments(page):
    labels = get_post_labels(page)
    if page.get('file', '').endswith('.mp3') or 'blog' in labels:
        settings = 'var disqus_identifier = "'+ page.url +'";'
        return u'<div id="disqus_thread"></div><script type="text/javascript">if (window.location.href.indexOf("http://localhost:") == 0) var disqus_developer = 1;'+ settings +' (function() { var dsq = document.createElement(\'script\'); dsq.type = \'text/javascript\'; dsq.async = true; dsq.src = \'http://tmradio.disqus.com/embed.js\'; (document.getElementsByTagName(\'head\')[0] || document.getElementsByTagName(\'body\')[0]).appendChild(dsq); })();</script><noscript>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript=tmradio">comments powered by Disqus.</a></noscript><a href="http://disqus.com" class="dsq-brlink">blog comments powered by <span class="logo-disqus">Disqus</span></a>'
    return ''

def print_player(page):
    extra = u''
    link = page.get('file', '')
    if link.endswith('.mp3'):
        extra = u'<p>Слушать выпуск:</p><div id="player"><object classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" codebase="http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=6,0,0,0" width="165" height="37" id="swf"><param name="movie" value="niftyplayer.swf?file='+ urllib.quote(link) +'"><param name="quality" value="high"/><param name="bgcolor" value="#FFFFFF"/><embed src="niftyplayer.swf?file='+ urllib.quote(link) +'" quality="high" bgcolor="#FFFFFF" width="165" height="37" name="swf" type="application/x-shockwave-flash" swLiveConnect="true" pluginspage="http://www.macromedia.com/go/getflashplayer"></embed></object></div>'
        extra += u'<p><a href="%s">Скачать выпуск</a></p>' % escape(link)
    extra += add_comments(page)
    return extra


def hook_preconvert_ccss():
    """
    Обработка CleverCSS.  Файлы с расширением .ccss конвертируются в .css.
    """
    for ccss in glob.glob(os.path.join(input, "**.ccss")):
        css = ccss[len(input):].lstrip("/")
        css = "%s.css" % os.path.splitext(css)[0]
        css = os.path.join(output, css)
        fpi = open(ccss)
        fpo = open(css, 'w')
        fpo.write(clevercss.convert(fpi.read()))
        fpi.close()
        fpo.close()


# -----------------------------------------------------------------------------
# generate rss feed
# -----------------------------------------------------------------------------

_RSS = u"""<?xml version="1.0"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
<atom:link href="http://dallas.example.com/rss.xml" rel="self" type="application/rss+xml"/>
<title>%s</title>
<link>%s</link>
<description>%s</description>
<language>ru-RU</language>
<pubDate>%s</pubDate>
<lastBuildDate>%s</lastBuildDate>
<docs>http://blogs.law.harvard.edu/tech/rss</docs>
<generator>Poole</generator>
%s
</channel>
</rss>
"""

def write_rss(pages, title, description, label=None):
    base = BASE_URL

    if label is None:
        filename = 'rss.xml'
    else:
        filename = label.replace(' ', '_') + '.xml'

    xml = u'<?xml version="1.0"?>\n'
    xml += u'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml += u'<channel>\n'
    xml += u'<atom:link href="%(base)s/%(filename)s" rel="self" type="application/rss+xml"/>\n' % { 'base': base, 'filename': filename }
    xml += u'<language>ru-RU</language>\n'
    xml += u'<docs>http://blogs.law.harvard.edu/tech/rss</docs>\n'
    xml += u'<generator>Poole</generator>\n'
    xml += u'<title>%s</title>\n' % escape(title)
    xml += u'<description>%s</description>\n' % escape(description)
    if label is None:
        xml += u'<link>%s/</link>\n' % base
    else:
        xml += u'<link>%s%s</link>\n' % (base, get_label_url(label))
    date = email.utils.formatdate()
    xml += u'<pubDate>%s</pubDate>\n' % date
    xml += u'<lastBuildDate>%s</lastBuildDate>\n' % date

    # leave only blog posts
    pages = [p for p in pages if p.has_key('title') and p.has_key('date') and '://' not in p.url and 'draft' not in get_post_labels(p)]
    # filter by label
    if label is not None:
        pages = [p for p in pages if label in get_post_labels(p)]
    # sort by date
    pages.sort(key=lambda p: p.date, reverse=True)
    # process first 10 items
    for p in pages:
        xml += u'<item>\n'
        xml += u'\t<title>%s</title>\n' % escape(p.title)
        link = u"%s/%s" % (BASE_URL, p.url)
        xml += u'\t<link>%s</link>\n' % link
        xml += u'\t<description>%s</description>\n' % escape(p.html)
        date = parse_date_time(p.date)
        xml += u'\t<pubDate>%s</pubDate>\n' % email.utils.formatdate(date)
        xml += u'\t<guid>%s</guid>\n' % link
        if p.has_key('file'):
            mime_type = mimetypes.guess_type(urlparse.urlparse(p.file).path)[0]
            xml += u'\t<enclosure url="%s" type="%s" length="%s"/>\n' % (p.file, mime_type, p.get('filesize', 1))
        for l in get_post_labels(p):
            xml += u'\t<category>%s</category>\n' % l
        author = p.get('author')
        if author:
            xml += u'\t<author>%s</author>\n' % author
        xml += u'</item>\n'

    xml += u'</channel>\n'
    xml += u'</rss>\n'

    print "info   : writing %s" % filename
    fp = open(os.path.join(output, filename), 'w')
    fp.write(xml.encode('utf-8'))
    fp.close()

    write_json(filename[:-4] + '.json', pages)

def write_json(filename, pages):
    items = []
    for p in pages:
        item = {
            'title': p.get('title'),
            'link': BASE_URL + '/' + p.get('url'),
            'date': email.utils.formatdate(parse_date_time(p.get('date'))),
        }
        if p.has_key('author'):
            item['author'] = p.get('author')
        if p.has_key('file'):
            item['file'] = p.get('file')
            item['filesize'] = p.get('filesize')
            item['filetype'] = mimetypes.guess_type(urlparse.urlparse(p.get('file')).path)[0]
        items.append(item)

    print "info   : writing %s" % filename
    fp = open(os.path.join(output, filename), 'w')
    fp.write(json.dumps(items))
    fp.close()

def hook_postconvert_rss():
    write_rss(pages, u'Тоже мне радио', u'Обновления сайта.')
    for label in get_label_stats(pages).keys():
        write_rss(pages, u'Тоже мне радио: ' + label, u'Страницы сайта Тоже мне радио с пометкой «%s».' % label, label)

def get_rss_table():
    labels = get_label_stats(pages).keys()
    pages_ = sorted([page for page in pages if os.path.splitext(page.url)[0] in labels or page.get('rsstitle')], key=lambda p: p.get('rsstitle', p.get('title')))

    html = u'<table id="rsst"><tbody>'
    for page in pages_:
        page['name'] = os.path.splitext(page.url)[0]
        page['rsstitle'] = page.get('rsstitle', page.get('title'))
        if not page['rsstitle']:
            continue
        page['rsslink'] = page.get('rsslink', page.get('name') + '.xml')
        page['jsonlink'] = page.get('jsonlink', page.get('name') + '.json')
        html += u'<tr><td><a href="%(url)s">%(rsstitle)s</a></td><td><a href="%(rsslink)s">RSS</a></td>' % page
        if page['jsonlink']:
            html += u'<td><a href="%(jsonlink)s">JSON</a>' % page
        html += u'</td></tr>'
    html += u'</tbody></table>\n'

    return html
