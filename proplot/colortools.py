#!/usr/bin/env python3
#------------------------------------------------------------------------------#
# Note colormaps are *callable*, will just deliver the corresponding color, easy.
# Notes on different colorspaces:
# * HCL is perfectly perceptually uniform, always. But some colors in the
#   range [0,360], [0,100], [0,100] are impossible.
# * HSL fixes this by, for *every hue and luminance*, designating 100 as
#   the maximum *possible* valid chroma. This makes it suitable for
#   single hue colormaps.
# * HPL fixes this by, for *every luminance*, designating 100 as
#   the *minimum* max chroma across *every hue for that luminance*. This
#   makes it more suitable for multi-hue colormaps.
# TODO: Allow some colormaps (e.g. topography) to have ***fixed*** levels,
# i.e. force the user to use very high resolution (e.g. 256 levels) and the
# 'x' coordinates will enforce discrete jumps between colors. Consider doing
# this for 'seismic' map, and others.
#------------------------------------------------------------------------------#
# Interesting cpt-city colormaps that did not use:
# * Considered Jim Mossman maps, but not very uniform.
# * Erik Jeschke grayscale ones are also neat, but probably not much
#   scientific use.
# * Rafi 'sky' themes were pretty, but ultimately not useful.
# * Crumblingwalls also interesting, but too many/some are weird.
# * NCL gradients mostly ugly, forget them.
# * Piecrust design has interesting 'nature' colormaps, but they are
#   not practical. Just added a couple astro ones (aurora, space, star).
# * Elvensword is cool, but most are pretty banded.
# Geographic ones not used:
# * Christian Heine geologic time maps are interesting, but again not
#   uniform and not useful.
# * IBCA could have been good, but bathymetry has ugly jumps.
# * GMT maps also interesting, but non uniform.
# * Victor Huérfano Caribbean map almost useful, but has banding.
# * Christopher Wesson martian topo map sort of cool, but too pale.
# * Thomas Deweez has more topo colors, but kind of ugly.
# Geographic ones to be adapted:
# * ESRI seems to have best geographic maps.
# * Wiki schemes are also pretty good, but not great.
#------------------------------------------------------------------------------#
# Notes on 'channel-wise alpha':
# * Colormaps generated from HCL space (and cmOcean ones) are indeed perfectly
#   perceptually uniform, but this still looks bad sometimes -- usually we
#   *want* to focus on the *extremes*, so want to weight colors more heavily
#   on the brighters/whiter part of the map! That's what the ColdHot map does,
#   it's what most of the ColorBrewer maps do, and it's what ColorWizard does.
# * By default extremes are stored at end of *lookup table*, not as
#   separate RGBA values (so look under cmap._lut, indexes cmap._i_over and
#   cmap._i_under). You can verify that your cmap is using most extreme values
#   by comparing high-resolution one to low-resolution one.
#------------------------------------------------------------------------------#
# Potential bottleneck, loading all this stuff?
# NO. Try using @timer on register functions, turns out worst is colormap
# one at 0.1 seconds. Just happens to be a big package, takes a bit to compile
# to bytecode (done every time module changed) then import.
#------------------------------------------------------------------------------#
# Here's some useful info on colorspaces
# https://en.wikipedia.org/wiki/HSL_and_HSV
# http://www.hclwizard.org/color-scheme/
# http://www.hsluv.org/comparison/ compares lch, hsluv (scaled lch), and hpluv (truncated lch)
# Info on the CIE conventions
# https://en.wikipedia.org/wiki/CIE_1931_color_space
# https://en.wikipedia.org/wiki/CIELUV
# https://en.wikipedia.org/wiki/CIELAB_color_space
# And some useful tools for creating colormaps and cycles
# https://nrlmry.navy.mil/TC.html
# http://help.mail.colostate.edu/tt_o365_imap.aspx
# http://schumacher.atmos.colostate.edu/resources/archivewx.php
# https://coolors.co/
# http://tristen.ca/hcl-picker/#/hlc/12/0.99/C6F67D/0B2026
# http://gka.github.io/palettes/#diverging|c0=darkred,deeppink,lightyellow|c1=lightyellow,lightgreen,teal|steps=13|bez0=1|bez1=1|coL0=1|coL1=1
# https://flowingdata.com/tag/color/
# http://tools.medialab.sciences-po.fr/iwanthue/index.php
# https://learntocodewith.me/posts/color-palette-tools/
#------------------------------------------------------------------------------
import os
import re
import json
from lxml import etree
from numbers import Number
import numpy as np
import numpy.ma as ma
import matplotlib.colors as mcolors
import matplotlib.cm as mcm
from matplotlib import rcParams
from cycler import cycler
from glob import glob
from . import colormath
from .utils import _default, ic, edges
_data = f'{os.path.dirname(__file__)}' # or parent, but that makes pip install distribution hard

# Default number of colors
_N_hires = 256

# Define some new palettes
# Note the default listed colormaps
_cycles_loaded = {}
_cycles_preset = {
    # Default matplotlib v2
    'default':      ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
    # Copied from stylesheets; stylesheets just add color themese from every possible tool, not already present as a colormap
    '538':          ['#008fd5', '#fc4f30', '#e5ae38', '#6d904f', '#8b8b8b', '#810f7c'],
    'ggplot':       ['#E24A33', '#348ABD', '#988ED5', '#777777', '#FBC15E', '#8EBA42', '#FFB5B8'],
    # The default seaborn ones (excluded deep/muted/bright because thought they were unappealing)
    'ColorBlind':   ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#F0E442', '#56B4E9'],
    'ColorBlind10': ["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC", "#CA9161", "#FBAFE4", "#949494", "#ECE133", "#56B4E9"], # versions with more colors
    # From the website
    'FlatUI':       ["#3498db", "#e74c3c", "#95a5a6", "#34495e", "#2ecc71", "#9b59b6"],
    # Created with online tools; add to this
    # See: http://tools.medialab.sciences-po.fr/iwanthue/index.php
    'Cinematic':    [(51,92,103), (158,42,43), (255,243,176), (224,159,62), (84,11,14)],
    'Cool':         ["#6C464F", "#9E768F", "#9FA4C4", "#B3CDD1", "#C7F0BD"],
    'Sugar':        ["#007EA7", "#B4654A", "#80CED7", "#B3CDD1", "#003249"],
    'Vibrant':      ["#007EA7", "#D81159", "#B3CDD1", "#FFBC42", "#0496FF"],
    'Office':       ["#252323", "#70798C", "#DAD2BC", "#F5F1ED", "#A99985"],
    'Industrial':   ["#38302E", "#6F6866", "#788585", "#BABF95", "#CCDAD1"],
    'Tropical':     ["#0D3B66", "#F95738", "#F4D35E", "#FAF0CA", "#EE964B"],
    'Intersection': ["#2B4162", "#FA9F42", "#E0E0E2", "#A21817", "#0B6E4F"],
    'Field':        ["#23395B", "#D81E5B", "#FFFD98", "#B9E3C6", "#59C9A5"],
    }

# Color stuff
# Keep major color names, and combinations of those names
_distinct_colors_space = 'hsl' # register colors distinct in this space?
_distinct_colors_threshold = 0.07
_distinct_colors_exceptions = [
    'white', 'black', 'gray', 'red', 'pink', 'grape',
    'sky blue', 'eggshell', 'sea blue',
    'violet', 'indigo', 'blue',
    'coral', 'tomato red', 'crimson',
    'cyan', 'teal', 'green', 'lime', 'yellow', 'orange',
    'red orange', 'yellow orange', 'yellow green', 'blue green',
    'blue violet', 'red violet',
    ]
_space_aliases = {
    'rgb':   'rgb',
    'hsv':   'hsv',
    'hpl':   'hpl',
    'hpluv': 'hpl',
    'hsl':   'hsl',
    'hsluv': 'hsl',
    'hcl':   'hcl',
    'lch':   'hcl',
    }

