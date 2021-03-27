bl_info = {
    "name": "TextGen",
    "blender": (2, 80, 0),
    "category": "Node",
    }

import bpy
import sys
import os
import time
import random
import subprocess

from bpy.props import StringProperty, PointerProperty, IntProperty, BoolProperty, FloatProperty, CollectionProperty, EnumProperty

from bpy.types import PropertyGroup, Operator

from bpy.app.handlers import persistent


fonts = {}
latest_error = 0
no_update = False
warning_animation = True


def install_pillow():
    # You need administrator rights to install pillow in Windows
    # so that has to be done manually
    prefix = sys.exec_prefix
    if sys.platform != "win32":
        blender_python_path = prefix + "/bin/python3.7m"
        os.system(blender_python_path + " -m ensurepip")
        os.system(blender_python_path + " -m pip install Pillow")
    else:
        blender_python_path = prefix + "/bin/python"
        os.system('"' + blender_python_path + '"' + " -m ensurepip")
        user_command = "& " + '"' + blender_python_path + '"' + " -m pip install Pillow" + " --target=" + '"' + prefix + "/lib" + '"'
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!WARNING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\nYour using Windows ): so you have to install pillow manually, do this by opening powershell as administrator and running the following command:\n\n")
        print(user_command + "\n\nAfter having done this, restart blender and you're good to go!\n\n")


try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    install_pillow()
    from PIL import Image, ImageDraw, ImageFont


def text_changed_now_refresh(self, context):
    global latest_error

    # Don't update when duplicating a text item
    if no_update:
        return None

    textgen = bpy.context.scene.textgen
    item = textgen.textitems[textgen.selected]

    # When font family is changed, font type can get empty because enum
    # pointer is too large for type options length
    if item.font_type == "":
        item.font_type = get_enums(self, context)[0][0]

    # Show first line of the text item in the selection menu
    item.name = item.lines[0].text

    text = get_text(item)

    if not item.use_font_path:
        font_path = fonts[item.font_family][1][item.font_type]
    # Abort if font path is invalid
    elif (".ttf" not in item.font_path and item.font_path) or (not item.font_path and sys.platform == "darwin"):
        return None
    else:
        # If font path is empty, set the path of the selected font
        if item.font_path == "":
            item.font_path = fonts[item.font_family][1][item.font_type]
        font_path = item.font_path

    # Prepare text to draw
    text_draws, font, max_x, max_y = prepare_text(item, text, font_path)

    # Check for safetylock and create image
    if max_x * max_y > 10**8 and textgen.safetylock:
        latest_error = time.time()
    else:
        create_img(text_draws, font, max_x, max_y, item)
        latest_error = 0

    # Keep track of what the previous image file was for renaming
    item.old_image_file = item.image_file

    # (Re)load image
    refresh_image(item.image_file)


# If image file gets changed rename file on disk and in Blender
def rename(self, context):
    textgen = context.scene.textgen
    item = textgen.textitems[textgen.selected]
    blender_path = '/'.join(bpy.data.filepath.replace("\\", "/").split("/")[:-1])
    if item.old_image_file + ".png" not in bpy.data.images:
        # If image file doesn't exist, create one
        text_changed_now_refresh(None, None)
    else:
        os.rename(blender_path + "/" + item.old_image_file + ".png", blender_path + "/" + item.image_file + ".png")
        bpy.data.images[item.old_image_file + ".png"].filepath = blender_path + "/" + item.image_file + ".png"
        bpy.data.images[item.old_image_file + ".png"].name = item.image_file + ".png"
    item.old_image_file = item.image_file


# If font family changed. Set type to regular first
def font_changed(self, context):
    textgen = context.scene.textgen
    item = textgen.textitems[textgen.selected]
    types = fonts[item.font_family][1]
    if "Regular" in types:
        item.font_type = "Regular"
    else:
        item.font_type = next(iter(types))

def get_text(item):
    if item.use_random_text:
        text = get_random_text(item.random_length, item.random_width, item.seed)
    else:
        # Add all lines together and check for the appearance of
        # #R#CHARS:LENGTH:SEED#R# and replace with random text
        text = ""
        for i in range(len(item.lines)):
            line = item.lines[i].text
            parts = line.split("#R#")
            for j in range(1, len(parts), 2):
                try:
                    arguments = parts[j].split(":")
                    parts[j] = get_random_text(int(arguments[0]), int(arguments[1]), int(arguments[2]))
                except (ValueError, IndexError):
                    pass
            if i != 0:
                text += "\\n"
            text += "".join(parts)
    return text


