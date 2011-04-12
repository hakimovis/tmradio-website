# vim: set tw=0 fileencoding=utf-8:

from xml.sax.saxutils import escape
import clevercss
import datetime
import email.utils
import glob
import json
import mimetypes
import os.path
import sys
import time
import urllib
import urlparse

BASE_URL = 'http://www.tmradio.net'
ADMIN_EMAIL = 'info@tmradio.net'
DISQUS_ID = 'tmradio'
LABEL_NAMES = {
    'daily': u'новость дня',
    'guests': u'гости',
    'mcast': u'микроподкасты',
    'podcast': u'подкасты',
    'programs': u'программы',
    'prokino': u'про кино',
    'tsn': u'так себе новости',
    'hotline': u'горячая линия',
    }
LABEL_PAGES = ('input/%s.md', 'input/programs/%s/index.md', 'input/guests/%s/index.md', 'input/%s/index.md')

def get_page_labels(page):
    labels = [l.strip() for l in page.get('labels', '').split(',') if l.strip()]
    if page.has_key('file') and 'podcast' not in labels:
        labels.append('podcast')
    return sorted(labels)


def get_label_url(label):
    for pattern in LABEL_PAGES:
        fn = pattern % label
        if os.path.exists(fn):
            return strip_index('/' + os.path.splitext(fn)[0].split('/', 1)[1] + '.html')

def get_label_link(label):
    text = label
    if LABEL_NAMES.has_key(label):
        text = LABEL_NAMES[label]
    return u'<a href="%s">%s</a>' % (get_label_url(label), text)

def get_label_stats(posts):
    labels = {}
    for post in posts:
        for label in get_page_labels(post):
            if not labels.has_key(label):
                labels[label] = 1
            else:
                labels[label] += 1
    # Удаляем метки, для которых нет страниц.
    for label in labels.keys():
        for pattern in LABEL_PAGES:
            fn = pattern % label
            if os.path.exists(fn):
                label = None
        if label is not None:
            del labels[label]
    return labels


def init_comments(page):
    if DISQUS_ID is not None:
        return u'<script type="text/javascript">var disqus_url = "'+ BASE_URL + strip_index('/' + page.get('url')) +'";</script>'

def strip_index(url, suffix='index.html'):
    if url.endswith('/' + suffix):
        url = url[:-len(suffix)]
    return url

def parse_date_time(text, as_float=True):
    """Преобразует дату-время из текста в структуру.

    Поддерживаемый формат: ГГГГ-ММ-ДД ЧЧ:ММ:СС, недостающие сегменты с конца
    заполняюся нулями.
    """
    default = '0000-01-01 00:00:00'
    text = text + default[len(text):]
    result = time.strptime(text, '%Y-%m-%d %H:%M:%S')
    if as_float:
        result = time.mktime(result)
    return result


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


def page_meta(page):
    """Prints page metadata (creation date, labels etc.)"""
    parts = []

    if page.get('date'):
        parts.append(time.strftime('%d.%m.%y', time.localtime(parse_date_time(page.get('date')))))

    author = get_page_author(page)
    if author[1] != 'anonymous':
        parts.append(u'автор: <a href="mailto:%s">%s</a>' % author)

    if page.get('labels'):
        stats = get_label_stats(pages)
        labels = []
        for label in get_page_labels(page):
            if stats.has_key(label):
                labels.append(get_label_link(label))
        if labels:
            parts.append(u'метки: ' + u', '.join(labels))

    if not parts:
        return u''
    return u'<p class="meta">%s</p>' % u'; '.join(parts)

