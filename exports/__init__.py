from typing import Callable, Dict, Tuple, List, Any

# Contract: every export returns (sheet_name, headers, rows)
ExportResult = Tuple[str, List[str], List[List[Any]]]

# type of function that can generate export
ExportGenerator = Callable[[], ExportResult]