# Function which generates real looking text
def get_random_text(length, width, seed):
    random.seed(seed)

    # Words and sentence structures to use for generation
    words = {2: ['as', 'he', 'on', 'be', 'at', 'by', 'is', 'it', 'or', 'of', 'to', 'in', 'we', 'do', 'if', 'an', 'us', 'me', 'up', 'so', 'go', 'no', 'my', 'oh', 'am'], 1: ['I', 'a'], 3: ['his', 'was', 'for', 'are', 'one', 'hot', 'but', 'you', 'had', 'the', 'and', 'can', 'out', 'how', 'set', 'air', 'end', 'put', 'add', 'big', 'act', 'why', 'ask', 'men', 'off', 'try', 'any', 'new', 'get', 'man', 'our', 'say', 'low', 'boy', 'old', 'too', 'she', 'all', 'use', 'way', 'her', 'see', 'him', 'two', 'has', 'day', 'did', 'who', 'may', 'now', 'own', 'sun', 'eye', 'let', 'saw', 'far', 'sea', 'run', 'few', 'eat', 'cut', 'got', 'car', 'red', 'dog', 'top', 'dry', 'ago', 'ran', 'hot', 'yes', 'fly', 'cry', 'box', 'six', 'ten', 'war', 'lay', 'map', 'bed', 'egg', 'art', 'ice', 'yet', 'arm', 'sit', 'leg', 'sky', 'joy', 'sat', 'cow', 'job', 'fun', 'gas', 'row', 'die', 'bad', 'oil', 'mix', 'fit', 'ear', 'son', 'pay', 'age', 'lot', 'key', 'buy', 'cat', 'law', 'bit', 'lie', 'hit', 'bat', 'rub', 'tie', 'gun', 'fat', 'dad', 'bar', 'log', 'fig', 'led', 'win', 'nor', 'hat'], 4: ['that', 'with', 'they', 'have', 'this', 'from', 'word', 'what', 'some', 'were', 'time', 'will', 'said', 'each', 'tell', 'does', 'want', 'well', 'also', 'play', 'home', 'read', 'hand', 'port', 'even', 'land', 'here', 'must', 'high', 'such', 'went', 'kind', 'need', 'near', 'self', 'work', 'part', 'take', 'made', 'live', 'back', 'only', 'year', 'came', 'show', 'good', 'give', 'name', 'very', 'just', 'form', 'help', 'line', 'turn', 'much', 'mean', 'move', 'same', 'when', 'your', 'many', 'then', 'them', 'like', 'long', 'make', 'look', 'more', 'come', 'most', 'over', 'know', 'than', 'call', 'down', 'side', 'been', 'find', 'head', 'page', 'grow', 'food', 'four', 'keep', 'last', 'city', 'tree', 'farm', 'hard', 'draw', 'left', 'late', 'real', 'life', 'book', 'took', 'room', 'idea', 'fish', 'stop', 'once', 'base', 'hear', 'sure', 'face', 'wood', 'main', 'open', 'seem', 'next', 'walk', 'ease', 'both', 'mark', 'mile', 'feet', 'care', 'girl', 'ever', 'list', 'feel', 'talk', 'bird', 'soon', 'body', 'pose', 'song', 'door', 'wind', 'ship', 'area', 'half', 'rock', 'fire', 'told', 'knew', 'pass', 'king', 'inch', 'stay', 'full', 'blue', 'deep', 'moon', 'foot', 'busy', 'test', 'boat', 'gold', 'game', 'miss', 'heat', 'snow', 'tire', 'fill', 'east', 'unit', 'town', 'fine', 'fall', 'lead', 'dark', 'note', 'wait', 'plan', 'star', 'noun', 'rest', 'able', 'done', 'week', 'gave', 'warm', 'free', 'mind', 'tail', 'fact', 'best', 'hour', 'true', 'five', 'step', 'hold', 'west', 'fast', 'verb', 'sing', 'less', 'slow', 'love', 'road', 'rain', 'rule', 'pull', 'cold', 'hunt', 'ride', 'cell', 'pick', 'size', 'vary', 'pair', 'felt', 'ball', 'wave', 'drop', 'wide', 'sail', 'race', 'lone', 'wall', 'wish', 'wild', 'kept', 'edge', 'sign', 'past', 'soft', 'bear', 'hope', 'gone', 'trip', 'seed', 'tone', 'join', 'lady', 'yard', 'rise', 'blow', 'grew', 'cent', 'team', 'wire', 'cost', 'lost', 'wear', 'sent', 'fell', 'flow', 'fair', 'bank', 'save', 'else', 'case', 'kill', 'lake', 'loud', 'milk', 'tiny', 'cool', 'poor', 'iron', 'flat', 'skin', 'hole', 'jump', 'baby', 'meet', 'root', 'push', 'held', 'hair', 'cook', 'burn', 'hill', 'safe', 'type', 'copy', 'tall', 'sand', 'soil', 'roll', 'beat', 'view', 'rich', 'noon', 'crop', 'ring', 'atom', 'bone', 'rail', 'thus', 'wing', 'wash', 'corn', 'poem', 'bell', 'meat', 'tube', 'fear', 'thin', 'mine', 'send', 'dead', 'spot', 'suit', 'lift', 'rose', 'post', 'glad', 'duck', 'dear', 'path', 'neck', 'huge', 'coat', 'mass', 'card', 'band', 'rope', 'slip', 'feed', 'tool', 'seat', 'sell', 'deal', 'swim', 'term', 'wife', 'shoe', 'camp', 'born', 'nine', 'shop', 'gray', 'salt', 'nose'], 5: ['other', 'which', 'their', 'three', 'small', 'large', 'spell', 'light', 'house', 'again', 'point', 'world', 'build', 'earth', 'place', 'where', 'after', 'round', 'every', 'under', 'great', 'think', 'cause', 'right', 'there', 'about', 'write', 'would', 'these', 'thing', 'could', 'sound', 'water', 'first', 'stand', 'found', 'study', 'still', 'learn', 'plant', 'cover', 'state', 'never', 'cross', 'start', 'might', 'story', 'don’t', 'while', 'press', 'close', 'night', 'north', 'carry', 'began', 'horse', 'watch', 'color', 'white', 'begin', 'paper', 'group', 'music', 'those', 'often', 'until', 'river', 'plain', 'usual', 'young', 'ready', 'above', 'leave', 'black', 'short', 'class', 'order', 'south', 'piece', 'since', 'whole', 'wheel', 'force', 'plane', 'stead', 'laugh', 'check', 'shape', 'bring', 'paint', 'among', 'power', 'field', 'pound', 'drive', 'stood', 'front', 'teach', 'final', 'green', 'quick', 'ocean', 'clear', 'space', 'heard', 'early', 'reach', 'table', 'vowel', 'money', 'serve', 'voice', 'count', 'speak', 'grand', 'heart', 'heavy', 'dance', 'store', 'train', 'sleep', 'prove', 'catch', 'mount', 'board', 'glass', 'grass', 'visit', 'month', 'happy', 'trade', 'mouth', 'exact', 'least', 'shout', 'wrote', 'clean', 'break', 'blood', 'touch', 'brown', 'equal', 'quite', 'broke', 'scale', 'child', 'speed', 'organ', 'dress', 'cloud', 'quiet', 'stone', 'climb', 'stick', 'smile', 'eight', 'raise', 'solve', 'metal', 'seven', 'third', 'shall', 'floor', 'coast', 'value', 'fight', 'sense', 'won’t', 'chair', 'fruit', 'thick', 'party', 'whose', 'radio', 'spoke', 'human', 'agree', 'woman', 'guess', 'sharp', 'crowd', 'sight', 'hurry', 'chief', 'clock', 'enter', 'major', 'fresh', 'allow', 'print', 'track', 'shore', 'sheet', 'favor', 'spend', 'chord', 'share', 'bread', 'offer', 'slave', 'chick', 'enemy', 'reply', 'drink', 'occur', 'range', 'steam', 'meant', 'teeth', 'shell', 'sugar', 'death', 'skill', 'women', 'thank', 'match', 'steel', 'guide', 'score', 'apple', 'pitch', 'dream', 'total', 'basic', 'smell', 'block', 'chart', 'event', 'quart', 'truck', 'noise', 'level', 'throw', 'shine', 'wrong', 'broad', 'anger', 'claim'], 6: ['follow', 'change', 'animal', 'mother', 'father', 'little', 'differ', 'before', 'number', 'people', 'should', 'answer', 'school', 'friend', 'always', 'letter', 'second', 'enough', 'though', 'family', 'direct', 'happen', 'street', 'course', 'object', 'decide', 'island', 'system', 'record', 'common', 'wonder', 'equate', 'figure', 'beauty', 'minute', 'strong', 'behind', 'better', 'during', 'ground', 'listen', 'travel', 'simple', 'toward', 'center', 'person', 'appear', 'govern', 'notice', 'energy', 'sudden', 'square', 'reason', 'length', 'region', 'settle', 'weight', 'matter', 'circle', 'divide', 'engine', 'forest', 'window', 'summer', 'winter', 'bright', 'finish', 'flower', 'clothe', 'melody', 'office', 'symbol', 'except', 'garden', 'choose', 'middle', 'moment', 'spring', 'nation', 'method', 'design', 'bottom', 'single', 'twenty', 'crease', 'either', 'result', 'phrase', 'silent', 'finger', 'excite', 'danger', 'doctor', 'please', 'modern', 'corner', 'supply', 'locate', 'insect', 'caught', 'period', 'effect', 'expect', 'gentle', 'create', 'rather', 'string', 'depend', 'famous', 'dollar', 'stream', 'planet', 'colony', 'search', 'yellow', 'desert', 'arrive', 'master', 'parent', 'charge', 'proper', 'market', 'degree', 'speech', 'nature', 'motion', 'liquid', 'oxygen', 'pretty', 'season', 'magnet', 'silver', 'branch', 'suffix', 'afraid', 'sister', 'bought', 'valley', 'double', 'spread', 'invent', 'cotton', 'chance', 'gather', 'column', 'select', 'repeat', 'plural'], 7: ['picture', 'through', 'country', 'between', 'thought', 'science', 'example', 'measure', 'product', 'numeral', 'problem', 'nothing', 'surface', 'brought', 'distant', 'certain', 'machine', 'correct', 'contain', 'develop', 'special', 'produce', 'hundred', 'morning', 'several', 'against', 'pattern', 'brother', 'believe', 'perhaps', 'subject', 'general', 'include', 'present', 'written', 'weather', 'million', 'strange', 'receive', 'trouble', 'suggest', 'collect', 'control', 'decimal', 'observe', 'section', 'village', 'whether', 'century', 'natural', 'capital', 'soldier', 'process', 'operate', 'protect', 'element', 'student', 'history', 'imagine', 'provide', 'captain', 'compare', 'current', 'connect', 'station', 'segment', 'instant', 'support', 'discuss', 'forward', 'similar', 'evening', 'success', 'company', 'arrange', 'stretch', 'require', 'prepare'], 8: ['sentence', 'mountain', 'together', 'children', 'question', 'complete', 'multiply', 'possible', 'thousand', 'language', 'remember', 'interest', 'probable', 'syllable', 'position', 'material', 'fraction', 'exercise', 'straight', 'surprise', 'describe', 'consider', 'industry', 'practice', 'separate', 'indicate', 'electric', 'neighbor', 'triangle', 'division', 'original', 'populate', 'quotient', 'solution', 'continue', 'subtract', 'opposite', 'shoulder', 'property', 'molecule'], 9: ['represent', 'consonant', 'paragraph', 'difficult', 'character', 'necessary', 'substance', 'condition', 'determine', 'continent'], 10: ['instrument', 'dictionary', 'experiment', 'especially', 'experience', 'particular'], 11: ['temperature']}
    sentences = {24: [[4, 3, 4, 4, 4], [1, 4, 3, 3, 3, 4], [4, 6, 4, 6]], 64: [[1, 4, 2, 5, 2, 2, 4, 3, 3, 3, 5, 3, 5, 2, 5], [1, 3, 5, 8, 3, 4, 4, 2, 4, 2, 1, 6, 8]], 40: [[1, 8, 4, 3, 3, 3, 5, 5], [1, 2, 6, 7, 1, 3, 3, 3, 5], [2, 5, 2, 4, 2, 6, 4, 2, 4]], 26: [[1, 4, 1, 5, 2, 7], [2, 3, 4, 2, 3, 6]], 28: [[2, 6, 2, 3, 4, 5], [5, 3, 3, 3, 3, 5], [2, 3, 4, 8, 2, 3]], 31: [[3, 5, 3, 5, 6, 3], [3, 7, 3, 4, 3, 5], [4, 4, 3, 4, 5, 5], [2, 4, 2, 5, 2, 2, 7]], 11: [[3, 6]], 39: [[4, 4, 2, 3, 7, 3, 9]], 21: [[2, 3, 4, 8], [4, 4, 4, 5], [8, 2, 8]], 42: [[1, 4, 4, 2, 3, 7, 2, 3, 3, 3], [3, 7, 3, 5, 3, 3, 2, 4, 3]], 25: [[3, 4, 2, 3, 1, 3, 2], [2, 3, 4, 6, 5], [3, 6, 4, 3, 4], [4, 4, 2, 3, 2, 4], [3, 4, 3, 4, 6], [2, 3, 4, 1, 3, 2, 3]], 18: [[5, 4, 6]], 23: [[2, 3, 4, 10], [2, 6, 4, 7], [4, 3, 4, 3, 4]], 36: [[3, 3, 3, 5, 4, 2, 4, 4]], 30: [[3, 4, 4, 5, 9]], 13: [[3, 3, 4]], 45: [[3, 4, 2, 3, 5, 7, 2, 3, 3, 3]], 47: [[3, 3, 3, 5, 4, 2, 4, 6, 3, 4]], 44: [[1, 7, 2, 5, 2, 5, 3, 5, 5], [2, 4, 2, 5, 5, 2, 3, 3, 2, 6]], 22: [[3, 4, 3, 2, 5]], 43: [[3, 6, 3, 4, 4, 3, 5, 7], [3, 3, 1, 3, 2, 7, 2, 3, 10]], 16: [[5, 3, 5], [4, 3, 3, 2]], 38: [[3, 3, 5, 4, 2, 1, 4, 4, 3]], 14: [[3, 1, 7]], 27: [[1, 3, 1, 4, 7, 5], [5, 5, 6, 2, 4]], 29: [[4, 4, 4, 6, 2, 3]], 32: [[2, 3, 3, 2, 3, 4, 3, 4]], 48: [[5, 3, 6, 4, 2, 5, 3, 3, 3, 4], [3, 4, 3, 6, 3, 3, 6, 5, 6]], 12: [[6, 4]], 15: [[1, 5, 3, 2]], 57: [[1, 7, 4, 4, 4, 5, 4, 11, 8]], 20: [[5, 3, 3, 5]]}

    text = ""

    total = 0
    cur_width = 0
    while total < length:
        chars_left = length - total
        # If running out of characters, take one last sentence as close to
        # the chars left as possible
        if chars_left < 65:
            if chars_left in sentences:
                sentence_key = chars_left
            else:
                sentence_key = max(list(sentences), key=lambda x: 1/(chars_left - x))
        else:
            sentence_key = random.choice(list(sentences))

        sentence = random.choice(sentences[sentence_key])
        total += sentence_key
        slen = len(sentence)
        for i in range(slen):
            word = random.choice(words[sentence[i]])
            word_length = len(word) + (i != 0) + (i == slen - 1)
            cur_width += word_length
            if cur_width >= width:
                text += "\\n"
                cur_width = word_length
            elif total != sentence_key or i != 0:
                text += " "
            if not i:
                word = word.title()
            text += word
            if i == slen - 1:
                text += "."

    return text


