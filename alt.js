// The following is a copy of Peter's code to recover to/from links
// I really should use that module, but I don't yet know how to use
// JS modules in that way.

console.log('loading alt');

// I think his code would have to export this function?

// Find graph structure from SVG contents:
function svg_to_graph() {
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
    return graph_structure;
}

// ================================================================
// My code. Retroactively add hyperlinks to prereqs and successors

// The graph structure is such that there are sometimes links from one
// course to its prerequisite, so if you look in graph_structure under
// cs203, you'll find a link to cs111. Most of the time, there's a
// link from a course to a node from which there are links to prereq
// courses, such as cs332 to cs112or230. For my version, I will
// "flatten" these.

// I'll also accumlate the info for adding successor links, but I
// haven't added those links yet.

var add_prereqs_log = true;	// whether to spew output messages

function add_prereqs(graph_structure, log) {
    log = log || add_prereqs_log;
    let successor_links = {};	// not used yet

    function add_prereq_link(course_elt, prereq) {
        let c = $(course_elt).attr('id');
        console.log(`${prereq} is a prereq of ${c}`);
        // all the jQuery code is here.
        let a = $("<a>").attr('href','#'+prereq).text(prereq);
        let td = $(course_elt).find(".prereqs");
        // prereq_links is a UL of hyperlinks like the one above.
        let pl = $(td).find('.prereq_links');
        if( pl.length == 0 ) {
            console.log(`creating UL for ${c}`);
            let ul = $('<ul>',{class: 'prereq_links'});
            $(td)
            .append('<span>links: </span>')
            .append(ul);
            pl = ul;
        } else {
            console.log('reusing existing list');
        }
        $('<li>').append(a).appendTo(pl);
    }

    // key is something like "cs111" or "cs231or235"
    for( let key in graph_structure ) {
	let course = graph_structure[key];
	let course_elt = document.getElementById(key);
	if( course_elt ) {
	    // something like cs111 will have a corresponding DOM element
	    // but cs230or220 will not, so we skip those
	    // edges is an array, so use "for .. of"
	    for( let prereq of course.edges ) {
		// prereq is also a string that is a key into the graph_structure
		let dest = document.getElementById(prereq);
		if( dest ) {
		    add_prereq_link(course_elt, prereq);
		} else {
		    // probably an intermediate "or" node.
		    // Iterate over the successors
		    console.log(`\tconsidering non_element ${prereq} from ${key}`);
		    let succ_node = graph_structure[prereq];
		    if(succ_node) {
			// again, edges is an array, so use "for .. of"
			for( let succ of succ_node.edges ) {
			    console.log(`\tsuccessor ${succ}`);
			    let dest = document.getElementById(succ);
			    if( dest ) {
				add_prereq_link(course_elt, succ);
			    }
			}
		    }
		}
	    }
	}
    }
}

window.addEventListener('DOMContentLoaded', (event) => {
    console.log('DOM fully loaded and parsed');
    let gs = svg_to_graph();
    add_prereqs(gs);
});


// Debugging code to remove
globalThis.svg_to_graph = svg_to_graph;
globalThis.add_prereqs = add_prereqs;
