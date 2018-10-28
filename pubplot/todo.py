"""
Tools for converting colors from one space to another.
"""
import numpy as np
import colorsys
from itertools import cycle
import numpy as np
import matplotlib as mpl
from .external import husl
from .utils import desaturate, set_hls_values, get_color_cycle
__all__ = ["color_palette", "hls_palette", "husl_palette", "mpl_palette",
           "dark_palette", "light_palette", "diverging_palette",
           "blend_palette", "xkcd_palette", "crayon_palette",
           "cubehelix_palette", "set_color_codes"]
SEABORN_PALETTES = dict(
    deep=["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3",
          "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD"],
    deep6=["#4C72B0", "#55A868", "#C44E52",
           "#8172B3", "#CCB974", "#64B5CD"],
    muted=["#4878D0", "#EE854A", "#6ACC64", "#D65F5F", "#956CB4",
           "#8C613C", "#DC7EC0", "#797979", "#D5BB67", "#82C6E2"],
    muted6=["#4878D0", "#6ACC64", "#D65F5F",
            "#956CB4", "#D5BB67", "#82C6E2"],
    pastel=["#A1C9F4", "#FFB482", "#8DE5A1", "#FF9F9B", "#D0BBFF",
            "#DEBB9B", "#FAB0E4", "#CFCFCF", "#FFFEA3", "#B9F2F0"],
    pastel6=["#A1C9F4", "#8DE5A1", "#FF9F9B",
             "#D0BBFF", "#FFFEA3", "#B9F2F0"],
    bright=["#023EFF", "#FF7C00", "#1AC938", "#E8000B", "#8B2BE2",
            "#9F4800", "#F14CC1", "#A3A3A3", "#FFC400", "#00D7FF"],
    bright6=["#023EFF", "#1AC938", "#E8000B",
             "#8B2BE2", "#FFC400", "#00D7FF"],
    dark=["#001C7F", "#B1400D", "#12711C", "#8C0800", "#591E71",
          "#592F0D", "#A23582", "#3C3C3C", "#B8850A", "#006374"],
    dark6=["#001C7F", "#12711C", "#8C0800",
           "#591E71", "#B8850A", "#006374"],
    colorblind=["#0173B2", "#DE8F05", "#029E73", "#D55E00", "#CC78BC",
                "#CA9161", "#FBAFE4", "#949494", "#ECE133", "#56B4E9"],
    colorblind6=["#0173B2", "#029E73", "#D55E00",
                 "#CC78BC", "#ECE133", "#56B4E9"]
    )
MPL_QUAL_PALS = {
    "tab10": 10, "tab20": 20, "tab20b": 20, "tab20c": 20,
    "Set1": 9, "Set2": 8, "Set3": 12,
    "Accent": 8, "Paired": 12,
    "Pastel1": 9, "Pastel2": 8, "Dark2": 8,
}
QUAL_PALETTE_SIZES = MPL_QUAL_PALS.copy()
QUAL_PALETTE_SIZES.update({k: len(v) for k, v in SEABORN_PALETTES.items()})

class _ColorPalette(list):
    """Set the color palette in a with statement, otherwise be a list."""
    def __enter__(self):
        """Open the context."""
        from .rcmod import set_palette
        self._orig_palette = color_palette()
        set_palette(self)
        return self
    def __exit__(self, *args):
        """Close the context."""
        from .rcmod import set_palette
        set_palette(self._orig_palette)
    def as_hex(self):
        """Return a color palette with hex codes instead of RGB values."""
        hex = [mpl.colors.rgb2hex(rgb) for rgb in self]
        return _ColorPalette(hex)

