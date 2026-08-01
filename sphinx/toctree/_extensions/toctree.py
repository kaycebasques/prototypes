import json
from docutils import nodes
from typing import Any, Dict
from sphinx.application import Sphinx
from sphinx.environment.adapters.toctree import global_toctree_for_doc

def extract_panes(toctree_node):
    nav_panes = []
    
    def process_list(bullet_list, current_id, current_title, current_href, parent_id, parent_title):
        pane = {
            "id": current_id,
            "parent": None if parent_id is None else {"id": parent_id, "title": parent_title},
            "title": current_title,
            "href": current_href,
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
            node_id = title.replace(' ', '-').lower()
            
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
                "has_children": has_children
            })
            
            if has_children:
                process_list(
                    nested_bullet_list,
                    current_id=node_id,
                    current_title=title,
                    current_href=href,
                    parent_id=current_id,
                    parent_title=current_title
                )
                
        nav_panes.append(pane)

    if toctree_node and len(toctree_node) > 0:
        first_child = toctree_node[0]
        if isinstance(first_child, nodes.bullet_list):
            process_list(first_child, "root", "root", ".", None, None)
            
    return nav_panes

import os
from jinja2 import Environment, FileSystemLoader

def on_html_page_context(app, pagename, templatename, context, doctree):
    # Retrieve global toctree relative to the current page
    result = global_toctree_for_doc(app.env, pagename, app.builder)
    panes = extract_panes(result)
    context['nav_panes'] = panes
    
    # Generate standalone nav.html once during the build of 'index'
    if pagename == 'index':
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
