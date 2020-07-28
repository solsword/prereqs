#!/usr/bin/env python3

"""
scrape.py

Web scraper for Wellesley course browser to get info on course
descriptions, etc.
"""

# built-in modules
import re, json, time, sys

# dependencies
import requests
import bs4

# TODO: Update this!
# Note: This represents different semesters to search in as a cascading
# fallback if we can't find a class description.
SEMESTERS = [
    "202009", # Fall 2020
    "202102", # Spring 2021
    "202002", # Spring 2020
    "201909", # Fall 2019
]

classes = sys.stdin.read().split()

if classes == []:
    print(
        "You must supply a list of class IDs (e.g., cs111) via stdin.",
         file=sys.stderr
    )
    exit(1)

def longest_group(groups):
    grlens = [len(g) for g in groups]
    idx = grlens.index(max(grlens))
    return groups[idx]


front_url = "https://courses.wellesley.edu/"
back_url = "https://courses.wellesley.edu/display_single_course_cb.php"
dc_params = [
    "crn",
    "semester",
    "pe_term",
    "myelement",
    "frame_title",
    "show_locations",
    "subj_code",
    "show_schedules",
    "w_crns",
    "secret",
]
post_params = [
    "crn",
    "semester",
    "pe_term",
    "myelement",
    "frame_title",
    "show_locations",
    "show_schedules",
    "w_crns",
    "secret",
]

output = "course_info.json"

full_info = {}

remaining = set(classes)
found = set()

# Try searching in different semesters to see if we can find a
# description...
for semester in SEMESTERS:
    remaining -= found
    if remaining:
        print("\nSearching in semester '" + semester + "'...")
    for cid in remaining:
        time.sleep(0.05) # don't crawl too fast
        print("Looking up course '" + cid + "' ...")
        post_data = {
            "submit": "Search",
            "keywords": cid,
            "semester": semester,
            "department_subject": "All",
            "department": "All",
            "subject": "All",
            "faculty": "All",
            "meeting_day": "All",
            "meeting_time": "All",
            "special": "All"
        }
        resp = requests.post(front_url, data=post_data)

        # Use Beautiful Soup to parse the HTML
        soup = bs4.BeautifulSoup(resp.text, 'html.parser')

        listing = soup.find(id="course_listing")
        print('listing: {}'.format(listing))
        entries = listing.find_all(class_="courseitem")
        print('entries: {}'.format(entries))
        match = None
        for entry in entries:
            entry_html = str(entry)
            if cid.upper() in entry_html:
                match = entry_html
                break
        if match == None:
            print("Warning: could not find course entry for '{}'.".format(cid))
            continue

        # find last displayCourse call on the page
        dc_calls = re.findall(r"displayCourse\([^)]*\)", match)
        first_call = dc_calls[0]
        argspart = first_call.split('(')[1].split(')')[0]
        argsbits = [
            longest_group(groups).strip()
            for groups in re.findall(
                r'''('[^']*'\s*)|("[^"]*"\s*)|([^'",]+\s*)(?:,|$)''',
                argspart
            )
        ]
        args = [
            arg[1:-1]
                if arg[0] in "'\"" # a quoted string
                else (
                    int(arg) # an integer?
                        if arg.isdigit()
                        else '' # give up...
                )
            for arg in argsbits
        ]

        # Check length
        if len(args) != len(dc_params):
            print (
                "Warning: Wrong # of args:\n{}\nvs\n{}".format(args, dc_params)
            )

        # Build post data dictionary
        info = { dc_params[i]: args[i] for i in range(len(args)) }
        post_data = { param: info[param] for param in post_params }


        time.sleep(0.05) # don't crawl too fast

        # Make backend request
        presp = requests.post(back_url, data=post_data)

        # Use Beautiful Soup to parse the HTML
        soup = bs4.BeautifulSoup(presp.text, 'html.parser')

        # Extract what we're interested in
        prof_nodes = soup.find_all('a', class_="professorname")
        detail_node = soup.find(class_="coursedetail")

        # Extract subsequent divs that hold course info
        course_info = {
            "professors": [],
            "description": "unknown",
            "semester": semester,
            "details": "",
            "meeting_info": "",
            "distributions": "",
            "linked_courses": "",
            "prereqs": "",
            "extra_info": [],
        }

        for prof_node in prof_nodes:
            course_info["professors"].append([
                prof_node.get_text().strip(),
                "https://courses.wellesley.edu/" + prof_node.get('href')
            ])

        dtext = detail_node.get_text()
        print("  ...found: '" + dtext[:55] + "...")

        extra = []
        first = True
        for child in detail_node.children:
            if isinstance(child, bs4.NavigableString):
                child_str = str(child).strip()
                if len(child_str) == 0:
                    continue
            else:
                child_str = child.get_text().strip()

            if first:
                course_info["description"] = child_str
                first = False
                continue

            if (
                child_str.startswith("CRN")
             or child_str.startswith("Credit Hours")
            ):
                course_info["details"] = child_str
            elif child_str.startswith("Meeting Time"):
                course_info["meeting_info"] = child_str
            elif child_str.startswith("Distributions"):
                course_info["distributions"] = child_str
            elif child_str.startswith("Prerequisites"):
                course_info["prereqs"] = child_str
            elif child_str.startswith("Linked Courses"):
                course_info["linked_courses"] = child_str
            elif child_str.startswith("Notes"):
                course_info["notes"] = child_str
            elif not child_str.startswith("ShareThis"):
                course_info["extra_info"].append(child_str)
            # else ignore it

        full_info[cid] = course_info
        found.add(cid)

print("...done scraping; writing JSON output.")

with open(output, 'w') as fout:
    json.dump(full_info, fout, indent=2)