def color_palette(palette=None, n_colors=None, desat=None):
    """Return a list of colors defining a color palette.
    Available seaborn palette names:
        deep, muted, bright, pastel, dark, colorblind
    Other options:
        name of matplotlib cmap, 'ch:<cubehelix arguments>', 'hls', 'husl',
        or a list of colors in any format matplotlib accepts
    Calling this function with ``palette=None`` will return the current
    matplotlib color cycle.
    Matplotlib palettes can be specified as reversed palettes by appending
    "_r" to the name or as "dark" palettes by appending "_d" to the name.
    (These options are mutually exclusive, but the resulting list of colors
    can also be reversed).
    This function can also be used in a ``with`` statement to temporarily
    set the color cycle for a plot or set of plots.
    See the :ref:`tutorial <palette_tutorial>` for more information.
    Parameters
    ----------
    palette: None, string, or sequence, optional
        Name of palette or None to return current palette. If a sequence, input
        colors are used but possibly cycled and desaturated.
    n_colors : int, optional
        Number of colors in the palette. If ``None``, the default will depend
        on how ``palette`` is specified. Named palettes default to 6 colors,
        but grabbing the current palette or passing in a list of colors will
        not change the number of colors unless this is specified. Asking for
        more colors than exist in the palette will cause it to cycle.
    desat : float, optional
        Proportion to desaturate each color by.
    Returns
    -------
    palette : list of RGB tuples.
        Color palette. Behaves like a list, but can be used as a context
        manager and possesses an ``as_hex`` method to convert to hex color
        codes.
    See Also
    --------
    set_palette : Set the default color cycle for all plots.
    set_color_codes : Reassign color codes like ``"b"``, ``"g"``, etc. to
                      colors from one of the seaborn palettes.
    Examples
    --------
    Calling with no arguments returns all colors from the current default
    color cycle:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.color_palette())
    Show one of the other "seaborn palettes", which have the same basic order
    of hues as the default matplotlib color cycle but more attractive colors.
    Calling with the name of a palette will return 6 colors by default:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.color_palette("muted"))
    Use discrete values from one of the built-in matplotlib colormaps:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.color_palette("RdBu", n_colors=7))
    Make a customized cubehelix color palette:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.color_palette("ch:2.5,-.2,dark=.3"))
    Use a categorical matplotlib palette and add some desaturation:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.color_palette("Set1", n_colors=8, desat=.5))
    Make a "dark" matplotlib sequential palette variant. (This can be good
    when coloring multiple lines or points that correspond to an ordered
    variable, where you don't want the lightest lines to be invisible):
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.color_palette("Blues_d"))
    Use as a context manager:
    .. plot::
        :context: close-figs
        >>> import numpy as np, matplotlib.pyplot as plt
        >>> with sns.color_palette("husl", 8):
        ...    _ = plt.plot(np.c_[np.zeros(8), np.arange(8)].T)
    """
    if palette is None:
        palette = get_color_cycle()
        if n_colors is None:
            n_colors = len(palette)
    elif not isinstance(palette, str):
        palette = palette
        if n_colors is None:
            n_colors = len(palette)
    else:
        if n_colors is None:
            # Use all colors in a qualitative palette or 6 of another kind
            n_colors = QUAL_PALETTE_SIZES.get(palette, 6)
        if palette in SEABORN_PALETTES:
            # Named "seaborn variant" of old matplotlib default palette
            palette = SEABORN_PALETTES[palette]
        elif palette == "hls":
            # Evenly spaced colors in cylindrical RGB space
            palette = hls_palette(n_colors)
        elif palette == "husl":
            # Evenly spaced colors in cylindrical Lab space
            palette = husl_palette(n_colors)
        elif palette.startswith("ch:"):
            # Cubehelix palette with params specified in string
            args, kwargs = _parse_cubehelix_args(palette)
            palette = cubehelix_palette(n_colors, *args, **kwargs)
        else:
            try:
                # Perhaps a named matplotlib colormap?
                palette = mpl_palette(palette, n_colors)
            except ValueError:
                raise ValueError("%s is not a valid palette name" % palette)
    if desat is not None:
        palette = [desaturate(c, desat) for c in palette]
    # Always return as many colors as we asked for
    pal_cycle = cycle(palette)
    palette = [next(pal_cycle) for _ in range(n_colors)]
    # Always return in r, g, b tuple format
    try:
        palette = map(mpl.colors.colorConverter.to_rgb, palette)
        palette = _ColorPalette(palette)
    except ValueError:
        raise ValueError("Could not generate a palette for %s" % str(palette))
    return palette

