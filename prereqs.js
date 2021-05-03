// jshint esversion: 6
// jshint -W014
// jshint -W083
// jshint -W097
/* globals document, console, window, info */

"use strict";

// From an SVG polygon node, extracts an array of x/y floating-point
// position value pairs, plus an array containing the minimum x and y
// values and the maximum x and y values in the polygon.
function extract_points_and_limits(polygon_node) {
    let points = [];
    let minx, miny, maxx, maxy;
    for (let coords of polygon_node.getAttribute("points").split(" ")) {
        let [x, y] = coords.split(",");
        x = parseFloat(x);
        y = parseFloat(y);
        if (isNaN(x) || isNaN(y)) {
            continue;
        }
        points.push([x, y]);
        if (minx == undefined || x < minx) {
            minx = x;
        }
        if (miny == undefined || y < miny) {
            miny = y;
        }
        if (maxx == undefined || x > maxx) {
            maxx = x;
        }
        if (maxy == undefined || y > maxy) {
            maxy = y;
        }
    }
    return [points, [minx, miny, maxx, maxy]];
}

// Re-sizes the polygon in the top node so that it stretches down to the
// bottom of the polygon in the bottom node.
function subsume_polygon(top_node, bot_node) {
    // Re-size desctop node
    // We grab the "desctop" and "descbot" nodes, extract the points from
    // their polygons, and then resize the desctop node so that it stretches
    // over both nodes (they're set up in graphviz to be laid out directly
    // above/below each other).
    let top_poly = top_node.querySelector("polygon");
    let bot_poly = bot_node.querySelector("polygon");
    let [top_points, toplimits] = extract_points_and_limits(top_poly);
    let [bot_points, botlimits] = extract_points_and_limits(bot_poly);

    // Take top points from top polygon + bottom points from bottom polygon:
    let tl, tr, bl, br;
    for (let [top_x, top_y] of top_points) {
        if (top_y == toplimits[1]) {
            if (top_x == toplimits[0]) {
                tl = [top_x, top_y];
            } else {
                tr = [top_x, top_y];
            }
        }
    }
    for (let [bot_x, bot_y] of bot_points) {
        if (bot_y != botlimits[1]) {
            if (bot_x == botlimits[0]) {
                bl = [bot_x, bot_y];
            } else {
                br = [bot_x, bot_y];
            }
        }
    }
    let new_points = [tl, tr, br, bl];

    // Construct a points attribute string for a new polygon
    let points_attr = "";
    for (let [x, y] of new_points) {
        points_attr += " " + x + "," + y;
    }

    // Remove bottom description node
    bot_node.parentNode.removeChild(bot_node);

    // Expand top description node with the new points
    top_poly.setAttribute("points", points_attr);
}

// Grab description nodes
let desctop = document.querySelector(".node.desc-top");
let descbot = document.querySelector(".node.desc-bot");

// Stretch description top polygon and dispose of bottom node
subsume_polygon(desctop, descbot);

// Remove title from desctop and make it no longer be a "node"
desctop.classList.remove("node");
desctop.removeChild(desctop.querySelector("title"));

// Now we hide the SVG polygon... (we need to keep it around to track
// window resizes, and it can't have display none because then
// getBoundingClientRect won't work).
desctop.style.opacity = 0;

// This function takes the #desc node and positions it exactly on top of
// the desctop polygon. To do that it uses getBoundingClientRect to
// figure out where that polygon is in HTML coordinates, and then it
// changes a bunch of style attributes to position the HTML node.
function reposition_node(target_node, place_onto) {
    // We can't actually nest a DIV or other HTML stuff inside of an SVG
    // group... but we can put it on top and give it the exact same
    // coordinates! T_T
    let desc_bcr = place_onto.getBoundingClientRect();

    // Absolute position will be relative to the parent, which we assume
    // has relative position
    let parent_bcr = target_node.parentNode.getBoundingClientRect();

    target_node.style.position = "absolute";
    target_node.style.left = (desc_bcr.x - parent_bcr.x) + "px";
    target_node.style.top = (desc_bcr.y - parent_bcr.y) + "px";
    target_node.style.width = desc_bcr.width + "px";
    target_node.style.height = desc_bcr.height + "px";
    target_node.style.boxSizing = "border-box";
}

// Initial call positions description properly at start
reposition_node(document.getElementById("desc"), desctop);

// TODO: Use % sizing to avoid this?
// Set up a listener to reposition description when the window size
// changes.
window.addEventListener("resize", function () {
    reposition_node(document.getElementById("desc"), desctop);
});

