= Introduction =

  >>> from bs4 import BeautifulSoup
  >>> soup = BeautifulSoup("<p>Some<b>bad<i>HTML")
  >>> print soup.prettify()
  <html>
   <body>
    <p>
     Some
     <b>
      bad
      <i>
       HTML
      </i>
     </b>
    </p>
   </body>
  </html>
  >>> soup.find(text="bad")
  u'bad'

  >>> soup.i
  <i>HTML</i>

  >>> soup = BeautifulSoup("<tag1>Some<tag2/>bad<tag3>XML", "xml")
  >>> print soup.prettify()
  <?xml version="1.0" encoding="utf-8">
  <tag1>
   Some
   <tag2 />
   bad
   <tag3>
    XML
   </tag3>
  </tag1>

= About Beautiful Soup 4 =

This is a nearly-complete rewrite that removes Beautiful Soup's custom
HTML parser in favor of a system that lets you write a little glue
code and plug in any HTML or XML parser you want.

Beautiful Soup 4.0 comes with glue code for four parsers:

 * Python's standard HTMLParser
 * lxml's HTML and XML parsers
 * html5lib's HTML parser

HTMLParser is the default, but I recommend you install one of the
other parsers, or you'll have problems handling real-world markup.

== The module name has changed ==

Previously you imported the BeautifulSoup class from a module also
called BeautifulSoup. To save keystrokes and make it clear which
version of the API is in use, the module is now called 'bs4':

    >>> from bs4 import BeautifulSoup

== It works with Python 3 ==

Beautiful Soup 3.1.0 worked with Python 3, but the parser it used was
so bad that it barely worked at all. Beautiful Soup 4 works with
Python 3, and since its parser is pluggable, you don't sacrifice
quality.

Special thanks to Thomas Kluyver for getting Python 3 support to the
finish line.

== Better method names ==

Methods and attributes have been renamed to comply with PEP 8. The old names
still work. Here are the renames:

 * replaceWith -> replace_with
 * replaceWithChildren -> replace_with_children
 * findAll -> find_all
 * findAllNext -> find_all_next
 * findAllPrevious -> find_all_previous
 * findNext -> find_next
 * findNextSibling -> find_next_sibling
 * findNextSiblings -> find_next_siblings
 * findParent -> find_parent
 * findParents -> find_parents
 * findPrevious -> find_previous
 * findPreviousSibling -> find_previous_sibling
 * findPreviousSiblings -> find_previous_siblings
 * nextSibling -> next_sibling
 * previousSibling -> previous_sibling

Methods have been renamed for compatibility with Python 3.

 * Tag.has_key() -> Tag.has_attr()

   (This was misleading, anyway, because has_key() looked at
   a tag's attributes and __in__ looked at a tag's contents.)

Some attributes have also been renamed:

 * Tag.isSelfClosing -> Tag.is_empty_element
 * UnicodeDammit.unicode -> UnicodeDammit.unicode_markup
 * Tag.next -> Tag.next_element
 * Tag.previous -> Tag.previous_element

So have some arguments to popular methods:

 * BeautifulSoup(parseOnlyThese=...) -> BeautifulSoup(parse_only=...)
 * BeautifulSoup(fromEncoding=...) -> BeautifulSoup(from_encoding=...)

== Generators are now properties ==

The generators have been given more sensible (and PEP 8-compliant)
names, and turned into properties:

 * childGenerator() -> children
 * nextGenerator() -> next_elements
 * nextSiblingGenerator() -> next_siblings
 * previousGenerator() -> previous_elements
 * previousSiblingGenerator() -> previous_siblings
 * recursiveChildGenerator() -> recursive_children
 * parentGenerator() -> parents

So instead of this:

 for parent in tag.parentGenerator():
     ...

You can write this:

 for parent in tag.parents:
     ...

(But the old code will still work.)

== tag.string is recursive ==

tag.string now operates recursively. If tag A contains a single tag B
and nothing else, then A.string is the same as B.string. So:

<a><b>foo</b></a>

The value of a.string used to be None, and now it's "foo".

== Empty-element tags ==

Beautiful Soup's handling of empty-element tags (aka self-closing
tags) has been improved, especially when parsing XML. Previously you
had to explicitly specify a list of empty-element tags when parsing
XML. You can still do that, but if you don't, Beautiful Soup now
considers any empty tag to be an empty-element tag.

The determination of empty-element-ness is now made at runtime rather
than parse time. If you add a child to an empty-element tag, it stops
being an empty-element tag.

== Entities are always converted to Unicode ==

An HTML or XML entity is always converted into the corresponding
Unicode character. There are no longer any smartQuotesTo or
convertEntities arguments. (Unicode, Dammit still has smart_quotes_to,
but its default is now to turn smart quotes into Unicode.)

== CDATA sections are normal text, if they're understood at all. ==

Currently, the lxml and html5lib HTML parsers ignore CDATA sections in
markup:

 <p><![CDATA[foo]]></p> => <p></p>

A future version of html5lib will turn CDATA sections into text nodes,
but only within tags like <svg> and <math>:

 <svg><![CDATA[foo]]></svg> => <p>foo</p>

The default XML parser (which uses lxml behind the scenes) turns CDATA
sections into ordinary text elements:

 <p><![CDATA[foo]]></p> => <p>foo</p>

In theory it's possible to preserve the CDATA sections when using the
XML parser, but I don't see how to get it to work in practice.

== Miscellaneous other stuff ==

If the BeautifulSoup instance has .is_xml set to True, an appropriate
XML declaration will be emitted when the tree is transformed into a
string:

    <?xml version="1.0" encoding="utf-8">
    <markup>
     ...
    </markup>

The ['lxml', 'xml'] tree builder sets .is_xml to True; the other tree
builders set it to False. If you want to parse XHTML with an HTML
parser, you can set it manually.