def hls_palette(n_colors=6, h=.01, l=.6, s=.65):  # noqa
    """Get a set of evenly spaced colors in HLS hue space.
    h, l, and s should be between 0 and 1
    Parameters
    ----------
    n_colors : int
        number of colors in the palette
    h : float
        first hue
    l : float
        lightness
    s : float
        saturation
    Returns
    -------
    palette : seaborn color palette
        List-like object of colors as RGB tuples.
    See Also
    --------
    husl_palette : Make a palette using evently spaced circular hues in the
                   HUSL system.
    Examples
    --------
    Create a palette of 10 colors with the default parameters:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.hls_palette(10))
    Create a palette of 10 colors that begins at a different hue value:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.hls_palette(10, h=.5))
    Create a palette of 10 colors that are darker than the default:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.hls_palette(10, l=.4))
    Create a palette of 10 colors that are less saturated than the default:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.hls_palette(10, s=.4))
    """
    hues = np.linspace(0, 1, n_colors + 1)[:-1]
    hues += h
    hues %= 1
    hues -= hues.astype(int)
    palette = [colorsys.hls_to_rgb(h_i, l, s) for h_i in hues]
    return _ColorPalette(palette)

def husl_palette(n_colors=6, h=.01, s=.9, l=.65):  # noqa
    """Get a set of evenly spaced colors in HUSL hue space.
    h, s, and l should be between 0 and 1
    Parameters
    ----------
    n_colors : int
        number of colors in the palette
    h : float
        first hue
    s : float
        saturation
    l : float
        lightness
    Returns
    -------
    palette : seaborn color palette
        List-like object of colors as RGB tuples.
    See Also
    --------
    hls_palette : Make a palette using evently spaced circular hues in the
                  HSL system.
    Examples
    --------
    Create a palette of 10 colors with the default parameters:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.husl_palette(10))
    Create a palette of 10 colors that begins at a different hue value:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.husl_palette(10, h=.5))
    Create a palette of 10 colors that are darker than the default:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.husl_palette(10, l=.4))
    Create a palette of 10 colors that are less saturated than the default:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.husl_palette(10, s=.4))
    """
    hues = np.linspace(0, 1, n_colors + 1)[:-1]
    hues += h
    hues %= 1
    hues *= 359
    s *= 99
    l *= 99  # noqa
    palette = [husl.husl_to_rgb(h_i, s, l) for h_i in hues]
    return _ColorPalette(palette)

def mpl_palette(name, n_colors=6):
    """Return discrete colors from a matplotlib palette.
    Note that this handles the qualitative colorbrewer palettes
    properly, although if you ask for more colors than a particular
    qualitative palette can provide you will get fewer than you are
    expecting. In contrast, asking for qualitative color brewer palettes
    using :func:`color_palette` will return the expected number of colors,
    but they will cycle.
    If you are using the IPython notebook, you can also use the function
    :func:`choose_colorbrewer_palette` to interactively select palettes.
    Parameters
    ----------
    name : string
        Name of the palette. This should be a named matplotlib colormap.
    n_colors : int
        Number of discrete colors in the palette.
    Returns
    -------
    palette or cmap : seaborn color palette or matplotlib colormap
        List-like object of colors as RGB tuples, or colormap object that
        can map continuous values to colors, depending on the value of the
        ``as_cmap`` parameter.
    Examples
    --------
    Create a qualitative colorbrewer palette with 8 colors:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.mpl_palette("Set2", 8))
    Create a sequential colorbrewer palette:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.mpl_palette("Blues"))
    Create a diverging palette:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.mpl_palette("seismic", 8))
    Create a "dark" sequential palette:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.mpl_palette("GnBu_d"))
    """
    if name.endswith("_d"):
        pal = ["#333333"]
        pal.extend(color_palette(name.replace("_d", "_r"), 2))
        cmap = blend_palette(pal, n_colors, as_cmap=True)
    else:
        cmap = mpl.cm.get_cmap(name)
        if cmap is None:
            raise ValueError("{} is not a valid colormap".format(name))
    if name in MPL_QUAL_PALS:
        bins = np.linspace(0, 1, MPL_QUAL_PALS[name])[:n_colors]
    else:
        bins = np.linspace(0, 1, n_colors + 2)[1:-1]
    palette = list(map(tuple, cmap(bins)[:, :3]))
    return _ColorPalette(palette)