// Grab legend and stop it from being a node any more
let legend = document.querySelector(".node.legend-top");
legend.classList.add("legend");
legend.classList.remove("node");

// Strip off node polygon fill attributes so that CSS can set them.
for (let node_poly of document.querySelectorAll("g.node polygon")) {
    node_poly.removeAttribute("fill");
}

// Strip off font-size attributes
for (let node_text of document.querySelectorAll("g.node text")) {
    node_text.removeAttribute("font-size");
}


// Find graph structure from SVG contents:
let all_nodes = document.querySelectorAll("g.node");
let node_titles = document.querySelectorAll("g.node title");
let all_edges = document.querySelectorAll("g.edge");
let edge_titles = document.querySelectorAll("g.edge title");

let node_map = {};

for (let node of all_nodes) {
    node_map[node.firstElementChild.innerHTML] = node;
}

let graph_structure = {};

for (let title of node_titles) {
    graph_structure[title.innerHTML] = { "id": title.innerHTML, "edges": [] };
}

for (let edge_title of edge_titles) {
    // skip invisible edges
    if (edge_title.parentNode.classList.contains("invisible")) {
        continue;
    }
    let parts = edge_title.innerHTML.split("-&gt;");
    let fr = parts[0];
    let to = parts[1];
    graph_structure[fr].edges.push(to);
}

// Turn the legend nodes into a real legend
let legend_bot = document.querySelector(".node.legend-bot");
// Throw out middle node (only needed to ensure verticality?)
let legend_mid = document.querySelector(".node.legend-mid");
legend_mid.parentNode.removeChild(legend_mid);
subsume_polygon(legend, legend_bot);
let legend_polygon = legend.querySelector("polygon");
let [lpoints, llimits] = extract_points_and_limits(legend_polygon);
let lp_width = llimits[2] - llimits[0];
let lp_height = llimits[3] - llimits[1];
let legend_scale = lp_width / 100;

// How much to expand the legend on both the top and the bottom
let legend_expand = 0;

// Set up a translate on the legend group and re-position the legend
// rectangle so that it's easy to position other elements in the group
legend.setAttribute(
    "transform",
    "translate(" + llimits[0] + "," + (llimits[1] - legend_expand) + ")"
);
let points_attr = "";
for (let [x, y] of lpoints) {
    if (y == llimits[3]) {
        // it's a bottom point; move it down a bit
        y += 2*legend_expand;
    }
    points_attr += " " + (x - llimits[0]) + "," + (y - llimits[1]);
}
legend_polygon.setAttribute("points", points_attr);

let title = document.createElementNS("http://www.w3.org/2000/svg", "text");
title.setAttribute("x", 50 * legend_scale);
title.setAttribute("y", 4 * legend_scale);
title.setAttribute("text-anchor", "middle");
title.setAttribute("dominant-baseline", "hanging");
title.setAttribute("font-size", (14 * legend_scale) + "pt");
title.setAttribute("style", "font-weight: bold");
title.innerHTML = "Legend";
legend.appendChild(title);

function create_legend_text(desc, clas, y) {
    let elem = document.createElementNS("http://www.w3.org/2000/svg", "g");
    elem.classList.add("node");
    if (clas != "") {
        elem.classList.add(clas);
    }
    let backing = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "polygon"
    );
    let margin = 5;
    let points = [
        [margin, y],
        [100 - margin, y],
        [100 - margin, y + 16],
        [margin, y + 16],
    ];
    backing.setAttribute(
        "points",
        points.map(pair => pair.map(n => n * legend_scale).join(",")).join(" ")
    );
    backing.setAttribute("stroke", "black");
    elem.appendChild(backing);

    let text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.innerHTML = desc;
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("dominant-baseline", "hanging");
    text.setAttribute("x", 50 * legend_scale);
    text.setAttribute("y", (y + 2) * legend_scale);
    text.setAttribute("font-size", (12 * legend_scale) + "px"); // TODO: THIS?!?
    elem.appendChild(text);

    return elem;
}