# Names of builtin colormaps
# NOTE: Has support for 'x' coordinates in first column.
# NOTE: For 'alpha' column, must use a .rgba filename
# TODO: Better way to save colormap files.
_cmap_categories = { # initialize as empty lists
    # We keep these ones
    'Matplotlib Originals': [
        'viridis', 'plasma', 'inferno', 'magma', 'twilight', 'twilight_shifted',
        ],

    # Assorted origin, but these belong together
    'Grayscale': [
        'Grays',
        'GrayCM',
        'GrayC',
        'PseudoGray',
        'GrayCycle',
        'GrayCycle_shifted',
        ],

    # Included ColorBrewer
    'ColorBrewer2.0 Sequential': [
        'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
        'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
        'PuBu', 'PuBuGn', 'BuGn', 'GnBu', 'YlGnBu', 'YlGn'
        ],

    # Added diverging versions
    # See: http://soliton.vm.bytemark.co.uk/pub/cpt-city/jjg/polarity/index.html
    # Other JJ Green maps weren't that great
    # TODO: Add 'serated' maps? See: http://soliton.vm.bytemark.co.uk/pub/cpt-city/jjg/serrate/index.html
    # TODO: Add tool for cutting center out of ***any*** colormap by ending
    # with the _cut suffix or something?
    'ColorBrewer2.0 Diverging': [
        # 'GYPi', 'GnRP', 'BrBG', 'PuOr', 'GyRd', 'BuRd', 'BuYlRd', 'GnYlRd', 'Spectral'
        'Spectral', 'Spectral_cut', 'PiYG', 'PiYG_cut', 'PRGn', 'PRGn_cut',
        'BrBG', 'BrBG_cut', 'PuOr', 'PuOr_cut', 'RdGY', 'RdGY_cut',
        'RdBu', 'RdBu_cut', 'RdYlBu', 'RdYlBu_cut', 'RdYlGn', 'RdYlGn_cut',
        ],

    # Custom maps
    'ProPlot Sequential': [
         'Glacial',
        'Bog', 'Verdant',
        'Lake', 'Turquoise', 'Forest',
        'Blood',
        'Sunrise', 'Sunset', 'Fire',
        'Golden'
        ],
        # 'Vibrant'], # empty at first, fill automatically
    'ProPlot Diverging': [
        'IceFire', 'NegPos', 'BlueRed', 'PurplePink', 'DryWet', 'DrierWetter', 'LandSea'
        ],

    # cmOcean
    'cmOcean Sequential': [
        'Oxy', 'Thermal', 'Dense', 'Ice', 'Haline',
        'Deep', 'Algae', 'Tempo', 'Speed', 'Turbid', 'Solar', 'Matter',
        'Amp', 'Phase', 'Phase_shifted'
        ],
    'cmOcean Diverging': [
        'Balance', 'Curl', 'Delta'
        ],

    # Other
    # BlackBody2 is actually from Los Alamos, and a couple are from Kenneth's
    # website, but organization is better this way.
    'Miscellaneous': [
        'BWR',
        'ColdHot',
        'Temperature', # from ???
        'BlackBody1', 'BlackBody2', 'BlackBody3', # 3rd one is actually sky theme from rafi
        'Star',
        'cividis',
        # 'JMN', # James map; ugly, so deleted
        'CubeHelix', 'SatCubeHelix',
        # 'Aurora', 'Space', # from PIEcrust; not uniform, so deleted
        # 'TemperatureJJG', # from JJG; ugly, so deleted
        'Kindlmann', 'ExtendedKindlmann',
        # 'Seismic', # note this one originally had hard boundaries/no interpolation
        'MutedBio', 'DarkBio', # from: ???, maybe SciVisColor
        ],

    # Statistik
    'Statistik Stadt Zürich': [
        'MutedBlue', 'MutedRed', 'MutedDry', 'MutedWet',
        'MutedBuRd', 'MutedBuRd_cut', 'MutedDryWet', 'MutedDryWet_cut',
        ],

    # Kenneth Moreland
    # See: http://soliton.vm.bytemark.co.uk/pub/cpt-city/km/index.html
    # Soft coolwarm from: https://www.kennethmoreland.com/color-advice/
    # 'Kenneth Moreland Sequential': [
    #     'BlackBody', 'Kindlmann', 'ExtendedKindlmann',
    #     ],
    'Kenneth Moreland': [
        'CoolWarm', 'MutedCoolWarm', 'SoftCoolWarm',
        'BlueTan', 'PurpleOrange', 'CyanMauve', 'BlueYellow', 'GreenRed',
        ],

    # Sky themes from rafi; not very scientifically useful, but pretty
    # 'Sky' : [
    #     'Sky1', 'Sky2', 'Sky3', 'Sky4', 'Sky5', 'Sky6', 'Sky7',
    #     ],

    # CET maps
    # See: https://peterkovesi.com/projects/colourmaps/
    # Only kept the 'nice' ones
    'CET Selections': [
        'CET1', 'CET2', 'CET3', 'CET4',
        'Iso1', 'Iso2', 'Iso3', 
        ],
    # 'CET Rainbow': [
    #     ],
    # 'CET Diverging': [
    #     ],
    # 'CET Cyclic': [
    #     ],

    # FabioCrameri
    # See: http://www.fabiocrameri.ch/colourmaps.php
    'Fabio Crameri Sequential': [
        'Acton', 'Buda', 'Lajolla',
        'Imola', 'Bamako', 'Nuuk', 'Davos', 'Oslo', 'Devon', 'Tokyo', 'Hawaii', 'Batlow',
        'Turku', 'Bilbao', 'Lapaz',
        ],
    'Fabio Crameri Diverging': [
        'Roma', 'Broc', 'Cork',  'Vik', 'Oleron', 'Lisbon', 'Tofino', 'Berlin',
        ],

    # Los Alamos
    # See: https://datascience.lanl.gov/colormaps.html
    # Most of these have analogues in SciVisColor, added the few unique
    # ones to Miscellaneous category
    # 'Los Alamos Sequential': [
    #     'MutedRainbow', 'DarkRainbow', 'MutedBlue', 'DeepBlue', 'BrightBlue', 'BrightGreen', 'WarmGray',
    #     ],
    # 'Los Alamos Diverging': [
    #     'MutedBlueGreen', 'DeepBlueGreen', 'DeepBlueGreenAsym', 'DeepColdHot', 'DeepColdHotAsym', 'ExtendedCoolWarm'
    #     ],

    # SciVisColor
    # Culled these because some were ugly
    # Actually nevermind... point of these is to *combine* them, make
    # stacked colormaps that highlight different things.
    # 'SciVisColor': [
    #           'SciPale',
    #           'SciBlue', 'SciCyan', 'SciSky',
    #           'SciTurquoise',
    #           'SciBlueGreen',
    #           'SciBrightGreen', 'SciGreen', 'SciYellowGreen',
    #           'SciYellow',
    #           'SciOrange',
    #           'SciYellowRed',
    #           'SciOrangeRed',
    #           'SciRed',
    #           'SciBrown',
    #           'SciMauve',
    #           'SciPurple',
    #           'SciViolet',
    #           'SciBlueViolet',
    #       ],
    'SciVisColor Blues': [
        'Blue0', 'Blue1', 'Blue2', 'Blue3', 'Blue4', 'Blue5', 'Blue6', 'Blue7', 'Blue8', 'Blue9', 'Blue10', 'Blue11',
        ],
    'SciVisColor Greens': [
        'Green1', 'Green2', 'Green3', 'Green4', 'Green5', 'Green6', 'Green7', 'Green8',
        ],
    'SciVisColor Oranges': [
        'Orange1', 'Orange2', 'Orange3', 'Orange4', 'Orange5', 'Orange6', 'Orange7', 'Orange8',
        ],
    'SciVisColor Browns': [
        'Brown1', 'Brown2', 'Brown3', 'Brown4', 'Brown5', 'Brown6', 'Brown7', 'Brown8', 'Brown9',
        ],
    'SciVisColor Reds/Purples': [
        'RedPurple1', 'RedPurple2', 'RedPurple3', 'RedPurple4', 'RedPurple5', 'RedPurple6', 'RedPurple7', 'RedPurple8',
        ],
    # 'SciVisColor Diverging': [
    #     'Div1', 'Div2', 'Div3', 'Div4', 'Div5'
    #     ],

    # Waves, also filtered
    # 'SciVisColor 3 Waves': [
    #     '3Wave1', '3Wave2', '3Wave3', '3Wave4', '3Wave5', '3Wave6', '3Wave7'
    #     ],
    # 'SciVisColor 4 Waves': [
    #     '4Wave1', '4Wave2', '4Wave3', '4Wave4', '4Wave5', '4Wave6', '4Wave7'
    #     ],
    # 'SciVisColor 5 Waves': [
    #     '5Wave1', '5Wave2', '5Wave3', '5Wave4', '5Wave5', '5Wave6'
    #     ],

    # Decided to totally forget these
    # 'SciVisColor Waves': [
    #     '3Wave1', '3Wave2', '3Wave3',
    #     '4Wave1', '4Wave2', '4Wave3',
    #     '5Wave1', '5Wave2', '5Wave3',
    #     ],
    # 'SciVisColor Inserts': [
    #     'Insert1', 'Insert2', 'Insert3', 'Insert4', 'Insert5', 'Insert6', 'Insert7', 'Insert8', 'Insert9', 'Insert10'
    #     ],
    # 'SciVisColor Thick Inserts': [
    #     'ThickInsert1', 'ThickInsert2', 'ThickInsert3', 'ThickInsert4', 'ThickInsert5'
    #     ],
    # 'SciVisColor Highlight': [
    #     'Highlight1', 'Highlight2', 'Highlight3', 'Highlight4', 'Highlight5',
    #     ],

    # Most of these were ugly, deleted them
    # 'SciVisColor Outlier': [
    #     'DivOutlier1', 'DivOutlier2', 'DivOutlier3', 'DivOutlier4',
    #     'Outlier1', 'Outlier2', 'Outlier3', 'Outlier4'
    #     ],

    # Duncan Agnew
    # See: http://soliton.vm.bytemark.co.uk/pub/cpt-city/dca/index.html
    # These are 1.0.5 through 1.4.0
    # 'Duncan Agnew': [
    #     'Alarm1', 'Alarm2', 'Alarm3', 'Alarm4', 'Alarm5', 'Alarm6', 'Alarm7'
    #     ],

    # Elevation and bathymetry
    # 'Geographic': [
    #     'Bath1', # from XKCD; see: http://soliton.vm.bytemark.co.uk/pub/cpt-city/xkcd/tn/xkcd-bath.png.index.html
    #     'Bath2', # from Tom Patterson; see: http://soliton.vm.bytemark.co.uk/pub/cpt-city/tp/index.html
    #     'Bath3', # from: http://soliton.vm.bytemark.co.uk/pub/cpt-city/ibcso/tn/ibcso-bath.png.index.html
    #     'Bath4', # ^^ same
    #     'Geography4-1', # mostly ocean
    #     'Geography5-4', # range must be -4000 to 5000
    #     'Geography1', # from ???
    #     'Geography2', # from: http://soliton.vm.bytemark.co.uk/pub/cpt-city/ngdc/tn/ETOPO1.png.index.html
    #     'Geography3', # from: http://soliton.vm.bytemark.co.uk/pub/cpt-city/mby/tn/mby.png.index.html
    #     ],
    # Gross. These ones will be deleted.
    'Alt Sequential': [
        'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
        'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
        'multi', 'cividis',
        'afmhot', 'gist_heat', 'copper'
        ],
    'Alt Rainbow': [
        'multi', 'cividis'
        ],
    'Alt Diverging': [
        'coolwarm', 'bwr', 'seismic'
        ],
    'Miscellaneous Orig': [
        'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
        'gnuplot', 'gnuplot2', 'CMRmap', 'brg', 'hsv', 'hot', 'rainbow',
        'gist_rainbow', 'jet', 'nipy_spectral', 'gist_ncar'
        ]}

# Categories to ignore/*delete* from dictionary because they suck donkey balls
_cmap_categories_delete = ['Alt Diverging', 'Alt Sequential', 'Alt Rainbow', 'Miscellaneous Orig']

# Slice indices that split up segments of names
# WARNING: Must add to this list manually! Not worth trying to generalize.
# List of string cmap names, and the indices where they can be broken into parts
_cmap_parts = {
    # Sequential
    # Decided these shouldn't be reversed; left colors always refer
    # to 'light' colors, right to 'dark' colors. Also there is BuPu and PuBu
    # 'ylorbr':       (None, 2, 4, None),
    # 'ylorrd':       (None, 2, 4, None),
    # 'orrd':         (None, 2, None),
    # 'purd':         (None, 2, None),
    # 'rdpu':         (None, 2, None),
    # 'bupu':         (None, 2, None),
    # 'gnbu':         (None, 2, None),
    # 'pubu':         (None, 2, None),
    # 'ylgnbu':       (None, 2, 4, None),
    # 'pubugn':       (None, 2, 4, None),
    # 'bugn':         (None, 2, None),
    # 'ylgn':         (None, 2, None),
    # Diverging
    'piyg':         (None, 2, None),
    'prgn':         (None, 1, 2, None), # purple red green
    'brbg':         (None, 2, 3, None), # brown blue green
    'puor':         (None, 2, None),
    'rdgy':         (None, 2, None),
    'rdbu':         (None, 2, None),
    'rdylbu':       (None, 2, 4, None),
    'rdylgn':       (None, 2, 4, None),
    # Other diverging
    'coldhot':      (None, 4, None),
    'bwr':          (None, 1, 2, None),
    'icefire':      (None, 3, None),
    'negpos':       (None, 3, None),
    'bluered':      (None, 4, None),
    'purplepink':   (None, 4, None),
    'drywet':       (None, 3, None),
    'drierwetter':  (None, 5, None),
    'landsea':      (None, 4, None),
    }