def color_to_rgb(color, input):
    """Add some more flexibility to color choices."""
    if input=='hls':
        color = colorsys.hls_to_rgb(*color)
    elif input=='husl':
        color = husl.husl_to_rgb(*color)
    return color

def dark_palette(color, n_colors=6, reverse=False, as_cmap=False, input="rgb"):
    """Make a sequential palette that blends from dark to ``color``.
    This kind of palette is good for data that range between relatively
    uninteresting low values and interesting high values.
    The ``color`` parameter can be specified in a number of ways, including
    all options for defining a color in matplotlib and several additional
    color spaces that are handled by seaborn. You can also use the database
    of named colors from the XKCD color survey.
    If you are using the IPython notebook, you can also choose this palette
    interactively with the :func:`choose_dark_palette` function.
    Parameters
    ----------
    color : base color for high values
        hex, rgb-tuple, or html color name
    n_colors : int, optional
        number of colors in the palette
    reverse : bool, optional
        if True, reverse the direction of the blend
    as_cmap : bool, optional
        if True, return as a matplotlib colormap instead of list
    input : {'rgb', 'hls', 'husl', xkcd'}
        Color space to interpret the input color. The first three options
        apply to tuple inputs and the latter applies to string inputs.
    Returns
    -------
    palette or cmap : seaborn color palette or matplotlib colormap
        List-like object of colors as RGB tuples, or colormap object that
        can map continuous values to colors, depending on the value of the
        ``as_cmap`` parameter.
    See Also
    --------
    light_palette : Create a sequential palette with bright low values.
    diverging_palette : Create a diverging palette with two colors.
    Examples
    --------
    Generate a palette from an HTML color:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.dark_palette("purple"))
    Generate a palette that decreases in lightness:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.dark_palette("seagreen", reverse=True))
    Generate a palette from an HUSL-space seed:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.dark_palette((260, 75, 60), input="husl"))
    Generate a colormap object:
    .. plot::
        :context: close-figs
        >>> from numpy import arange
        >>> x = arange(25).reshape(5, 5)
        >>> cmap = sns.dark_palette("#2ecc71", as_cmap=True)
        >>> ax = sns.heatmap(x, cmap=cmap)
    """
    color = color_to_rgb(color, input)
    gray = "#222222"
    colors = [color, gray] if reverse else [gray, color]
    return blend_palette(colors, n_colors, as_cmap)