# Function to get img information
def prepare_text(item, text, font_path):
    text_size = item.text_size
    if not item.advanced:
        text_size = int(item.resolution * 100)

    font = ImageFont.truetype(font_path, size=text_size)
    if (fonts[item.font_family][0] and not item.use_font_path) or (item.use_font_path and "variable" in item.font_path.lower()):
        font.set_variation_by_axes([item.font_weight])

    row_height = font.getbbox("azertyuiopqsdghfjklmwxcvbnAZERTYUIOPQSDFGHJKLMWXCVBN|@#¼½^{[{}\]&é(§è!çà)-ùµ=:;,<>1234567890°_%£+/.?")[3]

    row_height = int(row_height * item.vertical_spacing)
    text_parts = text.split("\\n")
    text_draws = []

    max_y = 0
    max_x = 0

    for i in range(len(text_parts)):
        text_part = text_parts[i]
        left, top, right, bottom = font.getbbox(text_part)
        length = right - left
        max_x = max(max_x, length)
        words_width = []
        if item.use_fill:
            for word in text_part.split(" "):
                wordleft, wordtop, wordright, wordbottom = font.getbbox(word)
                words_width.append(wordright - wordleft)
        text_draws.append((left, length, i * row_height, text_part, words_width))
        if i == len(text_parts) - 1:
            max_y += bottom
        else:
            max_y += row_height

    # Override dimensions if manually set
    if item.advanced:
        if not item.stretch_width:
            max_x = item.width
        if not item.stretch_height:
            max_y = item.height
    return text_draws, font, max_x, max_y