# Tuple pairs of mirror image cmap names
_cmap_mirrors = [
    (name, ''.join(reversed([name[slice(*idxs[i:i+2])] for i in range(len(idxs)-1)])),)
    for name,idxs in _cmap_parts.items()
    ]

#------------------------------------------------------------------------------#
# Special class for colormap names
#------------------------------------------------------------------------------#
class _CmapDict(dict):
    """
    Flexible colormap identification.
    """
    # Initialize -- converts keys to lower case and
    # ignores the 'reverse' maps
    def __init__(self, kwargs):
        kwargs_filtered = {}
        for key,value in kwargs.items():
            if not isinstance(key, str):
                raise KeyError(f'Invalid key {key}. Must be string.')
            if key[-2:] != '_r': # don't need to store these!
                kwargs_filtered[key.lower()] = value
        super().__init__(kwargs_filtered)

    # Helper functions
    def _sanitize_key(self, key):
        # Try retrieving
        if not isinstance(key, str):
            raise ValueError(f'Invalid key {key}. Must be string.')
        key = key.lower()
        reverse = False
        if key[-2:] == '_r':
            key = key[:-2]
            reverse = True
        if not super().__contains__(key):
            # Attempt to get 'mirror' key, maybe that's the one
            # stored in colormap dict
            key_mirror = key
            for mirror in _cmap_mirrors:
                try:
                    idx = mirror.index(key)
                    key_mirror = mirror[1 - idx]
                except ValueError:
                    continue
            if super().__contains__(key_mirror):
                reverse = (not reverse)
                key = key_mirror
        # Return 'sanitized' key. Not necessarily in dictionary! Error
        # will be raised further down the line if so.
        if reverse:
            key = key + '_r'
        return key

    def _getitem(self, key):
        # Call this to avoid sanitization
        reverse = False
        if key[-2:] == '_r':
            key = key[:-2]
            reverse = True
        value = super().__getitem__(key) # may raise keyerror
        if reverse:
            try:
                value = value.reversed()
            except AttributeError:
                raise KeyError(f'Dictionary value in {key} must have reversed() method.')
        return value

    # Indexing and 'in' behavior
    def __getitem__(self, key):
        # Assume lowercase
        key = self._sanitize_key(key)
        return self._getitem(key)

    def __setitem__(self, key, item):
        # Set item
        if not isinstance(key, str):
            raise KeyError(f'Invalid key {key}. Must be string.')
        return super().__setitem__(key.lower(), item)

    def __contains__(self, item):
        # Must be overriden?
        try:
            self.__getitem__(item)
            return True
        except KeyError:
            return False

    # Other methods
    def get(self, key, *args):
        # Get item
        if len(args)>1:
            raise ValueError(f'_CmapDict.get() accepts only 1-2 arguments (got {len(args)+1}).')
        try:
            if not isinstance(key, str):
                raise KeyError(f'Invalid key {key}. Must be string.')
            return self.__getitem__(key.lower())
        except KeyError as key_error:
            if args:
                return args[0]
            else:
                raise key_error

    def pop(self, key, *args):
        # Pop item
        if len(args)>1:
            raise ValueError(f'_CmapDict.pop() accepts only 1-2 arguments (got {len(args)+1}).')
        try:
            key = self._sanitize_key(key)
            value = self._getitem(key) # could raise error
            del self[key]
        except KeyError as key_error:
            if args:
                return args[0]
            else:
                raise key_error
        return value

# Override entire colormap dictionary
if not isinstance(mcm.cmap_d, _CmapDict):
    mcm.cmap_d = _CmapDict(mcm.cmap_d)

#------------------------------------------------------------------------------#
# More generalized utility for retrieving colors
#------------------------------------------------------------------------------#
def get_space(space):
    """
    Verify requested colorspace is valid.
    """
    space = _space_aliases.get(space, None)
    if space is None:
        raise ValueError(f'Unknown colorspace "{space}".')
    return space

def to_rgb(color, space='rgb'):
    """
    Generalization of mcolors.to_rgb to translate color tuple
    from any colorspace to rgb. Also will convert color strings to tuple.
    """
    # First the RGB input
    # NOTE: Need isinstance here because strings stored in numpy arrays
    # are actually subclasses thereof!
    if isinstance(color, str):
        try:
            color = mcolors.to_rgb(color) # ensure is valid color
        except Exception:
            raise ValueError(f'Invalid RGBA argument {color}. Registered colors are: {", ".join(mcolors._colors_full_map.keys())}.')
    elif space=='rgb':
        color = color[:3] # trim alpha
        if any(c>1 for c in color):
            color = [c/255 for c in color] # scale to within 0-1
    # Next the perceptually uniform versions
    elif space=='hsv':
        color = colormath.hsl_to_rgb(*color)
    elif space=='hpl':
        color = colormath.hpluv_to_rgb(*color)
    elif space=='hsl':
        color = colormath.hsluv_to_rgb(*color)
    elif space=='hcl':
        color = colormath.hcl_to_rgb(*color)
    elif space=='rgb':
        color = color[:3] # trim alpha
        if any(c>1 for c in color):
            color = [c/255 for c in color] # scale to within 0-1
    else:
        raise ValueError('Invalid RGB value.')
    return color

def to_xyz(color, space):
    """
    Inverse of above, translate to some colorspace.
    """
    # Run tuple conversions
    # NOTE: Don't pass color tuple, because we may want to permit out-of-bounds RGB values to invert conversion
    if isinstance(color, str):
        color = mcolors.to_rgb(color) # convert string
    else:
        color = color[:3]
    if space=='hsv':
        color = colormath.rgb_to_hsl(*color) # rgb_to_hsv would also work
    elif space=='hpl':
        color = colormath.rgb_to_hpluv(*color)
    elif space=='hsl':
        color = colormath.rgb_to_hsluv(*color)
    elif space=='hcl':
        color = colormath.rgb_to_hcl(*color)
    elif space=='rgb':
        color = color # do nothing
    else:
        raise ValueError(f'Invalid colorspace {space}.')
    return color

def add_alpha(color):
    """
    Ensures presence of alpha channel.
    """
    if not np.iterable(color) or isinstance(color, str):
        raise ValueError('Input must be color tuple.')
    if len(color)==3:
        color = [*color, 1.0]
    elif len(color)==4:
        color = [*color] # copy, and put into list
    else:
        raise ValueError(f'Tuple length must be 3 or 4, got {len(color)}.')
    return color

def get_channel_value(color, channel, space='hsl'):
    """
    Gets hue, saturation, or luminance channel value from registered
    string color name.

    Arguments
    ---------
        color :
            scalar numeric ranging from 0-1, or string color name, optionally
            with offset specified as '+x' or '-x' at the end of the string for
            arbitrary float x.
        channel :
            channel number or name (e.g., 0, 1, 2, 'h', 's', 'l')
    """
    # Interpret channel
    channel_idxs = {'hue': 0, 'saturation': 1, 'chroma': 1, 'luminance': 2,
                    'alpha': 3, 'h': 0, 's': 1, 'c': 1, 'l': 2}
    channel = channel_idxs.get(channel, channel)
    if callable(color) or isinstance(color, Number):
        return color
    if channel not in (0,1,2):
        raise ValueError('Channel must be in [0,1,2].')
    # Interpret string or RGB tuple
    offset = 0
    if isinstance(color, str):
        regex = '([-+]\S*)$' # user can optionally offset from color; don't filter to just numbers, want to raise our own error if user messes up
        match = re.search(regex, color)
        if match:
            try:
                offset = float(match.group(0))
            except ValueError:
                raise ValueError(f'Invalid channel identifier "{color}".')
            color = color[:match.start()]
    return offset + to_xyz(to_rgb(color, 'rgb'), space)[channel]

