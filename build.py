#!/usr/bin/env python

import jinja2
import json
import sys, os

import config

if len(sys.argv) not in [8, 9] or '-h' in sys.argv:
    print(
        "Usage: build.py [alt] <template> <css> <classes_list>"
      + " <extra_info> <js> <svg> <ouptut>"
    )
    exit(0)

if len(sys.argv) == 8:
    alt = False
    (
        _,
        template_file,
        css_file,
        class_list,
        extra_info_file,
        js_file,
        svg_file,
        result_file
    ) = sys.argv
else:
    alt = True
    (
        _,
        _,
        template_file,
        css_file,
        class_list,
        extra_info_file,
        js_file,
        svg_file,
        result_file
    ) = sys.argv

# Read template file
with open(template_file, 'r') as fin:
    template = jinja2.Template(fin.read())

# Read CSS file
with open(css_file, 'r') as fin:
    css_code = fin.read()

# Read JS file
with open(js_file, 'r') as fin:
    js_code = fin.read()

# Read class list file
with open(class_list, 'r') as fin:
    cids = fin.read().strip().splitlines()

# Read individual info .json files
all_info = {}
for cid in cids:
    info = {'id': cid}
    filename = os.path.join("course_info", cid + ".json")
    if os.path.exists(filename):
        with open(filename, 'r') as fin:
            info = json.load(fin)
    all_info[cid] = info

# Read extra info file (if it exists)
if os.path.exists(extra_info_file):
    with open(extra_info_file, 'r') as fin:
        extra_info = json.load(fin)
else:
    extra_info = {}

# Merge extra info
for course_id in extra_info:
    if course_id not in all_info:
        all_info[course_id] = extra_info[course_id]
    else:
        # override per-key
        for key in extra_info[course_id]:
            all_info[course_id][key] = extra_info[course_id][key]

# Read svg file
with open(svg_file, 'r') as fin:
    svg = fin.read()

# Build main or alt template and render as HTML string 'result'
if not alt:
    result = template.render(
        title=config.TITLE,
        css=css_code,
        info=json.dumps(all_info),
        js=js_code,
        svg=svg
    )
else:
    info_list = sorted( tuple(all_info.items()) )
    result = template.render(
        title=config.TITLE,
        css=css_code,
        courses=info_list,
        js=js_code,
        svg=svg
    )

# Write output 
with open(result_file, 'w') as fout:
    fout.write(result)