# Create image
def create_img(text_draws, font, max_x, max_y, item):
    time_start = time.time()

    img = Image.new('L', (max_x, max_y))
    d = ImageDraw.Draw(img)

    for text_draw in text_draws:
        start, length, y, current_text, words_width = text_draw

        # Fill line if fill percentage is exceeded
        if item.use_fill and sum(words_width)/max_x > item.fill_percentage:
            empty = max_x - sum(words_width)
            words = current_text.split(" ")
            if len(words) != 1:
                spacing = empty/(len(words) - 1)
            else:
                spacing = 0
            current_line_length = 0
            for i in range(len(words)):
                d.text((current_line_length + spacing * i, y), words[i], fill=(255), font=font)
                current_line_length += words_width[i]
        elif item.alignment == "Center":
            d.text(((max_x - length)/2 - start, y), current_text, fill=(255), font=font)
        elif item.alignment == "Right":
            d.text((max_x - length - start, y), current_text, fill=(255), font=font)
        else:
            d.text((-start, y), current_text, fill=(255), font=font)

    # Don't create img when empty or file not saved
    if img.width and img.height:
        blender_path = '/'.join(bpy.data.filepath.replace("\\", "/").split("/")[:-1])
        save_path = blender_path + "/" + item.image_file + ".png"
        if blender_path != "":
            img.save(save_path)
            print("Created text image, time taken: {}, dimensions: {} {}".format((time.time() - time_start), img.width, img.height))
        else:
            print("Blender file isn't saved, there is no location to save image")


