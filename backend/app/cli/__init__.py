"""Operator-only command line tools (design D8).

Nothing in this package is exposed over HTTP: clinic provisioning happens on the
operator's machine, never through a public endpoint.
"""

from __future__ import annotations
