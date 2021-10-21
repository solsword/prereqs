#!/usr/bin/env python

import jinja2, bs4

import json
import sys, os, re

import config


def main(
    template_file,
    css_file,
    class_list,
    extra_info_file,
    js_file,
    svg_file,
    result_file,
    build_alt=False
):
    """
    Arguments specify filenames to extract info from (or write to in the
    case of result_file). build_alt controls whether we're building the
    visual or alternate version.
    """

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
        info = {'id': cid, 'url': course_url(cid)}
        filename = os.path.join("course_info", cid + ".json")
        fallback_file = os.path.join("fallback_info", cid + ".json")
        found = False
        if os.path.exists(filename):
            with open(filename, 'r') as fin:
                found = True
                info = json.load(fin)

                # Check for dummy info and use fallback file
                if info["description"] == "unknown":
                    found = False

        if not found and os.path.exists(fallback_file):
            print(f"Warning: Using fallback info for {cid}.")
            with open(fallback_file, 'r') as fin:
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

    # Extract offering info from SVG
    soup = bs4.BeautifulSoup(svg, 'xml')
    nodes = soup.find_all("g", class_=lambda s: "node" in s.split())
    for n in nodes:
        cid = n.find("title").text
        if cid not in all_info:
            continue
        classes = n["class"].split()
        offered = "both"
        oexpl = "Each semester"
        # TODO: More flexible here...
        if "notoffered" in classes:
            offered = "notoffered"
            oexpl = "Not offered this year"
        elif "fall" in classes:
            offered = "fall"
            oexpl = "Fall semester only"
        elif "spring" in classes:
            offered = "spring"
            oexpl = "Spring semester only"

        all_info[cid]['offered'] = offered
        all_info[cid]['offered_string'] = oexpl

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


def course_url(course_id):
    """
    Given a course id string, returns the URL for the link to that
    course's website.
    """
    if course_id.startswith("math"):
        return "https://www.wellesley.edu/math/curriculum/current_offerings"
    elif course_id.startswith("cs"):
        return "https://cs.wellesley.edu/~" + course_id
    else:
        dept_matches = re.findall("[a-z]+", course_id)
        dept = None
        if len(dept_matches) > 0:
            dept = dept_matches[0]

        if dept:
            return "https://www.wellesley.edu/" + dept + "/curriculum"
        else:
            print(f"Unable to extract department from: '{course_id}'")
            return "https://www.wellesley.edu/cs/curriculum"


# Figure out args and run main
if __name__ == "__main__":
    if len(sys.argv) not in [8, 9] or '-h' in sys.argv:
        print(
            "Usage: build.py [alt] <template> <css> <classes_list>"
          + " <extra_info> <js> <svg> <ouptut>"
        )
        exit(0)

    if len(sys.argv) == 8:
        alt = False
        args = sys.argv[1:]
    else:
        alt = True
        args = sys.argv[2:]

    main(*args, build_alt=alt)