#------------------------------------------------------------------------------#
# Generalized colormap/cycle constructors
#------------------------------------------------------------------------------#
def colormap(*args, extend='both',
        left=None, right=None, x=None, # optionally truncate color range by these indices
        ratios=1, reverse=False,
        gamma=None, gamma1=None, gamma2=None,
        name=None, register=False, save=False, N=None, **kwargs):
    """
    Convenience function for generating colormaps in a variety of ways.
    The 'extend' property will be used to resample LinearSegmentedColormap
    if we don't intend to use both out-of-bounds colors; otherwise we lose
    the strongest colors at either end of the colormap.

    You can still use extend='neither' in colormap() call with extend='both'
    in contour or colorbar call, just means that colors at ends of the main
    region will be same as out-of-bounds colors.

    Notes on Resampling
    -------------------
    From answer: see https://stackoverflow.com/q/48613920/4970632
    This resampling method is awful! All it does is reduce the
    lookup table size -- what ends up happening under the hood is matplotlib
    tries to *evenly* draw N-1 ('min'/'max') or N-2 ('neither') colors from
    a lookup table with N colors, which means it simply *skips over* 1 or
    2 colors in the middle of the lookup table, which will cause visual jumps!

    Segment data is completely divorced from the number of levels; can
    have many high-res segments with colormap N very small.
    """
    # Turns out pcolormesh makes QuadMesh, which itself is a Collection,
    # which itself gets colors when calling draw() using update_scalarmappable(),
    # which itself uses to_rgba() to get facecolors, which itself is an inherited
    # ScalarMappable method that simply calls the colormap with numbers. Anyway
    # the issue *has* to be with pcolor, because when giving pcolor an actual
    # instance, no longer does that thing where final levels equal extensions.
    # Since collection API does nothing to underlying data or cmap, must be
    # something done by pcolormesh function.
    _N = N or _N_hires
    _cmaps = []
    name = name or 'custom' # must have name, mcolors utilities expect this
    if len(args)==0:
        args = [rcParams['image.cmap']] # use default
    for cmap in args:
        # Retrieve Colormap instance
        # Also make sure you reset the lookup table (get_cmap does this
        # by calling _resample).
        if cmap is None:
            cmap = rcParams['image.cmap']
        if isinstance(cmap,str) and cmap in mcm.cmap_d:
            cmap = mcm.cmap_d[cmap]
            if isinstance(cmap, mcolors.LinearSegmentedColormap):
                cmap = cmap._resample(_N)
        if isinstance(cmap, mcolors.Colormap):
            # Allow gamma override, otherwise do nothing
            if isinstance(cmap, PerceptuallyUniformColormap):
                if gamma and not gamma1 and not gamma2:
                    gamma1 = gamma2 = gamma
                if gamma1 or gamma2:
                    segmentdata = cmap._segmentdata.copy()
                    if gamma1:
                        segmentdata['gamma1'] = gamma1
                    if gamma2:
                        segmentdata['gamma2'] = gamma2
                    cmap = type(cmap)(cmap.name, segmentdata, space=cmap.space, mask=cmap.mask)
            elif isinstance(cmap, mcolors.LinearSegmentedColormap):
                if gamma:
                    cmap._gamma = gamma
                    cmap._init()
        elif isinstance(cmap, dict):
            # Dictionary of hue/sat/luminance values or 2-tuples representing linear transition
            save = cmap.pop('save', save)
            name = cmap.pop('name', name)
            for key in cmap:
                if key in kwargs:
                    print(f'Warning: Got duplicate keys "{key}" in cmap dictionary ({cmap[key]}) and in keyword args ({kwargs[key]}). Using first one.')
            kw = kwargs.update
            cmap = PerceptuallyUniformColormap.from_hsl(name, N=_N, **{**kwargs, **cmap})
        elif not isinstance(cmap, str):
            # List of colors
            cmap = mcolors.ListedColormap(cmap, name=name, **kwargs)
        else:
            # Monochrome colormap based from input color (i.e. single hue)
            regex = '([0-9].)$'
            match = re.search(regex, cmap) # declare maximum luminance with e.g. red90, blue70, etc.
            cmap = re.sub(regex, '', cmap) # remove options
            fade = kwargs.pop('fade',100) if not match else match.group(1) # default fade to 100 luminance
            # Build colormap
            cmap = to_rgb(cmap) # to ensure is hex code/registered color
            cmap = monochrome_cmap(cmap, fade, name=name, N=_N, **kwargs)
        _cmaps += [cmap]
    # Now merge the result of this arbitrary user input
    # Since we are merging cmaps, potentially *many* color transitions; use big number by default
    if len(_cmaps)>1:
        N_merge = _N*len(_cmaps)
        cmap = merge_cmaps(*_cmaps, name=name, ratios=ratios, N=N_merge)

    # Reverse
    if reverse:
        cmap = cmap.reversed()

    # Optionally clip edges or resample map.
    try:
        left, right = x
    except TypeError:
        pass
    if isinstance(cmap, mcolors.ListedColormap):
        slicer = None
        if left is not None or right is not None:
            slicer = slice(left,right)
        elif N is not None:
            slicer = slice(None,N)
        # Just sample indices for listed maps
        if slicer:
            slicer = slice(left,right)
            try:
                cmap = mcolors.ListedColormap(cmap.colors[slicer])
            except Exception:
                raise ValueError(f'Invalid indices {slicer} for listed colormap.')
    elif left is not None or right is not None:
        # Trickier for segment data maps
        # First get segmentdata and parse input
        kw = {}
        olddata = cmap._segmentdata
        newdata = {}
        if left is None:
            left = 0
        if right is None:
            right = 1
        if hasattr(cmap, 'space'):
            kw['space'] = cmap.space
        # Next resample the segmentdata arrays
        for key,xyy in olddata.items():
            if key in ('gamma1', 'gamma2'):
                newdata[key] = xyy
                continue
            xyy = np.array(xyy)
            x = xyy[:,0]
            xleft, = np.where(x>left)
            xright, = np.where(x<right)
            if len(xleft)==0:
                raise ValueError(f'Invalid x minimum {left}.')
            if len(xright)==0:
                raise ValueError(f'Invalid x maximum {right}.')
            l, r = xleft[0], xright[-1]
            newxyy = xyy[l:r+1,:].copy()
            if l>0:
                xl = xyy[l-1,1:] + (left - x[l-1])*(xyy[l,1:] - xyy[l-1,1:])/(x[l] - x[l-1])
                newxyy = np.concatenate(([[left, *xl]], newxyy), axis=0)
            if r<len(x)-1:
                xr = xyy[r,1:] + (right - x[r])*(xyy[r+1,1:] - xyy[r,1:])/(x[r+1] - x[r])
                newxyy = np.concatenate((newxyy, [[right, *xr]]), axis=0)
            newxyy[:,0] = (newxyy[:,0] - left)/(right - left)
            newdata[key] = newxyy
        # And finally rebuild map
        cmap = type(cmap)(cmap.name, newdata, **kw)

    if isinstance(cmap, mcolors.LinearSegmentedColormap) and N is not None:
        # Perform a crude resampling of the data, i.e. just generate a
        # low-resolution lookup table instead
        # NOTE: All this does is create a new colormap with *attribute* N levels,
        # for which '_lut' attribute has not been generated yet.
        offset = {'neither':-1, 'max':0, 'min':0, 'both':1}
        if extend not in offset:
            raise ValueError(f'Unknown extend option {extend}.')
        cmap = cmap._resample(N - offset[extend]) # see mcm.get_cmap source

    # Optionally register a colormap
    if name and register:
        if name.lower() in [cat_cmap.lower() for cat,cat_cmaps in _cmap_categories.items()
                    for cat_cmap in cat_cmaps if 'ProPlot' not in cat]:
            print(f'Warning: Overwriting existing colormap "{name}".')
            # raise ValueError(f'Builtin colormap "{name}" already exists. Choose a different name.')
        elif name in mcm.cmap_d:
            pass # no warning necessary
        mcm.cmap_d[name] = cmap
        mcm.cmap_d[name + '_r'] = cmap.reversed()
        if re.search('[A-Z]',name):
            mcm.cmap_d[name.lower()] = cmap
            mcm.cmap_d[name.lower() + '_r'] = cmap.reversed()
        print(f'Registered {name}.') # not necessary

    # Optionally save colormap to disk
    if name and save:
        # Save segment data directly
        basename = f'{cmap.name}.json'
        filename = f'{_data}/cmaps/{basename}'
        data = cmap._segmentdata.copy()
        data['space'] = cmap.space
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
        print(f'Saved colormap to "{basename}".')
    return cmap

def colors(*args, vmin=0, vmax=1, **kwargs):
    """
    Convenience function to draw colors from arbitrary ListedColormap or
    LinearSegmentedColormap.

    In the latter case, we will draw samples from that colormap by (default)
    drawing from Use vmin/vmax to scale your samples.
    """
    samples = 10
    # Two modes:
    # 1) User inputs some number of samples; 99% of time, use this
    # to get samples from a LinearSegmentedColormap
    # draw colors.
    if isinstance(args[-1], Number) or (np.iterable(args[-1]) and not isinstance(args[-1], str)):
        args, samples = args[:-1], args[-1]
    # 2) User inputs a simple list; 99% of time, use this
    # to build up a simple ListedColormap.
    elif len(args)>1:
        args = [args] # presumably send a list of colors
    cmap = colormap(*args, **kwargs) # the cmap object itself
    if isinstance(cmap, mcolors.ListedColormap):
        # Just get the colors
        colors = cmap.colors
    elif isinstance(cmap, mcolors.LinearSegmentedColormap): # or subclass
        # Employ ***more flexible*** version of get_cmap() method, which does this:
        # LinearSegmentedColormap(self.name, self._segmentdata, lutsize)
        if isinstance(samples, Number):
            # samples = np.linspace(0, 1-1/nsample, nsample) # from 'centers'
            samples = np.linspace(0, 1, samples) # from edge to edge
        elif np.iterable(samples):
            samples = np.array(samples)
        else:
            raise ValueError(f'Invalid samples "{samples}". If you are building '
            'a colormap on-the-fly, input must be [*args, samples] where *args '
            'are passed to the colormap() constructor and "samples" is either '
            'the number of samples desired or a vector of colormap samples within [0,1].')
        colors = cmap((samples-vmin)/(vmax-vmin))
    else:
        raise ValueError(f'Colormap returned weird object type: {type(cmap)}.')
    return colors

def cycle(*args, **kwargs):
    """
    Simple alias.
    """
    return colors(*args, **kwargs)

