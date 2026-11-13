"""واجهة موحدة لأي مصدر جديد — أضف Adapter فقط وسيعمل مع باقي النظام."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Item


class Source(ABC):
    name = "base"

    @abstractmethod
    def collect(self, limit: int = 50) -> list[Item]:
        """اجمع العناصر الجديدة. يجب ألا يرمي استثناءً — أعد [] عند الفشل."""
        raise NotImplementedError
