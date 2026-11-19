Run this script on prod to get pathlogy codes
Then copy the resulting parquet file to your local machine

```python
import pandas as pd

from pathology_code_mapping.models import PathologyCode

codes = list(PathologyCode.objects.all().values())
codes_df = pd.DataFrame(codes)

codes_df.to_parquet("/tmp/mapping.parquet")
```