def light_palette(color, n_colors=6, reverse=False, as_cmap=False,
                  input="rgb"):
    """Make a sequential palette that blends from light to ``color``.
    This kind of palette is good for data that range between relatively
    uninteresting low values and interesting high values.
    The ``color`` parameter can be specified in a number of ways, including
    all options for defining a color in matplotlib and several additional
    color spaces that are handled by seaborn. You can also use the database
    of named colors from the XKCD color survey.
    If you are using the IPython notebook, you can also choose this palette
    interactively with the :func:`choose_light_palette` function.
    Parameters
    ----------
    color : base color for high values
        hex code, html color name, or tuple in ``input`` space.
    n_colors : int, optional
        number of colors in the palette
    reverse : bool, optional
        if True, reverse the direction of the blend
    as_cmap : bool, optional
        if True, return as a matplotlib colormap instead of list
    input : {'rgb', 'hls', 'husl', xkcd'}
        Color space to interpret the input color. The first three options
        apply to tuple inputs and the latter applies to string inputs.
    Returns
    -------
    palette or cmap : seaborn color palette or matplotlib colormap
        List-like object of colors as RGB tuples, or colormap object that
        can map continuous values to colors, depending on the value of the
        ``as_cmap`` parameter.
    See Also
    --------
    dark_palette : Create a sequential palette with dark low values.
    diverging_palette : Create a diverging palette with two colors.
    Examples
    --------
    Generate a palette from an HTML color:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.light_palette("purple"))
    Generate a palette that increases in lightness:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.light_palette("seagreen", reverse=True))
    Generate a palette from an HUSL-space seed:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.light_palette((260, 75, 60), input="husl"))
    Generate a colormap object:
    .. plot::
        :context: close-figs
        >>> from numpy import arange
        >>> x = arange(25).reshape(5, 5)
        >>> cmap = sns.light_palette("#2ecc71", as_cmap=True)
        >>> ax = sns.heatmap(x, cmap=cmap)
    """
    color = color_to_rgb(color, input)
    light = set_hls_values(color, l=.95)  # noqa
    colors = [color, light] if reverse else [light, color]
    return blend_palette(colors, n_colors, as_cmap)

def _flat_palette(color, n_colors=6, reverse=False, as_cmap=False,
                  input="rgb"):
    """Make a sequential palette that blends from gray to ``color``.
    Parameters
    ----------
    color : matplotlib color
        hex, rgb-tuple, or html color name
    n_colors : int, optional
        number of colors in the palette
    reverse : bool, optional
        if True, reverse the direction of the blend
    as_cmap : bool, optional
        if True, return as a matplotlib colormap instead of list
    Returns
    -------
    palette : list or colormap
    dark_palette : Create a sequential palette with dark low values.
    """
    color = color_to_rgb(color, input)
    flat = desaturate(color, 0)
    colors = [color, flat] if reverse else [flat, color]
    return blend_palette(colors, n_colors, as_cmap)

def diverging_palette(h_neg, h_pos, s=75, l=50, sep=10, n=6,  # noqa
                      center="light", as_cmap=False):
    """Make a diverging palette between two HUSL colors.
    If you are using the IPython notebook, you can also choose this palette
    interactively with the :func:`choose_diverging_palette` function.
    Parameters
    ----------
    h_neg, h_pos : float in [0, 359]
        Anchor hues for negative and positive extents of the map.
    s : float in [0, 100], optional
        Anchor saturation for both extents of the map.
    l : float in [0, 100], optional
        Anchor lightness for both extents of the map.
    n : int, optional
        Number of colors in the palette (if not returning a cmap)
    center : {"light", "dark"}, optional
        Whether the center of the palette is light or dark
    as_cmap : bool, optional
        If true, return a matplotlib colormap object rather than a
        list of colors.
    Returns
    -------
    palette or cmap : seaborn color palette or matplotlib colormap
        List-like object of colors as RGB tuples, or colormap object that
        can map continuous values to colors, depending on the value of the
        ``as_cmap`` parameter.
    See Also
    --------
    dark_palette : Create a sequential palette with dark values.
    light_palette : Create a sequential palette with light values.
    Examples
    --------
    Generate a blue-white-red palette:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.diverging_palette(240, 10, n=9))
    Generate a brighter green-white-purple palette:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.diverging_palette(150, 275, s=80, l=55, n=9))
    Generate a blue-black-red palette:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.diverging_palette(250, 15, s=75, l=40,
        ...                                   n=9, center="dark"))
    Generate a colormap object:
    .. plot::
        :context: close-figs
        >>> from numpy import arange
        >>> x = arange(25).reshape(5, 5)
        >>> cmap = sns.diverging_palette(220, 20, sep=20, as_cmap=True)
        >>> ax = sns.heatmap(x, cmap=cmap)
    """
    palfunc = dark_palette if center == "dark" else light_palette
    neg = palfunc((h_neg, s, l), 128 - (sep / 2), reverse=True, input="husl")
    pos = palfunc((h_pos, s, l), 128 - (sep / 2), input="husl")
    midpoint = dict(light=[(.95, .95, .95, 1.)],
                    dark=[(.133, .133, .133, 1.)])[center]
    mid = midpoint * sep
    pal = blend_palette(np.concatenate([neg, mid,  pos]), n, as_cmap=as_cmap)
    return pal

