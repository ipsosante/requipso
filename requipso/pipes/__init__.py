"""pipes - Block-based pipeline system for health data queries.

This module provides a pipeline system with:
- Two-level block hierarchy: BaseBlock -> TableBlock, BaseBlock -> CombinedBlock
- Pydantic-based parameters
- Composition over inheritance (RegexProcessor)
- Clean separation of concerns

Example usage:
    from requipso.pipes import CombinedBlock
    from requipso.pipes.patient import Age, AgeParams, EstVivant
    from requipso.data import Data

    # Simple block
    age_block = Age()
    data = age_block.execute(data)

    # Combined block
    combined = CombinedBlock(
        blocks=[EstVivant(), age_block],
        operator="AND",
        name="VivantAvecAge"
    )
    data = combined.execute(data)
"""

# Base classes
from .base import (
    BaseBlock,
    BlockConfig,
    CombinedBlock,
    Negation,
    OutputType,
    TableBlock,
)

# Parameter classes
from .params import (
    BlockParams,
    CategoryParam,
    CombineOperatorParam,
    MultiStringParam,
    StringParam,
)
