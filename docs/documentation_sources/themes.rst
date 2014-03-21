Creating Themes for Tavern
==========================

Creating a Theme for Tavern is pretty simple, but be warned-

Significant changes are present in various releases, and the interface is by no means stable.
This means that if you create a theme, you'll want to rebase before the next release.

To create one, copy the "themes/default" directory, to your own name.
You'll also want to copy "static/css/style-default.css" to "static/css/style-YOURNAME.css"

Then, just edit the new CSS you made, and change the templates in your theme folder.
The server will detect that there are multiple options in place, and automatically display them to the user in their preferences page.