class PerceptuallyUniformColormap(mcolors.LinearSegmentedColormap):
    """
    Generate LinearSegmentedColormap in perceptually uniform colorspace --
    i.e. either HSLuv, HCL, or HPLuv. Adds handy feature where *channel
    value for string-name color is looked up*.

    Example
    -------
    dict(hue        = [[0, 'red', 'red'], [1, 'blue', 'blue']],
         saturation = [[0, 1, 1], [1, 1, 1]],
         luminance  = [[0, 1, 1], [1, 0.2, 0.2]])
    """
    def __init__(self, name, segmentdata,
            space='hsl', gamma=None, gamma1=None, gamma2=None,
            mask=False, **kwargs):
        """
        Initialize with dictionary of values. Note that hues should lie in
        range [0,360], saturation/luminance in range [0,100].

        Arguments
        ---------
            mask :
                Whether to mask out-of-range colors as black, or just clip
                the RGB values (distinct from colormap clipping the extremes).
            gamma1 :
                Raise the line used to transition from a low chroma value (x=0)
                to a higher chroma value (x=1) by this power, like HCLWizard.
            gamma2 :
                Raise the line used to transition from a high luminance value (x=0)
                to a lower luminance value (x=1) by this power, like HCLWizard.
        Why change the direction of transition depending on which value is
        bigger? Because makes it much easier to e.g. weight the center of
        a diverging colormap.
        """
        # Attributes
        # NOTE: Don't allow power scaling for hue because that would be weird.
        # Idea is want to allow skewing so dark/saturated colors are
        # more isolated/have greater intensity.
        # NOTE: We add gammas to the segmentdata dictionary so it can be
        # pickled into .npy file
        space = get_space(space)
        if 'gamma' in kwargs:
            raise ValueError('Standard gamma scaling disabled. Use gamma1 or gamma2 instead.')
        gamma1 = _default(gamma, gamma1)
        gamma2 = _default(gamma, gamma2)
        segmentdata['gamma1'] = _default(gamma1, _default(segmentdata.get('gamma1', None), 1.0))
        segmentdata['gamma2'] = _default(gamma2, _default(segmentdata.get('gamma2', None), 1.0))
        self.space = space
        self.mask  = mask
        # First sanitize the segmentdata by converting color strings to their
        # corresponding channel values
        keys   = {*segmentdata.keys()}
        target = {'hue', 'saturation', 'luminance', 'gamma1', 'gamma2'}
        if keys != target and keys != {*target, 'alpha'}:
            raise ValueError(f'Invalid segmentdata dictionary with keys {keys}.')
        for key,array in segmentdata.items():
            # Allow specification of channels using registered string color names
            if 'gamma' in key:
                continue
            if callable(array):
                continue
            for i,xyy in enumerate(array):
                xyy = list(xyy) # make copy!
                for j,y in enumerate(xyy[1:]): # modify the y values
                    xyy[j+1] = get_channel_value(y, key, space)
                segmentdata[key][i] = xyy
        # Initialize
        # NOTE: Our gamma1 and gamma2 scaling is just fancy per-channel
        # gamma scaling, so disable the standard version.
        super().__init__(name, segmentdata, gamma=1.0, **kwargs)

    def reversed(self, name=None):
        """
        Reverse colormap.
        """
        if name is None:
            name = self.name + '_r'
        def factory(dat):
            def func_r(x):
                return dat(1.0 - x)
            return func_r
        data_r = {}
        for key,xyy in self._segmentdata.items():
            if key in ('gamma1', 'gamma2', 'space'):
                if 'gamma' in key: # optional per-segment gamma
                    xyy = np.atleast_1d(xyy)[::-1]
                data_r[key] = xyy
                continue
            elif callable(xyy):
                data_r[key] = factory(xyy)
            else:
                data_r[key] = [[1.0 - x, y1, y0] for x, y0, y1 in reversed(xyy)]
        return PerceptuallyUniformColormap(name, data_r, space=self.space)

    def _init(self):
        """
        As with LinearSegmentedColormap, but convert each value
        in the lookup table from 'input' to RGB.
        """
        # First generate the lookup table
        channels = ('hue','saturation','luminance')
        reverse = (False, False, True) # gamma weights *low chroma* and *high luminance*
        gammas = (1.0, self._segmentdata['gamma1'], self._segmentdata['gamma2'])
        self._lut_hsl = np.ones((self.N+3, 4), float) # fill
        for i,(channel,gamma,reverse) in enumerate(zip(channels, gammas, reverse)):
            self._lut_hsl[:-3,i] = make_mapping_array(self.N, self._segmentdata[channel], channel, gamma, reverse)
        if 'alpha' in self._segmentdata:
            self._lut_hsl[:-3,3] = make_mapping_array(self.N, self._segmentdata['alpha'], 'alpha')
        self._lut_hsl[:-3,0] %= 360
        # self._lut_hsl[:-3,0] %= 359 # wrong
        # Make hues circular, set extremes (i.e. copy HSL values)
        self._lut = self._lut_hsl.copy() # preserve this, might want to check it out
        self._set_extremes() # generally just used end values in segmentdata
        self._isinit = True
        # Now convert values to RGBA, and clip colors
        for i in range(self.N+3):
            self._lut[i,:3] = to_rgb(self._lut[i,:3], self.space)
        self._lut[:,:3] = clip_colors(self._lut[:,:3], self.mask)

    def _resample(self, N):
        """
        Return a new color map with *N* entries.
        """
        self.N = N # that easy
        self._i_under = self.N
        self._i_over = self.N + 1
        self._i_bad = self.N + 2
        self._init()
        return self

    @staticmethod
    def from_hsl(name,
            # h=0, s=99, l=[99, 20], c=None, a=None,
            h=0, s=100, l=[100, 20], c=None, a=None,
            hue=None, saturation=None, luminance=None, chroma=None, alpha=None,
            ratios=None, reverse=False, **kwargs):
        """
        Make linear segmented colormap by specifying channel values.
        """
        # Build dictionary, easy peasy
        h = _default(hue, h)
        s = _default(chroma, _default(c, _default(saturation, s)))
        l = _default(luminance, l)
        a = _default(alpha, _default(a, 1.0))
        cs = ['hue', 'saturation', 'luminance', 'alpha']
        channels = [h, s, l, a]
        cdict = {}
        for c,channel in zip(cs,channels):
            cdict[c] = make_segmentdata_array(channel, ratios, reverse, **kwargs)
        cmap = PerceptuallyUniformColormap(name, cdict, **kwargs)
        return cmap

    @staticmethod
    def from_list(name, color_list,
            ratios=None, reverse=False,
            **kwargs):
        """
        Make linear segmented colormap from list of color tuples. The values
        in a tuple can be strings, in which case that corresponding color-name
        channel value is deduced.

        Optional
        --------
            ratios : simple way to specify x-coordinates for listed color
                transitions -- bigger number is slower transition, smaller
                number is faster transition.
            space : colorspace of hue-saturation-luminance style input
                color tuples.
        """
        # Dictionary
        cdict = {}
        channels = [*zip(*color_list)]
        if len(channels) not in (3,4):
            raise ValueError(f'Bad color list: {color_list}')
        cs = ['hue', 'saturation', 'luminance']
        if len(channels)==4:
            cs += ['alpha']
        else:
            cdict['alpha'] = 1.0 # dummy function that always returns 1.0
        # Build data arrays
        for c,channel in zip(cs,channels):
            cdict[c] = make_segmentdata_array(channel, ratios, reverse, **kwargs)
        cmap = PerceptuallyUniformColormap(name, cdict, **kwargs)
        return cmap

def make_segmentdata_array(values, ratios=None, reverse=False, **kwargs):
    """
    Construct a list of linear segments for an individual channel.
    This was made so that user can input e.g. a callable function for
    one channel, but request linear interpolation for another one.
    """
    # Handle function handles
    if callable(values):
        if reverse:
            values = lambda x: values(1-x)
        return values # just return the callable
    values = np.atleast_1d(values)
    if len(values)==1:
        value = values[0]
        return [(0, value, value), (1, value, value)] # just return a constant transition

    # Get x coordinates
    if not np.iterable(values):
        raise TypeError('Colors must be iterable.')
    if ratios is not None:
        xvals = np.atleast_1d(ratios) # could be ratios=1, i.e. dummy
        if len(xvals) != len(values) - 1:
            raise ValueError(f'Got {len(values)} values, but {len(ratios)} ratios.')
        xvals = np.concatenate(([0], np.cumsum(xvals)))
        xvals = xvals/np.max(xvals) # normalize to 0-1
    else:
        xvals = np.linspace(0,1,len(values))

    # Build vector
    array = []
    slicer = slice(None,None,-1) if reverse else slice(None)
    for x,value in zip(xvals,values[slicer]):
        array.append((x, value, value))
    return array

def make_mapping_array(N, data, channel, gamma=1.0, reverse=False):
    """
    Mostly a copy of matplotlib version, with a few modifications:
    * Disable clipping, allow the 0-360, 0-100, 0-100 HSL values.
    * Allow circular hue gradations along 0-360.
    * Allow weighting each transition by going from:
        c = c1 + x*(c2 - c1)
        for x in range [0-1], to
        c = c1 + (x**gamma)*(c2 - c1)
      When reverse==True, we use 1-(1-x)**gamma to use that gamma to
      weight toward *higher* channel values instead of lower channel values.
    """
    # Optionally allow for ***callable*** instead of linearly interpolating
    # between line segments
    gammas = np.atleast_1d(gamma)
    if (gammas < 0.01).any() or (gammas > 10).any():
        raise ValueError('Gamma can only be in range [0.01,10].')
    if callable(data):
        if len(gammas)>1:
            raise ValueError('Only one gamma allowed for functional segmentdata.')
        x = np.linspace(0, 1, N)**gamma
        lut = np.array(data(x), dtype=float)
        return lut

    # Get array
    try:
        data = np.array(data)
    except Exception:
        raise TypeError('Data must be convertible to an array.')
    shape = data.shape
    if len(shape) != 2 or shape[1] != 3:
        raise ValueError('Data must be nx3 format.')
    if len(gammas)!=1 and len(gammas)!=shape[0]-1:
        raise ValueError(f'Need {shape[0]-1} gammas for {shape[0]}-level mapping array, but got {len(gamma)}.')
    if len(gammas)==1:
        gammas = np.repeat(gammas, shape[:1])

    # Get indices
    x  = data[:, 0]
    y0 = data[:, 1]
    y1 = data[:, 2]
    if x[0] != 0.0 or x[-1] != 1.0:
        raise ValueError('Data mapping points must start with x=0 and end with x=1.')
    if (np.diff(x) < 0).any():
        raise ValueError('Data mapping points must have x in increasing order.')
    x = x*(N - 1)

    # Get distances from the segmentdata entry to the *left* for each requested
    # level, excluding ends at (0,1), which must exactly match segmentdata ends
    xq = (N - 1)*np.linspace(0, 1, N)
    ind = np.searchsorted(x, xq)[1:-1] # where xq[i] must be inserted so it is larger than x[ind[i]-1] but smaller than x[ind[i]]
    distance = (xq[1:-1] - x[ind - 1])/(x[ind] - x[ind - 1])
    # Scale distances in each segment by input gamma
    # The ui are starting-points, the ci are counts from that point
    # over which segment applies (i.e. where to apply the gamma)
    _, uind, cind = np.unique(ind, return_index=True, return_counts=True)
    for i,(ui,ci) in enumerate(zip(uind,cind)): # i will range from 0 to N-2
        # Test if 1
        gamma = gammas[ind[ui]-1] # the relevant segment is to *left* of this number
        if gamma==1:
            continue
        # By default, weight toward a *lower* channel value (i.e. bigger
        # exponent implies more colors at lower value)
        # Again, the relevant 'segment' is to the *left* of index returned by searchsorted
        ir = False
        if ci>1: # i.e. more than 1 color in this 'segment'
            ir = ((y0[ind[ui]] - y1[ind[ui]-1]) < 0) # by default want to weight toward a *lower* channel value
        if reverse:
            ir = (not ir)
        if ir:
            distance[ui:ui + ci] = 1 - (1 - distance[ui:ui + ci])**gamma
        else:
            distance[ui:ui + ci] **= gamma

    # Perform successive linear interpolations all rolled up into one equation
    lut = np.zeros((N,), float)
    lut[1:-1] = distance*(y0[ind] - y1[ind - 1]) + y1[ind - 1]
    lut[0]  = y1[0]
    lut[-1] = y0[-1]
    return lut