function create_legend_edge(desc, clas, y) {
    let elem = document.createElementNS("http://www.w3.org/2000/svg", "g");
    elem.classList.add("edge");
    if (clas != "") {
        elem.classList.add(clas);
    }
    let edge = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let margin = 4;
    let top = [margin * legend_scale, y * legend_scale];
    let rmid = 9 * legend_scale;
    edge.setAttribute(
        "d",
        (
            "M" + top.join(",")
          + " q" + rmid + "," + 0 + " " + rmid + "," + rmid
          + " t" + rmid + "," + rmid
        )
    );
    edge.setAttribute("stroke-opacity", 1);
    edge.setAttribute("stroke-width", "1pt");
    edge.setAttribute("stroke", "#000000");
    edge.setAttribute("fill-opacity", 0);
    elem.appendChild(edge);

    let text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.innerHTML = desc;
    text.setAttribute("text-anchor", "start");
    text.setAttribute("dominant-baseline", "hanging");
    text.setAttribute("x", (margin + 20) * legend_scale);
    text.setAttribute("y", (y + 2) * legend_scale);
    text.setAttribute("font-size", (12 * legend_scale) + "px"); // TODO: THIS?!?
    elem.appendChild(text);
    return elem;
}

let y = 25;
let spacing = 20;
let notoffered = create_legend_text("Not offered", "notoffered", y);
legend.appendChild(notoffered);
let infall = create_legend_text("Fall semesters", "fall", y + spacing);
legend.appendChild(infall);
let inspring = create_legend_text("Spring semesters", "spring", y + 2*spacing);
legend.appendChild(inspring);
let both = create_legend_text("Both semesters", "", y + 3*spacing);
legend.appendChild(both);
let core = create_legend_text("Core course", "core", y + 4*spacing);
legend.appendChild(core);

let req = create_legend_edge("Requires", "", y + 5*spacing);
legend.appendChild(req);
let rec = create_legend_edge("Recommended", "recommended", y + 6*spacing);
legend.appendChild(rec);
let opt = create_legend_edge("Requires one", "option", y + 7*spacing);
legend.appendChild(opt);

// Returns an array containing all descendants of the specified node,
// along with that node itself as the first element of the result. Will
// enter an infinite recursion if there are circular paths in the graph.
function self_and_descendants(node_id) {
  let result = [ node_id ];
  for (let child of graph_structure[node_id].edges) {
      result = result.concat(self_and_descendants(child));
  }
  return result;
}

// Given a course ID, returns the URL to link to that course's website,
// in some cases defaulting to a department curriculum website (like for
// math courses).
function course_page_url(course_id) {
    // For custom course URLs:
    let course_info = get_course_info(course_id);

    if (course_info && course_info["url"]) {
        return course_info["url"];
    }

    if (course_id.startsWith("math")) {
        return "https://www.wellesley.edu/math/curriculum/current_offerings";
    } else if (course_id.startsWith("cs")) {
        return "https://cs.wellesley.edu/~" + course_id;
    } else {
        let dept_matches = /[a-z]+/.exec(course_id);
        let dept;
        if (dept_matches.length > 0) {
            dept = dept_matches[0];
        }
        if (dept) {
            return "https://www.wellesley.edu/" + dept + "/curriculum";
        } else {
            console.warn(`Unable to extract department from: '${course_id}'`);
            return "https://www.wellesley.edu/cs/curriculum";
        }
    }
}

// Fetches info from the 'info' variable (defined via concatenation in
// the template file, see build.py). Returns undefined if the info
// doesn't contain an entry for the given course ID.
function get_course_info(course_id) {
    return info[course_id];
}

