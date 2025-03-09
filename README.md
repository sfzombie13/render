# render
takes a report in docx format and makes an html webpage or of it.
uses pandoc, jinja2, docx, and beautifulsoup to extract text and inline
images from a docx report and places them into a temporary html file for
the text and a media folder for the images.  then it takes the html and 
uses the jinja2 template to create a webpage with the exact structure of
the docx report.  the images have to be inline and the header section has
to use the formatted header in the style section of word.   