def pagelist(pages, limit=None, label='blog', show_dates=True, order_by='date', reverse_order=True, show_comments=True):
    output = u''

    def is_ok(page):
        labels = get_page_labels(page)
        """
        if not page.get('date'):
            return False
        """
        if 'draft' in labels:
            return False
        if label not in labels:
            return False
        return True

    # Удаляем страницы без нужного свойства.
    pages = [page for page in pages if page.get(order_by) is not None]

    pages = sorted([page for page in pages if is_ok(page)], key=lambda p: p.get(order_by), reverse=reverse_order)[:limit]
    authors = list(set([p.get('author') for p in pages if p.get('author')]))
    show_author = len(authors) > 2

    for page in pages:
        output += u'<li><a href="%s">%s</a>' % (strip_index(page.get('url')), page.get('title'))
        if show_author:
            author = get_page_author(page)[1]
            if author != 'anonymous':
                output += u' (%s)' % get_page_author(page)[1]
        if limit is None and show_dates:
            date = page.date + ' 00:00'
            date = datetime.datetime.strptime(date[:16], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y')
            output += u' <span class="date">%s</span>' % date
        if DISQUS_ID is not None and show_comments:
            output += u' <a class="dcc" href="%s#disqus_thread">комментировать</a>' % (strip_index(page.get('url')))
            # output += u' <a class="dcc" href="%s#disqus_thread" data-disqus-identifier="%s">комментировать</a>' % (page.get('url'), get_disqus_page_id(page))
        output += u'</li>\n'

    if output:
        output = u'<ul class="pagelist">\n' + output + u'</ul>\n'
        if DISQUS_ID is not None and show_comments:
            output += u'<script type="text/javascript">var disqus_shortname = "'+ DISQUS_ID +'"; (function () { var s = document.createElement("script"); s.async = true; s.type = "text/javascript"; s.src = "http://" + disqus_shortname + ".disqus.com/count.js"; (document.getElementsByTagName("HEAD")[0] || document.getElementsByTagName("BODY")[0]).appendChild(s); }());</script>\n'
        return output

    return u'Ничего нет.'

def get_page_author(page):
    u'''Возвращает email автора записи и его имя.

    Данные вытаскиваются из свойства author формата "email (nickname)".  Если
    какой-то части нет, она угадывается.'''
    parts = page.get('author', 'info@tmradio.net (anonymous)').split(' ', 1)
    email = name = None
    if '@' in parts[0]:
        email = parts[0]
        if len(parts) > 1:
            name = parts[1].strip('()')
    else:
        email = 'info@tmradio.net'
        name = ' '.join(parts)
    if not name:
        name = email.split('@', 1)[0]
    return (email, name)

def get_page_classes(page):
    result = u' id="%s"' % page.url
    labels = [l.strip() for l in page.get('labels', '').split(',') if l.strip().encode('utf-8').isalpha()]
    if labels:
        result += u' class="%s"' % u' '.join(labels)
    return result


def get_disqus_page_id(page):
    return page.get('disqus_id', strip_index(page.get('url')))


def add_comments(page):
    labels = get_page_labels(page)
    if page.get('file', '').split('?')[0].endswith('.mp3') or 'blog' in labels:
        settings = 'var disqus_identifier = "'+ strip_index(page.url) +'";'
        return u'<div id="disqus_thread"></div><script type="text/javascript">if (window.location.href.indexOf("http://localhost:") == 0) var disqus_developer = 1;'+ settings +' (function() { var dsq = document.createElement(\'script\'); dsq.type = \'text/javascript\'; dsq.async = true; dsq.src = \'http://tmradio.disqus.com/embed.js\'; (document.getElementsByTagName(\'head\')[0] || document.getElementsByTagName(\'body\')[0]).appendChild(dsq); })();</script><noscript>Please enable JavaScript to view the <a href="http://disqus.com/?ref_noscript=tmradio">comments powered by Disqus.</a></noscript><a href="http://disqus.com" class="dsq-brlink">blog comments powered by <span class="logo-disqus">Disqus</span></a>'
    return ''

def print_player(link, extras=True):
    extra = u''
    if link.split('?')[0].endswith('.mp3'):
        if extras:
            extra += u'<p>Выпуск можно <a href="%s">скачать</a> или прослушать прямо здесь:</p>' % escape(link)
        extra += u'<div id="player"><object classid="clsid:D27CDB6E-AE6D-11cf-96B8-444553540000" codebase="http://download.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=6,0,0,0" width="165" height="37" id="swf"><param name="movie" value="/niftyplayer.swf?file='+ urllib.quote(link) +'"><param name="quality" value="high"/><param name="bgcolor" value="#FFFFFF"/><embed src="/niftyplayer.swf?file='+ urllib.quote(link) +'" quality="high" bgcolor="#FFFFFF" width="165" height="37" name="swf" type="application/x-shockwave-flash" swLiveConnect="true" pluginspage="http://www.macromedia.com/go/getflashplayer"></embed></object></div>'
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

def write_rss(pages, title, description, label=None, filename=None):
    base = BASE_URL

    if filename is None:
        if label is None:
            filename = 'rss.xml'
        else:
            filename = label.replace(' ', '_') + '.xml'

    # leave only blog posts
    pages = [p for p in pages if p.has_key('title') and p.has_key('date') and '://' not in p.url and 'draft' not in get_page_labels(p)]

    # filter by label
    if label is not None:
        pages = [p for p in pages if label in get_page_labels(p)]
    if not pages:
        print 'WARNING: no data for', filename
    # sort by date
    pages.sort(key=lambda p: p.date, reverse=True)

    xml = u'<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += u'<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
    xml += u'<channel>\n'
    xml += u'<atom:link href="%(base)s/%(filename)s" rel="self" type="application/rss+xml"/>\n' % { 'base': base, 'filename': filename }
    xml += u'<language>ru-RU</language>\n'
    xml += u'<docs>http://blogs.law.harvard.edu/tech/rss</docs>\n'
    xml += u'<itunes:owner><itunes:email>%s</itunes:email></itunes:owner>\n' % page.get('podcast_owner_email', ADMIN_EMAIL)
    xml += u'<itunes:explicit>%s</itunes:explicit>\n' % page.get('explicit', 'No')
    for cat in page.get('itunes_categories', 'Society & Culture').split(','):
        xml += u'<itunes:category text="%s"/>\n' % escape(cat.strip())
    xml += u'<generator>Poole</generator>\n'
    xml += u'<title>%s</title>\n' % escape(title)
    xml += u'<description>%s</description>\n' % escape(description)
    xml += u'<link>%s/%s</link>\n' % (BASE_URL.rstrip('/'), strip_index(filename, suffix='index.xml'))
    if pages:
        feed_pub_date = email.utils.formatdate(parse_date_time(pages[0].date))
        xml += u'<pubDate>%s</pubDate>\n' % feed_pub_date
        xml += u'<lastBuildDate>%s</lastBuildDate>\n' % feed_pub_date

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
        for l in get_page_labels(p):
            xml += u'\t<category>%s</category>\n' % l
        xml += u'\t<author>%s (%s)</author>\n' % get_page_author(p)
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
            'link': strip_index(BASE_URL + '/' + p.get('url')),
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

    feeds = [{
        'url': os.path.splitext(page.get('url'))[0] + '.xml',
        'label': page.get('rss'),
        'title': page.get('rsstitle', page.get('title')),
        'description': page.get('rssdescription', u'Страницы с меткой «%s»' % page.get('rss')),
    } for page in pages if page.get('rss')]

    for feed in feeds:
        write_rss(pages, feed['title'], feed['description'], feed['label'], filename=feed['url'])

def get_rss_table():
    labels = get_label_stats(pages).keys()
    pages_ = sorted([page for page in pages if os.path.splitext(page.url)[0] in labels or page.get('rsstitle')], key=lambda p: p.get('rsstitle', p.get('title')).lower())

    html = u'<table class="skel" id="rsst"><tbody>\n'
    for page in pages_:
        page['name'] = os.path.splitext(page.url)[0]
        page['rsstitle'] = page.get('rsstitle', page.get('title'))
        if not page['rsstitle']:
            continue
        page['rsslink'] = page.get('rsslink', page.get('name') + '.xml')
        page['jsonlink'] = page.get('jsonlink', page.get('name') + '.json')
        page['page_url'] = strip_index(page.get('url'))
        html += u'<tr><td><a href="%(page_url)s">%(rsstitle)s</a></td><td><a href="%(rsslink)s">RSS</a></td>' % page
        html += u'<td><a href="%s">iTunes</a></td>' % itunes_link(page['rsslink'])
        if page['jsonlink']:
            html += u'<td><a href="%(jsonlink)s">JSON</a>' % page
        html += u'</td></tr>\n'
    html += u'<tr><td>Всё подряд</td><td><a href="/rss.xml">RSS</a></td><td><a href="itcp://www.tmradio.net/rss.xml">iTunes</a></td><td><a href="/rss.json">JSON</a></td></tr>\n'
    html += u'</tbody></table>\n'

    return html

def itunes_link(link):
    if '://' not in link:
        link = BASE_URL + '/' + link.lstrip('/')
    return link.replace('http://', 'itpc://')


def init_flattr(page):
    return "<script type='text/javascript'>/* <![CDATA[ */ (function() { var s = document.createElement('script'), t = document.getElementsByTagName('script')[0]; s.type = 'text/javascript'; s.async = true; s.src = 'http://api.flattr.com/js/0.6/load.js?mode=auto'; t.parentNode.insertBefore(s, t); })(); /* ]]> */ </script>"


def yandex_money_stats():
    fn = 'input/support/donate/yandex/history.json'
    if os.path.exists(fn):
        data = json.load(open(fn, 'rb'))
        return u'Яндекс.Деньгами собрано: %(income).2f, потрачено: %(outcome).2f, осталось: %(left).2f (информация обновляется примерно раз в неделю); доступен <a href="/support/donate/yandex/">полный список транзакций</a>.' % data

def yandex_money_table():
    fn = 'input/support/donate/yandex/history.json'
    if os.path.exists(fn):
        data = json.load(open(fn, 'rb'))
        today = data['transactions'][-1][0]
        output = u'<table class="skel" id="yamoney">\n'

        output += u'<tfoot>\n'
        output += u'<tr><td/><td>%.2f</td><td>Всего получено</td></tr>\n' % (data['income'])
        output += u'<tr><td/><td>%.2f</td><td>Всего потрачено</td></tr>\n' % (data['outcome'])
        output += u'<tr><td/><td>%.2f</td><td>Текущий остаток</td></tr>\n' % (data['left'])
        output += u'</tfoot>\n'

        output += u'<tbody>\n'
        for t in data['transactions']:
            output += u'<tr><td>%s</td><td>%.2f</td><td>%s</td></tr>\n' % tuple(t)
        output += u'</tbody></table>\n'
        return output

# -----------------------------------------------------------------------------
# generate the site map
# -----------------------------------------------------------------------------

def XXX_once_dump_labels():
    for p in pages:
        print p.get('url'), get_page_labels(p)

def once_sitemap():
    """Generate Google sitemap.xml file."""

    contents = ''
    for p in pages:
        url = p.get('url')
        if '://' not in url: # skip external links
            contents += '<url>\n\t<loc>%s</loc>\n' % (strip_index(BASE_URL + '/' + url))
            page_date = p.get('date')
            if page_date:
                contents += '\t<lastmod>%s</lastmod>\n' % time.strftime('%Y-%m-%d', parse_date_time(page_date, as_float=False))
            contents += '</url>\n'

    contents = '<?xml version="1.0" encoding="utf-8"?>\n' \
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' \
        + contents + \
        '</urlset>'

    fname = os.path.join(options.project, "..", "sitemap.xml")
    fp = open(fname, 'w')
    fp.write(contents)
    fp.close()


def monthly_stats(date):
    data = json.load(open('input/blog/monthly.json', 'rb'))
    if date not in data:
        return u'Нет данных за указанный период.'

    columns = [
        ('connection_count', u'Количество <a href="/player.html">подключений</a>', str),
        ('connection_avg', u'Среднее время прослушивания, мин.', lambda x: str(x / 60)),
        ('connection_max', u'Максимальное число одновременных подключений', str),
        ('unique_ips', u'<a href="/listeners/#map">Уникальных IP-адресов</a>', str),
        ('track_count', u'Количество дорожек в медиатеке', str),
        ('track_length', u'Общая продолжительность медиатеки, ч.', lambda x: str(x / 3600)),
        ('traffic_stream', u'Трафик от прослушивания, Гб', str),
        ('traffic_total', u'<a href="http://stream.tmradio.net/">Общий трафик</a>, Гб', str),
        ('money_in', u'Пришло <a href="/support/donate/">пожертвований</a>, р.', str),
        ('money_out', u'Потрачено пожертвований, р.', str),
    ]

    output = u'<table class="mstat">\n<tbody>\n'
    for k, h, conv in columns:
        if k in data[date]:
            output += u'<tr><th>%s:</th><td>%s</td></th>\n' % (h, conv(data[date][k]))
    output += u'</tbody>\n</table>\n<p>Эти данные доступны также <a href="/blog/monthly.json">в формате JSON</a> (для машинной обработки).</p>'
    return output

def run(args):
    import subprocess
    subprocess.Popen(args).wait()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print >>sys.stderr, 'Usage: python macro.py command'
        sys.exit(1)

    if sys.argv[1] == 'new-blog':
        last_id = int([fn.split(os.sep)[-2] for fn in glob.glob(os.path.join('input', 'blog', '*', 'index.md'))][-1])
        filename = os.path.join('input', 'blog', str(last_id + 1), 'index.md')
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.mkdir(os.path.dirname(filename))

        contents = u"title: ...\ndate: %(date)s\nlabels: draft, blog\nauthor: hex@umonkey.net (umonkey)\n---\n..."
        open(filename, 'wb').write(contents.encode('utf-8'))

        run(['vim', filename])
