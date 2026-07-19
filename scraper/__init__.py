"""
211info.org comprehensive scraper package.

The package is organized into layered acquisition, parsing, enrichment,
export, and orchestration subpackages. Legacy flat module paths remain
importable through lazy aliases for backward compatibility.
"""

from __future__ import annotations

import sys
from importlib import abc, import_module, util

from .config import Config
from .storage import Storage

__version__ = "1.0.0"

__all__ = [
    "AgenticCrawlerDaemon",
    "BrowserScraper",
    "Config",
    "CrawlItem",
    "CrawlState",
    "DataProcessor",
    "DuckDBCrawlStore",
    "FetchResult",
    "SelfHealingSupervisor",
    "StaticScraper",
    "Storage",
    "SupervisorConfig",
    "WebArchivingAdapter",
    "pattern_prefix_for_url",
    "score_queue_item",
]

_SYMBOL_ALIASES = {
    "AgenticCrawlerDaemon": ("scraper.orchestration.agentic_daemon", "AgenticCrawlerDaemon"),
    "BrowserScraper": ("scraper.acquisition.browser_scraper", "BrowserScraper"),
    "CrawlItem": ("scraper.orchestration.agentic_daemon", "CrawlItem"),
    "CrawlState": ("scraper.orchestration.agentic_daemon", "CrawlState"),
    "DataProcessor": ("scraper.parsing.processor", "DataProcessor"),
    "DuckDBCrawlStore": ("scraper.duckdb_state", "DuckDBCrawlStore"),
    "FetchResult": ("scraper.orchestration.agentic_daemon", "FetchResult"),
    "SelfHealingSupervisor": ("scraper.orchestration.supervisor", "SelfHealingSupervisor"),
    "StaticScraper": ("scraper.acquisition.static_scraper", "StaticScraper"),
    "SupervisorConfig": ("scraper.orchestration.supervisor", "SupervisorConfig"),
    "WebArchivingAdapter": ("scraper.orchestration.agentic_daemon", "WebArchivingAdapter"),
    "pattern_prefix_for_url": ("scraper.duckdb_state", "pattern_prefix_for_url"),
    "score_queue_item": ("scraper.duckdb_state", "score_queue_item"),
}

_LEGACY_MODULE_ALIASES = {
    "scraper.agentic_daemon": "scraper.orchestration.agentic_daemon",
    "scraper.archive_ingest": "scraper.acquisition.archive_ingest",
    "scraper.backfill_pattern_stats": "scraper.enrichment.backfill_pattern_stats",
    "scraper.backfill_warehouse": "scraper.enrichment.backfill_warehouse",
    "scraper.browser_graphrag_corpus": "scraper.export.browser_graphrag_corpus",
    "scraper.browser_scraper": "scraper.acquisition.browser_scraper",
    "scraper.build_retrieval_package": "scraper.export.build_retrieval_package",
    "scraper.build_service_portal_package": "scraper.export.build_service_portal_package",
    "scraper.duckdb_etl": "scraper.enrichment.duckdb_etl",
    "scraper.enrich_service_addresses": "scraper.enrichment.enrich_service_addresses",
    "scraper.export_canonical_services": "scraper.export.export_canonical_services",
    "scraper.main": "scraper.orchestration.main",
    "scraper.office_text_extraction": "scraper.parsing.office_text_extraction",
    "scraper.pdf_text_extraction": "scraper.parsing.pdf_text_extraction",
    "scraper.processor": "scraper.parsing.processor",
    "scraper.reextract_warehouse": "scraper.enrichment.reextract_warehouse",
    "scraper.retry_failed_pages": "scraper.enrichment.retry_failed_pages",
    "scraper.static_scraper": "scraper.acquisition.static_scraper",
    "scraper.supervisor": "scraper.orchestration.supervisor",
    "scraper.warc_etl": "scraper.acquisition.warc_etl",
}


def __getattr__(name: str):
    module_name, attr_name = _SYMBOL_ALIASES.get(name, (None, None))
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))


class _LegacyModuleAliasLoader(abc.Loader):
    def __init__(self, fullname: str, target_name: str) -> None:
        self.fullname = fullname
        self.target_name = target_name

    def create_module(self, spec):
        return None

    def get_filename(self, fullname: str) -> str:
        target_spec = util.find_spec(self.target_name)
        if target_spec is None or target_spec.origin is None:
            raise ImportError(f"Cannot resolve legacy scraper module target {self.target_name!r}")
        return target_spec.origin

    def get_code(self, fullname: str):
        source = (
            "from importlib import import_module as _import_module\n"
            f"_alias_name = __name__\n"
            f"_target = _import_module({self.target_name!r})\n"
            "globals().update(_target.__dict__)\n"
            "globals()['__name__'] = _alias_name\n"
            "globals()['__package__'] = _alias_name.rpartition('.')[0]\n"
            "if _alias_name == '__main__' and callable(getattr(_target, 'main', None)):\n"
            "    _target.main()\n"
        )
        return compile(source, self.get_filename(fullname), "exec")

    def exec_module(self, module) -> None:
        alias_spec = module.__spec__
        target_module = import_module(self.target_name)
        module.__dict__.update(target_module.__dict__)
        module.__name__ = self.fullname
        module.__package__ = self.fullname.rpartition(".")[0]
        module.__loader__ = self
        module.__spec__ = alias_spec
        module.__file__ = getattr(target_module, "__file__", None)
        module.__doc__ = getattr(target_module, "__doc__", None)
        if getattr(target_module, "__path__", None) is not None:
            module.__path__ = target_module.__path__


class _LegacyModuleAliasFinder(abc.MetaPathFinder):
    def find_spec(self, fullname: str, path=None, target=None):
        target_name = _LEGACY_MODULE_ALIASES.get(fullname)
        if target_name is None:
            return None
        target_spec = util.find_spec(target_name)
        if target_spec is None:
            return None
        return util.spec_from_loader(
            fullname,
            _LegacyModuleAliasLoader(fullname, target_name),
            origin=target_spec.origin,
            is_package=target_spec.submodule_search_locations is not None,
        )


if not any(isinstance(finder, _LegacyModuleAliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _LegacyModuleAliasFinder())
