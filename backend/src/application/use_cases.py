from domain.models import TestTree
from domain.services import build_tree_from_collectors
from infrastructure.discovery_service import PytestDiscoveryService


class DiscoverTestsUseCase:
    """Application use case to coordinate test tree discovery."""

    def __init__(self, discovery_service: PytestDiscoveryService | None = None):
        self.discovery_service = discovery_service or PytestDiscoveryService()

    async def execute(self, target_path: str, suite_rel_path: str = "") -> TestTree:
        collectors, total_items = await self.discovery_service.collect_raw(target_path, suite_rel_path)
        tree_root = build_tree_from_collectors(collectors, suite_prefix=suite_rel_path)
        return TestTree(
            target_path=target_path,
            suite=suite_rel_path,
            total_nodes=total_items,
            root=tree_root,
        )
