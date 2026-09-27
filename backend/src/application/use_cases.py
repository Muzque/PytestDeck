from domain.models import TestTree
from domain.services import build_tree_from_collectors
from infrastructure.discovery_service import PytestDiscoveryService


class DiscoverTestsUseCase:
    """Application use case coordinating test tree discovery for a project repository.

    Attributes:
        discovery_service: Service handling pytest process invocation.
    """

    def __init__(self, discovery_service: PytestDiscoveryService | None = None):
        """Initializes the DiscoverTestsUseCase instance.

        Args:
            discovery_service: Optional custom PytestDiscoveryService instance.
        """
        self.discovery_service = discovery_service or PytestDiscoveryService()

    async def execute(self, target_path: str, suite_rel_path: str = "") -> TestTree:
        """Executes test discovery on the specified repository path.

        Args:
            target_path: Absolute directory path of the target repository.
            suite_rel_path: Relative directory path of the target test suite.

        Returns:
            TestTree: Complete collected test tree domain object.
        """
        collectors, total_items = await self.discovery_service.collect_raw(target_path, suite_rel_path)
        tree_root = build_tree_from_collectors(collectors, suite_prefix=suite_rel_path)
        return TestTree(
            target_path=target_path,
            suite=suite_rel_path,
            total_nodes=total_items,
            root=tree_root,
        )
