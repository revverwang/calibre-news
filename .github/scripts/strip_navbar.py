#!/usr/bin/env python3
"""把 calibre 自动塞进每篇文章的导航栏/『This article was downloaded by calibre』页脚删掉，
让 epub 里只剩干净的正文。用法：python3 strip_navbar.py converted_ebooks"""
import os
import re
import sys
import pathlib
import zipfile

# calibre 的导航栏是一个无嵌套的 div，里面是 <hr> + 页脚段落 + 上/下一篇链接
NAV = re.compile(r'<div class="calibre_navbar\d*">.*?</div>', re.S)


def clean(path):
    tmp = str(path) + '.tmp'
    removed = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.endswith(('.html', '.xhtml', '.htm')):
                text = data.decode('utf-8', 'replace')
                new, n = NAV.subn('', text)
                if n:
                    removed += n
                    data = new.encode('utf-8')
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = (zipfile.ZIP_STORED if info.filename == 'mimetype'
                                else zipfile.ZIP_DEFLATED)
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zout.writestr(zi, data)
    os.replace(tmp, path)
    return removed


def main(directory):
    total = 0
    for p in sorted(pathlib.Path(directory).glob('*.epub')):
        n = clean(p)
        print(f'{p.name}: removed {n} navbar block(s)')
        total += n
    print(f'polish done: {total} navbar blocks removed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'converted_ebooks'))
