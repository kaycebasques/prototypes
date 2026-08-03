import json
from docutils import nodes
from typing import Any, Dict
from sphinx.application import Sphinx
from sphinx.environment.adapters.toctree import global_toctree_for_doc

def extract_panes(toctree_node, app, pagename):
    nav_panes = []
    root_doc = app.config.root_doc
    root_href = app.builder.get_relative_uri(pagename, root_doc)
    root_is_current = (pagename == root_doc)
    
    def process_list(bullet_list, current_id, current_title, current_href, current_is_current, parent_id, parent_title):
        pane = {
            "id": current_id,
            "parent": None if parent_id is None else {"id": parent_id, "title": parent_title},
            "title": current_title,
            "href": current_href,
            "is_current": current_is_current,
            "children_links": []
        }
        
        for list_item in bullet_list.children:
            para = list_item.children[0]
            # Some entries might not have a reference (e.g., plain text), but for a toctree they usually do.
            if not para.children:
                continue
            ref = para.children[0]
            if not isinstance(ref, nodes.reference):
                continue
                
            title = ref.astext()
            href = ref.attributes.get('refuri', '')
            is_current = bool(ref.attributes.get('iscurrent', False)) or (href == '')
            node_id = title.replace(' ', '-').lower()
            
            # Ignore self-references in toctree (e.g. `self`) since pane title handles current doc
            if node_id == current_id:
                continue

            nested_bullet_list = None
            for child in list_item.children[1:]:
                if isinstance(child, nodes.bullet_list):
                    nested_bullet_list = child
                    break
            
            has_children = nested_bullet_list is not None
            
            pane["children_links"].append({
                "id": node_id,
                "title": title,
                "href": href,
                "has_children": has_children,
                "is_current": is_current
            })
            
            if has_children:
                process_list(
                    nested_bullet_list,
                    current_id=node_id,
                    current_title=title,
                    current_href=href,
                    current_is_current=is_current,
                    parent_id=current_id,
                    parent_title=current_title
                )
                
        nav_panes.append(pane)

    if toctree_node and len(toctree_node) > 0:
        first_child = toctree_node[0]
        if isinstance(first_child, nodes.bullet_list):
            process_list(first_child, "root", "root", root_href, root_is_current, None, None)

    # Identify which pane should be visible by default on initial page load (.active-pane).
    # A pane is active if it directly represents the current document or contains a child link to it.
    active_pane_found = False
    active_pane_id = None
    for pane in nav_panes:
        if pane.get("is_current") or any(c.get("is_current") for c in pane.get("children_links", [])):
            pane["is_active_pane"] = True
            active_pane_found = True
            active_pane_id = pane["id"]
            break

    # Fallback to root pane if no specific subpane matched
    if not active_pane_found and nav_panes:
        for pane in nav_panes:
            if pane["id"] == "root":
                pane["is_active_pane"] = True
                active_pane_id = "root"
                break

    # Build parent map and compute ancestor lists for proper slide transition directions
    parent_map = {p["id"]: (p["parent"]["id"] if p["parent"] else None) for p in nav_panes}
    for pane in nav_panes:
        ancestors = []
        curr = parent_map.get(pane["id"])
        while curr:
            ancestors.append(curr)
            curr = parent_map.get(curr)
        pane["ancestors"] = ancestors

    # Flag ancestors of the active pane for initial page load positioning (positioned off-screen to the left)
    active_ancestors = set()
    curr = parent_map.get(active_pane_id)
    while curr:
        active_ancestors.add(curr)
        curr = parent_map.get(curr)

    for pane in nav_panes:
        pane["is_ancestor_of_active"] = pane["id"] in active_ancestors

    return nav_panes

import os
from jinja2 import Environment, FileSystemLoader

def on_html_page_context(app, pagename, templatename, context, doctree):
    # Retrieve global toctree relative to the current page
    result = global_toctree_for_doc(app.env, pagename, app.builder)
    panes = extract_panes(result, app, pagename)
    context['nav_panes'] = panes
    
    # Generate standalone nav.html once during the build of 'index'
    if pagename == app.config.root_doc:
        env = Environment(loader=FileSystemLoader(os.path.join(app.srcdir, '_templates')))
        template = env.get_template('custom_nav.html')
        rendered = template.render(nav_panes=panes)
        
        out_path = os.path.join(app.builder.outdir, 'nav.html')
        with open(out_path, 'w') as f:
            f.write(rendered)

def setup(app: Sphinx) -> Dict[str, Any]:
    print("[toctree extension] Initialized custom extension!")
    app.connect('html-page-context', on_html_page_context)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