def blend_palette(colors, n_colors=6, as_cmap=False, input="rgb"):
    """Make a palette that blends between a list of colors.
    Parameters
    ----------
    colors : sequence of colors in various formats interpreted by ``input``
        hex code, html color name, or tuple in ``input`` space.
    n_colors : int, optional
        Number of colors in the palette.
    as_cmap : bool, optional
        If True, return as a matplotlib colormap instead of list.
    Returns
    -------
    palette or cmap : seaborn color palette or matplotlib colormap
        List-like object of colors as RGB tuples, or colormap object that
        can map continuous values to colors, depending on the value of the
        ``as_cmap`` parameter.
    """
    colors = [color_to_rgb(color, input) for color in colors]
    name = "blend"
    pal = mpl.colors.LinearSegmentedColormap.from_list(name, colors)
    if not as_cmap:
        pal = _ColorPalette(pal(np.linspace(0, 1, n_colors)))
    return pal

def cubehelix_palette(n_colors=6, start=0, rot=.4, gamma=1.0, hue=0.8,
                      light=.85, dark=.15, reverse=False, as_cmap=False):
    """Make a sequential palette from the cubehelix system.
    This produces a colormap with linearly-decreasing (or increasing)
    brightness. That means that information will be preserved if printed to
    black and white or viewed by someone who is colorblind.  "cubehelix" is
    also available as a matplotlib-based palette, but this function gives the
    user more control over the look of the palette and has a different set of
    defaults.
    In addition to using this function, it is also possible to generate a
    cubehelix palette generally in seaborn using a string-shorthand; see the
    example below.
    Parameters
    ----------
    n_colors : int
        Number of colors in the palette.
    start : float, 0 <= start <= 3
        The hue at the start of the helix.
    rot : float
        Rotations around the hue wheel over the range of the palette.
    gamma : float 0 <= gamma
        Gamma factor to emphasize darker (gamma < 1) or lighter (gamma > 1)
        colors.
    hue : float, 0 <= hue <= 1
        Saturation of the colors.
    dark : float 0 <= dark <= 1
        Intensity of the darkest color in the palette.
    light : float 0 <= light <= 1
        Intensity of the lightest color in the palette.
    reverse : bool
        If True, the palette will go from dark to light.
    as_cmap : bool
        If True, return a matplotlib colormap instead of a list of colors.
    Returns
    -------
    palette or cmap : seaborn color palette or matplotlib colormap
        List-like object of colors as RGB tuples, or colormap object that
        can map continuous values to colors, depending on the value of the
        ``as_cmap`` parameter.
    See Also
    --------
    choose_cubehelix_palette : Launch an interactive widget to select cubehelix
                               palette parameters.
    dark_palette : Create a sequential palette with dark low values.
    light_palette : Create a sequential palette with bright low values.
    References
    ----------
    Green, D. A. (2011). "A colour scheme for the display of astronomical
    intensity images". Bulletin of the Astromical Society of India, Vol. 39,
    p. 289-295.
    Examples
    --------
    Generate the default palette:
    .. plot::
        :context: close-figs
        >>> import seaborn as sns; sns.set()
        >>> sns.palplot(sns.cubehelix_palette())
    Rotate backwards from the same starting location:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.cubehelix_palette(rot=-.4))
    Use a different starting point and shorter rotation:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.cubehelix_palette(start=2.8, rot=.1))
    Reverse the direction of the lightness ramp:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.cubehelix_palette(reverse=True))
    Generate a colormap object:
    .. plot::
        :context: close-figs
        >>> from numpy import arange
        >>> x = arange(25).reshape(5, 5)
        >>> cmap = sns.cubehelix_palette(as_cmap=True)
        >>> ax = sns.heatmap(x, cmap=cmap)
    Use the full lightness range:
    .. plot::
        :context: close-figs
        >>> cmap = sns.cubehelix_palette(dark=0, light=1, as_cmap=True)
        >>> ax = sns.heatmap(x, cmap=cmap)
    Use through the :func:`color_palette` interface:
    .. plot::
        :context: close-figs
        >>> sns.palplot(sns.color_palette("ch:2,r=.2,l=.6"))
    """
    def get_color_function(p0, p1):
        # Copied from matplotlib because it lives in private module
        def color(x):
            # Apply gamma factor to emphasise low or high intensity values
            xg = x ** gamma
            # Calculate amplitude and angle of deviation from the black
            # to white diagonal in the plane of constant
            # perceived intensity.
            a = hue * xg * (1 - xg) / 2
            phi = 2 * np.pi * (start / 3 + rot * x)
            return xg + a * (p0 * np.cos(phi) + p1 * np.sin(phi))
        return color
    cdict = {
            "red": get_color_function(-0.14861, 1.78277),
            "green": get_color_function(-0.29227, -0.90649),
            "blue": get_color_function(1.97294, 0.0),
    }
    cmap = mpl.colors.LinearSegmentedColormap("cubehelix", cdict)
    x = np.linspace(light, dark, n_colors)
    pal = cmap(x)[:, :3].tolist()
    if reverse:
        pal = pal[::-1]
    if as_cmap:
        x_256 = np.linspace(light, dark, 256)
        if reverse:
            x_256 = x_256[::-1]
        pal_256 = cmap(x_256)
        cmap = mpl.colors.ListedColormap(pal_256, "seaborn_cubehelix")
        return cmap
    else:
        return _ColorPalette(pal)