# Function to return possible font axes
def get_font_axes(fontpath):
    if "variable" in fontpath.lower():
        font = ImageFont.truetype(fontpath)
        axes = font.get_variation_axes()
        return axes


# Create fonts dictionary
def get_fonts():
    # Use the command line tool fc-list for linux
    if sys.platform == "linux":
        result = str(subprocess.run(['fc-list', ':', 'file', 'family', 'style'], stdout=subprocess.PIPE).stdout)
        font_files = result.split("\\n")
        for font_file in font_files:
            parts = font_file.split(":")
            if len(parts) == 1:
                continue
            family = parts[1].split(",")[0][1:]
            style = parts[2].split("=")[1]
            axes = get_font_axes(parts[0])
            if axes:
                if family not in fonts or not fonts[family][0]:
                    fonts[family] = [axes[0], {}]
                if len(style.split(" ")) == 2:
                    fonts[family][1]["Italic"] = parts[0]
                else:
                    fonts[family][1]["Regular"] = parts[0]

            elif family not in fonts:
                fonts[family] = [None, {}]
                fonts[family][1][style] = parts[0]
            elif not fonts[family][0]:
                fonts[family][1][style] = parts[0]
    # On windows, get families and all fonts separatly then
    # assign them to their families
    elif sys.platform == "win32":
        # Get all fonts
        result = subprocess.run(["powershell.exe",
                                'reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts" /s'],
                                stdout=subprocess.PIPE)
        result = str(result.stdout)
        # Get list of families
        families = str(subprocess.run(['powershell.exe', '[System.Reflection.Assembly]::LoadWithPartialName("System.Drawing")\n(New-Object System.Drawing.Text.InstalledFontCollection).Families'], stdout=subprocess.PIPE).stdout)
        families = [ele.split("\\r")[0] for ele in families.split("Name : ")]
        for ele in result.split("\\r\\n"):
            if "    " not in ele:
                continue
            name = ele.split(" (")[0][4:]
            new_name = ""
            for family in families:
                if family in name and len(new_name) < len(family):
                    new_name = family
            style = name.replace(new_name, "")
            if style == "":
                style = "Regular"
            family = new_name
            if family == "":
                continue
            path_end = ele.split("    ")[-1]
            font_path = "C:\Windows/Fonts/" + path_end
            axes = get_font_axes(font_path)
            if axes:
                if family not in fonts or not fonts[family][0]:
                    fonts[family] = [axes[0], {}]
                if len(style.split(" ")) == 2:
                    fonts[family][1]["Italic"] = font_path
                else:
                    fonts[family][1]["Regular"] = font_path

            elif family not in fonts:
                fonts[family] = [None, {}]
                fonts[family][1][style] = font_path
            elif not fonts[family][0]:
                fonts[family][1][style] = font_path


# Function to create list of enum for type selection
def get_enums(self, context):
    textgen = context.scene.textgen
    current = textgen.textitems[textgen.selected].font_family
    enums = []
    types = fonts[current][1]
    for font_type in types:
        enums.append((font_type, font_type, "Choose the font type of this font"))
    return enums


# Get function for font weight to check if value is in range
def getweight(self):
    textgen = bpy.context.scene.textgen
    item = textgen.textitems[textgen.selected]
    if not item.use_font_path:
        axes = fonts[item.font_family][0]
    else:
        axes = get_font_axes(item.font_path)[0]
    if item.font_weight_value > axes["maximum"] or item.font_weight_value < axes["minimum"]:
        item.font_weight_value = axes["default"]
    return item.font_weight_value


# Set function for font weight that clamps value to font range
def setweight(self, value):
    textgen = bpy.context.scene.textgen
    item = textgen.textitems[textgen.selected]
    if not item.use_font_path:
        axes = fonts[item.font_family][0]
    else:
        axes = get_font_axes(item.font_path)[0]
    item.font_weight_value = max(min(value, axes["maximum"]), axes["minimum"])


# Declare property classes
class SelectItem(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Text",
    )


class LineItem(bpy.types.PropertyGroup):
    text: StringProperty(
        name="",
        description="Line of text, #R#CHARS:WIDTH:SEED#R# will get replaced by randomy generated text",
        update=text_changed_now_refresh
        )


