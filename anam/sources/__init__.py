from .base import Source
from .github import GitHubSource
from .npm import NpmSource
from .rss import RssSource

__all__ = ["Source", "GitHubSource", "NpmSource", "RssSource", "build_sources"]


def build_sources(cfg: dict) -> list[Source]:
    sources: list[Source] = []
    if cfg.get("github", {}).get("enabled", True):
        sources.append(GitHubSource(cfg))
    if cfg.get("npm", {}).get("enabled", True):
        sources.append(NpmSource(cfg))
    if cfg.get("rss", {}).get("enabled", True):
        sources.append(RssSource(cfg))
    return sources
