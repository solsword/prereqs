#!/usr/bin/env python3

"""
scrape.py

Web scraper for Wellesley course browser to get info on course
descriptions, etc.
"""

# built-in modules
import re, json, time, sys, os

# dependencies
import requests
import bs4

# configuration
import config

# Set this to control debugging
DEBUG = False


def debug(*args, **kwargs):
    """
    Use instead of print for debugging prints.
    """
    if DEBUG:
        print(*args, **kwargs)


# URLS and request parameters
FRONT_URL = "https://courses.wellesley.edu/"
BACK_URL = "https://courses.wellesley.edu/display_single_course_cb.php"
DC_PARAMS = [
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
POST_PARAMS = [
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

# Where to put output files
OUTDIR = "course_info"

# Cache essential info in this dictionary to avoid unnecessary http
# requests to back_urls
INSTRUCTOR_URLS = {}


def longest_group(groups):
    grlens = [len(g) for g in groups]
    idx = grlens.index(max(grlens))
    return groups[idx]


def find_course_info(info, semester):
    """
    Finds (additional) info for the specified course (given info dict's
    'id' key must be present) in the specified semester (6-digit semester
    ID string).
    """
    cid = info['id']

    # Fetch course listing info
    listing = None
    # Note that sometimes the server is exhausted, so we will keep trying
    # a few times...
    attempts = 0
    while listing is None and attempts < 3:
        attempts += 1
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
        resp = requests.post(FRONT_URL, data=post_data)

        # Use Beautiful Soup to parse the HTML
        soup = bs4.BeautifulSoup(resp.text, 'html.parser')

        listing = soup.find(id="course_listing")
        time.sleep(0.05 * attempts**2) # quadratic frequency backoff

    # Too many attempts without success...
    if listing is None:
        print(f"Unable to find listing for course after {attempts} attempts!")
        return

    debug('listing: {}'.format(listing))
    entries = listing.find_all(class_="courseitem")
    debug('entries: {}'.format(entries))

    # New code looks for all matches to extract term info and associated
    # instructors:
    matches = [entry for entry in entries if cid.upper() in str(entry)]

    if len(matches) == 0:
        print("Warning: could not find course entry for '{}'.".format(cid))
        return

    # Invariant: following code executed only if len(matches) >= 1:

    # If a current semester, parse entries into term/instructor info,
    # also updating INSTRUCTOR_URLS along the way. Should also collect
    # full info for each semester, but current only does that for first
    # class encountered
    if semester in config.CURRENT_SEMESTERS:
        collect_term_info_for_entries(info, semester, matches)
    else: # must be previous semester
        first_entry_info = get_entry_info(cid, matches[0])
        collect_detailed_info(info, semester, first_entry_info)


def collect_term_info_for_entries(info, semester, entries):
    '''Only called for current semesters, which have terms'''
    global INSTRUCTOR_URLS

    cid = info['id']
    term_info = {}
    for entry in entries:
        entry_info = get_entry_info(cid, entry)
        collect_detailed_info(info, semester, entry_info)
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
        # Defaults for missing instructors...
        idict_mode = {
            'name': str(instructor),
            'URL': INSTRUCTOR_URLS.get(
                instructor,
                "https://cs.wellesley.edu"
            ),
            'mode': mode
        }
        term_dict[section] = idict_mode
        if section[0] in ['D', 'L']: # lab/discussion section
            add_instructor(idict_mode, term_dict['lab_instructors'])
        else:
            add_instructor(idict_mode, term_dict['lecturers'])
    if 'term_info' not in info:
        info['term_info'] = term_info
    else:
        # Add new terms to existing dictionary
        info['term_info'].update(term_info)


def add_instructor(idict_mode, idict_modes_list):
    def find_instructor_dict_modes(name):
        matches = [dct for dct in idict_modes_list if dct['name'] == name]
        if len(matches) == 0:
            return None
        else:
            return matches[0]
    idict_modes = find_instructor_dict_modes(idict_mode['name'])
    mode = idict_mode['mode']
    if idict_modes is None:
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
    debug("Course name:", course_name)

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
    debug('get_dc_info first_call: {}'.format(first_call))
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
    debug('args: {}'.format(args))
    # Check length
    if len(args) != len(DC_PARAMS):
        print(
            "Warning: Wrong # of args:\n{}\nvs\n{}".format(args, DC_PARAMS)
        )

    # Build post data dictionary
    dc_info = { DC_PARAMS[i]: args[i] for i in range(len(args)) }
    debug('get_entryinfo dc_info {}'.format(dc_info))
    semester = dc_info['semester']
    debug('semester {}'.format(semester))
    section, term, mode = get_section_term_mode(cid, dc_info['crn'])
    debug('term {}'.format(term))
    debug('section {}'.format(section))
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


def collect_detailed_info(info, semester, entry_info):
    """
    Given basic entry info for a course in a given semester, looks up
    detailed info from that semester, and merges it into the given info
    dictionary.
    """
    global INSTRUCTOR_URLS

    # Extract info for backend request for detailed info
    dc_info = entry_info['dc_info']
    post_data = { param: dc_info[param] for param in POST_PARAMS }
    debug('post_data: {}'.format(post_data))

    time.sleep(0.05) # don't crawl too fast

    # Make backend request
    presp = requests.post(BACK_URL, data=post_data)

    # What if we get an empty response...
    if presp.text == '':
        print(
            "Got empty response from server for:\n{}\nwith:\n{}".format(
                BACK_URL,
                (
                    '{\n'
                  + '\n'.join(
                        "  {}: {}".format(k, repr(v))
                        for k, v in post_data.items()
                    )
                  + "\n}"
                )
            )
        )
        # In this case, we don't have access to extra info, so we'll put
        # in dummies
        blank_info = {
            "course_name": entry_info['course_name'], # lyn added
            "semester": semester,
            "term": entry_info['term'], # lyn added
            "section": entry_info['section'], # lyn added
            "professors": [],
            "description": "unknown",
            "details": "",
            "meeting_info": "",
            "distributions": "",
            "linked_courses": "",
            "prereqs": "",
            "extra_info": [],
            "blank_response": True
        }
        info.update(blank_info)
        return

    # Use Beautiful Soup to parse the HTML
    soup = bs4.BeautifulSoup(presp.text, 'html.parser')

    # Extract what we're interested in
    prof_nodes = soup.find_all('a', class_="professorname")

    # Start from already-identified professors if there are any
    professors = info.get("professors", [])

    # Collect each professor
    for prof_node in prof_nodes:
        debug('prof_node: {}'.format(prof_node))
        prof_name = prof_node.get_text().strip()
        prof_URL = "https://courses.wellesley.edu/" + prof_node.get('href')

        if prof_name not in INSTRUCTOR_URLS:
            INSTRUCTOR_URLS[prof_name] = prof_URL

        # Add this professor if it's not a duplicate...
        if not any(x == [prof_name, prof_URL] for x in professors):
            professors.append([prof_name, prof_URL])

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

    # Merge these results...
    info.update(course_info)


# For each semester, this retrieves one class at a time.
# TODO: Peter suggested a more efficient approach of fetching the all
# short descriptions for a dept (CS or MATH) for a semester at once to
# reduce number of web requests, but Lyn didn't have time to implement
# this.
def process_course(cid, filename):
    """
    Gathers course info from all current semesters or if not present from
    previous semesters. Writes the gathered info into the given file.
    """
    # Our course info dictionary:
    result = {"id": cid}

    # Try searching in different semesters to see if we can find a
    # description...
    for semester in config.CURRENT_SEMESTERS:
        print("\nSearching in current semester '" + semester + "'...")
        find_course_info(result, semester)

    # If we still haven't found anything, keep searching in previous
    # semesters...
    if len(result) == 1 or result.get("blank_response"):
        for semester in config.PREVIOUS_SEMESTERS:
            # TODO: This?
            if "blank_response" in result:
                del result["blank_response"]
            print("\nSearching in old semester '" + semester + "'...")
            find_course_info(result, semester)
            if len(result) > 1 and "blank_response" not in result:
                break

    print("...done scraping; writing JSON output.")
    with open(filename, 'w') as fout:
        json.dump(result, fout, indent=2, sort_keys=True)


def main():
    """
    Reads a single filename argument which contains a list of class IDs.
    Checks for OUTDIR/<cid>.json and updates those course info files for
    any courses where the mtime of that file is older than the mtime of
    the class ids list file.
    """
    if len(sys.argv) < 2 or '-h' in sys.argv or "--help" in sys.argv:
        print(
            "You must supply a file name of a file containing a list"
          + " of class IDs (e.g., cs111).",
             file=sys.stderr
        )
        exit(1)

    list_filename = sys.argv[1]

    # Read in list of classes
    with open(list_filename, 'r') as fin:
        classes = [
            line.strip()
            for line in fin.read().strip().splitlines()
        ]

    # Base time to check modification times against
    basetime = os.path.getmtime(list_filename)

    # Process only classes whose mtimes are older than the list file
    for cid in classes:
        # Filename
        course_file = os.path.join(OUTDIR, cid + ".json")

        # Get modification time
        if os.path.exists(course_file):
            mtime = os.path.getmtime(course_file)
        else:
            mtime = basetime # definitely update: file is missing

        # Only process if it's old
        if mtime <= basetime:
            print(f"Processing {cid}")
            process_course(cid, course_file)
        else:
            print(f"Skipping {cid}")


# Run main...
if __name__ == "__main__":
    main()