class TextItem(bpy.types.PropertyGroup):
    name: StringProperty(
        name="Textpart",
        default="Some text"
        )
    lines: CollectionProperty(
        name="Textparts",
        type=LineItem
        )
    resolution: FloatProperty(
        name="Resolution",
        description="Resolution of a character so it doesn't need to be larger when there is more text, don't set this higher than needed",
        default=1,
        min=0.01,
        max=100,
        update=text_changed_now_refresh
        )
    width: IntProperty(
        name="X",
        description="Width of the text in pixels",
        default=1920,
        min=0,
        update=text_changed_now_refresh
        )
    height: IntProperty(
        name="Y",
        description="Height of the text in pixels",
        default=1080,
        min=0,
        update=text_changed_now_refresh
        )
    stretch_width: BoolProperty(
        name="Wrap width",
        description="Use the width of the text as the width of the image. Else use width set by user",
        default=True,
        update=text_changed_now_refresh
        )
    stretch_height: BoolProperty(
        name="Wrap height",
        description="Use the height of the text as the height of the image. Else use height set by user",
        default=True,
        update=text_changed_now_refresh
        )
    text_size: IntProperty(
        name="Text size",
        description="Size of the text in pixels(might not be accurate)",
        default=100,
        min=1,
        update=text_changed_now_refresh
        )
    image_file: StringProperty(
        name="File",
        description="Name of the image file on disk where the image will be saved",
        default="text_image_blender",
        update=rename
        )
    old_image_file: StringProperty(
        name="Old image file"
        )
    use_random_text: BoolProperty(
        name="Random text",
        description="Neglect lines and generate random text instead",
        default=False,
        update=text_changed_now_refresh
        )
    random_length: IntProperty(
        name="Characters",
        description="Total length of the generated text in characters",
        default=100,
        min=25,
        update=text_changed_now_refresh
        )
    random_width: IntProperty(
        name="Text width",
        description="Width of text in characters",
        default=100,
        min=16,
        update=text_changed_now_refresh
        )
    font_family: StringProperty(
        name="",
        update=font_changed,
        default="Ubuntu" if sys.platform == "linux" else "Calibri"
        )
    font_type: EnumProperty(
        name="",
        description="Type of the font, choose between installed types",
        items=get_enums,
        update=text_changed_now_refresh,
        default=0
        )
    advanced: BoolProperty(
        name="Advanced mode",
        description="Manually control the width and height of the image",
        default=False,
        update=text_changed_now_refresh
        )
    alignment: EnumProperty(
        name="Alignment",
        items=[("Left", "Left", "", "ALIGN_LEFT", 0), ("Center", "Center", "", "ALIGN_CENTER", 1), ("Right", "Right", "", "ALIGN_RIGHT", 2)],
        default=0,
        update=text_changed_now_refresh
        )
    seed: IntProperty(
        name="Seed",
        description="Seed of the random generation, change to get other text",
        default=1,
        update=text_changed_now_refresh
        )
    vertical_spacing: FloatProperty(
        name="Line spacing",
        description="Amount of space between two lines, default is 1",
        default=1,
        update=text_changed_now_refresh
        )
    use_font_path: BoolProperty(
        name="",
        description="Use a path to a font instead of selection from detected installed fonts",
        default=sys.platform == "darwin",
        update=text_changed_now_refresh
        )
    font_path: StringProperty(
        name="Font",
        description="Path to truetype font file (.ttf) on disk",
        update=text_changed_now_refresh,
        subtype='FILE_PATH'
        )
    font_weight: IntProperty(
        name="Font weight",
        description="Weight of the font, this value usually controls how bold the text is. A higher value will result in a bolder font. Look beneath for minimum, maximum and default value",
        update=text_changed_now_refresh,
        set=setweight,
        get=getweight
        )
    font_weight_value: IntProperty(name="weight_value")

    use_fill: BoolProperty(
        name="Fill",
        description="Spread the text to fill the whole line when the fill percentage is exceeded",
        default=False,
        update=text_changed_now_refresh
        )
    fill_percentage: FloatProperty(
        name="Fill %",
        description="Percentage of the total image width which has to be occupied by text so that the line gets filled with text, if not reached the line will be aligned according to the chosen alignment type",
        update=text_changed_now_refresh,
        min=0,
        max=1,
        default=0.7
        )


class TextGenProperties(PropertyGroup):
    selected: IntProperty(
        name="Select text item",
        )
    textitems: CollectionProperty(
        name="textitems",
        type=TextItem
        )
    font_search: CollectionProperty(
        name="choose",
        type=SelectItem
        )
    safetylock: BoolProperty(
        name="",
        description="Safetylock, flickers when prevented image creation because of memory overflow risk. When disabled, be cautious",
        default=True,
        )