def _parse_cubehelix_args(argstr):
    """Turn stringified cubehelix params into args/kwargs."""
    if argstr.startswith("ch:"):
        argstr = argstr[3:]
    if argstr.endswith("_r"):
        reverse = True
        argstr = argstr[:-2]
    else:
        reverse = False
    if not argstr:
        return [], {"reverse": reverse}
    all_args = argstr.split(",")
    args = [float(a.strip(" ")) for a in all_args if "=" not in a]
    kwargs = [a.split("=") for a in all_args if "=" in a]
    kwargs = {k.strip(" "): float(v.strip(" ")) for k, v in kwargs}
    kwarg_map = dict(
        s="start", r="rot", g="gamma",
        h="hue", l="light", d="dark",  # noqa: E741
    )
    kwargs = {kwarg_map.get(k, k): v for k, v in kwargs.items()}
    if reverse:
        kwargs["reverse"] = True
    return args, kwargs

def set_color_codes(palette="deep"):
    if palette == "reset":
        colors = [(0., 0., 1.), (0., .5, 0.), (1., 0., 0.), (.75, .75, 0.),
                  (.75, .75, 0.), (0., .75, .75), (0., 0., 0.)]
    elif palette in SEABORN_PALETTES:
        if not palette.endswith("6"):
            palette = palette + "6"
        colors = SEABORN_PALETTES[palette] + [(.1, .1, .1)]
    else:
        err = "Cannot set colors with palette '{}'".format(palette)
        raise ValueError(err)
    for code, color in zip("bgrmyck", colors):
        rgb = mpl.colors.colorConverter.to_rgb(color)
        mpl.colors.colorConverter.colors[code] = rgb
        mpl.colors.colorConverter.cache[code] = rgb