#------------------------------------------------------------------------------#
# Colormap constructors
#------------------------------------------------------------------------------#
def merge_cmaps(*_cmaps, name='merged', N=512, ratios=1, **kwargs):
    """
    Merge arbitrary colormaps.
    Arguments
    ---------
        _cmaps : 
            List of colormap strings or instances for merging.
        name :
            Name of output colormap.
        N :
            Number of lookup table colors desired for output colormap.
    Notes
    -----
    * Old method had us simply calling the colormap with arrays of fractions.
      This was sloppy, because it just samples locations on the lookup table and
      will therefore degrade the original, smooth, functional transitions.
    * Better method is to combine the _segmentdata arrays and simply scale
      the x coordinates in each (x,y1,y2) channel-tuple according to the ratios.
    * In the case of ListedColormaps, we just combine the colors.
    """
    # Initial
    if len(_cmaps)<=1:
        raise ValueError('Need two or more input cmaps.')
    ratios = ratios or 1
    if isinstance(ratios, Number):
        ratios = [1]*len(_cmaps)

    # Combine the colors
    _cmaps = [colormap(cmap, N=None, **kwargs) for cmap in _cmaps] # set N=None to disable resamping
    if all(isinstance(cmap, mcolors.ListedColormap) for cmap in _cmaps):
        if not np.all(ratios==1):
            raise ValueError(f'Cannot assign different ratios when mering ListedColormaps.')
        colors = [color for cmap in _cmaps for color in cmap.colors]
        cmap = mcolors.ListedColormap(colors, name=name, N=len(colors))

    # Accurate methods for cmaps with continuous/functional transitions
    elif all(isinstance(cmap,mcolors.LinearSegmentedColormap) for cmap in _cmaps):
        # Combine the actual segmentdata
        kinds = {type(cmap) for cmap in _cmaps}
        if len(kinds)>1:
            raise ValueError(f'Got mixed colormap types.')
        kind = kinds.pop() # colormap kind
        keys = {key for cmap in _cmaps for key in cmap._segmentdata.keys()}
        ratios = np.array(ratios)/np.sum(ratios) # so if 4 cmaps, will be 1/4
        x0 = np.concatenate([[0], np.cumsum(ratios)])
        xw = x0[1:] - x0[:-1]

        # Combine the segmentdata, and use the y1/y2 slots at merge points
        # so the transition is immediate (can never interpolate between end
        # colors on the two colormaps)
        segmentdata = {}
        for key in keys:
            # Combine scalar values
            if key in ('gamma1', 'gamma2'):
                if key not in segmentdata:
                    segmentdata[key] = []
                for cmap in _cmaps:
                    segmentdata[key] += [cmap._segmentdata[key]]
                continue
            # Combine xyy data
            datas = []
            test = [callable(cmap._segmentdata[key]) for cmap in _cmaps]
            if not all(test) and any(test):
                raise ValueError('Mixed callable and non-callable colormap values.')
            if all(test): # expand range from x-to-w to 0-1
                for x,w,cmap in zip(x0[:-1], xw, _cmaps):
                    data = lambda x: data((x - x0)/w) # WARNING: untested!
                    datas.append(data)
                def data(x):
                    idx, = np.where(x<x0)
                    if idx.size==0:
                        i = 0
                    elif idx.size==x0.size:
                        i = x0.size-2
                    else:
                        i = idx[-1]
                    return datas[i](x)
            else:
                for x,w,cmap in zip(x0[:-1], xw, _cmaps):
                    data = np.array(cmap._segmentdata[key])
                    data[:,0] = x + w*data[:,0]
                    datas.append(data)
                for i in range(len(datas)-1):
                    datas[i][-1,2] = datas[i+1][0,2]
                    datas[i+1] = datas[i+1][1:,:]
                data = np.concatenate(datas, axis=0)
                data[:,0] = data[:,0]/data[:,0].max(axis=0) # scale to make maximum exactly 1 (avoid floating point errors)
            segmentdata[key] = data

        # Create object
        kwargs = {}
        if kind is PerceptuallyUniformColormap:
            spaces = {cmap.space for cmap in _cmaps}
            if len(spaces)>1:
                raise ValueError(f'Trying to merge colormaps with different HSL spaces {repr(spaces)}.')
            kwargs.update({'space':spaces.pop()})
        cmap = kind(name, segmentdata, N=N, **kwargs)
    else:
        raise ValueError('All colormaps should be of the same type (Listed or LinearSegmented).')
    return cmap

def monochrome_cmap(color, fade, reverse=False, space='hsl', name='monochrome', **kwargs):
    """
    Make a sequential colormap that blends from color to near-white.
    Arguments
    ---------
        color :
            Build colormap by varying the luminance of some RGB color while
            keeping its saturation and hue constant.
    Optional
    --------
        reverse : (False)
            Optionally reverse colormap.
        space : ('hsl')
            Colorspace in which we vary luminance.
    """
    # Get colorspace
    space = get_space(space)
    h, s, l = to_xyz(to_rgb(color), space)
    if isinstance(fade, Number): # allow just specifying the luminance channel
        # fade = np.clip(fade, 0, 99)
        fade = np.clip(fade, 0, 100)
        fade = to_rgb((h, 0, fade), space=space)
    _, fs, fl = to_xyz(to_rgb(fade), space)
    fs = s # consider changing this?
    index = slice(None,None,-1) if reverse else slice(None)
    return PerceptuallyUniformColormap.from_hsl(name, h, [s,fs][index], [l,fl][index], space=space, **kwargs)

def clip_colors(colors, mask=True, gray=0.2, verbose=False):
    """
    Arguments
    ---------
        colors :
            List of length-3 RGB color tuples.
        mask : (bool)
            Whether to mask out (set to some dark gray color) or clip (limit
            range of each channel to [0,1]) out-of-range RGB channels.
    Notes
    -----
    Could use np.clip (matplotlib.colors uses this under the hood) but want
    to display messages, and anyway premature efficiency is the root of all
    evil, we're manipulating like 1000 colors max here, it's no big deal.
    """
    message = 'Invalid' if mask else 'Clipped'
    colors = np.array(colors) # easier
    under = (colors<0)
    over  = (colors>1)
    if mask:
        colors[(under | over)] = gray
    else:
        colors[under] = 0
        colors[over]  = 1
    if verbose:
        for i,name in enumerate('rgb'):
            if under[:,i].any():
                print(f'Warning: {message} "{name}" channel (<0).')
            if over[:,i].any():
                print(f'Warning: {message} "{name}" channel (>1).')
    return colors
    # return colors.tolist() # so it is *hashable*, can be cached (wrote this because had weird error, was unrelated)

#------------------------------------------------------------------------------#
# Cycle helper functions
#------------------------------------------------------------------------------#
def set_cycle(cmap, samples=None, rename=False):
    """
    Set the color cycler.
    Arguments
    ---------
        cmap :
            Name of colormap or colormap instance from which we draw list of colors.
        samples :
            Array of values from 0-1 or number indicating number of evenly spaced
            samples from 0-1 from which to draw colormap colors. Will be ignored
            if the colormap is a ListedColormap (interpolation not possible).
    """
    _colors = colors(cmap, samples)
    cyl = cycler('color', _colors)
    rcParams['axes.prop_cycle'] = cyl
    rcParams['patch.facecolor'] = _colors[0]
    if rename:
        rename_colors(cmap)

def rename_colors(cycle='colorblind'):
    """
    Calling this will change how shorthand codes like "b" or "g"
    are interpreted by matplotlib in subsequent plots.
    Arguments
    ---------
        cycle : {deep, muted, pastel, dark, bright, colorblind}
            Named seaborn palette to use as the source of colors.
    """
    seaborn_cycles = ['colorblind', 'deep', 'muted', 'bright']
    if cycle=='reset':
        colors = [(0.0, 0.0, 1.0), (0.0, .50, 0.0), (1.0, 0.0, 0.0), (.75, .75, 0.0),
                  (.75, .75, 0.0), (0.0, .75, .75), (0.0, 0.0, 0.0)]
    elif cycle in seaborn_cycles:
        colors = cycles[cycle] + [(0.1, 0.1, 0.1)]
    else:
        raise ValueError(f'Cannot set colors with color cycle {cycle}.')
    for code, color in zip('bgrmyck', colors):
        rgb = mcolors.colorConverter.to_rgb(color)
        mcolors.colorConverter.colors[code] = rgb
        mcolors.colorConverter.cache[code]  = rgb

#------------------------------------------------------------------------------#
# Return arbitrary normalizer
#------------------------------------------------------------------------------
def norm(norm_in, levels=None, values=None, norm=None, **kwargs):
    """
    Return arbitrary normalizer.
    """
    norm_preprocess = norm
    if isinstance(norm_in, mcolors.Normalize):
        return norm_in
    if levels is None and values is not None:
        levels = edges(values)
    if not norm_in: # is None
        # By default, make arbitrary monotonic user levels proceed linearly
        # through color space
        if levels is not None:
            norm_in = 'segments'
        # Fall back if no levels provided
        else:
            norm_in = 'linear'
    if isinstance(norm_in, str):
        # Get class
        if norm_in not in normalizers:
            raise ValueError(f'Unknown normalizer "{norm_in}". Options are {", ".join(normalizers.keys())}.')
        norm_out = normalizers[norm_in]
        # Instantiate class
        if norm_out is BinNorm:
            raise ValueError('This normalizer can only be used internally!')
        if norm_out is MidpointNorm:
            if not np.iterable(levels):
                raise ValueError(f'Need levels for normalizer "{norm_in}". Received levels={levels}.')
            kwargs.update({'vmin':min(levels), 'vmax':max(levels)})
        elif norm_out is LinearSegmentedNorm:
            if not np.iterable(levels):
                raise ValueError(f'Need levels for normalizer "{norm_in}". Received levels={levels}.')
            kwargs.update({'levels':levels, 'norm':norm_preprocess})
        norm_out = norm_out(**kwargs) # initialize
    else:
        raise ValueError(f'Unknown norm "{norm_out}".')
    return norm_out

