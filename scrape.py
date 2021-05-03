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

CURRENT_SEMESTERS = [ # Treat semesters for current year specially to find term/instructor info
    "202109", # Fall 2020
    "202202" # Spring 2021
]

PREVIOUS_SEMESTERS = [ # Treat semesters for current year specially to find term/instructor info
    "202009", # Fall 2020
    "202102" # Spring 2021
    "202002", # Spring 2020
    "201909", # Fall 2019
]

# PREVIOUS_SEMESTERS = [ # Treat semesters for current year specially to find term/instructor info
#     "202002", # Spring 2020
#     "201909", # Fall 2019
# ]

SEMESTERS = CURRENT_SEMESTERS + PREVIOUS_SEMESTERS
# SEMESTERS = PREVIOUS_SEMESTERS + CURRENT_SEMESTERS

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

initial_class_set = set(classes)
remaining = set(classes)
found = set()

# Cache essential info in these dictionaries to avoid unnecessary http reqeusts to back_urls
full_info = {} # Stores full info including description for every course
course_names = {} 
instructor_URLs = {} 

def process_course(cid, semester): 
    listing = None
    while listing == None:
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
        time.sleep(0.05) # don't crawl too fast

    print('listing: {}'.format(listing))
    entries = listing.find_all(class_="courseitem")
    print('entries: {}'.format(entries))

    # Previous code looked only for a first match
    """
    match = None
    for entry in entries:
        entry_html = str(entry)
        if cid.upper() in entry_html:
           match = entry_html
           break
    if match == None:
        print("Warning: could not find course entry for '{}'.".format(cid))
        continue # used to be in loop; lyn changed loop body to function
    """

    # New code looks for all matches to extract term info and associated
    # instructors:
    matches = [entry for entry in entries if cid.upper() in str(entry)]

    if len(matches) == 0: 
        print("Warning: could not find course entry for '{}'.".format(cid))
        # continue
        return # lyn changed loop cotinue to function return 
    # Invariant: following code executed only if len(matches) >= 1:

    # If 2020-21 semester, parse entries into term/instructor info, also 
    # updating course_names, course_descriptions, instructors along the way.
    # Should also collect full_info for each semester, but current only
    # does that for first class encountered
    if semester in CURRENT_SEMESTERS: 
        collect_term_info_for_entries(cid, semester, matches)
    else: # must be previous semester 
        first_entry_info = get_entry_info(cid, matches[0])
        collect_detailed_info(cid, semester, first_entry_info)

def collect_term_info_for_entries(cid, semester, entries): 
    '''Only called for current semesters, which have terms'''
    term_info = {}
    for entry in entries:
        entry_info = get_entry_info(cid, entry)
        # only does work if necessary
        collect_detailed_info(cid, semester, entry_info)
        term = entry_info['term']
        if term not in term_info:
            term_dict = {'lecturers': [], 'lab_instructors': []}
            # dict that will map sections to instructors
            term_info[term] = term_dict
        else: 
            term_dict = term_info[term]
        section = entry_info['section']
        mode = entry_info['mode']
        instructor = entry_info['instructor']
        # Defaults missing instructors...
        idict_mode = {
            'name': str(instructor), 
            'URL': instructor_URLs.get(instructor, "https://cs.wellesley.edu"),
            'mode': mode
        }
        term_dict[section] = idict_mode
        if section[0] in ['D', 'L']: # lab/discussion section
            add_instructor(idict_mode, term_dict['lab_instructors'])
        else:
            add_instructor(idict_mode, term_dict['lecturers'])
    full_info_for_course = full_info[cid]
    if 'term_info' not in full_info_for_course:
        full_info_for_course['term_info'] = term_info
    else: 
        # Add new terms to existing dictionary
        full_info_for_course['term_info'].update(term_info)

def add_instructor(idict_mode, idict_modes_list):
    def find_instructor_dict_modes(name):
        matches = [dct for dct in idict_modes_list if dct['name'] == name]
        if len(matches) == 0:
            return None
        else: 
            return matches[0]
    idict_modes = find_instructor_dict_modes(idict_mode['name'])
    mode = idict_mode['mode']
    if idict_modes == None: 
        new_idict_modes = {
            'name': idict_mode['name'], 
            'URL': idict_mode['URL'], 
            'modes': [mode]
            # Note this is a list of strings, not just single string
        }
        idict_modes_list.append(new_idict_modes)
    else:
        if mode not in idict_modes['modes']:
            idict_modes['modes'].append(mode)

