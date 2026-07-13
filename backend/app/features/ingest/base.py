import abc
from typing import Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.documents.models import Document

class BaseCollector(abc.ABC):
    """
    Abstract Base Class for all data collection plugins (collectors) in DataForge AI.
    """
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Return the unique name of this collector."""
        pass

    @abc.abstractmethod
    async def collect(self, db: AsyncSession, **kwargs: Any) -> List[Document]:
        """
        Run the collection process and return the list of collected and stored Document instances.
        """
        pass