#------------------------------------------------------------------------------
# Very important normalization class. Essentially there are two ways to create
# discretized color levels from a functional/segmented colormap:
#   1) Make lo-res lookup table.
#   2) Make hi-res lookup table, but discretize the lookup table indices
#      generated by your normalizer. This is what BoundaryNorm does.
# Have found the second method was easier to implement/more flexible. So the
# below is used to always discretize colors.
#------------------------------------------------------------------------------
# WARNING: Many methods in ColorBarBase tests for class membership, crucially
# including _process_values(), which if it doesn't detect BoundaryNorm will
# end up trying to infer boundaries from inverse() method. So make it parent class.
class BinNorm(mcolors.BoundaryNorm):
    """
    This is a rough copy of BoundaryNorm, but includes some extra features.
    *Discreteizes* the possible normalized values (numbers in 0-1) that are
    used to index a color on a high-resolution colormap lookup table. But
    includes features for 

    Note
    ----
    If you are using a diverging colormap with extend='max/min', the center
    will get messed up. But that is very strange usage anyway... so please
    just don't do that :)

    Todo
    ----
    Allow this to accept transforms too, which will help prevent level edges
    from being skewed toward left or right in case of logarithmic/exponential data.

    Example
    -------
    Your levels edges are weirdly spaced [-1000, 100, 0, 100, 1000] or
    even [0, 10, 12, 20, 22], but center "colors" are always at colormap
    coordinates [.2, .4, .6, .8] no matter the spacing; levels just must be monotonic.
    """
    def __init__(self, levels, norm=None, clip=False, step=1.0, extend='neither', **kwargs):
        # Declare boundaries, vmin, vmax in True coordinates. The step controls
        # intensity transition to out-of-bounds color; by default, the step is
        # equal to the *average* step between in-bounds colors (step == 1).
        # NOTE: Idea is that we bin data into len(levels) discrete x-coordinates,
        # and optionally make out-of-bounds colors the same or different
        # NOTE: Don't need to call parent __init__, this is own implementation
        # Do need it to subclass BoundaryNorm, so ColorbarBase will detect it
        # See BoundaryNorm: https://github.com/matplotlib/matplotlib/blob/master/lib/matplotlib/colors.py
        extend = extend or 'both'
        levels = np.atleast_1d(levels)
        if levels.size<=1:
            raise ValueError('Need at least two levels.')
        elif ((levels[1:]-levels[:-1])<=0).any():
            raise ValueError(f'Levels {levels} passed to Normalize() must be monotonically increasing.')
        if extend not in ('both','min','max','neither'):
            raise ValueError(f'Unknown extend option "{extend}". Choose from "min", "max", "both", "neither".')

        # Determine color ids for levels, i.e. position in 0-1 space
        # NOTE: If user used LinearSegmentedNorm for the normalizer (the
        # default) any monotonic levels will be even.
        # NOTE: Length of these ids should be N + 1 -- that is, N - 1 colors
        # for values in-between levels, plus 2 colors for out-of-bounds.
        #   * For same out-of-bounds colors, looks like [0, 0, ..., 1, 1]
        #   * For unique out-of-bounds colors, looks like [0, X, ..., 1 - X, 1]
        #     where the offset X equals step/len(levels).
        # First get coordinates
        norm = norm or (lambda x: x) # e.g. a logarithmic transform
        x_b = norm(levels)
        x_m = (x_b[1:] + x_b[:-1])/2 # get level centers after norm scaling
        y = (x_m - x_m.min())/(x_m.max() - x_m.min())
        # Account for out of bounds colors
        offset = 0
        scale = 1
        eps = step/levels.size
        if extend in ('min','both'):
            offset = eps
            scale -= eps
        if extend in ('max','both'):
            scale -= eps
        if isinstance(y, ma.core.MaskedArray):
            y = y.filled(np.nan)
        y = y[np.isfinite(y)]
        y = np.concatenate(([0], offset + scale*y, [1])) # insert '0' (arg 3) before index '0' (arg 2)
        self._norm = norm
        self._x_b = x_b
        self._y = y

        # Add builtin properties
        # NOTE: Are vmin/vmax even used?
        self.boundaries = levels
        self.vmin = levels.min()
        self.vmax = levels.max()
        self.clip = clip
        self.N = levels.size

    def __call__(self, xq, clip=None):
        # Follow example of LinearSegmentedNorm, but perform no interpolation,
        # just use searchsorted to bin the data.
        # NOTE: The bins vector includes out-of-bounds negative (searchsorted
        # index 0) and out-of-bounds positive (searchsorted index N+1) values
        xq = self._norm(np.atleast_1d(xq))
        yq = self._y[np.searchsorted(self._x_b, xq)] # which x-bin does each point in xq belong to?
        return ma.masked_array(yq, np.isnan(xq))

    def inverse(self, yq):
        # Not possible
        raise ValueError('BinNorm is not invertible.')

#------------------------------------------------------------------------------#
# Normalizers intended to *pre-scale* levels passed to BinNorm
#------------------------------------------------------------------------------#
class LinearSegmentedNorm(mcolors.Normalize):
    """
    Description
    -----------
    Linearly *interpolate* colors between the provided boundary levels.
    Exactly analagous to the method in LinearSegmentedColormap: perform
    linear interpolations between successive monotonic, but arbitrarily
    spaced, points. Then let this index control color intensity.
    """
    def __init__(self, levels, clip=False, **kwargs):
        # Test
        levels = np.atleast_1d(levels)
        if levels.size<=1:
            raise ValueError('Need at least two levels.')
        elif ((levels[1:]-levels[:-1])<=0).any():
            raise ValueError(f'Levels {levels} passed to LinearSegmentedNorm must be monotonically increasing.')
        super().__init__(np.nanmin(levels), np.nanmax(levels), clip) # second level superclass
        self._x = levels
        self._y = np.linspace(0, 1, len(levels))

    def __call__(self, xq, clip=None):
        # Follow example of make_mapping_array for efficient, vectorized
        # linear interpolation across multiple segments
        # NOTE: normal test puts values at a[i] if a[i-1] < v <= a[i]; for
        # left-most data, satisfy a[0] <= v <= a[1]
        # NOTE: searchsorted gives where xq[i] must be inserted so it is larger
        # than x[ind[i]-1] but smaller than x[ind[i]]
        x = self._x # from arbitrarily spaced monotonic levels
        y = self._y # to linear range 0-1
        xq = np.atleast_1d(xq)
        ind = np.searchsorted(x, xq)
        ind[ind==0] = 1
        ind[ind==len(x)] = len(x) - 1 # actually want to go to left of that
        distance = (xq - x[ind - 1])/(x[ind] - x[ind - 1])
        yq = distance*(y[ind] - y[ind - 1]) + y[ind - 1]
        return ma.masked_array(yq, np.isnan(xq))

    def inverse(self, yq):
        # Performs inverse operation of __call__
        x = self._x
        y = self._y
        yq = np.atleast_1d(yq)
        ind = np.searchsorted(y, yq)
        ind[ind==0] = 1
        ind[ind==len(y)] = len(y) - 1
        distance = (yq - y[ind - 1])/(y[ind] - y[ind - 1])
        xq = distance*(x[ind] - x[ind - 1]) + x[ind - 1]
        return ma.masked_array(xq, np.isnan(yq))

class MidpointNorm(mcolors.Normalize):
    """
    Simple normalizer that ensures a 'midpoint' always lies at the central
    colormap color. Normally used with diverging colormaps and midpoint=0.
    Inspired from this thread: https://stackoverflow.com/q/25500541/4970632
    """
    def __init__(self, midpoint=0, vmin=None, vmax=None, clip=None):
        # Bigger numbers are too one-sided
        super().__init__(vmin, vmax, clip)
        self._midpoint = midpoint

    def __call__(self, xq, clip=None):
        # Get middle point in 0-1 coords, and value
        # NOTE: Look up these three values in case vmin/vmax changed; this is
        # a more general normalizer than the others. Others are 'parent'
        # normalizers, meant to be static more or less.
        # NOTE: searchsorted gives where xq[i] must be inserted so it is larger
        # than x[ind[i]-1] but smaller than x[ind[i]]
        # x, y = [self.vmin, self._midpoint, self.vmax], [0, 0.5, 1]
        # return ma.masked_array(np.interp(xq, x, y))
        if self.vmin >= self._midpoint or self.vmax <= self._midpoint:
            raise ValueError(f'Midpoint {self._midpoint} outside of vmin {self.vmin} and vmax {self.vmax}.')
        x = np.array([self.vmin, self._midpoint, self.vmax])
        y = np.array([0, 0.5, 1])
        xq = np.atleast_1d(xq)
        ind = np.searchsorted(x, xq)
        ind[ind==0] = 1 # in this case will get normed value <0
        ind[ind==len(x)] = len(x) - 1 # in this case, will get normed value >0
        distance = (xq - x[ind - 1])/(x[ind] - x[ind - 1])
        yq = distance*(y[ind] - y[ind - 1]) + y[ind - 1]
        return ma.masked_array(yq, np.isnan(xq))

    def inverse(self, yq, clip=None):
        # Invert the above
        # x, y = [self.vmin, self._midpoint, self.vmax], [0, 0.5, 1]
        # return ma.masked_array(np.interp(yq, y, x))
        # Performs inverse operation of __call__
        x = np.array([self.vmin, self._midpoint, self.vmax])
        y = np.array([0, 0.5, 1])
        yq = np.atleast_1d(yq)
        ind = np.searchsorted(y, yq)
        ind[ind==0] = 1
        ind[ind==len(y)] = len(y) - 1
        distance = (yq - y[ind - 1])/(y[ind] - y[ind - 1])
        xq = distance*(x[ind] - x[ind - 1]) + x[ind - 1]
        return ma.masked_array(xq, np.isnan(yq))

#------------------------------------------------------------------------------#
# Register new colormaps; must come before registering the color cycles
# * If leave 'name' empty in register_cmap, name will be taken from the
#   Colormap instance. So do that.
# * Note that **calls to cmap instance do not interpolate values**; this is only
#   done by specifying levels in contourf call, specifying lut in get_cmap,
#   and using LinearSegmentedColormap.from_list with some N.
# * The cmap object itself only **picks colors closest to the "correct" one
#   in a "lookup table**; using lut in get_cmap interpolates lookup table.
#   See LinearSegmentedColormap doc: https://matplotlib.org/api/_as_gen/matplotlib.colors.LinearSegmentedColormap.html#matplotlib.colors.LinearSegmentedColormap
# * If you want to always disable interpolation, use ListedColormap. This type
#   of colormap instance will choose nearest-neighbors when using get_cmap, levels, etc.
#------------------------------------------------------------------------------#
def register_colors(nmax=np.inf, verbose=False):
    """
    Register new color names. Will only read first n of these
    colors, since XKCD library is massive (they should be sorted by popularity
    so later ones are no loss).

    Notes
    -----
    * The 'threshold' arg denotes how separated each channel of the HCL converted
        colors must be.
    * This seems like it would be slow, but takes on average 0.03 seconds on
        my macbook, so it's fine.
    """
    # First ***reset*** the colors dictionary
    # Why? We want to add XKCD colors *sorted by popularity* from file, along
    # with crayons dictionary; having registered colors named 'xkcd:color' is
    # annoying and not useful
    scale = (360, 100, 100)
    translate =  {'b': 'blue', 'g': 'green', 'r': 'red', 'c': 'cyan',
                  'm': 'magenta', 'y': 'yellow', 'k': 'black', 'w': 'white'}
    base1 = mcolors.BASE_COLORS # one-character names
    base2 = {translate[key]:value for key,value in base1.items()} # full names
    mcolors._colors_full_map.clear() # clean out!
    mcolors._colors_full_map.cache.clear() # clean out!
    mcolors._colors_full_map.update(base1)
    mcolors._colors_full_map.update(base2)

    # First register colors and get their HSL values
    names = []
    hcls = np.empty((0,3))
    for file in glob(f'{_data}/colors/*.txt'):
        # Read data
        category, _ = os.path.splitext(os.path.basename(file))
        data = np.genfromtxt(file, delimiter='\t', dtype=str, comments='%', usecols=(0,1)).tolist()
        ncolors = min(len(data),nmax-1)
        # Add categories
        colors_unfiltered[category] = {}
        colors_filtered[category] = {} # just initialize this one
        # Sanitize names and add to dictionary
        hcl = np.empty((ncolors,3))
        for i,(name,color) in enumerate(data): # is list of name, color tuples
            if i>=nmax: # e.g. for xkcd colors
                break
            hcl[i,:] = to_xyz(color, space=_distinct_colors_space)
            name = re.sub('/', ' ', name)
            name = re.sub("'s", '', name)
            name = re.sub('grey', 'gray', name)
            name = re.sub('pinky', 'pink', name)
            name = re.sub('greeny', 'green', name)
            names.append((category, name))
            colors_unfiltered[category][name] = color
        # Concatenate HCL arrays
        hcls = np.concatenate((hcls, hcl), axis=0)

    # Remove colors that are 'too similar' by rounding to the nearest n units
    # WARNING: unique axis argument requires numpy version >=1.13
    # WARNING: evidently it is ***impossible*** to actually delete colors
    # from the custom_colors dictionary (perhaps due to quirk of autoreload,
    # perhaps by some more fundamental python thing), so we instead must create
    # *completely separate* dictionary and add colors from there
    hcls = hcls/np.array(scale)
    hcls = np.round(hcls/_distinct_colors_threshold).astype(np.int64)
    _, index, counts = np.unique(hcls, return_index=True, return_counts=True, axis=0) # get unique rows
    deleted = 0
    counts = counts.sum()
    exceptions_regex = '^(' + '|'.join(_distinct_colors_exceptions) + ')[0-9]?$'

    # Add colors to filtered colors
    for i,(category,name) in enumerate(names):
        if not re.match(exceptions_regex, name) and i not in index:
            deleted += 1
        else:
            colors_filtered[category][name] = colors_unfiltered[category][name]
    for category,dictionary in colors_filtered.items():
        mcolors._colors_full_map.update(dictionary)
    if verbose:
        print(f'Started with {len(names)} colors, removed {deleted} insufficiently distinct colors.')

