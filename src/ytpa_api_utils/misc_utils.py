from typing import Generator

import pandas as pd


def df_gen_from_queue(q) -> Generator[pd.DataFrame, None, None]:
    """DataFrame generator that pulls from a queue."""
    while 1:
        df = q.get()
        if df is None:
            return
        yield df
