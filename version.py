"""Single source of truth for the application version.

Imported by the engine (`import version`) and the `ui` package
(`from version import __version__`); both use a guarded import with a literal
fallback so a missing/edited file never breaks startup.
"""

__app_name__ = "Instagram Reels Encoder"
__version__ = "2.1.0"
__tagline__ = "Cineon Film Emulation Edition"