def register_cmaps():
    """
    Register colormaps and cycles in the cmaps directory.
    Note all of those methods simply modify the dictionary mcm.cmap_d.
    """
    # First read from file
    for filename in glob(f'{_data}/cmaps/*'):
        # Read table of RGB values
        if not re.search('\.(x?rgba?|json|xml)$', filename):
            continue
        name = os.path.basename(filename)
        name = name.split('.')[0]
        # if name in mcm.cmap_d: # don't want to re-register every time
        #     continue
        # Read .rgb, .rgba, .xrgb, and .xrgba files
        if re.search('\.x?rgba?$', filename):
            # Load
            ext = filename.split('.')[-1]
            try:
                cmap = np.loadtxt(filename, delimiter=',') # simple
            except:
                print(f'Failed to load {os.path.basename(filename)}.')
                continue
            # Build x-coordinates and standardize shape
            N = cmap.shape[0]
            if ext[0] != 'x':
                x = np.linspace(0, 1, N)
                cmap = np.concatenate((x[:,None], cmap), axis=1)
            if cmap.shape[1] not in (4,5):
                raise ValueError(f'Invalid number of columns for colormap "{name}": {cmap.shape[1]}.')
            if (cmap[:,1:4]>10).any(): # from 0-255 to 0-1
                cmap[:,1:4] = cmap[:,1:4]/255
            # Build color dict
            x = cmap[:,0]
            x = (x - x.min()) / (x.max() - x.min()) # for some reason, some aren't in 0-1 range
            if cmap.shape[1]==5:
                channels = ('red', 'green', 'blue', 'alpha')
            else:
                channels = ('red', 'green', 'blue')
            # Optional cycles
            if re.match('(cycle|qual)[0-9]', name.lower()):
                cmap = mcolors.ListedColormap(cmap[:,1:])
                cycles.add(name)
            else:
                cdict = {}
                for i,channel in enumerate(channels):
                    vector = cmap[:,i+1:i+2]
                    cdict[channel] = np.concatenate((x[:,None], vector, vector), axis=1).tolist()
                cmap = mcolors.LinearSegmentedColormap(name, cdict, N) # using static method is way easier
                cmaps.add(name)
        # Load XML files created with scivizcolor
        # Adapted from script found here: https://sciviscolor.org/matlab-matplotlib-pv44/
        elif re.search('\.xml$', filename):
            try:
                xmldoc = etree.parse(filename)
            except IOError:
                raise ValueError('The input file is invalid. It must be a colormap xml file. Go to https://sciviscolor.org/home/colormaps/ for some good options.')
            x = []
            colors = []
            for s in xmldoc.getroot().findall('.//Point'):
                x.append(float(s.attrib['x']))
                colors.append((float(s.attrib['r']), float(s.attrib['g']), float(s.attrib['b'])))
            N = len(x)
            x = np.array(x)
            x = (x - x.min()) / (x.max() - x.min()) # for some reason, some aren't in 0-1 range
            colors = np.array(colors)
            if re.match('(cycle|qual)[0-9]', name.lower()):
                cmap = mcolors.ListedColormap([to_rgb(color) for color in colors])
                cycles.add(name)
            else:
                cdict = {}
                for i,channel in enumerate(('red', 'green', 'blue')):
                    vector = colors[:,i:i+1]
                    cdict[channel] = np.concatenate((x[:,None], vector, vector), axis=1).tolist()
                cmap = mcolors.LinearSegmentedColormap(name, cdict, N) # using static method is way easier
                cmaps.add(name)
        # Directly read segmentdata of hex strings
        # Will ensure that HSL colormaps have the 'space' entry
        else:
            with open(filename, 'r') as file:
                segmentdata = json.load(file)
            if 'space' in segmentdata:
                space = segmentdata.pop('space')
                cmap = PerceptuallyUniformColormap(name, segmentdata, space=space, N=_N_hires)
            else:
                cmap = mcolors.LinearSegmentedColormap(name, segmentdata, N=_N_hires)
            cmaps.add(name)
        # Register maps (this is just what register_cmap does)
        # If the _r (reversed) version is stored on file, store the straightened one
        if re.search('_r$', name):
            name = name[:-2]
            cmap = cmap.reversed()
            cmap.name = name
        mcm.cmap_d[name] = cmap

    # Fix the builtin rainbow colormaps by switching from Listed to
    # LinearSegmented -- don't know why matplotlib shifts with these as
    # discrete maps by default, dumb.
    for name in _cmap_categories['Matplotlib Originals']: # initialize as empty lists
        cmap = mcm.cmap_d.get(name, None)
        if cmap and isinstance(cmap, mcolors.ListedColormap):
            mcm.cmap_d[name] = mcolors.LinearSegmentedColormap.from_list(name, cmap.colors)

    # Reverse some included colormaps, so colors
    # go from 'cold' to 'hot'
    for name in ('Spectral',):
        mcm.cmap_d[name] = mcm.cmap_d[name].reversed()

    # Add shifted versions of cyclic colormaps, and prevent same colors on ends
    # TODO: Add automatic shifting of colormap by N degrees in the _CmapDict
    for name in ['twilight', 'Phase']:
        cmap = mcm.cmap_d.get(name, None)
        if cmap and isinstance(cmap, mcolors.LinearSegmentedColormap):
            data = cmap._segmentdata
            data_shift = data.copy()
            for key,array in data.items():
                array = np.array(array)
                # Drop an end color
                array = array[1:,:]
                array_shift = array.copy()
                array_shift[:,0] -= 0.5
                array_shift[:,0] %= 1
                array_shift = array_shift[array_shift[:,0].argsort(),:]
                # Normalize x-range
                array[:,0] -= array[:,0].min()
                array[:,0] /= array[:,0].max()
                data[key] = array
                array_shift[:,0] -= array_shift[:,0].min()
                array_shift[:,0] /= array_shift[:,0].max()
                data_shift[key] = array_shift
            # Register shifted version and original
            mcm.cmap_d[name] = mcolors.LinearSegmentedColormap(name, data, cmap.N)
            mcm.cmap_d[name + '_shifted'] = mcolors.LinearSegmentedColormap(name + '_shifted', data_shift, cmap.N)

    # Delete ugly cmaps (strong-arm user into using the better ones)
    # TODO: Better way to generalize this language stuff? Not worth it maybe.
    greys = mcm.cmap_d.get('Greys', None)
    if greys is not None:
        mcm.cmap_d['Grays'] = greys
    # TODO: Add this to cmap dict __init__?
    for category in _cmap_categories_delete:
        for name in _cmap_categories:
            mcm.cmap_d.pop(name, None)

def register_cycles():
    """
    Register cycles defined right here by dictionaries.
    """
    # Read lists of hex strings from disk
    for filename in glob(f'{_data}/cmaps/*.hex'):
        name = os.path.basename(filename)
        name = name.split('.hex')[0]
        colors = [*open(filename)] # should just be a single line
        if len(colors)==0:
            continue # file is empty
        if len(colors)>1:
            raise ValueError('.hex color cycle files should contain only one line.')
        colors = colors[0].strip().split(',') # csv hex strings
        colors = [mcolors.to_rgb(c) for c in colors] # from list of tuples
        _cycles_loaded[name] = colors

    # Register names
    # Note that 'loaded' cycles will overwrite any presets with same name
    for name,colors in {**_cycles_preset, **_cycles_loaded}.items():
        mcm.cmap_d[name] = mcolors.ListedColormap([to_rgb(color) for color in colors])
        cycles.add(name)

    # Remove some redundant or ugly ones
    for key in ('tab10', 'tab20', 'Paired', 'Pastel1', 'Pastel2', 'Dark2'):
        mcm.cmap_d.pop(key, None)
    # *Change* the name of some more useful ones
    for (name1,name2) in [('Accent','Set1'), ('tab20b','Set4'), ('tab20c','Set5')]:
        mcm.cmap_d[name2] = mcm.cmap_d.pop(name1)
        cycles.add(name2)

# Register stuff when this module is imported
# The 'cycles' are simply listed colormaps, and the 'cmaps' are the smoothly
# varying LinearSegmentedColormap instances or subclasses thereof
cmaps = set() # track *downloaded* colormaps; user can then check this list
cycles = set() # track *all* color cycles
colors_filtered = {} # limit to 'sufficiently unique' color names
colors_unfiltered = {} # downloaded colors categorized by filename
register_colors() # must be done first, so we can register OpenColor cmaps
register_cmaps()
register_cycles()

# Finally our dictionary of normalizers
# Includes some custom classes, so has to go at end
# NOTE: Make BinNorm inaccessible to users. Idea is that all other normalizers
# can be wrapped by BinNorm -- BinNorm is just used to break colors into
# discrete levels.
normalizers = {
    'none':       mcolors.NoNorm,
    'null':       mcolors.NoNorm,
    'zero':       MidpointNorm,
    'midpoint':   MidpointNorm,
    'segments':   LinearSegmentedNorm,
    'segmented':  LinearSegmentedNorm,
    'boundary':   mcolors.BoundaryNorm,
    'log':        mcolors.LogNorm,
    'linear':     mcolors.Normalize,
    'power':      mcolors.PowerNorm,
    'symlog':     mcolors.SymLogNorm,
    }

