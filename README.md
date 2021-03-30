# Textgen Blender addon

---

## Download/Installation

Installation on Linux and MacOS is straightforward, but on Windows you'll need to install a library manually.

1. Download the textgen.py file from this Github repository.
2. Open Blender and go to Edit > Preferences > Add-ons.
3. Click install and choose the downloaded textgen.py file.
4. Enable the addon.
    1. This will throw an error on Windows, so for installation on Windows you also do the following:
    2. Go to  Window > Toggle  system console
    3. You should see a command starting with *&* and separated by blank lines
    4. Copy that command
    5. Open powershell as **an administrator** and run that command
    6. If no red text appears everything should be okay.
5. Restart Blender.
6. The add-on should be installed and working now, if you're still getting errors please report them.

## Features

This add-on's main goal is to make it easy and fast to create text images without having to use external applications. It comes with a bunch of features which allow you to make any kind of text you want:

* Use aligment options
* Change the resolution of the image
* Control the line spacing
* Autodetection of installed fonts
* Generation of random text

# Usage

---

## Tutorial

[Tutorial](https://youtu.be/MezRjCmSSsg)

## Properties

This is a description of all properties of the textgen window(**located in the viewport sidebar**) from top to bottom. Please note that some of these properties will be visible or not depending on certain other settings.

### List of text items

Here you can select which text item you want to be modifying.
On the right there are three buttons which let you add, remove or duplicate a text item.

* Add: This adds a new text item to the list. Note that this will set the name of the file of the image to *TextGeneratorFile* followed by the current number of text items.

* Remove: Removes the currently selected text item if it is not the last one left.

* Duplicate: Creates a duplicate of the currently selected text item. Note that this will change the name of the file of the image to the file of the original text item followed by a number. If there was already a number at the end it will add one.

### Advanced mode

Toggle between advanced mode, disabled by default. Advanced mode will allow you to control the width and height of the image. It will add/replace some properties with the following properties:

* Text size: This replaces the resolution property, it should more or less be the width of each character in pixels.

* Wrap width/height: this allows you to determine the width or height of the image yourself by changing the value underneath or instead wrap it to the text(that's what happens in not advanced mode).

### Safetylock

Safetylock will disable the creation of the image when the resulting image would be too large because that could result in all of your RAM getting used by the image which is not good. If you disable this behavior you should be carefull with what you do(setting the resolution to 100 is not such a good idea for example). This property will flicker when it has prevented image creation. 

### Lines

Here you can edit the lines of your texts. It will show you all the lines of your text as text properties stacked on each other.  
There are two character combinations which will do something special:

* **\\n**: This will start a new line in the output text, this can be handy if you want to paste a lot of text at once, but it's not very handy if you want to edit the text later so it's better to just add a new line.
* **#R#CHARS:WIDTH:SEED#R#**: This allows you to insert randomly generated text into your text which can be very handy if you're trying to create a letter or if you want to have alinea's. To use this, you change the CHARS, WIDTH and SEED in the template to respectively: the total number of characters of generated text, the width of each line in characters and the seed of the text generation.

At the right of the lines there are three buttons: add, remove and ?

* Add: This lets you insert a line somewhere, when clicking this, a pop-up window will show up which will let you select the line where the new line should be inserted and also if it should be inserted after or before that line.

* Remove: This lets you remove a line, when clicking this, a pop-up window will show up, here you can select which line should be removed. Note that you can't remove the last line.

* **?**: This lets you toggle random text mode. When enabled, the text lines will be neglected and instead random text will be generated according to three properties that will show up.

    * Characters: This is the total length of the generated text in characters. Note that this will not be the exact number of the actual output text, but rather an approximation.

    * Text width: This is the length of each line in characters with a minimum of 16 characters.

    * Seed: The seed of the text generation, changing this will give you different words.

### Alignment method

Speaks for itself. Choose between left, center and right

### Fill

When enabled, this will change the spacing between each word of the line so that it matches the width of the image.

* Fill percentage: Percentage of the total image width which has to be occupied with text so that the method will fill the line with text, if not reached the line will be aligned according to the chosen alignment type.

### Resolution

This is the resolution of each character. It doesn't have to be increased when adding more text. Don't use a higher resolution than needed because this property has a very big influence on the size of the image.

### Line spacing

The amount of space between two lines, 1 is the default spacing, if you increase this value there will be more blank space between the lines. If you go below 1 it can result in the lines of your text overlapping each other.

### Font family

This property lets you choose between all the installed fonts on your system. This property will not be visible to mac users as font detection isn't supported there yet.

### Use font path

Toggle to choose if you want to use the font family selection or instead select a .ttf file yourself from your PC this is usefull if you have font files which aren't installed on your system. This property will not be visible to mac users, mac users can't switch between a font path or font family selection as font detection is not supported on MacOS so they will always have to use a font path.

### Font type

Choose between the installed types of the selected font family, this property will only be visible if not using a font path.

### Font weight(Only visible when using variable fonts)

Weight of the font, this value usually controls how bold the text is. A higher value will result in a bolder font. Look beneath for minimum, maximum and default value.

### File

This is the name of the .png file in which the generated image **will be stored in the directory in which the blend file is saved**. Don't put *.png* in this property, that will automatically be added. Note that when this value is changed, the add-on won't generate a duplicate file but instead rename the current one, it will also rename the loaded image in blender. 

### Add texture node

This adds an image texture node with the image to the current node tree. It will also set it to clip as that's probably the most used extension setting for text images.

## Reporting errors/bugs

If you encounter a bug or error while using this add-on please open an issue if it's not reported yet. In your issue please say what operating system you are using and describe to bug or how to reproduce the error, the info of your system console is also handy.

## Contributing

For now, I think I'll try fix the issues on Windows and Linux myself, but I don't have a MacOS system so I can't realyy test it there. That's also the reason why font detection is not supported on MacOS. If you think a features should be added please send me an email: kwikandkwak@gmail.com

### Font detection on MacOS

If you're a MacOS user and you think you can code. Here's a project for you: what I need is a function that returns a dictionary of the following form: *{"Font family": {"type1":"path/to/font.ttf", "type2":"path/to/font.ttf", ...}, "Font family2": {"type1:"path/to/font.tff", "type2":"path/to/font.tff",...}, ... }*

If you made a function like that please send it to my email, I'll take a look at it and if I think it works I'll implement it. Note that the function should preferably not use external python modules.
