// jshint esversion: 6
// jshint -W014
// jshint -W083
// jshint -W097
/* globals document, console, window, info */

"use strict";

// Extracts an array of x/y floating-point position value pairs, plus an
// array containing the minimum x and y values from an SVG polygon node.
function extract_points_and_mins(polygon_node) {
    let points = [];
    let minx, miny;
    for (let coords of polygon_node.getAttribute("points").split(" ")) {
        let [x, y] = coords.split(",");
        x = parseFloat(x);
        y = parseFloat(y);
        points.push([x, y]);
        if (minx == undefined || x < minx) {
            minx = x;
        }
        if (miny == undefined || y < miny) {
            miny = y;
        }
    }
    return [points, [minx, miny]];
}

// Re-size desctop node
// We grab the "desctop" and "descbot" nodes, extract the points from
// their polygons, and then resize the desctop node so that it stretches
// over both nodes (they're set up in graphviz to be laid out directly
// above/below each other).
let desctop = document.querySelector("g.node.desc-top");
let descbot = document.querySelector("g.node.desc-bot");
let top_poly = desctop.querySelector("polygon");
let bot_poly = descbot.querySelector("polygon");
let [top_points, topmin] = extract_points_and_mins(top_poly);
let [bot_points, botmin] = extract_points_and_mins(bot_poly);

// Take top points from top polygon + bottom points from bottom polygon:
let tl, tr, bl, br;
for (let [top_x, top_y] of top_points) {
    if (top_y == topmin[1]) {
        if (top_x == topmin[0]) {
            tl = [top_x, top_y];
        } else {
            tr = [top_x, top_y];
        }
    }
}
for (let [bot_x, bot_y] of bot_points) {
    if (bot_y != botmin[1]) {
        if (bot_x == botmin[0]) {
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
descbot.parentNode.removeChild(descbot);

// Expand top description node with the new points
top_poly.setAttribute("points", points_attr);

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
function position_description() {
    // We can't actually nest a DIV or other HTML stuff inside of an SVG
    // group... but we can put it on top and give it the exact same
    // coordinates! T_T
    let desc_bcr = desctop.getBoundingClientRect();

    // Specific position for the description element on top of the SVG:
    let desc = document.getElementById("desc");
    desc.style.position = "absolute";
    desc.style.left = desc_bcr.x + "px";
    desc.style.top = desc_bcr.y + "px";
    desc.style.width = desc_bcr.width + "px";
    desc.style.height = desc_bcr.height + "px";
    desc.style.boxSizing = "border-box";
}

// Initial call positions description properly at start
position_description();

// TODO: Use % sizing to avoid this?
// Set up a listener to reposition description when the window size
// changes.
window.addEventListener("resize", function () {
    position_description();
});

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

// Add a legend in the upper-left
// TODO: Automatic placement of the legend (use proxy nodes like the
// description does)
let legend_scale = 1.0;
let legend = document.createElementNS("http://www.w3.org/2000/svg", "g");
legend.classList.add("legend");
legend.setAttribute("transform", "translate(8, 8)");
let svg = document.querySelectorAll("svg")[0];
svg.appendChild(legend);

let backing = document.createElementNS("http://www.w3.org/2000/svg", "rect");
backing.setAttribute("x", 0);
backing.setAttribute("y", 0);
backing.setAttribute("width", 100 * legend_scale);
backing.setAttribute("height", 187 * legend_scale);
backing.setAttribute("stroke", "black");
backing.setAttribute("fill-opacity", 0);
legend.appendChild(backing);

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
    let course_info = merge_course_info(course_id);

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

// Merges info from the 'info' and 'extra_info' variables (defined via
// concatenation in the template file, see build.py) into a single info
// dictionary for a course. Values from extra_info override entries from
// info on a per-field basis. Returns undefined if neither the normal
// info nor the extra info contain an entry for the given course ID.
function merge_course_info(course_id) {
    let result = {};
    let main_info = info[course_id];
    let alt_info = extra_info[course_id];
    if (main_info != undefined) {
        for (let k of Object.keys(main_info)) {
            result[k] = main_info[k];
        }
    }
    if (alt_info != undefined) {
        for (let k of Object.keys(alt_info)) {
            result[k] = alt_info[k];
        }
    }

    if (Object.keys(result).length > 0) {
        return result;
    } else {
        return undefined;
    }
}

// This function uses the 'info' and 'extra_info' variables (defined via
// concatenation in the template file, see build.py) to show course info
// in the #desc div.
function display_course_info(course_id, course_title) {
    let desc = document.getElementById("desc");

    // Clear out old description
    desc.innerHTML = "";

    let title = document.createElement("div");
    title.classList.add("course_title");
    desc.appendChild(title);

    let title_link = document.createElement("a");
    title_link.innerText = course_title;
    title_link.href = course_page_url(course_id);
    title_link.target = course_id;
    title.appendChild(title_link);

    let course_info = merge_course_info(course_id);
    if (course_info == undefined) { // No info available
        desc.appendChild(document.createTextNode("No info available..."));
        return;
    }

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