def get_entry_info(cid, entry): 
    coursename_element = entry.find(class_="coursename_small")
    # Example: 
    # <div class="coursename_small">
    #   <p>Data, Analytics, and Visualization </p>
    #   <span class="professorname">Eni Mustafaraj</span>
    # </div>
    # Example (uncompletely hired professor):
    # <div class="coursename_small">
    #   <p>Data, Analytics, and Visualization </p>
    # </div>
    course_name = coursename_element.find('p').contents[0].strip()
    print(course_name)

    # Assumes a single instructor; will update later for multiple instructors 
    instructor_elem = coursename_element.find(
        class_='professorname'
    )
    if instructor_elem:
        instructor = instructor_elem.get_text().strip()
    else:
        instructor = None

    # find info from first displayCourse call 
    dc_calls = re.findall(r"displayCourse\([^)]*\)", str(entry))
    first_call = dc_calls[0]
    print('get_dc_info first_call: {}'.format(first_call))
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
    print('args: {}'.format(args))
    # Check length
    if len(args) != len(dc_params):
        print (
            "Warning: Wrong # of args:\n{}\nvs\n{}".format(args, dc_params)
        )

    # Build post data dictionary
    dc_info = { dc_params[i]: args[i] for i in range(len(args)) }
    print('get_entryinfo dc_info {}'.format(dc_info))
    semester = dc_info['semester']
    print('semester {}'.format(semester))
    section, term, mode = get_section_term_mode(cid, dc_info['crn'])
    print('term {}'.format(term))
    print('section {}'.format(section))
    entry_info = {
        'semester': semester, 
        'term': term, 
        'section': section,
        'course_name': course_name, 
        'instructor': instructor,
        'mode': mode, 
        'dc_info': dc_info
        }
    return entry_info

def get_section_term_mode(cid, crn): 
    crn_parts = crn.split('-')
    # Examples: 
    # Regular semester: '27287~202002-CS240L02' => ['27287~202002', 'CS240L02]
    # Semester with terms: 
    #   18244-18245~202009-CS121T1-01 =>
    #       ['18244', '18245~202009', 'CS121T1', '01']
    #
    #   17041~202009-CS111T1-02-Remote =>
    #       ['17041~202009', 'CS111T1' '02' 'Remote']
    # Regular semester after terms:
    #   18609-18610~202109-CS11501 =>
    #       ['18609', '18610~202109', 'CS11501']

    try:
        # First, find out which part has the course ID in it:
        course_part = 0
        for i, part in enumerate(crn_parts):
            if cid.upper() in part:
                course_part = i
                break

        # next, split that part to get either a term designation
        # (starting with 'T' or a section designation (not starting with
        # 'T')
        section_or_term = crn_parts[course_part].split(cid.upper())[1]

        if section_or_term.startswith('T'):
            term = section_or_term
            section = crn_parts[course_part + 1]
        else:
            section = section_or_term
            term = None

        # Set mode if we're in a term system based on the last part:
        if term:
            if crn_parts[-1] == 'Remote':
                mode = 'remote'
            else:
                mode = 'in-person'
        else:
            mode = None

    except Exception as e: 
        print(f'***get_section_and_term: Unxpected crn format: {crn}')
        print(f'(Error was: {e})')
        section = None
        term = None
        mode = False

    return section, term, mode

def collect_detailed_info(cid, semester, entry_info): 
    instructor = entry_info['instructor']
    if instructor in instructor_URLs and cid in full_info: 
        # Have already cached essential info for course and instructor 
        # no need to do anything more; return early 
        return 
    
    # Extract info for backend request for detailed info
    dc_info = entry_info['dc_info']
    post_data = { param: dc_info[param] for param in post_params }
    print('post_data: {}'.format(post_data))

    time.sleep(0.05) # don't crawl too fast

    # Make backend request
    presp = requests.post(back_url, data=post_data)

    # Use Beautiful Soup to parse the HTML
    soup = bs4.BeautifulSoup(presp.text, 'html.parser')

    # Extract what we're interested in
    prof_nodes = soup.find_all('a', class_="professorname")

    professors = [] 

    for prof_node in prof_nodes:
        print('prof_node: {}'.format(prof_node))
        prof_name = prof_node.get_text().strip()
        prof_URL = "https://courses.wellesley.edu/" + prof_node.get('href')
        if prof_name not in instructor_URLs:
            instructor_URLs[prof_name] = prof_URL
        professors.append([prof_name, prof_URL])

    if cid in full_info: 
        # Have already cached essential info for course; no need to more
        return 

    detail_node = soup.find(class_="coursedetail")

    # Extract subsequent divs that hold course info
    course_info = {
        "course_name": entry_info['course_name'], # lyn added 
        "professors": professors,
        "description": "unknown",
        "semester": semester,
        "term": entry_info['term'], # lyn added
        "section": entry_info['section'], # lyn added 
        "details": "",
        "meeting_info": "",
        "distributions": "",
        "linked_courses": "",
        "prereqs": "",
        "extra_info": [],
    }

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

# For each semester, this retrieves one class at a time. 
# TODO: Peter suggested a more efficient approach of fetching the all
# short descriptions for a dept (CS or MATH) for a semester at once to
# reduce number of web requests, but Lyn didn't have time to implement
# this. 
def process_classes(): 
    global remaining 
    # Try searching in different semesters to see if we can find a
    # description...
    for semester in SEMESTERS:
        print("\nSearching in semester '" + semester + "'...")
        if semester in CURRENT_SEMESTERS:
            for cid in initial_class_set: # Every course in current semester
                process_course(cid, semester)
        else: 
            remaining -= found
            for cid in remaining: # Process only courses not seen yet. 
                process_course(cid, semester)
    print("...done scraping; writing JSON output.")
    with open(output, 'w') as fout:
        json.dump(full_info, fout, indent=2, sort_keys=True)

process_classes()
