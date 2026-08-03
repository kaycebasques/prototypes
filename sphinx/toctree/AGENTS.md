# toctree

this is a prototype for understanding how to programmatically extract and
transform sphinx toctree data. 

## background

the end goal is to generate a custom site navigation ui. we will use a sphinx
extension to extract and transform the toctree data. the sphinx project in this
repo merely exists to provide an example of sufficiently complex toctree data.

the desired end goal is to generate the nav HTML as a flat list of
siblings. something like this:

```
<div id="root">
  <ul>
    <li><a href=".">root</a></li>
    <li><a href="#a">a</a></li>
    <li><a href="#b">b</a></li>
  </ul>
</div>
<div id="a" hidden>
  <ul>
    <li><a href="#root">root</a></li>
    <li><a href="a/index.html">a</a></li>
    <li><a href="#c">c</a></li>
  </ul>
</div>
…
```

assuming that you're currently on the root doc, you see the `#root` level of
the nav only. clicking `#a` would reveal the next level of the site nav,
as represented by the toctree data in `a/index.rst`. and so on.

## build

```
./build.sh
```

## serve

```
./serve.sh
```

## data

Printing the result of `global_toctree_for_doc` produces pseudo-XML like this:

```xml
<compact_paragraph toctree="1">
  <bullet_list>
    <list_item classes="toctree-l1">
      <compact_paragraph classes="toctree-l1">
        <reference anchorname="" internal="1" refuri="a/index.html">
          a
        </reference>
      </compact_paragraph>
      <bullet_list>
        <list_item classes="toctree-l2">
          <compact_paragraph classes="toctree-l2">
            <reference anchorname="" internal="1" refuri="a/c/index.html">
              c
            </reference>
          </compact_paragraph>
          <bullet_list>
            <list_item classes="toctree-l3">
              <compact_paragraph classes="toctree-l3">
                <reference anchorname="" internal="1" refuri="a/c/e/index.html">
                  e
                </reference>
              </compact_paragraph>
            </list_item>
            <list_item classes="toctree-l3">
              <compact_paragraph classes="toctree-l3">
                <reference anchorname="" internal="1" refuri="a/c/f/index.html">
                  f
                </reference>
              </compact_paragraph>
            </list_item>
          </bullet_list>
        </list_item>
      </bullet_list>
    </list_item>
    <list_item classes="toctree-l1">
      <compact_paragraph classes="toctree-l1">
        <reference anchorname="" internal="1" refuri="b/index.html">
          b
        </reference>
      </compact_paragraph>
      <bullet_list>
        <list_item classes="toctree-l2">
          <compact_paragraph classes="toctree-l2">
            <reference anchorname="" internal="1" refuri="b/d/index.html">
              d
            </reference>
          </compact_paragraph>
        </list_item>
        <list_item classes="toctree-l2">
          <compact_paragraph classes="toctree-l2">
            <reference anchorname="" internal="0" refuri="https://example.com">
              external
            </reference>
          </compact_paragraph>
        </list_item>
      </bullet_list>
    </list_item>
  </bullet_list>
</compact_paragraph>
```

## implementation details

*   **Extraction:** We established a custom Sphinx extension (`_extensions/toctree.py`) that hooks into `html-page-context`, reads the deep Docutils `toctree` tree via `global_toctree_for_doc`, and flattens it down into an easy-to-render array of `nav_panes`.
*   **Templating:** We implemented a Jinja template at `_templates/custom_nav.html` that generates the flat HTML `div` siblings matching the desired final output.
*   **Transitions (CSS Only):** We completely avoided JavaScript for pane interactions. We dropped the `hidden` attribute in favor of a purely CSS-based solution leveraging the pseudo-classes `:target` (to listen to URL hash changes) and `:has()` (to hide the `#root` pane when children are targeted). This effortlessly yields a performant sliding panel UX.
*   **Verification:** Specifically to simplify inspection of this navigation artifact, our `toctree.py` script dumps an unadulterated standalone version of the resulting HTML to `_build/html/nav.html` during the build process.