# Panel class, creates the sidebar panel in the viewport
class TextGenPanel(bpy.types.Panel):
    bl_idname = "TEXTGEN_PT_PANEL"
    bl_label = "TextGen"
    bl_category = "TextGen"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        global warning_animation
        layout = self.layout
        textgen = context.scene.textgen

        row = layout.row(align=True)

        row.template_list("UI_UL_list", "lines_list", textgen, "textitems", textgen, "selected", item_dyntip_propname="name")

        col = row.column(align=True)

        col.operator("textgen.additem", icon='ADD')
        col.operator("textgen.removeitem", icon='REMOVE')
        col.operator("textgen.duplicate", icon='DUPLICATE')

        # Abort if no text item
        if len(textgen.textitems) == 0:
            return None

        item = textgen.textitems[textgen.selected]
        lines = item.lines

        row = layout.row()
        row.prop(item, "advanced", toggle=True)

        # Make safetylock property trippy if prevented image creation
        if time.time() - latest_error < 5:
            warning_animation = not warning_animation
            row.prop(textgen, "safetylock", icon="ERROR", icon_only=True, emboss=warning_animation, text="Image creation prevented")
        elif textgen.safetylock:
            row.prop(textgen, "safetylock", icon="LOCKED", icon_only=True)
        else:
            row.prop(textgen, "safetylock", icon="UNLOCKED", icon_only=True)

        row = layout.row(align=True)
        col = row.column(align=True)
        col.prop(lines[0], "text")

        # Grey lines out when using random text
        col.enabled = not item.use_random_text

        # Use a different layout depending on the amount of lines
        if len(lines) == 1:
            row.operator("textgen.addline", icon='ADD', text="")
            row.operator("textgen.removeline", icon='REMOVE', text="")
            row.prop(item, "use_random_text", icon='QUESTION', icon_only=True)

        elif len(lines) == 2:
            col2 = row.column(align=True)
            col2.prop(item, "use_random_text", icon='QUESTION', icon_only=True)
            row2 = col2.row(align=True)
            row2.operator("textgen.addline", icon='ADD', text="")
            row2.operator("textgen.removeline", icon='REMOVE', text="")
        else:
            col2 = row.column(align=True)
            col2.prop(item, "use_random_text", icon='QUESTION', icon_only=True)
            col2.operator("textgen.addline", icon='ADD', text="")
            col2.operator("textgen.removeline", icon='REMOVE', text="")

        # Show random generation properties when enabled
        if item.use_random_text:
            layout.prop(item, "random_length")
            row = layout.row(align=True)
            row.prop(item, "random_width")
            row.prop(item, "seed")

        # Create all line properties
        for i in range(len(lines) - 1):
            col.prop(lines[i + 1], "text")

        row = layout.row(align=True)
        row.alignment = "CENTER"
        row.prop(item, "alignment", expand=True, toggle=-1)

        row = layout.row(align=True)
        row.prop(item, "use_fill", toggle=True, icon="ALIGN_FLUSH", icon_only=True)
        col = row.column()
        col.prop(item, "fill_percentage", slider=True)

        # Grey out fill percentage if fill is disabled
        col.enabled = item.use_fill

        # Show resolution or text size depending on advanced mode
        if item.advanced:
            layout.prop(item, "text_size", icon='SMALL_CAPS')
        else:
            layout.prop(item, "resolution")

        # Add dimension properties if advanced mode
        if item.advanced:
            row = layout.row(align=True)
            row.prop(item, "stretch_width", toggle=1)
            row.prop(item, "stretch_height", toggle=1)

            row = layout.row(align=True)
            col = row.column()
            col.prop(item, "width")
            col.enabled = not item.stretch_width

            col = row.column()
            col.prop(item, "height")
            col.enabled = not item.stretch_height

        layout.prop(item, "vertical_spacing", icon='COLLAPSEMENU', icon_value=0)

        row = layout.row()
        if not item.use_font_path:
            row.prop_search(item, "font_family", textgen, "font_search", icon="FILE_FONT")
        else:
            row.prop(item, "font_path")

        # Don't give ability to toggle of font path to MacOS users
        if sys.platform != "darwin":
            row.prop(item, "use_font_path", icon='FILEBROWSER', toggle=True)

        if not item.use_font_path:
            layout.prop(item, "font_type", icon="ITALIC")

        # Show weight property and info if font is variable
        if (fonts[item.font_family][0] and not item.use_font_path) or (item.use_font_path and "variable" in item.font_path.lower()):
            if item.use_font_path:
                axes = get_font_axes(item.font_path)[0]
            else:
                axes = fonts[item.font_family][0]
            layout.prop(item, "font_weight")
            layout.label(text="min : {} max : {} default : {}".format(axes["minimum"], axes["maximum"], axes["default"]))

        layout.prop(item, "image_file", icon='FILE')

        layout.operator("textgen.node", icon='ADD')


# Function to get enums to select line when adding/removing a line
def get_line_enums(self, context):
    textgen = context.scene.textgen
    item = textgen.textitems[textgen.selected]
    enums = []
    for i in range(len(item.lines)):
        name = "Line " + str(i + 1) + ":" + item.lines[i].text
        enums.append((str(i), name, "Perform action at this line"))
    return enums


class RemoveLine(Operator):
    bl_idname = "textgen.removeline"
    bl_description = "Remove a line from the text"
    bl_label = "Remove line"
    bl_options = {'INTERNAL'}

    line: EnumProperty(name="Line", items=get_line_enums)

    def execute(self, context):
        textgen = context.scene.textgen
        lines = textgen.textitems[textgen.selected].lines

        # Abort when only one line left
        if len(lines) == 1:
            return {'FINISHED'}
        lines.remove(int(self.line))
        text_changed_now_refresh(None, None)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "line")


class AddLine(Operator):
    bl_idname = "textgen.addline"
    bl_description = "Add a line to the text"
    bl_label = "Add line"
    bl_options = {'INTERNAL'}

    line: EnumProperty(name="Line", items=get_line_enums)
    placement: EnumProperty(name="Place", items=[("0", "before line", ""), ("1", "after line", "")])

    def execute(self, context):
        textgen = context.scene.textgen
        lines = textgen.textitems[textgen.selected].lines
        lines.add()
        lines.move(len(lines) - 1, int(self.line) + int(self.placement))
        text_changed_now_refresh(None, None)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "placement")
        layout.prop(self, "line")


class AddItem(Operator):
    bl_idname = "textgen.additem"
    bl_label = ""
    bl_description = "Add a text item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global no_update
        # Set no update so that text_changed_now_refresh gets aborted
        no_update = True

        textgen = context.scene.textgen
        textitems = textgen.textitems
        item = textitems.add()
        textgen.selected = len(textitems) - 1
        # Set image file to a new value
        item.image_file = "TextGeneratorFile{}".format(len(textitems))
        item.lines.add().text = "Text"
        item.name = "Text"
        no_update = False
        return {'FINISHED'}


class RemoveItem(Operator):
    bl_idname = "textgen.removeitem"
    bl_label = ""
    bl_description = "Remove selected text item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        textgen = context.scene.textgen
        textitems = textgen.textitems
        current_select = textgen.selected
        # If removed item was last in list, change pointer to
        # the previous text item
        if current_select == len(textitems) - 1:
            textgen.selected -= 1
        textitems.remove(current_select)

        return {'FINISHED'}


