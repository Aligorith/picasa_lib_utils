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

* [2] https://sites.google.com/site/picasaresources/picasa/how-picasa-works



Original Author
===============

Joshua Leung (@Aligorith)
July 2025
