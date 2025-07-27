Picasa Settings Utils
=====================

Utilities for working with Picasa database / settings files, 
as a precursor to porting years of edit-history from the discontinued
but handy Picasa photo management + non-destructive editing tool,
into more modern alternatives.


Usage
=====

To get a JSON Dump of a given folder's ".Picasa.ini", run the following Python script:
```shell
$ python3 picasa_loader.py [path/to/albumName/picasa.ini] > [output/dir/albumName.json]
```



References
==========

The following resources have been invaluable in developing these tools:
* [1] https://gist.github.com/fbuchinger/1073823/9986cc61ae67afeca2f4a2f984d7b5d4a818d4f0
  Notes on the Picasa.ini File Format

* [2] https://sites.google.com/site/picasaresources/picasa/how-picasa-works
  Community-driven site with lots of useful tidbits about how Picasa works
  and/or can be used.

* [3] https://github.com/ashaduri/embed_picasa_tags
  PHP script for converting face-tagging / other tags from Picasa.ini into
  per-file tags

* [4] https://superuser.com/questions/151146/what-file-format-database-format-does-picasa-use
  This is a treasure trove of links to info about the database format(s) that Picasa uses.

  * [4a] https://forensicir.blogspot.com/2007/07/picasa.html
    Notes about all the files, folders, and registry keys it uses (from 2007)
 
  * [4b] https://stackoverflow.com/questions/1467004/how-to-access-the-picasa-desktop-database/8482061#8482061
    General info about the Picasa database formats.
    
    Most pertinent tips:
    * thumbs.db is the standard "thumbs.db" format that Windows uses
      ** [4c] https://stackoverflow.com/questions/228304/is-there-any-c-lib-to-read-thumbnails-from-thumb-db-in-windows-folder
      ** [4d] https://vinetto.sourceforge.net/docs.html
    
    * PMP format contains a bunch of metadata not found in other files
      ** [4e] https://sbktech.blogspot.com/2011/12/picasa-pmp-format.html
   



Original Author
===============

Joshua Leung (@Aligorith)
July 2025