// This function uses the 'info' and 'extra_info' variables (defined via
// concatenation in the template file, see build.py) to show course info
// in the #desc div.
function display_course_info(course_id, course_number) {
    // console.log(`course_id=${course_id}; course_number=${course_number}`);
    // Example: course_id='cs304', course_number='CS 304'
    let desc = document.getElementById("desc");

    // Clear out old description
    desc.innerHTML = "";

    let title = document.createElement("div");
    title.classList.add("course_title");
    desc.appendChild(title);

    let course_info = get_course_info(course_id);
    if (course_info == undefined) { // No info available
        desc.appendChild(document.createTextNode("No info available..."));
        return;
    }

    let title_link = document.createElement("a");
    let course_name = course_info['course_name'];
    let course_title = `${course_number}: ${course_name}`;

    title_link.innerText = course_title;
    title_link.href = course_page_url(course_id);
    title_link.target = course_id;
    title.appendChild(title_link);

    let term_div = document.createElement("div");
    term_div.classList.add("term_div");
    desc.appendChild(term_div);

    let term_info = course_info['term_info'];
    if (term_info === undefined) {
      term_div.innerHTML = "<i>Not offered in 2020-21</i>";
    } else { 
      let term_list = document.createElement("ul");
      term_list.classList.add("term_list");
      term_div.appendChild(term_list);
      let term_names = Object.keys(term_info);
      term_names.sort(); // Want them in order: (subsequence of) T1, T2, T3, T4
      for (let term_name of term_names) {
        let term_item = document.createElement("li");
        term_item.classList.add("term_item");
        term_list.appendChild(term_item);
        term_item.innerHTML = term_to_html(term_name, term_info[term_name]);
        
      }
    }

    /* // lyn sez: term info above supersedes prof info for 2020-21;
       // and may not want to include prof info for previous years.
    let profs = document.createElement("div");
    profs.classList.add("professors");
    desc.appendChild(profs);

    for (let [prof_name, prof_url] of course_info["professors"]) {
        let prof_link = document.createElement("a");
        prof_link.setAttribute("href", prof_url);
        prof_link.setAttribute("target", prof_name);
        prof_link.innerText = prof_name;
        profs.appendChild(prof_link);
        profs.appendChild(document.createTextNode(" "));
    } 
    */

    // Add standard info to the description
    for (
        let info_piece of [
            "distributions",
            "prereqs",
            "description",
        ]
    ) {
        let piece = document.createElement("div");
        piece.classList.add(info_piece);
        if (course_info.hasOwnProperty(info_piece)) {
            piece.innerText = course_info[info_piece];
        } else {
            piece.innerText = "Unknown " + info_piece;
        }
        desc.appendChild(piece);
    }

    // Add any notes and extra info
    /* TODO: This if we're getting accurate data...
    if (course_info.notes || course_info.extra_info) {
        let note_pieces = [];
        if (course_info.notes) {
            note_pieces.push(course_info.notes);
        }
        note_pieces = note_pieces.concat(course_info.extra_info);
        let notes = document.createElement("div");
        notes.classList.add("notes");
        notes.innerHTML = note_pieces.join("<br>\n");
        desc.appendChild(notes);
    }
    */
}

function term_to_html(term_name, term_dict) {
  let lects = term_dict['lecturers'];
  let ISLs = term_dict['lab_instructors'];
  if (ISLs.length == 0) {
    return `${term_name} ${instructors_to_html(term_name, lects)}`;
  } else {
    return (`${term_name} `
            + `<i>Lecturer${lects.length > 1 ? 's' : ''}:</i> `
            + `${instructors_to_html(term_name, lects)}; `
            + `<i>Lab Instructor${ISLs.length > 1 ? 's' : ''}:</i> `
            + `${instructors_to_html(term_name, ISLs)}`);
  }
}

function instructors_to_html(term_name, instrs) {
  function instructor_to_html(instr) {
    instr['modes'].sort();
    let modeInfo = ['T1', 'T2'].includes(term_name) ?
      ` (${instr['modes'].join(', ')})`
      : ' (TBD)'
      return `<a href=${instr['URL']}>${instr['name']}</a>${modeInfo}`;
  }
  return instrs.map(instructor_to_html).join(', ')
}
          
// Set up mouseover/mouseout handlers for each node
for (let node of all_nodes) {
    node.addEventListener("mouseover", function () {
        let node_id = node.firstElementChild.innerHTML;
        let course_title = (
            node.querySelectorAll("text")[0].innerHTML
        );
        display_course_info(node_id, course_title);
        let highlight = self_and_descendants(node_id);
        for (let node of all_nodes) {
            node.style.fillOpacity = 0.25;
            node.style.strokeOpacity = 0.25;
        }
        for (let edge of all_edges) {
            let from = edge.firstElementChild.innerHTML.split("-&gt;")[0];
            if (highlight.indexOf(from) >= 0) {
                edge.style.fillOpacity = 1;
                edge.style.strokeOpacity = 1;
            } else {
                edge.style.fillOpacity = 0.25;
                edge.style.strokeOpacity = 0.25;
            }
        }
        for (let desc of highlight) {
            let desc_node = node_map[desc];
            desc_node.style.fillOpacity = 1;
            desc_node.style.strokeOpacity = 1;
        }
    });
    node.addEventListener("mouseout", function () {
        let node_id = node.firstElementChild.innerHTML;
        for (let node of all_nodes) {
            node.style.fillOpacity = 1;
            node.style.strokeOpacity = 1;
        }
        for (let edge of all_edges) {
            edge.style.fillOpacity = 1;
            edge.style.strokeOpacity = 1;
        }
    });

    node.addEventListener("click", function () {
        let node_id = node.firstElementChild.innerHTML;
        let url = course_page_url(node_id);
        let classtab = window.open(
            url,
            node_id
        );
        // TODO: Does this work when cross-origin issues aren't in play?
        try {
            classtab.addEventListener("error", function () {
                classtab.location.assign(
                    "https://www.wellesley.edu/cs/curriculum"
                );
            });
        } catch (e) {
            // do nothing
        }
        classtab.focus();
    });
}
