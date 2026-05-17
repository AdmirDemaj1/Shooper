from crawler.sources.base import SourceAdapter
from crawler.sources.gjirafa import GjirafaAdapter
from crawler.sources.merrjep import MerrjepAdapter
from crawler.sources.mobile_al import MobileAlAdapter
from crawler.sources.njoftime import NjoftimeAdapter


def get_adapter(source_name: str) -> SourceAdapter:
    source_name = source_name.strip().lower()
    adapters: dict[str, SourceAdapter] = {
        "merrjep": MerrjepAdapter(),
        "mobile_al": MobileAlAdapter(),
        "gjirafa": GjirafaAdapter(),
        "njoftime": NjoftimeAdapter(),
    }
    if source_name not in adapters:
        raise ValueError(f"Unknown source: {source_name!r}. Known: {list(adapters)}")
    return adapters[source_name]