class AddDuplicate(Operator):
    bl_idname = "textgen.duplicate"
    bl_label = ""
    bl_description = "Make duplicate of current text item"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        global no_update
        # Set no update so that text_changed_now_refresh gets aborted
        no_update = True

        textgen = context.scene.textgen
        textitems = textgen.textitems
        # If no text items, abort
        if len(textitems) == 0:
            no_update = False
            return {'FINISHED'}

        src = textitems[textgen.selected]
        copy = textitems.add()

        # Assigning all values of the source textitem to the newly created one.
        copy.advanced = src.advanced
        copy.alignment = src.alignment
        copy.fill_percentage = src.fill_percentage
        copy.font_family = src.font_family
        copy.font_path = src.font_path
        copy.font_type = src.font_type

        # Copy font weight if font is variable
        if "variable" in src.font_path.lower():
            copy.font_weight = src.font_weight

        copy.font_weight_value = src.font_weight_value
        copy.height = src.height
        copy.name = src.name
        copy.random_length = src.random_length
        copy.random_width = src.random_width
        copy.resolution = src.resolution
        copy.seed = src.seed
        copy.stretch_height = src.stretch_height
        copy.stretch_width = src.stretch_width
        copy.text_size = src.text_size
        copy.use_fill = src.use_fill
        copy.use_font_path = src.use_font_path
        copy.use_random_text = src.use_random_text
        copy.vertical_spacing = src.vertical_spacing
        copy.width = src.width

        for line in src.lines:
            text_part = copy.lines.add()
            text_part.text = line.text
        # Change image file to new value in a smart way
        try:
            new_image_file = src.image_file[:-1] + str(int(src.image_file[-1]) + 1)
        except ValueError:
            new_image_file = src.image_file + "1"

        copy.image_file = new_image_file
        textgen.selected = len(textitems) - 1
        no_update = False
        return {'FINISHED'}


class AddTextureNode (bpy.types.Operator):
    bl_idname = "textgen.node"
    bl_label = "Add texture node"
    bl_description = "Add an image texture node with the created image to the current node tree"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        textgen = context.scene.textgen
        item = textgen.textitems[textgen.selected]
        image_file = item.image_file
        current_object = context.active_object

        # Abort if no object selected
        if not current_object:
            self.report({'ERROR'}, "No object is selected")
            return {'FINISHED'}

        material = current_object.active_material

        # Abort if object doesn't have a node tree
        if hasattr(material, "node_tree"):
            nodes = material.node_tree.nodes
        else:
            self.report({'ERROR'}, "Current object doesn't have a node tree")
            return {'FINISHED'}

        node = nodes.new("ShaderNodeTexImage")

        try:
            node.image = bpy.data.images[image_file + ".png"]
        except KeyError:
            if bpy.data.filepath:
                text_changed_now_refresh(None, None)
                node.image = bpy.data.images[image_file + ".png"]
            else:
                self.report({'ERROR'}, "Blender file isn't saved, there is no location to save image")

        # Set extension method to CLIP as it's much more likely to get used
        # for text images
        node.extension = 'CLIP'
        return {'FINISHED'}


# Function to refresh the loaded image in blender
def refresh_image(image_file):
    # If image already exist, reload. Else load from disk
    if image_file + ".png" in bpy.data.images:
        bpy.data.images[image_file + ".png"].reload()
    else:
        blender_path = '/'.join(bpy.data.filepath.replace("\\", "/").split("/")[:-1])
        if blender_path != "":
            bpy.data.images.load(filepath=blender_path + "/" + image_file + ".png")
        else:
            print("Blender file isn't saved, there is no location to save image")


# Function which will load fonts on file opening
@persistent
def init_font_search(scene):
    start = time.time()

    # First clear existing fonts as new ones might be found
    bpy.context.scene.textgen.font_search.clear()

    # This will load all available fonts into the 'fonts' variable
    get_fonts()

    # For every family add a selection item
    for ele in fonts:
        item = bpy.context.scene.textgen.font_search.add()
        item.name = ele
    # Print amount of time taken(shoud be around one hundredth of a second)
    print("Initialized fonts in {} seconds".format(time.time() - start))


def register():
    start = time.time()
    bpy.utils.register_class(TextGenPanel)
    bpy.utils.register_class(LineItem)
    bpy.utils.register_class(TextItem)
    bpy.utils.register_class(SelectItem)
    bpy.utils.register_class(TextGenProperties)
    bpy.utils.register_class(AddTextureNode)
    bpy.utils.register_class(AddLine)
    bpy.utils.register_class(RemoveLine)
    bpy.utils.register_class(AddItem)
    bpy.utils.register_class(RemoveItem)
    bpy.utils.register_class(AddDuplicate)

    # Set pointer property
    bpy.types.Scene.textgen = PointerProperty(type=TextGenProperties)

    # Append init_font_search to app handler load_post to get it
    # to run on file opening
    if sys.platform != "darwin":
        bpy.app.handlers.load_post.append(init_font_search)

    # Print that the add-on registered succesfully
    print("Registered textgen addon in {} seconds".format(round(time.time() - start, 5)))


def unregister():
    bpy.utils.unregister_class(TextGenPanel)
    bpy.utils.unregister_class(LineItem)
    bpy.utils.unregister_class(TextItem)
    bpy.utils.unregister_class(SelectItem)
    bpy.utils.unregister_class(TextGenProperties)
    bpy.utils.unregister_class(AddTextureNode)
    bpy.utils.unregister_class(AddLine)
    bpy.utils.unregister_class(RemoveLine)
    bpy.utils.unregister_class(AddItem)
    bpy.utils.unregister_class(RemoveItem)
    bpy.utils.unregister_class(AddDuplicate)

    if sys.platform != "darwin":
        bpy.app.handlers.load_post.remove(init_font_search)


if __name__ == "__main__":
    register()
